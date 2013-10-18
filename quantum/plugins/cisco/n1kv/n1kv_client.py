# vim: tabstop=4 shiftwidth=4 softtabstop=4

# Copyright 2013 Cisco Systems, Inc.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.
#
# @author: Abhishek Raut, Cisco Systems, Inc.
# @author: Rudrajit Tapadar, Cisco Systems, Inc.

import base64
import httplib2
import netaddr

from quantum.common import exceptions as q_exc
from quantum.extensions import providernet
from quantum.openstack.common import log as logging
from quantum.plugins.cisco.common import cisco_constants as c_const
from quantum.plugins.cisco.common import cisco_credentials_v2 as c_cred
from quantum.plugins.cisco.common import cisco_exceptions as c_exc
from quantum.plugins.cisco.db import network_db_v2
from quantum.plugins.cisco.extensions import n1kv_profile
from quantum.wsgi import Serializer

LOG = logging.getLogger(__name__)


class Client(object):

    """
    Client for the Cisco Nexus1000V Quantum Plugin

    This client implements functions to communicate with
    Cisco Nexus1000V VSM.

    For every Quantum objects Cisco Nexus1000V Quantum Plugin
    creates a corresponding object in the controller (Cisco
    Nexus1000V VSM).

    CONCEPTS:

    Following are few concepts used in Nexus1000V VSM:

    port-profiles:
    Policy profiles correspond to port profiles on Nexus1000V VSM.
    Port profiles are the primary mechanism by which network policy is
    defined and applied to switch interfaces in a Nexus 1000V system.

    network-segment:
    Each network-segment represents a broadcast domain.

    network-segment-pool:
    A network-segment-pool contains one or more network-segments.

    logical-network:
    A logical-network contains one or more network-segment-pools.

    bridge-domain:
    A bridge-domain is created when the network-segment is of type VXLAN.
    Each VXLAN <--> VLAN combination can be thought of as a bridge domain.

    ip-pool:
    Each ip-pool represents a subnet on the Nexus1000V VSM.

    vm-network:
    vm-network refers to a network-segment and policy-profile.
    It maintains a list of ports that uses the network-segment and
    policy-profile this vm-network refers to.


    WORK FLOW:

    For every network profile a corresponding logical-network and
    a network-segment-pool, under this logical-network, will be created.

    For every network created from a given network profile, a
    network-segment will be added to the network-segment-pool corresponding
    to that network profile.

    A port is created on a network and associated with a policy-profile.
    Hence for every unique combination of a network and a policy-profile, a
    unique vm-network will be created and a reference to the port will be
    added. If the same combination of network and policy-profile is used by
    another port, the refernce to that port will be added to the same
    vm-network.


    """

    # Metadata for deserializing xml
    _serialization_metadata = {
        "application/xml": {
            "attributes": {
                "network": ["id", "name"],
                "port": ["id", "mac_address"],
                "subnet": ["id", "prefix"]
            },
        },
        "plurals": {
            "networks": "network",
            "ports": "port",
            "set": "instance",
            "subnets": "subnet",
            "mappings": "mapping",
            "segments": "segment"
        }
    }

    # Define paths for the URI where the client connects for HTTP requests.
    port_profiles_path = "/virtual-port-profile"
    network_segments_path = "/network-segment"
    network_segment_path = "/network-segment/%s"
    network_segment_trunk_path = "/network-segment/%s"
    network_segment_pools_path = "/network-segment-pool"
    network_segment_pool_path = "/network-segment-pool/%s"
    ip_pools_path = "/ip-pool-template"
    ip_pool_path = "/ip-pool-template/%s"
    ports_path = "/kvm/vm-network/%s/ports"
    port_path = "/kvm/vm-network/%s/ports/%s"
    vm_networks_path = "/kvm/vm-network"
    vm_network_path = "/kvm/vm-network/%s"
    bridge_domains_path = "/kvm/bridge-domain"
    bridge_domain_path = "/kvm/bridge-domain/%s"
    logical_networks_path = "/logical-network"
    logical_network_path = "/logical-network/%s"
    clusters_path = "/cluster"
    encap_profiles_path = "/encapsulation-profile"
    encap_profile_path = "/encapsulation-profile/%s"

    def __init__(self, **kwargs):
        """Initialize a new client for the plugin."""
        self.format = 'json'
        self.hosts = self._get_vsm_hosts()
        self.action_prefix = 'http://%s/api/n1k' % self.hosts[0]
        self.timeout = 15
        self.request_number = 0

    def list_port_profiles(self):
        """
        Fetch all policy profiles from the VSM.

        :returns: XML string
        """
        return self._get(self.port_profiles_path)

    def create_bridge_domain(self, network, vxlan_subtype):
        """
        Create a bridge domain on VSM.

        :param network: network dict
        """
        body = {'name': network['id'] + c_const.BRIDGE_DOMAIN_SUFFIX,
                'tenantId': network['tenant_id'],
                'segmentId': network[providernet.SEGMENTATION_ID],
                'subType': vxlan_subtype}
        if vxlan_subtype == c_const.TYPE_VXLAN_MULTICAST:
            body['groupIp'] = network[n1kv_profile.MULTICAST_IP]
        return self._post(self.bridge_domains_path,
                          body=body)

    def delete_bridge_domain(self, name):
        """
        Delete a bridge domain on VSM

        :param name: name of the bridge domain to be deleted
        """
        return self._delete(self.bridge_domain_path % (name))

    def create_network_segment(self, network, network_profile):
        """
        Create a network segment on the VSM

        :param network: network dict
        :param network_profile: network profile dict
        """
        LOG.debug(_("seg id %s"), network_profile['name'])
        body = {'publishName': network['name'],
                'description': network['name'],
                'id': network['id'],
                'tenantId': network['tenant_id'],
                'networkSegmentPool': network_profile['id'], }
        if network[providernet.NETWORK_TYPE] == c_const.NETWORK_TYPE_VLAN:
            body['vlan'] = network[providernet.SEGMENTATION_ID]
        elif network[providernet.NETWORK_TYPE] == c_const.NETWORK_TYPE_VXLAN:
            body['bridgeDomain'] = network['id'] + '_bd'
        if network_profile['segment_type'] == c_const.NETWORK_TYPE_TRUNK:
            body['mode'] = c_const.NETWORK_TYPE_TRUNK
            body['segmentType'] = network_profile['sub_type']
            if network_profile['sub_type'] == c_const.NETWORK_TYPE_VLAN:
                body['addSegments'] = network['add_segment_list']
                body['delSegments'] = network['del_segment_list']
            else:
                body['encapProfile'] = (network['id'] +
                                        c_const.ENCAPSULATION_PROFILE_SUFFIX)
        else:
            body['mode'] = 'access'
            body['segmentType'] = network_profile['segment_type']
        return self._post(self.network_segment_path % (network['id']),
                          body=body)

    def update_network_segment(self, network_segment_id, body):
        """
        Update a network segment on the VSM

        Network segment on VSM can be updated to associate it with an ip-pool
        or update its description and segment id.

        :param network_segment_id: UUID of the network segment
        :param body: dict of arguments to be updated
        """
        return self._post(self.network_segment_path % (network_segment_id),
                          body=body)

    def delete_network_segment(self, network_segment_id):
        """
        Delete a network segment on the VSM

        :param network_segment_name: name of the network segment
        """
        return self._delete(self.network_segment_path % (network_segment_id))

    def create_logical_network(self, network_profile, tenant_id):
        """
        Create a logical network on the VSM

        :param network_profile: network profile dict
        :param tenant_id: UUID representing the tenant
        """
        LOG.debug(_("logical network"))
        body = {'description': network_profile['name'],
                'tenantId': tenant_id}
        logical_network_name = network_profile['id'] + "_log_net"
        return self._post(self.logical_network_path % (logical_network_name),
                          body=body)

    def delete_logical_network(self, logical_network_name):
        """ Delete a logical network on VSM."""
        return self._delete(self.logical_network_path %
                            (logical_network_name))

    def create_network_segment_pool(self, network_profile, tenant_id):
        """
        Create a network segment pool on the VSM

        :param network_profile: network profile dict
        :param tenant_id: UUID representing the tenant
        """
        LOG.debug(_("network_segment_pool"))
        logical_network_name = network_profile['id'] + "_log_net"
        body = {'name': network_profile['name'],
                'description': network_profile['name'],
                'id': network_profile['id'],
                'logicalNetwork': logical_network_name,
                'tenantId': tenant_id}
        return self._post(self.network_segment_pool_path % (network_profile['id']),
                          body=body)

    def update_network_segment_pool(self, network_profile):
        """
        Update a Network Segment Pool on the VSM

        :param network_profile: network profile dict
        """
        body = {'name': network_profile['name'],
                'description': network_profile['name']}
        return self._post(self.network_segment_pool_path %
                          (network_profile['id']), body=body)

    def delete_network_segment_pool(self, network_segment_pool_id):
        """
        Delete a network segment pool on the VSM

        :param network_segment_pool_id: UUID representing the network segment pool
        """
        return self._delete(self.network_segment_pool_path %
                            (network_segment_pool_id))

    def create_ip_pool(self, subnet):
        """
        Create an ip-pool on the VSM

        :param subnet: subnet dict
        """
        if subnet['cidr']:
            try:
                ip = netaddr.IPNetwork(subnet['cidr'])
                netmask = str(ip.netmask)
                network_address = str(ip.network)
            except netaddr.AddrFormatError:
                msg = _("Invalid input for CIDR")
                raise q_exc.InvalidInput(error_message=msg)
        else:
            netmask = network_address = ""

        if subnet['allocation_pools']:
            address_range_start = subnet['allocation_pools'][0]['start']
            address_range_end = subnet['allocation_pools'][0]['end']
        else:
            address_range_start = None
            address_range_end = None

        body = {'addressRangeStart': address_range_start,
                'addressRangeEnd': address_range_end,
                'ipAddressSubnet': netmask,
                'description': subnet['name'],
                'gateway': subnet['gateway_ip'],
                'networkAddress': network_address,
                'netSegmentName': subnet['network_id'],
                'dhcp': subnet['enable_dhcp'],
                'dnsServersList': subnet['dns_nameservers'],
                'id': subnet['id'],
                'tenantId': subnet['tenant_id']}
        return self._post(self.ip_pool_path % (subnet['id']),
                          body=body)

    def update_ip_pool(self, subnet):
        """
        Update an ip-pool on the VSM

        :param subnet: subnet dict
        """
        if subnet['cidr']:
            try:
                ip = netaddr.IPNetwork(subnet['cidr'])
                netmask = str(ip.netmask)
                network_address = str(ip.network)
            except netaddr.AddrFormatError:
                msg = _("Invalid input for CIDR")
                raise q_exc.InvalidInput(error_message=msg)
        else:
            netmask = network_address = ""

        if subnet['allocation_pools']:
            address_range_start = subnet['allocation_pools'][0]['start']
            address_range_end = subnet['allocation_pools'][0]['end']
        else:
            address_range_start = None
            address_range_end = None

        body = {'addressRangeStart': address_range_start,
                'addressRangeEnd': address_range_end,
                'ipAddressSubnet': netmask,
                'description': subnet['name'],
                'gateway': subnet['gateway_ip'],
                'networkAddress': network_address,
                'netSegmentName': subnet['network_id'],
                'dhcp': subnet['enable_dhcp'],
                'dnsServersList': subnet['dns_nameservers'],
                'id': subnet['id'],
                'tenantId': subnet['tenant_id']}
        return self._post(self.ip_pool_path % (subnet['id']),
                          body=body)

    def delete_ip_pool(self, subnet_id):
        """
        Delete an ip-pool on the VSM

        :param subnet_id: UUID of the subnet
        """
        return self._delete(self.ip_pool_path % (subnet_id))

    def create_vm_network(self,
                          port,
                          vm_network_name,
                          policy_profile):
        """
        Create a VM network on the VSM

        :param port: port dict
        :param vm_network_name: name of the VM network
        :param policy_profile: policy profile dict
        """
        body = {'name': vm_network_name,
                'tenantId': port['tenant_id'],
                'networkSegmentId': port['network_id'],
                'networkSegment': port['network_id'],
                'portProfile': policy_profile['name'],
                'portProfileId': policy_profile['id'],
                'portId': port['id'],
                'macAddress': port['mac_address'],
                }
        return self._post(self.vm_networks_path,
                          body=body)

    def delete_vm_network(self, vm_network_name):
        """
        Delete a VM network on the VSM

        :param vm_network_name: name of the VM network
        """
        return self._delete(self.vm_network_path % (vm_network_name))

    def create_n1kv_port(self, port, vm_network_name):
        """
        Create a port on the VSM

        :param port: port dict
        :param vm_network_name: name of the VM network which imports this port
        """
        body = {'id': port['id'],
                'macAddress': port['mac_address']}
        return self._post(self.ports_path % (vm_network_name),
                          body=body)

    def update_n1kv_port(self, vm_network_name, port_id, body):
        """
        Update a port on the VSM

        Update the mac address associated with the port

        :param vm_network_name: name of the VM network which imports this port
        :param port_id: UUID of the port
        :param body: dict of the arguments to be updated
        """
        return self._post(self.port_path % ((vm_network_name), (port_id)),
                          body=body)

    def delete_n1kv_port(self, vm_network_name, port_id):
        """
        Delete a port on the VSM

        :param vm_network_name: name of the VM network which imports this port
        :param port_id: UUID of the port
        """
        return self._delete(self.port_path % ((vm_network_name), (port_id)))

    def _do_request(self, method, action, body=None,
                    headers=None):
        """
        Perform the HTTP request

        The response is in either XML format or plain text. A GET method will
        invoke a XML response while a PUT/POST/DELETE returns message from the
        VSM in plain text format.
        Exception is raised when VSM replies with an INTERNAL SERVER ERROR HTTP
        status code (500) i.e. an error has occurred on the VSM or SERVICE
        UNAVAILABLE (503) i.e. VSM is not reachable.

        :param method: type of the HTTP request. POST, GET, PUT or DELETE
        :param action: path to which the client makes request
        :param body: dict for arguments which are sent as part of the request
        :param headers: header for the HTTP request
        :returns: XML or plain text in HTTP response
        """
        action = self.action_prefix + action
        if not headers and self.hosts:
            headers = self._get_auth_header(self.hosts[0])
        headers['Content-Type'] = self._set_content_type('json')
        headers['cache-control'] = 'no-cache'
        headers['Connection'] = 'close'
        if body:
            body = self._serialize(body)
            LOG.debug(_("req: %s"), body)
        try:
            h = httplib2.Http(timeout=self.timeout)
            resp, replybody = (h.request(action, method, body=body,
                                         headers=headers))
            h.connections.clear()
        except Exception as e:
            raise c_exc.VSMConnectionFailed(reason=e)
        LOG.debug(_("status_code %s"), resp.status)
        if resp.status == 200:
            if 'application/xml' in resp['content-type']:
                return self._deserialize(replybody, resp.status)
            elif 'text/plain' in resp['content-type']:
                LOG.debug(_("VSM: %s"), replybody)
        else:
            raise c_exc.VSMError(reason=replybody)

    def _serialize(self, data):
        """
        Serialize a dictionary with a single key into either xml or json

        :param data: data in the form of dict
        """
        if data is None:
            return None
        elif type(data) is dict:
            return Serializer().serialize(data, self._set_content_type())
        else:
            raise Exception("unable to serialize object of type = '%s'" %
                            type(data))

    def _deserialize(self, data, status_code):
        """
        Deserialize an XML string into a dictionary

        :param data: XML string from the HTTP response
        :param status_code: integer status code from the HTTP response
        :return: data in the form of dict
        """
        if status_code == 204:
            return data
        return Serializer(self._serialization_metadata).deserialize(
            data, self._set_content_type('xml'))

    def _set_content_type(self, format=None):
        """
        Set the mime-type to either 'xml' or 'json'.

        :param format: format to be set.
        :return: mime-type string
        """
        if not format:
            format = self.format
        return "application/%s" % (format)

    def _delete(self, action, body=None, headers=None):
        return self._do_request("DELETE", action, body=body,
                                headers=headers)

    def _get(self, action, body=None, headers=None):
        return self._do_request("GET", action, body=body,
                                headers=headers)

    def _post(self, action, body=None, headers=None):
        return self._do_request("POST", action, body=body,
                                headers=headers)

    def _put(self, action, body=None, headers=None):
        return self._do_request("PUT", action, body=body,
                                headers=headers)

    def _get_vsm_hosts(self):
        """
        Retrieve a list of VSM ip addresses.

        :return: list of host ip addresses.
        """
        return [cr[c_const.CREDENTIAL_NAME] for cr in
                network_db_v2.get_all_n1kv_credentials()]

    def _get_auth_header(self, host_ip):
        """
        Retreive header with auth info for the VSM

        :param host_ip: IP address of the VSM
        :return: authorization header dict
        """
        username = c_cred.Store.get_username(host_ip)
        password = c_cred.Store.get_password(host_ip)
        auth = base64.encodestring("%s:%s" % (username, password))
        header = {"Authorization": "Basic %s" % auth}
        return header

    def get_clusters(self):
        """Fetches a list of all vxlan gateway clusters."""
        return self._get(self.clusters_path)

    def create_encapsulation_profile(self, encap):
        """
        Create an encapsulation profile on VSM.

        :param encap: encapsulation dict
        """
        body = {'name': encap['name'],
                'addMappings': encap['add_segment_list'],
                'delMappings': encap['del_segment_list']}
        return self._post(self.encap_profiles_path,
                          body=body)

    def update_encapsulation_profile(self, context, profile_name, body):
        """
        Adds a vlan to bridge-domain mapping to an encapsulation profile.

        :param profile_name: Name of the encapsulation profile
        :param body: mapping dictionary
        """
        return self._post(self.encap_profile_path
                          % (profile_name), body=body)

    def delete_encapsulation_profile(self, name):
        """
        Delete an encapsulation profile on VSM.

        :param name: name of the encapsulation profile to be deleted
        """
        return self._delete(self.encap_profile_path % (name))

# Copyright 2014 OpenStack Foundation
# All rights reserved.
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

import sqlalchemy.orm.exc as sa_exc

from neutron import context as ncontext
import neutron.db.api as db
from neutron.db import models_v2
from neutron.plugins.common import constants as p_const
from neutron.plugins.ml2.drivers.cisco.n1kv import exceptions as n1kv_exc
from neutron.plugins.ml2.drivers.cisco.n1kv import n1kv_models


def add_network_binding(network_id,
                        network_type,
                        segment_id,
                        netp_id,
                        db_session=None):
    """
    Create the network to network profile binding.

    :param db_session: database session
    :param network_id: UUID representing the network
    :param network_type: string representing type of network (VLAN, VXLAN)
    :param segment_id: integer representing VLAN or VXLAN ID
    :param netp_id: network profile ID based on which this network
                    is created
    """
    db_session = db_session or db.get_session()
    binding = n1kv_models.N1kvNetworkBinding(network_id=network_id,
                                             network_type=network_type,
                                             segmentation_id=segment_id,
                                             profile_id=netp_id)
    db_session.add(binding)
    db_session.flush()
    return binding


def get_network_profile_by_type(segment_type, db_session=None):
    """Retrieve a network profile using its type."""
    db_session = db_session or db.get_session()
    try:
        return (db_session.query(n1kv_models.NetworkProfile).
                filter_by(segment_type=segment_type).one())
    except sa_exc.NoResultFound:
        raise n1kv_exc.NetworkProfileNotFound(profile=segment_type)


def add_network_profile(netp_name, netp_type, db_session=None):
    """Create a network profile."""
    db_session = db_session or db.get_session()
    netp = n1kv_models.NetworkProfile(name=netp_name,
                                      segment_type=netp_type)
    db_session.add(netp)
    db_session.flush()
    return netp


def remove_network_profile(netp_id, db_session=None):
    """Delete a network profile."""
    db_session = db_session or db.get_session()
    nprofile = (db_session.query(n1kv_models.NetworkProfile).
                filter_by(id=netp_id).first())
    if nprofile:
        db_session.delete(nprofile)
        db_session.flush()


def get_policy_profile_by_name(name, db_session=None):
    """Retrieve policy profile by name."""
    db_session = db_session or db.get_session()
    policy_profile = (db_session.query(n1kv_models.PolicyProfile).
                      filter_by(name=name).first())
    if policy_profile:
        return policy_profile
    else:
        raise n1kv_exc.PolicyProfileNotFound(profile=id)


def get_policy_profile_by_uuid(db_session, id):
    """Retrieve policy profile by its UUID."""
    policy_profile = (db_session.query(n1kv_models.PolicyProfile).
                      filter_by(id=id).first())
    if policy_profile:
        return policy_profile
    else:
        raise n1kv_exc.PolicyProfileNotFound(profile=id)


def get_policy_profiles_by_host(vsm_ip, db_session=None):
    """Retrieve policy profile by host."""
    db_session = db_session or db.get_session()
    try:
        return (db_session.query(n1kv_models.PolicyProfile).
                filter_by(vsm_ip=vsm_ip))
    except sa_exc.NoResultFound:
        raise n1kv_exc.PolicyProfileNotFound(profile=vsm_ip)


def policy_profile_in_use(profile_id):
    """
    Checks if a policy profile is being used in a port binding.

    :param segment_id: UUID of the policy profile to be checked
    :returns: boolean
    """
    db_session = db.get_session()
    ret = (db_session.query(n1kv_models.N1kvPortBinding).
           filter_by(profile_id=profile_id).first())
    return bool(ret)


def get_network_binding(network_id):
    """Retrieve network binding."""
    db_session = db.get_session()
    try:
        return (db_session.query(n1kv_models.N1kvNetworkBinding).
                filter_by(network_id=network_id).one())
    except sa_exc.NoResultFound:
        raise n1kv_exc.NetworkBindingNotFound(network_id=network_id)


def add_policy_binding(port_id, pprofile_id, db_session=None):
    """Create the port to policy profile binding."""
    db_session = db_session or db.get_session()
    binding = n1kv_models.N1kvPortBinding(port_id=port_id,
                                          profile_id=pprofile_id)
    db_session.add(binding)
    db_session.flush()
    return binding


def get_policy_binding(port_id, db_session=None):
    """Retrieve port to policy profile binding."""
    db_session = db_session or db.get_session()
    try:
        return (db_session.query(n1kv_models.N1kvPortBinding).
                filter_by(port_id=port_id).one())
    except sa_exc.NoResultFound:
        raise n1kv_exc.PortBindingNotFound(port_id=port_id)


def get_network_profiles(db_base_plugin=None):
    '''
    Get details for all network profiles from N1kv table of the neutron db.

    :return: List of network profile objects
    '''
    db_session = db.get_session()
    np_objects = db_session.query(n1kv_models.NetworkProfile).all()
    return np_objects


def get_networks(db_base_plugin):
    '''
    Get details for all networks, from non-N1kv tables of the neutron database.

    :param db_base_plugin: Instance of the NeutronDbPluginV2 class

    :return: List of network dictionaries
    '''
    context = ncontext.get_admin_context()
    nets = db_base_plugin.get_networks(context)
    return nets


def get_subnets(db_base_plugin):
    '''
    Get details for all subnets, from non-N1kv tables of the neutron database

    :param db_base_plugin: Instance of the NeutronDbPluginV2 class

    :return: List of subnet dictionaries
    '''
    context = ncontext.get_admin_context()
    subnets = db_base_plugin.get_subnets(context)
    return subnets


def get_ports(db_base_plugin):
    '''
    Get details for all ports, from non-N1kv tables of the neutron database

    :param db_base_plugin:  Instance of the NeutronDbPluginV2 class

    :return: List of port dictionaries
    '''
    context = ncontext.get_admin_context()
    ports = db_base_plugin.get_ports(context)
    return ports


def get_network_profile_by_network(network_id):
    '''
    Given a network, get all the details of its network profile

    :param network_id: UUID of the network

    :return: Network profile object
    '''
    db_session = db.get_session()
    network_profile_local = (db_session.query(n1kv_models.N1kvNetworkBinding).
                             filter_by(network_id=network_id).one())
    network_profile_global = (db_session.query(n1kv_models.NetworkProfile).
                              filter_by(id=network_profile_local.
                                        profile_id).one())
    return network_profile_global


def get_vxlan_networks():
    '''
    Get all VxLAN networks.

    :return: A list of all VxLAN networks
    '''
    db_session = db.get_session()
    network_binding_rows = db_session.query(
        models_v2.Network, n1kv_models.N1kvNetworkBinding).filter(
            models_v2.Network.id ==
            n1kv_models.N1kvNetworkBinding.network_id).filter(
                n1kv_models.N1kvNetworkBinding.network_type ==
                p_const.TYPE_VXLAN).all()
    return [network for (network, binding) in network_binding_rows]

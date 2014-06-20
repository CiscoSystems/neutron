# Copyright (c) 2014 Cisco Systems
# All Rights Reserved.
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
# @author: Henry Gessau, Cisco Systems

import mock

from neutron.common import constants as n_constants
from neutron.plugins.ml2.drivers.cisco.apic import mechanism_apic as md
from neutron.plugins.ml2.drivers import type_vlan  # noqa
from neutron.tests import base
from neutron.tests.unit.ml2.drivers.cisco.apic import (
    test_cisco_apic_common as mocked)


HOST_ID1 = 'ubuntu'
HOST_ID2 = 'rhel'
ENCAP = '101'

SUBNET_GATEWAY = '10.3.2.1'
SUBNET_CIDR = '10.3.1.0/24'
SUBNET_NETMASK = '24'

TEST_SEGMENT1 = 'test-segment1'
TEST_SEGMENT2 = 'test-segment2'


class TestCiscoApicMechDriver(base.BaseTestCase,
                              mocked.ControllerMixin,
                              mocked.ConfigMixin,
                              mocked.DbModelMixin):

    def setUp(self):
        super(TestCiscoApicMechDriver, self).setUp()
        mocked.ControllerMixin.set_up_mocks(self)
        mocked.ConfigMixin.set_up_mocks(self)
        mocked.DbModelMixin.set_up_mocks(self)

        self.mock_apic_manager_login_responses()
        self.driver = md.APICMechanismDriver()
        self.driver.vif_type = 'test-vif_type'
        self.driver.cap_port_filter = 'test-cap_port_filter'
        self.driver.name_mapper = mock.Mock()
        self.driver.name_mapper.tenant.return_value = mocked.APIC_TENANT
        self.driver.name_mapper.network.return_value = mocked.APIC_NETWORK
        self.driver.name_mapper.subnet.return_value = mocked.APIC_SUBNET
        self.driver.name_mapper.port.return_value = mocked.APIC_PORT
        self.driver.apic_manager = mock.Mock(
            name_mapper=mock.Mock(), ext_net_dict=self.external_network_dict)

        self.addCleanup(mock.patch.stopall)

    def test_initialize(self):
        mock.patch('neutron.plugins.ml2.drivers.cisco.apic.apic_manager.'
                   'APICManager.ensure_infra_created_on_apic').start()
        mock.patch('neutron.plugins.ml2.drivers.cisco.apic.apic_manager.'
                   'APICManager.ensure_bgp_pod_policy_created_on_apic').start()
        self.driver.initialize()
        self.session = self.driver.apic_manager.apic.session
        self.assert_responses_drained()

    def test_update_port_postcommit(self):
        net_ctx = self._get_network_context(mocked.APIC_TENANT,
                                            mocked.APIC_NETWORK,
                                            TEST_SEGMENT1)
        port_ctx = self._get_port_context(mocked.APIC_TENANT,
                                          mocked.APIC_NETWORK,
                                          'vm1', net_ctx, HOST_ID1)
        mgr = self.driver.apic_manager
        self.driver.update_port_postcommit(port_ctx)
        mgr.ensure_tenant_created_on_apic.assert_called_once_with(
            mocked.APIC_TENANT)
        mgr.ensure_path_created_for_port.assert_called_once_with(
            mocked.APIC_TENANT, mocked.APIC_NETWORK, HOST_ID1,
            ENCAP)

    def test_update_gw_port_postcommit(self):
        net_ctx = self._get_network_context(mocked.APIC_TENANT,
                                            mocked.APIC_NETWORK,
                                            TEST_SEGMENT1, external=True)
        port_ctx = self._get_port_context(mocked.APIC_TENANT,
                                          mocked.APIC_NETWORK,
                                          'vm1', net_ctx, HOST_ID1, gw=True)
        mgr = self.driver.apic_manager
        mgr.get_router_contract.return_value = mocked.FakeDbContract(
            mocked.APIC_CONTRACT)
        self.driver.update_port_postcommit(port_ctx)
        mgr.get_router_contract.assert_called_once_with(
            port_ctx.current['device_id'])
        mgr.ensure_context_enforced.assert_called_once()
        mgr.ensure_external_routed_network_created.assert_called_once_with(
            mocked.APIC_NETWORK)
        mgr.ensure_logical_node_profile_created.assert_called_once_with(
            mocked.APIC_NETWORK, mocked.APIC_EXT_SWITCH,
            mocked.APIC_EXT_MODULE, mocked.APIC_EXT_PORT,
            mocked.APIC_EXT_ENCAP, mocked.APIC_EXT_CIDR_EXPOSED)
        mgr.ensure_static_route_created.assert_called_once_with(
            mocked.APIC_NETWORK, mocked.APIC_EXT_SWITCH,
            mocked.APIC_EXT_GATEWAY_IP)
        mgr.ensure_external_epg_created.assert_called_once_with(
            mocked.APIC_NETWORK)
        mgr.ensure_external_epg_consumed_contract.assert_called_once_with(
            mocked.APIC_NETWORK, mocked.APIC_CONTRACT)
        mgr.ensure_external_epg_provided_contract.assert_called_once_with(
            mocked.APIC_NETWORK, mocked.APIC_CONTRACT)

    def test_update_gw_port_postcommit_fail_contract_create(self):
        net_ctx = self._get_network_context(mocked.APIC_TENANT,
                                            mocked.APIC_NETWORK,
                                            TEST_SEGMENT1, external=True)
        port_ctx = self._get_port_context(mocked.APIC_TENANT,
                                          mocked.APIC_NETWORK,
                                          'vm1', net_ctx, HOST_ID1, gw=True)
        mgr = self.driver.apic_manager
        with mock.patch('neutron.plugins.ml2.drivers.cisco.apic.apic_manager.'
                        'APICManager.ensure_external_routed_network_created',
                        side_effect=Exception()):
            self.driver.update_port_postcommit(port_ctx)
            mgr.ensure_external_routed_network_deleted.assert_called_once()

    def test_create_network_postcommit(self):
        ctx = self._get_network_context(mocked.APIC_TENANT,
                                        mocked.APIC_NETWORK,
                                        TEST_SEGMENT1)
        mgr = self.driver.apic_manager
        self.driver.create_network_postcommit(ctx)
        mgr.ensure_bd_created_on_apic.assert_called_once_with(
            mocked.APIC_TENANT, mocked.APIC_NETWORK)
        mgr.ensure_epg_created_for_network.assert_called_once_with(
            mocked.APIC_TENANT, mocked.APIC_NETWORK)

    def test_create_external_network_postcommit(self):
        ctx = self._get_network_context(mocked.APIC_TENANT,
                                        mocked.APIC_NETWORK,
                                        TEST_SEGMENT1, external=True)
        mgr = self.driver.apic_manager
        self.driver.create_network_postcommit(ctx)
        self.assertFalse(mgr.ensure_bd_created_on_apic.called)
        self.assertFalse(mgr.ensure_epg_created_for_network.called)

    def test_delete_network_postcommit(self):
        ctx = self._get_network_context(mocked.APIC_TENANT,
                                        mocked.APIC_NETWORK,
                                        TEST_SEGMENT1)
        mgr = self.driver.apic_manager
        self.driver.delete_network_postcommit(ctx)
        mgr.delete_bd_on_apic.assert_called_once_with(
            mocked.APIC_TENANT, mocked.APIC_NETWORK)
        mgr.delete_epg_for_network.assert_called_once_with(
            mocked.APIC_TENANT, mocked.APIC_NETWORK)

    def test_delete_external_network_postcommit(self):
        ctx = self._get_network_context(mocked.APIC_TENANT,
                                        mocked.APIC_NETWORK,
                                        TEST_SEGMENT1, external=True)
        mgr = self.driver.apic_manager
        self.driver.delete_network_postcommit(ctx)
        mgr.delete_external_routed_network.assert_called_once_with(
            mocked.APIC_NETWORK)

    def test_create_subnet_postcommit(self):
        net_ctx = self._get_network_context(mocked.APIC_TENANT,
                                            mocked.APIC_NETWORK,
                                            TEST_SEGMENT1)
        subnet_ctx = self._get_subnet_context(SUBNET_GATEWAY,
                                              SUBNET_CIDR,
                                              net_ctx)
        mgr = self.driver.apic_manager
        self.driver.create_subnet_postcommit(subnet_ctx)
        mgr.ensure_subnet_created_on_apic.assert_called_once_with(
            mocked.APIC_TENANT, mocked.APIC_NETWORK,
            '%s/%s' % (SUBNET_GATEWAY, SUBNET_NETMASK))

    def _get_network_context(self, tenant_id, net_id, seg_id=None,
                             seg_type='vlan', external=False):
        network = {'id': net_id,
                   'name': net_id + '-name',
                   'tenant_id': tenant_id,
                   'provider:segmentation_id': seg_id}
        if external:
            network['router:external'] = True
        if seg_id:
            network_segments = [{'id': seg_id,
                                 'segmentation_id': ENCAP,
                                 'network_type': seg_type,
                                 'physical_network': 'physnet1'}]
        else:
            network_segments = []
        return FakeNetworkContext(network, network_segments)

    def _get_subnet_context(self, gateway_ip, cidr, network):
        subnet = {'tenant_id': network.current['tenant_id'],
                  'network_id': network.current['id'],
                  'id': '[%s/%s]' % (gateway_ip, cidr),
                  'gateway_ip': gateway_ip,
                  'cidr': cidr}
        return FakeSubnetContext(subnet, network)

    def _get_port_context(self, tenant_id, net_id, vm_id, network, host,
                          gw=False):
        port = {'device_id': vm_id,
                'device_owner': 'compute',
                'binding:host_id': host,
                'tenant_id': tenant_id,
                'id': mocked.APIC_PORT,
                'name': mocked.APIC_PORT,
                'network_id': net_id}
        if gw:
            port['device_owner'] = n_constants.DEVICE_OWNER_ROUTER_GW
            port['device_id'] = mocked.APIC_ROUTER
        return FakePortContext(port, network)


class FakeNetworkContext(object):
    """To generate network context for testing purposes only."""

    def __init__(self, network, segments):
        self._network = network
        self._segments = segments

    @property
    def current(self):
        return self._network

    @property
    def network_segments(self):
        return self._segments


class FakeSubnetContext(object):
    """To generate subnet context for testing purposes only."""

    def __init__(self, subnet, network):
        self._subnet = subnet
        self._network = network
        self._plugin = mock.Mock()
        self._plugin_context = mock.Mock()
        self._plugin.get_network.return_value = {}

    @property
    def current(self):
        return self._subnet

    @property
    def network(self):
        return self._network


class FakePortContext(object):
    """To generate port context for testing purposes only."""

    def __init__(self, port, network):
        self._port = port
        self._network = network
        self._plugin = mock.Mock()
        self._plugin_context = mock.Mock()
        self._plugin.get_ports.return_value = []
        if network.network_segments:
            self._bound_segment = network.network_segments[0]
        else:
            self._bound_segment = None

    @property
    def current(self):
        return self._port

    @property
    def network(self):
        return self._network

    @property
    def bound_segment(self):
        return self._bound_segment

    def set_binding(self, segment_id, vif_type, cap_port_filter):
        pass

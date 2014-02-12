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

from oslo.config import cfg

from neutron.plugins.ml2.drivers.cisco.apic import mechanism_apic as md
from neutron.plugins.ml2.drivers import type_vlan  # noqa
from neutron.tests import base
from neutron.tests.unit.ml2.drivers.cisco.apic import (
    test_cisco_apic_common as mocked)


HOST_ID1 = 'ubuntu'
HOST_ID2 = 'rhel'

SUBNET_GATEWAY = '10.3.2.1'
SUBNET_CIDR = '24'

TEST_SEGMENT1 = 'test-segment1'
TEST_SEGMENT2 = 'test-segment2'

TEST_VIF_TYPE = 'test-vif_type'
TEST_CAP_PORT_FILTER = 'test-cap_port_filter'


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

        self.addCleanup(mock.patch.stopall)

    def test_initialize(self):
        cfg.CONF.set_override('network_vlan_ranges', ['physnet1:100:199'],
                              'ml2_type_vlan')
        ns = mocked.APIC_VLAN_NAME
        mode = mocked.APIC_VLAN_MODE
        self.mock_response_for_get('fvnsVlanInstP', name=ns, mode=mode)
        self.mock_response_for_get('vmmDomP', name=mocked.APIC_DOMAIN)
        self.mock_response_for_get('infraAttEntityP',
                                   name=mocked.APIC_ATT_ENT_PROF)
        self.mock_response_for_get('infraAccPortGrp',
                                   name=mocked.APIC_ACC_PORT_GRP)
        mock.patch('neutron.plugins.ml2.drivers.cisco.apic.apic_manager.'
                   'APICManager.ensure_infra_created_on_apic').start()
        self.driver.initialize()
        self.assert_responses_drained(self.driver.apic_manager.apic.session)

    def test_create_port_precommit(self):
        net_ctx = self._get_network_context(mocked.APIC_TENANT,
                                            mocked.APIC_NETWORK,
                                            TEST_SEGMENT1)
        port_ctx = self._get_port_context(mocked.APIC_TENANT,
                                          mocked.APIC_NETWORK,
                                          'vm1', net_ctx, HOST_ID1)
        mgr = self.driver.apic_manager = mock.Mock()
        self.driver.create_port_precommit(port_ctx)
        mgr.ensure_tenant_created_on_apic.assert_called_once_with(
            mocked.APIC_TENANT)
        mgr.ensure_path_created_for_port.assert_called_once_with(
            mocked.APIC_TENANT, mocked.APIC_NETWORK, HOST_ID1,
            TEST_SEGMENT1, mocked.APIC_NETWORK + '-name')

    def test_create_port_precommit_no_host(self):
        net_ctx = self._get_network_context(mocked.APIC_TENANT,
                                            mocked.APIC_NETWORK,
                                            TEST_SEGMENT1)
        port_ctx = self._get_port_context(mocked.APIC_TENANT,
                                          mocked.APIC_NETWORK,
                                          'vm1', net_ctx, host=None)
        mgr = self.driver.apic_manager = mock.Mock()
        self.driver.create_port_precommit(port_ctx)
        self.assertFalse(mgr.ensure_tenant_created_on_apic.called)
        self.assertFalse(mgr.ensure_path_created_for_port.called)

    def test_create_network_precommit(self):
        ctx = self._get_network_context(mocked.APIC_TENANT,
                                        mocked.APIC_NETWORK,
                                        TEST_SEGMENT1)
        mgr = self.driver.apic_manager = mock.Mock()
        self.driver.create_network_precommit(ctx)
        mgr.ensure_bd_created_on_apic.assert_called_once_with(
            mocked.APIC_TENANT, mocked.APIC_NETWORK)
        mgr.ensure_epg_created_for_network.assert_called_once_with(
            mocked.APIC_TENANT, mocked.APIC_NETWORK,
            mocked.APIC_NETWORK + '-name')

    def test_delete_network_precommit(self):
        ctx = self._get_network_context(mocked.APIC_TENANT,
                                        mocked.APIC_NETWORK,
                                        TEST_SEGMENT1)
        mgr = self.driver.apic_manager = mock.Mock()
        self.driver.delete_network_precommit(ctx)
        mgr.delete_bd_on_apic.assert_called_once_with(
            mocked.APIC_TENANT, mocked.APIC_NETWORK)
        mgr.delete_epg_for_network.assert_called_once_with(
            mocked.APIC_TENANT, mocked.APIC_NETWORK)

    def test_create_subnet_precommit(self):
        net_ctx = self._get_network_context(mocked.APIC_TENANT,
                                            mocked.APIC_NETWORK,
                                            TEST_SEGMENT1)
        subnet_ctx = self._get_subnet_context(SUBNET_GATEWAY,
                                              SUBNET_CIDR,
                                              net_ctx)
        mgr = self.driver.apic_manager = mock.Mock()
        self.driver.create_subnet_precommit(subnet_ctx)
        mgr.ensure_subnet_created_on_apic.assert_called_once_with(
            mocked.APIC_TENANT, mocked.APIC_NETWORK,
            '%s/%s' % (SUBNET_GATEWAY, SUBNET_CIDR))

    def test_bind_port(self):
        net_ctx = self._get_network_context(mocked.APIC_TENANT,
                                            mocked.APIC_NETWORK,
                                            TEST_SEGMENT1)
        port_ctx = self._get_port_context(mocked.APIC_TENANT,
                                          mocked.APIC_NETWORK,
                                          'vm1', net_ctx, HOST_ID1)
        self.driver.vif_type = TEST_VIF_TYPE
        self.driver.cap_port_filter = TEST_CAP_PORT_FILTER
        with mock.patch.object(md, 'LOG') as log:
            self.driver.bind_port(port_ctx)
            self.assertFalse(log.error.called)

    def test_bind_port_bad_type(self):
        net_ctx = self._get_network_context(mocked.APIC_TENANT,
                                            mocked.APIC_NETWORK,
                                            TEST_SEGMENT1,
                                            seg_type='unsupported')
        port_ctx = self._get_port_context(mocked.APIC_TENANT,
                                          mocked.APIC_NETWORK,
                                          'vm1', net_ctx, HOST_ID1)
        self.driver.vif_type = TEST_VIF_TYPE
        self.driver.cap_port_filter = TEST_CAP_PORT_FILTER
        with mock.patch.object(md, 'LOG') as log:
            self.driver.bind_port(port_ctx)
            self.assertTrue(log.error.called)

    def test_bind_port_no_segments(self):
        net_ctx = self._get_network_context(mocked.APIC_TENANT,
                                            mocked.APIC_NETWORK)
        port_ctx = self._get_port_context(mocked.APIC_TENANT,
                                          mocked.APIC_NETWORK,
                                          'vm1', net_ctx, HOST_ID1)
        self.driver.vif_type = TEST_VIF_TYPE
        self.driver.cap_port_filter = TEST_CAP_PORT_FILTER
        with mock.patch.object(md, 'LOG') as log:
            self.driver.bind_port(port_ctx)
            self.assertFalse(log.error.called)

    def _get_network_context(self, tenant_id, net_id, seg_id=None,
                             seg_type='vlan'):
        network = {'id': net_id,
                   'name': net_id + '-name',
                   'tenant_id': tenant_id,
                   'provider:segmentation_id': seg_id}
        if seg_id:
            network_segments = [{'id': seg_id,
                                 'segmentation_id': '101',
                                 'network_type': seg_type,
                                 'physical_network': 'physnet1'}]
        else:
            network_segments = []
        return FakeNetworkContext(network, network_segments, network)

    def _get_subnet_context(self, gateway_ip, cidr, network):
        subnet = {'tenant_id': network.current['tenant_id'],
                  'network_id': network.current['id'],
                  'id': '[%s/%s]' % (gateway_ip, cidr),
                  'gateway_ip': gateway_ip,
                  'cidr': cidr}
        return FakeSubnetContext(subnet, network)

    def _get_port_context(self, tenant_id, net_id, vm_id, network, host):
        port = {'device_id': vm_id,
                'device_owner': 'compute',
                'binding:host_id': host,
                'tenant_id': tenant_id,
                'id': mocked.APIC_PORT,
                'name': mocked.APIC_PORT,
                'network_id': net_id}
        return FakePortContext(port, network)


class FakeNetworkContext(object):
    """To generate network context for testing purposes only."""

    def __init__(self, network, segments=None, original_network=None):
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

    @property
    def current(self):
        return self._port

    @property
    def network(self):
        return self._network

    def set_binding(self, segment_id, vif_type, cap_port_filter):
        # TODO(Henry): do some asserts here
        pass

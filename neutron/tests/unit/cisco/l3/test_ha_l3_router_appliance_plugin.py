# Copyright 2015 Cisco Systems, Inc.  All rights reserved.
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

import copy

from oslo.config import cfg

import neutron
from neutron import context
from neutron.extensions import extraroute
from neutron.extensions import l3
from neutron.common import constants as l3_constants
from neutron.openstack.common import log as logging
from neutron.openstack.common import uuidutils
from neutron.plugins.cisco.db.l3 import ha_db
from neutron.plugins.cisco.extensions import ha
from neutron.plugins.cisco.extensions import routertype
from neutron.plugins.common import constants as service_constants
from neutron.tests.unit.cisco.device_manager import device_manager_test_support
from neutron.tests.unit.cisco.l3 import test_db_routertype
from neutron.tests.unit.cisco.l3 import test_l3_router_appliance_plugin

LOG = logging.getLogger(__name__)

_uuid = uuidutils.generate_uuid


CORE_PLUGIN_KLASS = device_manager_test_support.CORE_PLUGIN_KLASS
L3_PLUGIN_KLASS = (
    "neutron.tests.unit.cisco.l3.test_ha_l3_router_appliance_plugin."
    "TestApplianceHAL3RouterServicePlugin")
extensions_path = neutron.plugins.__path__[0] + '/cisco/extensions'


class TestHAL3RouterApplianceExtensionManager(
        test_db_routertype.L3TestRoutertypeExtensionManager):

    def get_resources(self):
        l3.RESOURCE_ATTRIBUTE_MAP['routers'].update(
            extraroute.EXTENDED_ATTRIBUTES_2_0['routers'])
        l3.RESOURCE_ATTRIBUTE_MAP['routers'].update(
            ha.EXTENDED_ATTRIBUTES_2_0['routers'])
        return super(TestHAL3RouterApplianceExtensionManager,
                     self).get_resources()


# A set routes and HA capable L3 routing service plugin class
# supporting appliances
class TestApplianceHAL3RouterServicePlugin(
        test_l3_router_appliance_plugin.TestApplianceL3RouterServicePlugin,
        ha_db.HA_db_mixin):

    supported_extension_aliases = ["router", "extraroute",
                                   routertype.ROUTERTYPE_ALIAS,
                                   ha.HA_ALIAS]


class HAL3RouterApplianceNamespaceTestCase(
    test_l3_router_appliance_plugin.L3RouterApplianceNamespaceTestCase):

    def setUp(self, core_plugin=None, l3_plugin=None, dm_plugin=None,
              ext_mgr=None):
        if l3_plugin is None:
            l3_plugin = L3_PLUGIN_KLASS
        if ext_mgr is None:
            ext_mgr = TestHAL3RouterApplianceExtensionManager()
        cfg.CONF.set_override('ha_enabled_by_default', True, group='ha')
        super(HAL3RouterApplianceNamespaceTestCase, self).setUp(
            l3_plugin=l3_plugin, ext_mgr=ext_mgr)


class HAL3RouterApplianceVMTestCase(
    test_l3_router_appliance_plugin.L3RouterApplianceVMTestCase):

    def setUp(self, core_plugin=None, l3_plugin=None, dm_plugin=None,
              ext_mgr=None):
        if l3_plugin is None:
            l3_plugin = L3_PLUGIN_KLASS
        if ext_mgr is None:
            ext_mgr = TestHAL3RouterApplianceExtensionManager()
        cfg.CONF.set_override('ha_enabled_by_default', True, group='ha')
        cfg.CONF.set_override('default_ha_redundancy_level', 2, group='ha')
        super(HAL3RouterApplianceVMTestCase, self).setUp(
            l3_plugin=l3_plugin, ext_mgr=ext_mgr)

    def _get_ha_defaults(self, ha_enabled=None, ha_type=None,
                         redundancy_level=None, priority=10,
                         probing_enabled=None, probe_target=None,
                         probe_interval=None):

        if ha_enabled is None:
            ha_enabled = cfg.CONF.ha.ha_enabled_by_default
        if not ha_enabled:
            return {ha.ENABLED: False}
        ha_details = {
            ha.TYPE: ha_type or cfg.CONF.ha.default_ha_mechanism,
            ha.PRIORITY: priority,
            ha.REDUNDANCY_LEVEL: (redundancy_level or
                                  cfg.CONF.ha.default_ha_redundancy_level),
            ha.PROBE_CONNECTIVITY: (
                probing_enabled if probing_enabled is not None else
                cfg.CONF.ha.connectivity_probing_enabled_by_default)}
        if probing_enabled:
            ha_details.update({
                ha.PING_TARGET: (probe_target or
                                 cfg.CONF.ha.default_ping_target),
                ha.PING_INTERVAL: (probe_interval or
                                   cfg.CONF.ha.default_ping_interval)})
        return {ha.ENABLED: ha_enabled, ha.DETAILS: ha_details}

    def _verify_ha_settings(self, router, expected_ha):
            self.assertEqual(router[ha.ENABLED], expected_ha[ha.ENABLED])
            if expected_ha[ha.ENABLED]:
                ha_details = copy.deepcopy(router[ha.DETAILS])
                redundancy_routers = ha_details.pop(ha.REDUNDANCY_ROUTERS)
                self.assertDictEqual(ha_details,
                                     expected_ha[ha.DETAILS])
                self.assertEqual(len(redundancy_routers),
                                 expected_ha[ha.DETAILS][ha.REDUNDANCY_LEVEL])
            else:
                self.assertIsNone(router.get(ha.DETAILS))

    def test_create_ha_router_with_defaults(self):
        with self.subnet() as s:
            self._set_net_external(s['subnet']['network_id'])
            with self.router(external_gateway_info={
                'network_id': s['subnet']['network_id']}) as r:
                self.assertEqual(
                    s['subnet']['network_id'],
                    r['router']['external_gateway_info']['network_id'])
                self._verify_ha_settings(r['router'], self._get_ha_defaults())

    def test_create_ha_router_with_ha_specification(self):
        #TODO(bobmel): Implement this test
        pass

    def test_show_ha_router_non_admin(self):
        tenant_id = _uuid()
        with self.network(tenant_id=tenant_id) as n_external:
            res = self._create_subnet(self.fmt, n_external['network']['id'],
                                      cidr='10.0.1.0/24', tenant_id=tenant_id)
            s = self.deserialize(self.fmt, res)
            self._set_net_external(s['subnet']['network_id'])
            with self.router(tenant_id=tenant_id,
                             external_gateway_info={
                                 'network_id': s['subnet']['network_id']},
                             set_context=True) as r:
                self.assertEqual(
                    s['subnet']['network_id'],
                    r['router']['external_gateway_info']['network_id'])
                self.assertTrue(r['router'][ha.ENABLED])
                # ensure that no ha details are included
                self.assertNotIn(ha.DETAILS, r['router'])
                r_s = self._show('routers', r['router']['id'],
                                 neutron_context=context.Context('',
                                                                 tenant_id))
                self.assertTrue(r_s['router'][ha.ENABLED])
                # ensure that no ha details are included
                self.assertNotIn(ha.DETAILS, r_s['router'])

    def _verify_router_ports(self, router_id, external_net_id,
                             external_subnet_id, internal_net_id,
                             internal_subnet_id):
        body = self._list('ports',
                          query_params='device_id=%s' % router_id)
        ports = body['ports']
        self.assertEqual(len(ports), 2)
        if ports[0]['network_id'] == external_net_id:
            p_e = ports[0]
            p_i = ports[1]
        else:
            p_e = ports[1]
            p_i = ports[0]
        self.assertEqual(p_e['fixed_ips'][0]['subnet_id'], external_subnet_id)
        self.assertEqual(p_e['device_owner'],
                         l3_constants.DEVICE_OWNER_ROUTER_GW)
        self.assertEqual(p_i['network_id'], internal_net_id)
        self.assertEqual(p_i['fixed_ips'][0]['subnet_id'], internal_subnet_id)
        self.assertEqual(p_i['device_owner'],
                         l3_constants.DEVICE_OWNER_ROUTER_INTF)

    def _ha_router_port_test(self, subnet, router, port, ha_spec=None,
                             additional_tests_function=None):
        body = self._router_interface_action('add', router['id'], None,
                                             port['id'])
        self.assertIn('port_id', body)
        self.assertEqual(body['port_id'], port['id'])
        if ha_spec is None:
            ha_spec = self._get_ha_defaults()
        # verify router visible to user
        self._verify_ha_settings(router, ha_spec)
        self._verify_router_ports(router['id'], subnet['network_id'],
                                  subnet['id'], port['network_id'],
                                  port['fixed_ips'][0]['subnet_id'])
        ha_disabled_settings = self._get_ha_defaults(ha_enabled=False)
        redundancy_routers =  []
        # verify redundancy routers
        for rr_info in router[ha.DETAILS][ha.REDUNDANCY_ROUTERS]:
            rr = self._show('routers', rr_info['id'])
            redundancy_routers.append(rr['router'])
            # check that redundancy router is hidden
            self.assertEqual(rr['router']['tenant_id'], '')
            # redundancy router should have ha disabled
            self._verify_ha_settings(rr['router'], ha_disabled_settings)
            # check that redundancy router has all ports
            self._verify_router_ports(rr['router']['id'], subnet['network_id'],
                                      subnet['id'], port['network_id'],
                                      port['fixed_ips'][0]['subnet_id'])
        if additional_tests_function is not None:
            additional_tests_function(redundancy_routers)
        # clean-up
        self._router_interface_action('remove', router['id'], None, port['id'])

    def test_ha_router_add_and_remove_interface_port(self):
        with self.subnet(cidr='10.0.1.0/24') as s:
            self._set_net_external(s['subnet']['network_id'])
            with self.router(external_gateway_info={
                    'network_id': s['subnet']['network_id']}) as r:
                with self.port() as p:
                    self._ha_router_port_test(s['subnet'], r['router'],
                                              p['port'])

    def test_ha_router_disable_ha_succeeds(self):
        def _disable_ha_tests(redundancy_routers):
            body = {'router': {ha.ENABLED: False}}
            updated_router = self._update('routers', r['router']['id'], body)
            self._verify_ha_settings(updated_router['router'],
                                     self._get_ha_defaults(ha_enabled=False))
            params = "|".join(["id=%s" % rr['id'] for rr in redundancy_routers])
            redundancy_routers = self._list('routers', query_params=params)
 #               query_params="id=%s|id=%s" % (
 #                   redundancy_routers[0]['id'],
 #                   redundancy_routers[1]['id']))
            self.assertEqual(len(redundancy_routers['routers']), 0)

        with self.subnet(cidr='10.0.1.0/24') as s:
            self._set_net_external(s['subnet']['network_id'])
            with self.router(external_gateway_info={
                    'network_id': s['subnet']['network_id']}) as r:
                with self.port() as p:
                    self._ha_router_port_test(s['subnet'], r['router'],
                                              p['port'], None,
                                              _disable_ha_tests)

    def test_ha_router_disable_ha_non_admin_succeeds(self):
        def _disable_ha_tests(redundancy_routers):
            body = {'router': {ha.ENABLED: False}}
            updated_router = self._update(
                'routers', r['router']['id'], body,
                neutron_context=context.Context('', tenant_id))
            self._verify_ha_settings(updated_router['router'],
                                     self._get_ha_defaults(ha_enabled=False))
            params = "|".join(["id=%s" % rr['id'] for rr in redundancy_routers])
            redundancy_routers = self._list('routers', query_params=params)
#                query_params="id=%s|id=%s" % (
#                    redundancy_router1['router']['id'],
#                    redundancy_router2['router']['id']))
            self.assertEqual(len(redundancy_routers['routers']), 0)

        tenant_id = _uuid()
        with self.network(tenant_id=tenant_id) as n_external:
            res = self._create_subnet(self.fmt, n_external['network']['id'],
                                      cidr='10.0.1.0/24', tenant_id=tenant_id)
            s = self.deserialize(self.fmt, res)
            self._set_net_external(s['subnet']['network_id'])
            with self.router(
                    external_gateway_info={
                        'network_id': s['subnet']['network_id']},
                    tenant_id=tenant_id) as r:
                with self.port(tenant_id=tenant_id) as p:
                    self._ha_router_port_test(s['subnet'], r['router'],
                                              p['port'], None,
                                              _disable_ha_tests)

    def test_enable_ha_on_gateway_router_succeeds(self):
        with self.subnet(cidr='10.0.1.0/24') as s:
            self._set_net_external(s['subnet']['network_id'])
            kwargs = {ha.ENABLED: False,
                      l3.EXTERNAL_GW_INFO: {'network_id':
                                            s['subnet']['network_id']}}
            with self.router(arg_list=(ha.ENABLED,), **kwargs) as r:
                with self.port() as p:
                    body = self._router_interface_action('add',
                                                         r['router']['id'],
                                                         None,
                                                         p['port']['id'])
                    self.assertIn('port_id', body)
                    self.assertEqual(body['port_id'], p['port']['id'])
                    self._verify_router_ports(
                        r['router']['id'], s['subnet']['network_id'],
                        s['subnet']['id'], p['port']['network_id'],
                        p['port']['fixed_ips'][0]['subnet_id'])
                    ha_disabled_settings = self._get_ha_defaults(
                        ha_enabled=False)
                    self._verify_ha_settings(r['router'], ha_disabled_settings)
                    body = {'router': {ha.ENABLED: True,
                                       ha.DETAILS: {ha.TYPE: ha.HA_VRRP}}}
                    updated_router = self._update('routers', r['router']['id'],
                                                  body)
                    self._verify_ha_settings(
                        updated_router['router'],
                        self._get_ha_defaults(ha_type=ha.HA_VRRP))
                    ha_d = updated_router['router'][ha.DETAILS]
                    rr_ids = [rr['id'] for rr in ha_d[ha.REDUNDANCY_ROUTERS]]
                    redundancy_routers = self._list(
                        'routers',
                        query_params="id="+",".join(["%s" % x for x in rr_ids]))
                    self._verify_ha_settings(r['router'], ha_disabled_settings)
                    # check that redundancy routers have all ports
                    for rr in redundancy_routers['routers']:
                        self._verify_router_ports(
                            rr['id'], s['network_id'], s['id'],
                            p['network_id'], p['fixed_ips'][0]['subnet_id'])
                    # clean-up
                    self._router_interface_action('remove', r['router']['id'],
                                                  None, p['port']['id'])



    def test_enable_ha_on_non_gateway_router_fails(self):
        pass

    def test_update_ha_router_non_admin_fails(self):
        pass

    def _test_change_ha_router_redundancy_level(self, new_level=1):
        def _change_redundancy_tests(redundancy_router1, redundancy_router2):
            body = {'router': {ha.ENABLED: True,
                               ha.DETAILS: {ha.TYPE: ha.HA_HSRP,
                                            ha.REDUNDANCY_LEVEL: new_level,
                                            ha.PROBE_CONNECTIVITY: False}}}
            updated_router = self._update('routers', r['router']['id'], body)
            self.assertTrue(updated_router['router'][ha.ENABLED])
            self.assertEqual(updated_router['router'][ha.ENABLED], new_level)
            redundancy_routers = self._list(
                'routers', query_params="id=%s|id=%s" % (
                    redundancy_router1['router']['id'],
                    redundancy_router2['router']['id']))
            self.assertEqual(len(redundancy_routers['routers']), new_level)
            # verify router visible to user
            self._verify_router_ports(r['id'], s['network_id'], s['id'],
                                      p['network_id'],
                                      p['fixed_ips'][0]['subnet_id'])
            self._verify_ha_settings(redundancy_routers['routers'][0],
                                     self._get_ha_defaults(ha_enabled=False))
            # check that redundancy routers have all ports
            for rr in redundancy_routers['routers']:
                self._verify_router_ports(rr['id'], s['network_id'], s['id'],
                                          p['network_id'],
                                          p['fixed_ips'][0]['subnet_id'])

        with self.subnet(cidr='10.0.1.0/24') as s:
            self._set_net_external(s['subnet']['network_id'])
            with self.router(external_gateway_info={
                    'network_id': s['subnet']['network_id']}) as r:
                with self.port() as p:
                    self._ha_router_port_test(s['subnet'], r['router'],
                                              p['port'], None,
                                              _change_redundancy_tests)

    def test_decrease_ha_router_redundancy_level(self):
        self._test_change_ha_router_redundancy_level()

    def test_increase_ha_router_redundancy_level(self):
        self._test_change_ha_router_redundancy_level(new_level=3)

    def test_update_ha_type_on_router_with_ha_enabled_fails(self):
        pass

    def test_update_ha_router_probing_settings(self):
        pass

    def test_update_ha_router_priority(self):
        pass

    def test_update_ha_redundancy_router_priority(self):
        pass


class L3AgentHARouterApplianceTestCase(
    test_l3_router_appliance_plugin.L3AgentRouterApplianceTestCase):

    def setUp(self, core_plugin=None, l3_plugin=None, dm_plugin=None,
              ext_mgr=None):
        if l3_plugin is None:
            l3_plugin = L3_PLUGIN_KLASS
        if ext_mgr is None:
            ext_mgr = TestHAL3RouterApplianceExtensionManager()
        super(L3AgentHARouterApplianceTestCase, self).setUp(
            l3_plugin=l3_plugin, ext_mgr=ext_mgr)


class L3CfgAgentHARouterApplianceTestCase(
    test_l3_router_appliance_plugin.L3CfgAgentRouterApplianceTestCase):

    def setUp(self, core_plugin=None, l3_plugin=None, dm_plugin=None,
              ext_mgr=None):
        self.core_plugin = device_manager_test_support.TestCorePlugin()
        # service plugin providing L3 routing
        self.plugin = TestApplianceHAL3RouterServicePlugin()
        self.orig_get_sync_data = self.plugin.get_sync_data
        self.plugin.get_sync_data = self.plugin.get_sync_data_ext

        super(L3CfgAgentHARouterApplianceTestCase, self).setUp(
            core_plugin=core_plugin, l3_plugin=l3_plugin, dm_plugin=dm_plugin,
            ext_mgr=ext_mgr)

        self._mock_svc_vm_create_delete(self.core_plugin)
        self._mock_get_routertype_scheduler_always_none()

    def tearDown(self):
        self.plugin.get_sync_data = self.orig_get_sync_data
        super(L3CfgAgentHARouterApplianceTestCase, self).tearDown()

    def _test_notify_op_agent(self, target_func, *args):
        kargs = [item for item in args]
        kargs.append(self._cfg_agent_mock)
        target_func(*kargs)

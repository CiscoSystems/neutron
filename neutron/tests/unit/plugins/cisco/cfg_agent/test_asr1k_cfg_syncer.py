# Copyright 2014 Cisco Systems, Inc.  All rights reserved.
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

import ciscoconfparse
from oslo_config import cfg
from oslo_serialization import jsonutils

import mock
from neutron.tests import base

from neutron.plugins.cisco.cfg_agent.device_drivers.asr1k import (
    asr1k_cfg_syncer)

from neutron.plugins.cisco.cfg_agent.device_drivers.asr1k import (
    asr1k_routing_driver as driver)


cfg.CONF.register_opts(driver.ASR1K_DRIVER_OPTS, "multi_region")


class ASR1kCfgSyncer2(base.BaseTestCase):

    def _read_neutron_db_data(self):
        """
        helper function for reading the dummy neutron router db
        """
        with open(base.ROOTDIR +
                  '/unit/plugins/cisco/etc/cfg_syncer/neutron_router_db.json',
                  'r') as fp:
            self.router_db_info = jsonutils.load(fp)

    def _read_asr_running_cfg(self, file_name='asr_running_cfg.json'):
        """
        helper function for reading sample asr running cfg files (json format)
        """
        asr_running_cfg = (
            '/unit/plugins/cisco/etc/cfg_syncer/%s' % (file_name))

        with open(base.ROOTDIR + asr_running_cfg, 'r') as fp:
            asr_running_cfg_json = jsonutils.load(fp)
            return asr_running_cfg_json

    def setUp(self):
        super(ASR1kCfgSyncer2, self).setUp()

        self._read_neutron_db_data()
        self.hosting_device_info = \
            {'id': '00000000-0000-0000-0000-000000000003'}
        self.driver = mock.Mock()
        self.config_syncer = \
            asr1k_cfg_syncer.ConfigSyncer2(self.router_db_info,
                                           self.driver,
                                           self.hosting_device_info)

    def tearDown(self):
        super(ASR1kCfgSyncer2, self).tearDown()

    def test_process_plugin_routers_data(self):
        self.config_syncer = \
            asr1k_cfg_syncer.ConfigSyncer2(self.router_db_info,
                                           self.driver,
                                           self.hosting_device_info)

    def test_delete_invalid_cfg(self):

        cfg.CONF.set_override('enable_multi_region', False, 'multi_region')
        router_db_info = []
        self.config_syncer = \
            asr1k_cfg_syncer.ConfigSyncer2(router_db_info,
                                           self.driver,
                                           self.hosting_device_info)

        self.config_syncer.get_running_config = \
            mock.Mock(return_value=self._read_asr_running_cfg(
                               'asr_basic_running_cfg_no_multi_region.json'))
        invalid_cfg = self.config_syncer.delete_invalid_cfg()

        self.assertEqual(8, len(invalid_cfg))


class ASR1kCfgSyncer(base.BaseTestCase):

    def _read_neutron_db_data(self):
        """
        helper function for reading the dummy neutron router db
        """
        with open(base.ROOTDIR +
                  '/unit/plugins/cisco/etc/cfg_syncer/neutron_router_db.json',
                  'r') as fp:
            self.router_db_info = jsonutils.load(fp)

    def _read_asr_running_cfg(self, file_name='asr_running_cfg.json'):
        """
        helper function for reading sample asr running cfg files (json format)
        """
        asr_running_cfg = (
            '/unit/plugins/cisco/etc/cfg_syncer/%s' % (file_name))

        with open(base.ROOTDIR + asr_running_cfg, 'r') as fp:
            asr_running_cfg_json = jsonutils.load(fp)
            return asr_running_cfg_json

    def setUp(self):
        super(ASR1kCfgSyncer, self).setUp()

        self._read_neutron_db_data()
        self.hosting_device_info = \
            {'id': '00000000-0000-0000-0000-000000000003'}
        self.driver = mock.Mock()
        self.config_syncer = asr1k_cfg_syncer.ConfigSyncer(self.router_db_info,
                                                      self.driver,
                                                      self.hosting_device_info)

    def tearDown(self):
        super(ASR1kCfgSyncer, self).tearDown()

    def test_delete_invalid_cfg_empty_routers_list(self):
        """
        expected invalid_cfg
        [u'ip nat inside source static 10.2.0.5 172.16.0.126 vrf'
          ' nrouter-3ea5f9 redundancy neutron-hsrp-1064-3000',
         u'ip nat inside source list neutron_acl_2564 pool'
          ' nrouter-3ea5f9_nat_pool vrf nrouter-3ea5f9 overload',
         u'ip nat pool nrouter-3ea5f9_nat_pool 172.16.0.124'
          ' 172.16.0.124 netmask 255.255.0.0',
         u'ip route vrf nrouter-3ea5f9 0.0.0.0 0.0.0.0'
          ' Port-channel10.3000 172.16.0.1',
         u'ip access-list standard neutron_acl_2564',
         <IOSCfgLine # 83 'interface Port-channel10.2564'>,
         <IOSCfgLine # 96 'interface Port-channel10.3000'>,
         u'nrouter-3ea5f9']
        """
        cfg.CONF.set_override('enable_multi_region', False, 'multi_region')

        router_db_info = []

        self.config_syncer = asr1k_cfg_syncer.ConfigSyncer(router_db_info,
                                                      self.driver,
                                                      self.hosting_device_info)
        self.config_syncer.get_running_config = \
            mock.Mock(return_value=self._read_asr_running_cfg(
                               'asr_basic_running_cfg_no_multi_region.json'))
        invalid_cfg = self.config_syncer.delete_invalid_cfg()
        self.assertEqual(8, len(invalid_cfg))

    def test_delete_invalid_cfg_with_multi_region_and_empty_routers_list(self):
        """
        This test verifies that the  cfg-syncer will delete invalid cfg
        if the neutron-db (routers dictionary list) happens to be empty.

        Since the neutron-db router_db_info is empty, all region 0000002
        running-config should be deleted.

        Expect 8 invalid configs found

        ['ip nat inside source static 10.2.0.5 172.16.0.126'
          ' vrf nrouter-3ea5f9-0000002 redundancy neutron-hsrp-1064-3000',
         'ip nat inside source list neutron_acl_0000002_2564 pool '
         'nrouter-3ea5f9-0000002_nat_pool vrf nrouter-3ea5f9-0000002 overload',
         'ip nat pool nrouter-3ea5f9-0000002_nat_pool '
          '172.16.0.124 172.16.0.124 netmask 255.255.0.0',
         'ip route vrf nrouter-3ea5f9-0000002 0.0.0.0 0.0.0.0'
          ' Port-channel10.3000 172.16.0.1',
         'ip access-list standard neutron_acl_0000002_2564',
         <IOSCfgLine # 83 'interface Port-channel10.2564'>,
         <IOSCfgLine # 96 'interface Port-channel10.3000'>,
         'nrouter-3ea5f9-0000002']
        """
        cfg.CONF.set_override('enable_multi_region', True, 'multi_region')
        cfg.CONF.set_override('region_id', '0000002', 'multi_region')
        cfg.CONF.set_override('other_region_ids', ['0000001'], 'multi_region')
        router_db_info = []

        self.config_syncer = asr1k_cfg_syncer.ConfigSyncer(router_db_info,
                                                      self.driver,
                                                      self.hosting_device_info)
        self.config_syncer.get_running_config = \
            mock.Mock(return_value=self._read_asr_running_cfg(
                                            'asr_basic_running_cfg.json'))
        invalid_cfg = self.config_syncer.delete_invalid_cfg()
        """
        (Pdb++) pp.pprint(invalid_cfg)
        [u'ip nat inside source static 10.2.0.5 172.16.0.126 vrf nrouter-3ea5f9-0000002 redundancy neutron-hsrp-1064-3000',
         u'ip nat inside source list neutron_acl_0000002_2564 pool nrouter-3ea5f9-0000002_nat_pool vrf nrouter-3ea5f9-0000002 overload',
         u'ip nat pool nrouter-3ea5f9-0000002_nat_pool 172.16.0.124 172.16.0.124 netmask 255.255.0.0',
         u'ip route vrf nrouter-3ea5f9-0000002 0.0.0.0 0.0.0.0 Port-channel10.3000 172.16.0.1',
         <IOSCfgLine # 83 'interface Port-channel10.2564'>,
         <IOSCfgLine # 96 'interface Port-channel10.3000'>,
         u'nrouter-3ea5f9-0000002']
        """
        self.assertEqual(8, len(invalid_cfg))

    def test_clean_interfaces_basic_multi_region_enabled(self):
        """
        In this test, we are simulating a cfg-sync, clean_interfaces for
        region 0000002 cfg-agent.  Running-cfg only exists for region
        0000001.

        At the end of test, we should expect zero entries in invalid_cfg.
        """

        cfg.CONF.set_override('enable_multi_region', True, 'multi_region')
        cfg.CONF.set_override('region_id', '0000002', 'multi_region')
        cfg.CONF.set_override('other_region_ids', ['0000001'], 'multi_region')

        intf_segment_dict = self.config_syncer.intf_segment_dict
        segment_nat_dict = self.config_syncer.segment_nat_dict

        invalid_cfg = []
        conn = self.driver._get_connection()

        asr_running_cfg = self._read_asr_running_cfg(
            file_name='asr_running_cfg_no_R2.json')

        parsed_cfg = ciscoconfparse.CiscoConfParse(asr_running_cfg)

        invalid_cfg += self.config_syncer.clean_interfaces(conn,
                                              intf_segment_dict,
                                              segment_nat_dict,
                                              parsed_cfg)
        self.assertEqual(0, len(invalid_cfg))

    def test_clean_interfaces_multi_region_disabled(self):
        """
        In this test, we are simulating a cfg-sync, clean_interfaces for
        region 0000002 cfg-agent.  Running-cfg only exists for region
        0000001, but multi_region is disabled.

        At the end of test, we should expect zero entries in invalid_cfg.
        """
        cfg.CONF.set_override('enable_multi_region', False, 'multi_region')

        intf_segment_dict = self.config_syncer.intf_segment_dict
        segment_nat_dict = self.config_syncer.segment_nat_dict

        invalid_cfg = []
        conn = self.driver._get_connection()

        asr_running_cfg = self._read_asr_running_cfg(
            file_name='asr_running_cfg_no_R2.json')

        parsed_cfg = ciscoconfparse.CiscoConfParse(asr_running_cfg)

        invalid_cfg += self.config_syncer.clean_interfaces(conn,
                                              intf_segment_dict,
                                              segment_nat_dict,
                                              parsed_cfg)
        self.assertEqual(0, len(invalid_cfg))

    def test_clean_interfaces_R2_run_cfg_present_multi_region_enabled(self):
        """
        In this test, we are simulating a cfg-sync, clean_interfaces for
        region 0000002 cfg-agent.  Existing running-cfg exists for region
        0000001 and 0000002.

        At the end of test, we should expect zero entries in invalid_cfg.
        """
        cfg.CONF.set_override('enable_multi_region', True, 'multi_region')
        cfg.CONF.set_override('region_id', '0000002', 'multi_region')
        cfg.CONF.set_override('other_region_ids', ['0000001'], 'multi_region')

        intf_segment_dict = self.config_syncer.intf_segment_dict
        segment_nat_dict = self.config_syncer.segment_nat_dict

        invalid_cfg = []
        conn = self.driver._get_connection()

        asr_running_cfg = self._read_asr_running_cfg()

        # This will trigger gateway only testing
        # asr_running_cfg = \
        #    self._read_asr_running_cfg('asr_basic_running_cfg.json')
        parsed_cfg = ciscoconfparse.CiscoConfParse(asr_running_cfg)

        invalid_cfg += self.config_syncer.clean_interfaces(conn,
                                              intf_segment_dict,
                                              segment_nat_dict,
                                              parsed_cfg)
        # disabled for now
        self.assertEqual(0, len(invalid_cfg))

    def test_clean_interfaces_R2_with_invalid_intfs(self):
        """
        In this test, we are simulating a cfg-sync, clean_interfaces for
        region 0000002 cfg-agent.  Existing running-cfg exists for region
        0000001 and 0000002.

        At the end of test, we should expect two invalid intfs
        detected.

        invalid tenant router, int Po10.2536 (invalid segment-id)
        invalid ext-gw-port, int Po10.3000 (invalid HSRP VIP)
        """
        cfg.CONF.set_override('enable_multi_region', True, 'multi_region')
        cfg.CONF.set_override('region_id', '0000002', 'multi_region')
        cfg.CONF.set_override('other_region_ids', ['0000001'], 'multi_region')

        intf_segment_dict = self.config_syncer.intf_segment_dict
        segment_nat_dict = self.config_syncer.segment_nat_dict

        invalid_cfg = []
        conn = self.driver._get_connection()

        asr_running_cfg = \
            self._read_asr_running_cfg(
                                    'asr_running_cfg_with_invalid_intfs.json')
        parsed_cfg = ciscoconfparse.CiscoConfParse(asr_running_cfg)

        invalid_cfg += self.config_syncer.clean_interfaces(conn,
                                              intf_segment_dict,
                                              segment_nat_dict,
                                              parsed_cfg)
        # disabled for now
        self.assertEqual(2, len(invalid_cfg))

    def test_clean_acls_basic_running_cfg(self):
        """
        region 1 acls should be ignored
        """
        cfg.CONF.set_override('enable_multi_region', True, 'multi_region')
        cfg.CONF.set_override('region_id', '0000002', 'multi_region')
        cfg.CONF.set_override('other_region_ids', ['0000001'], 'multi_region')

        intf_segment_dict = self.config_syncer.intf_segment_dict
        segment_nat_dict = self.config_syncer.segment_nat_dict

        invalid_cfg = []
        conn = self.driver._get_connection()

        asr_running_cfg = \
            self._read_asr_running_cfg(
                                    'asr_running_cfg.json')

        parsed_cfg = ciscoconfparse.CiscoConfParse(asr_running_cfg)

        invalid_cfg += self.config_syncer.clean_acls(conn,
                                                     intf_segment_dict,
                                                     segment_nat_dict,
                                                     parsed_cfg)

        self.assertEqual(0, len(invalid_cfg))

    def test_clean_nat_pool_overload_basic_running_cfg(self):
        """
        region 1 acls should be ignored
        """
        cfg.CONF.set_override('enable_multi_region', True, 'multi_region')
        cfg.CONF.set_override('region_id', '0000002', 'multi_region')
        cfg.CONF.set_override('other_region_ids', ['0000001'], 'multi_region')

        router_id_dict = self.config_syncer.router_id_dict
        intf_segment_dict = self.config_syncer.intf_segment_dict
        segment_nat_dict = self.config_syncer.segment_nat_dict

        invalid_cfg = []
        conn = self.driver._get_connection()

        asr_running_cfg = \
            self._read_asr_running_cfg(
                                    'asr_running_cfg.json')

        parsed_cfg = ciscoconfparse.CiscoConfParse(asr_running_cfg)
        invalid_cfg += self.config_syncer.clean_nat_pool_overload(conn,
                                                     router_id_dict,
                                                     intf_segment_dict,
                                                     segment_nat_dict,
                                                     parsed_cfg)

        self.assertEqual(0, len(invalid_cfg))

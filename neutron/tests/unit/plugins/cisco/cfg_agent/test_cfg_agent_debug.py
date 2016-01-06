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


from neutron.plugins.cisco.cfg_agent import (cfg_agent_debug)
from neutron.tests import base
from oslo_config import cfg

import pprint


class CfgAgentDebug(base.BaseTestCase):

    def setUp(self):
        super(CfgAgentDebug, self).setUp()
        cfg.CONF.set_override('enable_cfg_agent_debug', False, 'cfg_agent')
        cfg.CONF.set_override('max_parent_records', 101, 'cfg_agent')
        cfg.CONF.set_override('max_child_records', 1, 'cfg_agent')
        self.cfg_agent_debug = cfg_agent_debug.CfgAgentDebug()

    def tearDown(self):
        super(CfgAgentDebug, self).tearDown()

    def test_process_plugin_routers_data(self):
        """
        In this test, 101 parent records and 1 child record
        are added to the routers debug dict
        """
        router_id_spec = 'nrouter-abc%d-0000001'
        request_id_spec = 'req-abc%d'
        cfg.CONF.set_override('enable_cfg_agent_debug', True, 'cfg_agent')

        gw_port = {'network_id': '7a38a5fd-3ad9-4952-ab08-4def22407269'}
        ext_gw_comment = "ext-net-id: %s"

        for i in xrange(0, 101):
            router_id = router_id_spec % i
            request_id = request_id_spec % i

            self.cfg_agent_debug.add_router_txn(router_id,
                                            'GW_PORT_ADD',
                                            request_id,
                                            ext_gw_comment % (
                                                pprint.pformat(
                                                    gw_port['network_id'])))

        self.assertEqual(101,
                         self.cfg_agent_debug._get_total_txn_count())

        # print(self.cfg_agent_debug.get_all_router_txns_strfmt())
        print("Just nrouter-abc100-0000001 txns")
        # expected_txns = [{req_id: 'req-abc100', txn_type: 'ADD_GW_PORT'}]
        print(self.cfg_agent_debug.get_router_txns_strfmt(
                                                    'nrouter-abc100-0000001'))
        # self.assertAlmostEquals(expected_txns,

    def test_process_plugin_routers_data_constrained(self):
        """
        In this test, max parent records and child records are constrained.
        """
        router_id_spec = 'nrouter-abc%d-0000001'
        request_id_spec = 'req-abc%d'

        cfg.CONF.set_override('enable_cfg_agent_debug', True, 'cfg_agent')
        cfg.CONF.set_override('max_parent_records', 2, 'cfg_agent')
        cfg.CONF.set_override('max_child_records', 2, 'cfg_agent')
        # fixed_ips = [{'ip_address': '192.168.0.7',
        #              'prefixlen': 24,
        #              'subnet_id': '6fdaaae3-4034-4890-ab60-1411527e4556'}]
        port = {'network_id': '5ca17eaa-8761-48b3-9284-983d9c0983df'}
        gw_port = {'network_id': '7a38a5fd-3ad9-4952-ab08-4def22407269'}
        ext_gw_comment = "ext-net-id: %s"
        comment = "net-id: %s"
        for i in xrange(0, 101):
            router_id = router_id_spec % i
            request_id = request_id_spec % i
            self.cfg_agent_debug.add_router_txn(router_id,
                                            'GW_PORT_ADD',
                                            request_id,
                                            ext_gw_comment % (
                                                pprint.pformat(
                                                    gw_port['network_id'])))
            self.cfg_agent_debug.add_router_txn(router_id,
                                                'RTR_INTF_INTF_ADD',
                                                request_id,
                                                comment % (
                                                    pprint.pformat(
                                                        port['network_id'])))

            self.cfg_agent_debug.add_router_txn(router_id,
                                            'GW_PORT_RM',
                                            request_id,
                                            ext_gw_comment % (
                                                pprint.pformat(
                                                    gw_port['network_id'])))
        self.assertEqual(2, len(self.cfg_agent_debug.routers))
        self.assertEqual(4, self.cfg_agent_debug._get_total_txn_count())

        # print(self.cfg_agent_debug.get_all_router_txns_strfmt())
        print("Just nrouter-abc100-0000001 txns")
        # expected_txns = [{req_id: 'req-abc100', txn_type: 'ADD_GW_PORT'}]
        print(self.cfg_agent_debug.get_router_txns_strfmt(
                                                    'nrouter-abc100-0000001'))

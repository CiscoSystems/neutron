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

import pprint


class CfgAgentDebug(base.BaseTestCase):

    def setUp(self):
        super(CfgAgentDebug, self).setUp()
        self.cfg_agent_debug = cfg_agent_debug.CfgAgentDebug()

    def tearDown(self):
        super(CfgAgentDebug, self).tearDown()

    def test_process_plugin_routers_data(self):
        router_id_spec = 'nrouter-abc%d-0000001'
        request_id_spec = 'req-abc%d'

        for i in xrange(0, 101):
            router_id = router_id_spec % i
            request_id = request_id_spec % i

            self.cfg_agent_debug.add_router_txn(router_id,
                                                'ADD_GW_PORT',
                                                request_id)
        self.assertEqual(101, self.cfg_agent_debug.total_router_txns)
        self.assertEqual(self.cfg_agent_debug.total_router_txns,
                         self.cfg_agent_debug._get_total_txn_count())

        print(self.cfg_agent_debug.get_all_router_txns_strfmt())
        print("Just nrouter-abc70-0000001 txns")
        print(self.cfg_agent_debug.get_router_txns_strfmt(
                                                    'nrouter-abc70-0000001'))

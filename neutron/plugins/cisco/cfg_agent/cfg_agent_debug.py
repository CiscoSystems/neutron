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

from collections import OrderedDict
from oslo_config import cfg

import datetime
import logging
import pprint
import prettytable

LOG = logging.getLogger(__name__)

# all-together, 10,000 records
CFG_AGENT_DEBUG_OPTS = [
    cfg.BoolOpt('enable_cfg_agent_debug',
                default=False,
                help=_("Enables/Disables cfg_agent debug module")),
    cfg.IntOpt('max_parent_records',
               default=200,
               help=_("Max number of keys for each debug dictionary")),
    cfg.IntOpt('max_child_records',
               default=50,
               help=_("Max number of child records"
                      " for each debug dict record")),
]

cfg.CONF.register_opts(CFG_AGENT_DEBUG_OPTS, "cfg_agent")


class CfgAgentDebug(object):
    """"
    Encapsulates Cfg-Agent related debugging logic
    """

    def __init__(self):
        # key: request-id
        # value: {timestamp: <timestamp>}
        self.requests = {}

        # a lookup table of transactions applied to a router
        # key: router-id
        # value: list of txn-records
        # {
        #   time: <time-stamp>,
        #   req_id: <string>
        #   txn type: [router-intf-added]
        # }
        self.routers = OrderedDict()

        # a lookup table of transactions/events pertaining to a hosting-device
        self.hosting_devices = {}

    def __repr__(self):
        ret_val = {'router_txns': self.routers,
                   'total_router_txns': self._get_total_txn_count(),
                   'hosting_device_txns': self.hosting_devices}
        return "%s" % pprint.pformat(ret_val)

    @staticmethod
    def _enforce_parent_record_constraints(debug_dict):
        max_parent_records = cfg.CONF.cfg_agent.max_parent_records
        if (debug_dict is not None and
            len(debug_dict) >= max_parent_records):
            # eject and log
            key = debug_dict.keys().pop(0)
            txns = debug_dict.pop(key)

            return (key, txns)
        else:
            return (None, None)

    @staticmethod
    def _add_child_record(debug_dict, key, value):
        """
        This helper static method enforces the max child records
        constraint when attempting to add a debug_dict child record
        """
        cfg.CONF.cfg_agent.max_child_records
        if key not in debug_dict:
            debug_dict[key] = []

        child_records = debug_dict[key]

        if (len(child_records) >= cfg.CONF.cfg_agent.max_child_records):
            popped_record = child_records.pop(0)
            LOG.debug("popped record = %s" % (pprint.pformat(popped_record)))
            LOG.debug("len child records = %d" % (len(child_records)))

        child_records.append(value)

    def add_request(self, request_id):
        self.requests[request_id] = {'time': datetime.datetime.strftime(
                       datetime.datetime.now(), format='%Y-%m-%d %H:%M:%S.%f')}

    def add_router_txn(self, router_id, txn_type, request_id=None,
                       comment=None):
        if not cfg.CONF.cfg_agent.enable_cfg_agent_debug:
            return

        if router_id not in self.routers:

            popped_router_key, popped_router_txns = \
                CfgAgentDebug._enforce_parent_record_constraints(self.routers)

            if (popped_router_key is not None and
                popped_router_txns is not None):
                LOG.debug("Popped key %s, val = %s" % (popped_router_key,
                                           pprint.pformat(popped_router_txns)))
            self.routers[router_id] = []

        txn_record = {'time': datetime.datetime.strftime(
                       datetime.datetime.now(), format='%Y-%m-%d %H:%M:%S.%f'),
                      'request_id': request_id,
                      'txn_type': txn_type,
                      'comment': comment}

        CfgAgentDebug._add_child_record(self.routers, router_id, txn_record)

    def get_router_txns_strfmt(self, router_id):
        """
        Returns router txn records for a specified router_id
        """
        router_txn_buffer = None

        if router_id in self.routers:
            table = prettytable.PrettyTable(["time", "request_id",
                                             "txn_type", "comment"])
            router_txns = self.routers[router_id]

            for txn in router_txns:
                table.add_row([txn['time'],
                               txn['request_id'],
                               txn['txn_type'],
                               txn['comment']])

            router_txn_buffer = "router_id:%s\n%s" % (
                                                router_id, table.get_string())

        return router_txn_buffer

    def get_all_router_txns_strfmt(self):
        """
        returns all router txn records for all router-ids
        """
        all_router_txns = ''
        for router_id in self.routers:

            all_router_txns += "\n%s\n" % (
                                        self.get_router_txns_strfmt(router_id))

        return all_router_txns

    def _get_total_txn_count(self):

        txn_count = 0

        for router_id in self.routers:

            txn_count += len(self.routers[router_id])

        return txn_count

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

import datetime

import pprint
import prettytable

MAX_RECORDS_PER_ROUTER = 100
MAX_ROUTERS = 50


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
        self.routers = {}
        self.total_router_txns = 0

        # a lookup table of transactions/events pertaining to a hosting-device
        self.hosting_devices = {}

    def __repr__(self):
        ret_val = {'router_txns': self.routers,
                   'total_router_txns': self.total_router_txns,
                   'hosting_device_txns': self.hosting_devices}
        return "%s" % pprint.pformat(ret_val)

    def add_request(self, request_id):
        self.requests[request_id] = {'time': datetime.datetime.strftime(
                       datetime.datetime.now(), format='%Y-%m-%d %H:%M:%S.%f')}

    def add_router_txn(self, router_id, txn_type, request_id=None):

        if router_id not in self.routers:
            self.routers[router_id] = []
        txn_record = {'time': datetime.datetime.strftime(
                       datetime.datetime.now(), format='%Y-%m-%d %H:%M:%S.%f'),
                      'request_id': request_id,
                      'txn_type': txn_type}

        self.routers[router_id].append(txn_record)

        self.total_router_txns += 1

    def get_router_txns_strfmt(self, router_id):
        """
        Returns router txn records for a specified router_id
        """
        router_txn_buffer = None

        if router_id in self.routers:
            table = prettytable.PrettyTable(["time", "request_id", "txn_type"])
            router_txns = self.routers[router_id]

            for txn in router_txns:
                table.add_row([txn['time'],
                               txn['request_id'],
                               txn['txn_type']])

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

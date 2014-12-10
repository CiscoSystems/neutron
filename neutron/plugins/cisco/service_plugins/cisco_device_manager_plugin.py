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
#
# @author: Bob Melander, Cisco Systems, Inc.

from oslo.config import cfg
from oslo import messaging

from neutron.common import rpc as n_rpc
from neutron.common import topics
from neutron.db import api as qdbapi
from neutron.db import model_base
from neutron import manager
from neutron.openstack.common import importutils
import neutron.plugins
from neutron.plugins.cisco.common import cisco_constants as c_constants
from neutron.plugins.cisco.db.device_manager import (hosting_device_manager_db
                                                     as dev_mgr_db)
from neutron.plugins.cisco.db.scheduler import (cfg_agentschedulers_db as
                                                agt_sched_db)
from neutron.plugins.cisco.device_manager.rpc import (devices_cfgagent_rpc_cb
                                                      as devices_rpc)
from neutron.plugins.cisco.extensions import ciscocfgagentscheduler
from neutron.plugins.cisco.extensions import ciscohostingdevicemanager
from neutron.plugins.cisco.device_manager.rpc import devmgr_rpc_cfgagent_api


class CiscoDevMgrPluginRpcCallbacks(n_rpc.RpcCallback,
                                    devices_rpc.DeviceMgrCfgRpcCallbackMixin):
    target = messaging.Target(version='1.0')

    def __init__(self, plugin):
        super(CiscoDevMgrPluginRpcCallbacks, self).__init__()
        self._dmplugin = plugin


class CiscoDeviceManagerPlugin(dev_mgr_db.HostingDeviceManagerMixin,
                               agt_sched_db.CfgAgentSchedulerDbMixin):
    """Implementation of Cisco Device Manager Service Plugin for Neutron.

    This class implements a (hosting) device manager service plugin that
    provides hosting device template and hosting device resources. As such
    it manages associated REST API processing. All DB functionality is
    implemented in class hosting_device_manager_db.HostingDeviceManagerMixin.
    """
    supported_extension_aliases = [
        ciscohostingdevicemanager.HOSTING_DEVICE_MANAGER_ALIAS,
        ciscocfgagentscheduler.CFG_AGENT_SCHEDULER_ALIAS]

    def __init__(self):
        qdbapi.register_models(base=model_base.BASEV2)
        self.setup_rpc()
        basepath = neutron.plugins.__path__[0]
        ext_paths = [basepath + '/cisco/extensions']
        cp = cfg.CONF.api_extensions_path
        to_add = ""
        for ext_path in ext_paths:
            if cp.find(ext_path) == -1:
                to_add += ':' + ext_path
        if to_add != "":
            cfg.CONF.set_override('api_extensions_path', cp + to_add)
        self.cfg_agent_scheduler = importutils.import_object(
            cfg.CONF.configuration_agent_scheduler_driver)
        self._setup_device_manager()

    def setup_rpc(self):
        # RPC support
        self.topic = topics.DEVICE_MANAGER_PLUGIN
        self.conn = n_rpc.create_connection(new=True)
        self.agent_notifiers[c_constants.AGENT_TYPE_CFG] = (
            devmgr_rpc_cfgagent_api.DeviceMgrCfgAgentNotifyAPI(self))
        self.endpoints = [CiscoDevMgrPluginRpcCallbacks(self)]
        self.conn.create_consumer(self.topic, self.endpoints, fanout=False)
        self.conn.consume_in_threads()

    @property
    def _core_plugin(self):
        try:
            return self._plugin
        except AttributeError:
            self._plugin = manager.NeutronManager.get_plugin()
            return self._plugin


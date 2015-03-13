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

from oslo import messaging
from oslo_log import log as logging

from neutron.common import constants
from neutron.common import rpc as n_rpc
from neutron.common import topics
from neutron.common import utils
from neutron import manager
from neutron.plugins.cisco.common import cisco_constants
from neutron.plugins.cisco.extensions import ciscocfgagentscheduler
from neutron.plugins.common import constants as svc_constants

LOG = logging.getLogger(__name__)


L3AGENT_SCHED = constants.L3_AGENT_SCHEDULER_EXT_ALIAS
CFGAGENT_SCHED = ciscocfgagentscheduler.CFG_AGENT_SCHEDULER_ALIAS
CFG_AGENT_L3_ROUTING = cisco_constants.CFG_AGENT_L3_ROUTING


class L3RouterCfgAgentNotifyAPI(object):
    """API for plugin to notify Cisco cfg agent."""

    def __init__(self, l3plugin, topic=CFG_AGENT_L3_ROUTING):
        self._l3plugin = l3plugin
        target = messaging.Target(topic, version='1.0')
        self.client = n_rpc.get_client(target)

    def _agent_notification(self, context, method, routers, operation,
                            shuffle_agents):
        """Notify individual Cisco cfg agents."""
        admin_context = context.is_admin and context or context.elevated()
        dmplugin = manager.NeutronManager.get_service_plugins().get(
            svc_constants.DEVICE_MANAGER)
        for router in routers:
            if (router['hosting_device'] is not None and
                    utils.is_extension_supported(dmplugin, CFGAGENT_SCHED)):
                agents = dmplugin.get_cfg_agents_for_hosting_devices(
                    admin_context, [router['hosting_device']['id']],
                    admin_state_up=True, active=True, schedule=True)
            else:
                continue
            for agent in agents:
                LOG.debug('Notify %(agent_type)s at %(topic)s.%(host)s the '
                          'message %(method)s',
                          {'agent_type': agent.agent_type,
                           'topic': CFG_AGENT_L3_ROUTING,
                           'host': agent.host,
                           'method': method})
                cctxt = self.client.prepare(topic=CFG_AGENT_L3_ROUTING,
                                            server=agent.host,
                                            version='1.0')
                cctxt.cast(context, method, routers=[router['id']])

    def _notification(self, context, method, routers, operation,
                      shuffle_agents):
        """Notify all or individual Cisco cfg agents."""
        if utils.is_extension_supported(self._l3plugin, L3AGENT_SCHED):
            adm_context = (context.is_admin and context or context.elevated())
            # This is where hosting device gets scheduled to Cisco cfg agent
            self._l3plugin.schedule_routers(adm_context, routers)
            self._agent_notification(
                context, method, routers, operation, shuffle_agents)
        else:
            cctxt = self.client.prepare(topics=topics.L3_AGENT, fanout=True)
            cctxt.cast(context, method, routers=[r['id'] for r in routers])

    def router_deleted(self, context, router):
        """Notifies cfg agents about a deleted router."""
        self._agent_notification(context, 'router_deleted', [router], None,
                                 False)

    def routers_updated(self, context, routers, operation=None, data=None,
                        shuffle_agents=False):
        """Notifies cfg agents about configuration changes to routers.

        This includes operations performed on the router like when a
        router interface is added or removed.
        """
        if routers:
            self._notification(context, 'routers_updated', routers, operation,
                               shuffle_agents)

    def router_removed_from_hosting_device(self, context, router):
        """Notification that router has been removed from hosting device."""
        self._notification(context, 'router_removed_from_hosting_device',
                           [router], operation=None, shuffle_agents=False)

    def router_added_to_hosting_device(self, context, router):
        """Notification that router has been added to hosting device."""
        self._notification(context, 'router_added_to_hosting_device',
                           [router], operation=None, shuffle_agents=False)

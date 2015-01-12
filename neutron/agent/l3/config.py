# Copyright (c) 2015 OpenStack Foundation.
#
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

from oslo.config import cfg


OPTS = [
    cfg.StrOpt('agent_mode', default='legacy',
               help=_("The working mode for the agent. Allowed modes are: "
                      "'legacy' - this preserves the existing behavior "
                      "where the L3 agent is deployed on a centralized "
                      "networking node to provide L3 services like DNAT, "
                      "and SNAT. Use this mode if you do not want to "
                      "adopt DVR. 'dvr' - this mode enables DVR "
                      "functionality and must be used for an L3 agent "
                      "that runs on a compute host. 'dvr_snat' - this "
                      "enables centralized SNAT support in conjunction "
                      "with DVR.  This mode must be used for an L3 agent "
                      "running on a centralized node (or in single-host "
                      "deployments, e.g. devstack)")),
    cfg.StrOpt('external_network_bridge', default='br-ex',
               help=_("Name of bridge used for external network "
                      "traffic.")),
    cfg.IntOpt('metadata_port',
               default=9697,
               help=_("TCP Port used by Neutron metadata namespace "
                      "proxy.")),
    cfg.IntOpt('send_arp_for_ha',
               default=3,
               help=_("Send this many gratuitous ARPs for HA setup, if "
                      "less than or equal to 0, the feature is disabled")),
    cfg.StrOpt('router_id', default='',
               help=_("If namespaces is disabled, the l3 agent can only"
                      " configure a router that has the matching router "
                      "ID.")),
    cfg.BoolOpt('handle_internal_only_routers',
                default=True,
                help=_("Agent should implement routers with no gateway")),
    cfg.StrOpt('gateway_external_network_id', default='',
               help=_("UUID of external network for routers implemented "
                      "by the agents.")),
    cfg.BoolOpt('enable_metadata_proxy', default=True,
                help=_("Allow running metadata proxy.")),
    cfg.BoolOpt('router_delete_namespaces', default=False,
                help=_("Delete namespace after removing a router.")),
    cfg.StrOpt('metadata_proxy_socket',
               default='$state_path/metadata_proxy',
               help=_('Location of Metadata Proxy UNIX domain '
                      'socket')),
    cfg.StrOpt('metadata_proxy_user',
               default='',
               help=_("User (uid or name) running metadata proxy after "
                      "its initialization (if empty: L3 agent effective "
                      "user)")),
    cfg.StrOpt('metadata_proxy_group',
               default='',
               help=_("Group (gid or name) running metadata proxy after "
                      "its initialization (if empty: L3 agent effective "
                      "group)"))
]

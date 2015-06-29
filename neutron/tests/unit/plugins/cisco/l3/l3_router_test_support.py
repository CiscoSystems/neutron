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

import mock
from oslo_log import log as logging

from neutron.api.v2 import attributes
from neutron.common import test_lib
from neutron.db import common_db_mixin
from neutron.extensions import l3
import neutron.plugins
from neutron.plugins.cisco.db.l3 import l3_router_appliance_db
from neutron.plugins.cisco.db.l3 import routertype_db
from neutron.plugins.cisco.db.scheduler import (
    l3_routertype_aware_schedulers_db as router_sch_db)
from neutron.plugins.cisco.extensions import routerhostingdevice
from neutron.plugins.cisco.extensions import routerrole
from neutron.plugins.cisco.extensions import routertype
from neutron.plugins.common import constants as service_constants
from neutron.tests import base

LOG = logging.getLogger(__name__)


L3_PLUGIN_KLASS = (
    'neutron.tests.unit.plugins.cisco.l3.l3_router_test_support.'
    'TestL3RouterServicePlugin')
extensions_path = neutron.plugins.__path__[0] + '/cisco/extensions'


class L3RouterTestSupportMixin(object):

    def _mock_get_routertype_scheduler_always_none(self):
        self.get_routertype_scheduler_fcn_p = mock.patch(
            'neutron.plugins.cisco.db.l3.l3_router_appliance_db.'
            'L3RouterApplianceDBMixin._get_router_type_scheduler',
            mock.Mock(return_value=None))
        self.get_routertype_scheduler_fcn_p.start()

    def _add_router_plugin_ini_file(self):
        # includes config file for router service plugin
        cfg_file = (
            base.ROOTDIR +
            '/unit/plugins/cisco/etc/cisco_router_plugin.ini')
        if 'config_files' in test_lib.test_config:
            test_lib.test_config['config_files'].append(cfg_file)
        else:
            test_lib.test_config['config_files'] = [cfg_file]


class TestL3RouterBaseExtensionManager(object):

    def get_resources(self):
        # Add the resources to the global attribute map
        # This is done here as the setup process won't
        # initialize the main API router which extends
        # the global attribute map
        # first, add hosting device attribute to router resource
        l3.RESOURCE_ATTRIBUTE_MAP['routers'].update(
            routerhostingdevice.EXTENDED_ATTRIBUTES_2_0['routers'])
        # also add role attribute to router resource
        l3.RESOURCE_ATTRIBUTE_MAP['routers'].update(
            routerrole.EXTENDED_ATTRIBUTES_2_0['routers'])
        # also add routertype attribute to router resource
        l3.RESOURCE_ATTRIBUTE_MAP['routers'].update(
            routertype.EXTENDED_ATTRIBUTES_2_0['routers'])
        # finally, extend the global attribute map
        attributes.RESOURCE_ATTRIBUTE_MAP.update(
            l3.RESOURCE_ATTRIBUTE_MAP)
        res = l3.L3.get_resources()
        # add routertype resource
        for item in routertype.Routertype.get_resources():
            res.append(item)
        return res

    def get_actions(self):
        return []

    def get_request_extensions(self):
        return []


# A L3 routing service plugin class supporting the routertype and
# routerhost:hostingdevice extensions
class TestL3RouterServicePlugin(
    common_db_mixin.CommonDbMixin,
    routertype_db.RoutertypeDbMixin,
    l3_router_appliance_db.L3RouterApplianceDBMixin,
    # we need the router scheduling db but do not expose the scheduling
    # REST operations
        router_sch_db.L3RouterTypeAwareSchedulerDbMixin):

    supported_extension_aliases = [
        "router",
        routerhostingdevice.ROUTERHOSTINGDEVICE_ALIAS,
        routerrole.ROUTERROLE_ALIAS,
        routertype.ROUTERTYPE_ALIAS]

    def get_plugin_type(self):
        return service_constants.L3_ROUTER_NAT

    def get_plugin_description(self):
        return "L3 Routing Service Plugin for testing"

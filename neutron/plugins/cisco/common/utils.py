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

from functools import wraps
import imp
import time

from oslo_log import log as logging

from neutron.common import exceptions as nexception
from neutron.i18n import _LE

LOG = logging.getLogger(__name__)


class DriverNotFound(nexception.NetworkNotFound):
    message = _("Driver %(driver)s does not exist")


def retry(ExceptionToCheck, tries=4, delay=3, backoff=2):
    """Retry calling the decorated function using an exponential backoff.

    Reference: http://www.saltycrane.com/blog/2009/11/trying-out-retry
    -decorator-python/

    :param ExceptionToCheck: the exception to check. may be a tuple of
        exceptions to check
    :param tries: number of times to try (not retry) before giving up
    :param delay: initial delay between retries in seconds
    :param backoff: backoff multiplier e.g. value of 2 will double the delay
        each retry
    """
    def deco_retry(f):
        @wraps(f)
        def f_retry(*args, **kwargs):
            mtries, mdelay = tries, delay
            while mtries > 1:
                try:
                    return f(*args, **kwargs)
                except ExceptionToCheck as e:
                    LOG.debug("%(err_mess)s. Retry calling function "
                              "\'%(f_name)s\' in %(delta)d seconds.",
                              {'err_mess': str(e), 'f_name': f.__name__,
                               'delta': mdelay})
                    time.sleep(mdelay)
                    mtries -= 1
                    mdelay *= backoff
            LOG.debug("Last retry calling function \'%(f_name)s\'.",
                      {'err_mess': str(e), 'f_name': f.__name__,
                       'delta': mdelay})
            return f(*args, **kwargs)

        return f_retry  # true decorator

    return deco_retry


def convert_validate_driver_class(driver_class_name):
    # Verify that import_obj is a loadable class
    if driver_class_name is None or driver_class_name == '':
        return driver_class_name
    else:
        parts = driver_class_name.split('.')
        m_pathname = '/'.join(parts[:-1])
        try:
            info = imp.find_module(m_pathname)
            mod = imp.load_module(parts[-2], *info)
            if parts[-1] in dir(mod):
                return driver_class_name
        except ImportError as e:
            LOG.error(_LE('Failed to verify driver module %(name)s: %(err)s'),
                      {'name': driver_class_name, 'err': e})
    raise DriverNotFound(driver=driver_class_name)


# NOTE(bobmel): call _mock_ncclient() in main() of cfg_agent.py to run config
# agent with fake ncclient. That mocked mode of running the config agent is
# useful for end-2-end-like debugging without actual backend hosting devices.
def mock_ncclient():
    import mock
    import os
    import cisco_ios_xe_simulator as cisco_ios_xe

    def _fake_connect(host, port, username, password, device_params, timeout):
        sim = cisco_ios_xe.CiscoIOSXESimulator(
            '', host, "255.255.255.0", port, username, password,
            device_params, "GigabitEthernet0", timeout)
        connection_mock = mock.MagicMock()
        connection_mock.edit_config.side_effect = _get_fake_edit_config(sim)
        connection_mock.get_config.side_effect = (
            _get_fake_get_config(sim))
        return connection_mock

    def _get_fake_edit_config(simulator):

        def edit_config(config, format='xml', target='candidate',
                        default_operation=None, test_option=None,
                        error_option=None):
            rc_emul.edit_config(config)
            print rc_emul.get_config()
            return ok_xml_obj

        ok_xml_obj = mock.MagicMock()
        ok_xml_obj.xml = "<ok />"
        rc_emul = simulator
        return edit_config

    def _get_fake_get_config(simulator):

        def get_running_config(source):
            head=('<?xml version="1.0" encoding="UTF-8"?><rpc-reply '
                  'message-id="urn:uuid:ec8bab72-a500-11e5-a92f-74a2e6d55908" '
                  'xmlns="urn:ietf:params:xml:ns:netconf:base:1.0"><data>'
                  '<cli-config-data-block>!')
            tail = '</cli-config-data-block></data></rpc-reply>'
            raw_rc = rc_emul.get_config()
            return cisco_ios_xe.FakeRunningConfig(head + raw_rc + tail)

        rc_emul = simulator
        return get_running_config

    def _fake_is_pingable(ip):
        # if a file with a certain name (derived for the 'ip' argument):
        #
        #     /opt/stack/data/neutron/DEAD__10_0_5_8       (ip = 10.0.5.8)
        #
        # exists then the (faked) hosting device with that IP address
        # will appear to NOT respond to pings
        path = '/opt/stack/data/neutron'
        indicator_filename = path + '/DEAD_' + str(ip).replace('.', '_')
        return not os.path.isfile(indicator_filename)

    targets = ['neutron.plugins.cisco.cfg_agent.device_drivers.'
               'csr1kv.csr1kv_routing_driver.manager',
               'neutron.plugins.cisco.cfg_agent.device_drivers.'
               'csr1kv.iosxe_routing_driver.manager']
    ncc_patchers = []
    ncclient_mgr_mock = mock.MagicMock()
    ncclient_mgr_mock.connect.side_effect = _fake_connect

    for target in targets:
        patcher = mock.patch(target, ncclient_mgr_mock)
        patcher.start()
        ncc_patchers.append(patcher)

    is_pingable_mock = mock.MagicMock()
    is_pingable_mock.side_effect = _fake_is_pingable
    pingable_patcher = mock.patch(
        'neutron.plugins.cisco.cfg_agent.device_status._is_pingable',
        is_pingable_mock)
    pingable_patcher.start()

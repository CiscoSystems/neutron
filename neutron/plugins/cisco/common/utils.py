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
from neutron.i18n import _LE, _LW

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
                    LOG.warn(_LW("%(ex)s, Retrying in %(delt)d seconds.."),
                            {'ex': str(e), 'delt': mdelay})
                    time.sleep(mdelay)
                    mtries -= 1
                    mdelay *= backoff
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

    targets = ['neutron.plugins.cisco.cfg_agent.device_drivers.'
               'csr1kv.csr1kv_routing_driver.manager',
               'neutron.plugins.cisco.cfg_agent.device_drivers.'
               'csr1kv.iosxe_routing_driver.manager']
    ncc_patchers = []
    ncclient_mock = mock.MagicMock()
    ok_xml_obj = mock.MagicMock()
    ok_xml_obj.xml = "<ok />"
    ncclient_mock.connect.return_value.edit_config.return_value = ok_xml_obj
    for target in targets:
        patcher = mock.patch(target, ncclient_mock)
        patcher.start()
        ncc_patchers.append(patcher)

    targets = ['neutron.plugins.cisco.cfg_agent.device_drivers'
               '.csr1kv.csr1kv_routing_driver.CSR1kvRoutingDriver.'
               '_get_running_config',
               'neutron.plugins.cisco.cfg_agent.device_drivers.'
               'csr1kv.iosxe_routing_driver.IosXeRoutingDriver.'
               '_get_running_config',
               'neutron.plugins.cisco.cfg_agent.device_drivers.'
               'asr1k.asr1k_cfg_syncer.ConfigSyncer.get_running_config']
    fake_running_config = ("interface GigabitEthernet1\n"
                           "ip address 10.0.0.10 255.255.255.255\n"
                           "ip route 0.0.0.0 0.0.0.0 GigabitEthernet1 "
                           "10.0.0.1")
    g_r_c_patchers = []
    g_r_c_mock = mock.MagicMock(return_value=fake_running_config)
    empty_g_r_c_mock = mock.MagicMock(return_value=[""])
    g_r_c_mocks = [g_r_c_mock, g_r_c_mock, empty_g_r_c_mock]
    for i in range(len(targets)):
        patcher = mock.patch(targets[i], g_r_c_mocks[i])
        patcher.start()
        g_r_c_patchers.append(patcher)

    is_pingable_mock = mock.MagicMock(return_value=True)
    pingable_patcher = mock.patch(
        'neutron.plugins.cisco.cfg_agent.device_status._is_pingable',
        is_pingable_mock)
    pingable_patcher.start()

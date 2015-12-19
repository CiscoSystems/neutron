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
from oslo_utils import timeutils

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

    def managed_is_pingable(ip):
        # if a file with a certain name (derived for the 'ip' argument):
        #
        #     /opt/stack/data/neutron/DEAD__10_0_5_8       (ip = 10.0.5.8)
        #
        # exists then the (faked) hosting device with that IP address
        # will appear to NOT respond to pings
        path = '/opt/stack/data/neutron'
        indicator_filename = path + '/DEAD_' + str(ip).replace('.', '_')
        return not os.path.isfile(indicator_filename)

    def connect(host, port, username, password, device_params, timeout):
        emu = NCClientIosXeRunningConfigEmulator(
            '', host, port, username, password, device_params, timeout)
        connection_mock = mock.MagicMock()
        connection_mock.edit_config.side_effect = get_fake_edit_config(emu)
        connection_mock.get_config.side_effect = (
            get_fake_get_config(emu))
        return connection_mock

    def get_fake_edit_config(emulator):

        def edit_config(config, format='xml', target='candidate',
                        default_operation=None, test_option=None,
                        error_option=None):
            rc_emul.edit_config(config)
            print rc_emul.get_config()
            return ok_xml_obj

        rc_emul = emulator
        return edit_config

    def get_fake_get_config(emulator):

        def get_running_config(source):
            head=('<?xml version="1.0" encoding="UTF-8"?><rpc-reply '
                  'message-id="urn:uuid:ec8bab72-a500-11e5-a92f-74a2e6d55908" '
                  'xmlns="urn:ietf:params:xml:ns:netconf:base:1.0"><data>'
                  '<cli-config-data-block>!')
            tail = '</cli-config-data-block></data></rpc-reply>'
            raw_rc = rc_emul.get_config()
            return RunningConfig(head + raw_rc + tail)

        rc_emul = emulator
        return get_running_config

    ok_xml_obj = mock.MagicMock()
    ok_xml_obj.xml = "<ok />"

    targets = ['neutron.plugins.cisco.cfg_agent.device_drivers.'
               'csr1kv.csr1kv_routing_driver.manager',
               'neutron.plugins.cisco.cfg_agent.device_drivers.'
               'csr1kv.iosxe_routing_driver.manager']
    ncc_patchers = []
    ncclient_mgr_mock = mock.MagicMock()
    ncclient_mgr_mock.connect.side_effect = connect

    for target in targets:
        patcher = mock.patch(target, ncclient_mgr_mock)
        patcher.start()
        ncc_patchers.append(patcher)

    is_pingable_mock = mock.MagicMock()
    is_pingable_mock.side_effect = managed_is_pingable
    pingable_patcher = mock.patch(
        'neutron.plugins.cisco.cfg_agent.device_status._is_pingable',
        is_pingable_mock)
    pingable_patcher.start()


class RunningConfig(object):
    def __init__(self, rc):
        self._raw = rc


import re


class NCClientIosXeRunningConfigEmulator(object):

    log_only_commands = {'exit-address-family'}

    def __init__(self, path, host_ip, port, username, password, device_params,
                 timeout):
#        self.rcf = path + 'running_config_' + host_ip.replace('.', '_')
        self.host_ip = host_ip
        self.port = port
        self.username = username
        self.password = password
        self.device_params = device_params
        self.timeout = timeout
        self.rc = self._get_dict()

    def get_config(self):
        ts = timeutils.utcnow()
        change_date = timeutils.strtime(ts, '%a %b %d %Y')
        change_time = timeutils.strtime(ts, '%H:%M:%S')
        intro_lines = ("! Last configuration change at " + change_time + " " +
                       "UTC " + change_date + " by " + self.username + "\n!\n")
        rc_data = {'rc_str': intro_lines}
        for cmd, args in sorted(self.rc.iteritems()):
            line = cmd
            self._build_line(rc_data, args, line, True)
        return rc_data['rc_str']

    def edit_config(self, snippet):
        command_lines = self._get_command_lines(snippet)
        if not command_lines:
            return
        pre, main_cmd_line = self._get_command_prepending(command_lines[0])
        if pre is None:
            self._process_next_level(self.rc, self.rc, command_lines, True)
        elif pre == "no":
            pass
        elif pre == "do":
            pass
        return True

    def _build_line(self, rc_data, current_dict, baseline, is_root=False):
        for current, the_rest in sorted(current_dict.iteritems()):
            if current == 'EOL':
                continue
            line = baseline
            line += ' ' + current if line != "" else current
            if 'EOL' in the_rest:
                rc_data['rc_str'] += line + "\n"
                line = ""
            self._build_line(rc_data, the_rest, line)
            if is_root is True:
                rc_data['rc_str'] += "!\n"

    def _process_next_level(self, parent, current_dict, remaining_lines,
                            is_root=False):
        if not remaining_lines:
            return
        cmd_line = remaining_lines[0]
        cmd, args = self._get_command_and_args(cmd_line)
        if cmd in self.log_only_commands:
            self._process_next_level(parent, current_dict, remaining_lines[1:])
            return
        level_dict = parent.get(cmd)
        if level_dict is None:
            level_dict = current_dict.get(cmd)
            if level_dict is None:
                level_dict = self._get_dict()
                current_dict[cmd] = level_dict
                current_parent = parent if is_root is False else level_dict
            else:
                current_parent = current_dict
        else:
            current_parent = current_dict
        for arg in args:
            next_dict = level_dict.get(arg)
            if next_dict is None:
                next_dict = self._get_dict()
                level_dict[arg] = next_dict
            else:
                current_parent = level_dict
            level_dict = next_dict
        level_dict['EOL'] = True
        if is_root is True:
            current_dict = level_dict
        self._process_next_level(current_parent, current_dict,
                                 remaining_lines[1:])

    def _get_command_lines(self, snippet):
        if not snippet:
            return []
        lines = snippet.split('\n')
        commands = []
        for line in lines:
            if self._should_skip_line(line):
                continue
            cmd = self._get_embedded_command_string(line)
            if cmd is not None:
                commands.append(cmd)
        return commands

    def _should_skip_line(self, line):
        if line == "":
            return True
        if line.find("config>") != -1:
            return True
        elif line.find("cli-config-data>") != -1:
            return True
        return False

    def _get_embedded_command_string(self, line):
        match_obj = re.match(r'\s*<cmd>(.*)</cmd>\s*', line)
        if match_obj:
            return match_obj.group(1)
        return None

    def _get_command_prepending(self, cmd):
        match_obj = re.match(r'\s*(no|do) (.*)\s*', cmd)
        if match_obj:
            return match_obj.group(1), match_obj.group(2)
        return None, cmd

    def _get_command_and_args(self, cmd):
        str_list = cmd.split(" ")
        return str_list[0], str_list[1:]

    def _get_dict(self):
        return {}

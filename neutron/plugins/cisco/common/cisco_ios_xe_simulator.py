import re

from oslo_utils import timeutils


class CiscoIOSXESimulator(object):

    # set of commands to be logged only
    log_only_commands = set()
    # set of commands bound to immediately preceding line
    parent_bound_commands = {'address-family'}

    def __init__(self, path, host_ip, netmask, port, username, password,
                 device_params, mgmt_interface, timeout):
#        self.rcf = path + 'running_config_' + host_ip.replace('.', '_')
        self.host_ip = host_ip
        self.netmask = netmask
        self.port = port
        self.username = username
        self.password = password
        self.device_params = device_params
        self.mgmt_interface = mgmt_interface
        self.timeout = timeout
        self.rc = self._get_dict()
        self._set_default_config()

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
        self._process_next_level(self.rc, self.rc, command_lines, True)
        return True

    def _set_default_config(self):
        command_chunks = [
            ["vrf definition Mgmt-intf",
             "address-family ipv4",
             "exit-address-family",
             "address-family ipv6",
             "exit-address-family"],
            ["interface " + self.mgmt_interface,
             "vrf forwarding Mgmt-intf",
             "ip address " + self.host_ip + " " + self.netmask,
             "negotiation auto"]
        ]
        for commands in command_chunks:
            self._process_next_level(self.rc, self.rc, commands, True)

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
        pre, cmd_line = self._get_command_prepending(remaining_lines[0])
        if pre is None:
            self._process_set(cmd_line, parent, current_dict,
                              remaining_lines, is_root)
        elif pre.lower() == "no":
            self._process_unset(cmd_line.split(" "), current_dict)

    def _process_set(self, cmd_line, parent, current_dict, remaining_lines,
                     is_root):
        cmd, args = self._get_command_and_args(cmd_line)
        if cmd in self.log_only_commands:
            self._process_next_level(parent, current_dict, remaining_lines[1:])
            return
        level_dict = parent.get(cmd)
        if level_dict is None:
            level_dict, current_parent = self._get_successor_and_its_parent(
                parent, cmd, current_dict, is_root)
        else:
            current_parent = current_dict
        for arg in args:
            next_dict, current_parent = self._get_successor_and_its_parent(
                current_parent, arg, level_dict, is_root)
            level_dict = next_dict
        level_dict['EOL'] = True
        if is_root is True:
            current_dict = level_dict
        self._process_next_level(current_parent, current_dict,
                                 remaining_lines[1:])

    def _process_unset(self, remaining, current):
        if not remaining:
            return
        arg = remaining[0]
        rest = remaining[1:]
        if arg in current:
            if not rest:
                del current[arg]
            else:
                self._process_unset(rest, current[arg])
                num_items = len(current[arg])
                if num_items == 0:                                   
                    del current[arg]

    def _get_successor_and_its_parent(self, parent, string, current, is_root):
        successor = current.get(string)
        if successor is None:
            successor = self._get_dict()
            current[string] = successor
            current_parent = parent if is_root is False else successor
        else:
            current_parent = current
        return successor, current_parent

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

    def _get_command_and_args(self, cmd_line):
        str_list = cmd_line.split(" ")
        return str_list[0], str_list[1:]

    def _get_dict(self):
        return {}


# A simple Cisco IOS XE CLI simulator
class FakeRunningConfig(object):
    def __init__(self, rc):
        self._raw = rc
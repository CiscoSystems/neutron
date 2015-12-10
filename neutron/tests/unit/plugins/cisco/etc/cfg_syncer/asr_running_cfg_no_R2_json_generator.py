
import json
import pprint as pp

asr_running_cfg = ['!',
 '! Last configuration change at 17:00:50 UTC Tue Dec 8 2015 by admin',
 '!',
 'version 15.5',
 'service timestamps debug datetime msec',
 'service timestamps log datetime msec',
 'no platform punt-keepalive disable-kernel-core',
 '!',
 'hostname hh30ASR-1006-top',
 '!',
 'boot-start-marker',
 'boot system flash bootflash:asr1000rp2-adventerprisek9.03.16.01a.S.155-3.S1a-ext.bin',
 'boot-end-marker',
 '!',
 '!',
 'vrf definition Mgmt-intf',
 ' !',
 ' address-family ipv4',
 ' exit-address-family',
 ' !',
 ' address-family ipv6',
 ' exit-address-family',
 '!',
 'vrf definition nrouter-9ad979-0000001',
 ' !',
 ' address-family ipv4',
 ' exit-address-family',
 ' !',
 ' address-family ipv6',
 ' exit-address-family',
 '!',
 'no logging console',
 '!',
 'no aaa new-model',
 '!',
 'no ip domain lookup',
 'ip domain name ctocllab.cisco.com',
 '!',
 'subscriber templating',
 '!',
 'multilink bundle-name authenticated',
 '!',
 'spanning-tree extend system-id',
 '!',
 'username admin privilege 15 password 0 password',
 'username onecloud privilege 15 password 0 password',
 '!',
 'redundancy',
 ' mode sso',
 '!',
 'cdp run',
 '!',
 'interface Port-channel10',
 ' no ip address',
 '!',
 'interface Port-channel10.165',
 ' description OPENSTACK_NEUTRON_0000001_INTF',
 ' encapsulation dot1Q 165',
 ' ip address 10.23.229.153 255.255.255.240',
 ' ip nat outside',
 ' standby delay minimum 30 reload 60',
 ' standby version 2',
 ' standby 1064 ip 10.23.229.152',
 ' standby 1064 timers 1 3',
 ' standby 1064 priority 20',
 ' standby 1064 name neutron-hsrp-1064-165',
 '!',
 'interface Port-channel10.2005',
 ' description OPENSTACK_NEUTRON_0000001_INTF',
 ' encapsulation dot1Q 2005',
 ' vrf forwarding nrouter-9ad979-0000001',
 ' ip address 192.168.3.15 255.255.255.0',
 ' ip nat inside',
 ' standby delay minimum 30 reload 60',
 ' standby version 2',
 ' standby 1064 ip 192.168.3.1',
 ' standby 1064 timers 1 3',
 ' standby 1064 priority 10',
 ' standby 1064 name neutron-hsrp-1064-2005',
 '!',
 'interface Port-channel10.2029',
 ' description OPENSTACK_NEUTRON_0000001_INTF',
 ' encapsulation dot1Q 2029',
 ' vrf forwarding nrouter-9ad979-0000001',
 ' ip address 192.168.2.15 255.255.255.0',
 ' ip nat inside',
 ' standby delay minimum 30 reload 60',
 ' standby version 2',
 ' standby 1064 ip 192.168.2.1',
 ' standby 1064 timers 1 3',
 ' standby 1064 priority 10',
 ' standby 1064 name neutron-hsrp-1064-2029',
 '!',
 'interface Port-channel10.2031',
 ' description OPENSTACK_NEUTRON_0000001_INTF',
 ' encapsulation dot1Q 2031',
 ' vrf forwarding nrouter-9ad979-0000001',
 ' ip address 192.168.1.30 255.255.255.0',
 ' ip nat inside',
 ' standby delay minimum 30 reload 60',
 ' standby version 2',
 ' standby 1064 ip 192.168.1.1',
 ' standby 1064 timers 1 3',
 ' standby 1064 priority 10',
 ' standby 1064 name neutron-hsrp-1064-2031',
 '!',
 'interface Port-channel10.2044',
 ' description OPENSTACK_NEUTRON_0000001_INTF',
 ' encapsulation dot1Q 2044',
 ' vrf forwarding nrouter-9ad979-0000001',
 ' ip address 192.168.0.4 255.255.255.0',
 ' ip nat inside',
 ' standby delay minimum 30 reload 60',
 ' standby version 2',
 ' standby 1064 ip 192.168.0.1',
 ' standby 1064 timers 1 3',
 ' standby 1064 priority 10',
 ' standby 1064 name neutron-hsrp-1064-2044',
 '!',
 'interface Port-channel10.2499',
 ' ip nat outside',
 '!',
 'interface TenGigabitEthernet0/0/0',
 ' no ip address',
 ' cdp enable',
 ' channel-group 10 mode active',
 '!',
 'interface TenGigabitEthernet0/1/0',
 ' no ip address',
 ' cdp enable',
 ' channel-group 10 mode active',
 '!',
 'interface TenGigabitEthernet0/3/0',
 ' no ip address',
 ' shutdown',
 '!',
 'interface GigabitEthernet0',
 ' vrf forwarding Mgmt-intf',
 ' ip address 172.20.231.19 255.255.255.0',
 ' negotiation auto',
 ' no mop enabled',
 '!',
 'ip nat pool nrouter-9ad979-0000001_nat_pool 10.23.229.149 10.23.229.149 netmask 255.255.255.240',
  'ip nat inside source static 192.168.0.3 10.23.229.154 vrf nrouter-9ad979-0000001 redundancy neutron-hsrp-1064-165',
 'ip nat inside source static 192.168.2.13 10.23.229.155 vrf nrouter-9ad979-0000001 redundancy neutron-hsrp-1064-165',
 'ip nat inside source list neutron_acl_0000001_2005 pool nrouter-9ad979-0000001_nat_pool vrf nrouter-9ad979-0000001 overload',
 'ip nat inside source list neutron_acl_0000001_2029 pool nrouter-9ad979-0000001_nat_pool vrf nrouter-9ad979-0000001 overload',
 'ip nat inside source list neutron_acl_0000001_2031 pool nrouter-9ad979-0000001_nat_pool vrf nrouter-9ad979-0000001 overload',
 'ip nat inside source list neutron_acl_0000001_2044 pool nrouter-9ad979-0000001_nat_pool vrf nrouter-9ad979-0000001 overload',
 'ip forward-protocol nd',
 '!',
 'ip ftp source-interface GigabitEthernet0',
 'no ip http server',
 'no ip http secure-server',
 'ip tftp source-interface GigabitEthernet0',
 'ip route vrf Mgmt-intf 0.0.0.0 0.0.0.0 172.20.231.1',
 'ip route vrf nrouter-9ad979-0000001 0.0.0.0 0.0.0.0 Port-channel10.165 10.23.229.145',
 'ip ssh maxstartups 16',
 'ip ssh time-out 60',
 'ip ssh authentication-retries 2',
 'ip ssh source-interface GigabitEthernet0',
 'ip ssh rsa keypair-name ssh-key',
 'ip ssh version 2',
 'ip scp server enable',
 '!',
 'ip access-list standard neutron_acl_0000001_2005',
 ' permit 192.168.3.0 0.0.0.255',
 'ip access-list standard neutron_acl_0000001_2029',
 ' permit 192.168.2.0 0.0.0.255',
 'ip access-list standard neutron_acl_0000001_2031',
 ' permit 192.168.1.0 0.0.0.255',
 'ip access-list standard neutron_acl_0000001_2044',
 ' permit 192.168.0.0 0.0.0.255',
 '!',
 '!',
 'control-plane',
 '!',
 '!',
 'line con 0',
 ' stopbits 1',
 'line aux 0',
 ' stopbits 1',
 'line vty 0 4',
 ' exec-timeout 0 0',
 ' login local',
 'line vty 5 15',
 ' login local',
 '!',
 'netconf max-sessions 16',
 'netconf max-message 1000000',
 'netconf ssh',
 '!',
 'end',
 '']

with open('asr_running_cfg_no_R2.json', 'w') as fp:
    json.dump(asr_running_cfg, fp)

# test it
with open('asr_running_cfg_no_R2.json', 'r') as fp:
    reread_data =json.load(fp)

print(pp.pformat(reread_data))

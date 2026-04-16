# Script gerado pelo MikroTik Config Tool
# RouterOS alvo: v7
# Perfil de firewall: medium
# Revise antes de aplicar em producao

/system identity
set name="MikroTik-v7"

/interface bridge
add name=bridge-lan protocol-mode=rstp

/interface bridge port
add bridge=bridge-lan interface=ether2

/ip address
add address=192.168.1.1/24 interface=bridge-lan comment="LAN principal"

/ip pool
add name=pool-lan ranges=192.168.1.10-192.168.1.254

/ip dhcp-server
add name=dhcp-lan interface=bridge-lan address-pool=pool-lan disabled=no

/ip dhcp-server network
add address=192.168.1.0/24 gateway=192.168.1.1 dns-server=192.168.1.1

/ip dns
set allow-remote-requests=yes

/interface pppoe-client
add name=pppoe-out1 interface=ether1 user="your-pppoe-user" password="your-pppoe-password" add-default-route=yes use-peer-dns=yes disabled=no

/interface list
add name=WAN comment="Created by MikroTik Config Tool"
add name=LAN comment="Created by MikroTik Config Tool"

/interface list member
add interface=pppoe-out1 list=WAN
add interface=bridge-lan list=LAN

/ip firewall filter
add chain=input action=accept connection-state=established,related,untracked comment="mtk-tool input established"
add chain=input action=drop connection-state=invalid comment="mtk-tool input invalid"
add chain=input action=accept protocol=icmp comment="mtk-tool input icmp"
add chain=input action=accept in-interface-list=LAN comment="mtk-tool allow lan management"
add chain=input action=drop in-interface-list=WAN protocol=tcp psd=21,3s,3,1 comment="mtk-tool drop port scan"
add chain=input action=drop in-interface-list=WAN protocol=tcp dst-port=22 connection-limit=3,32 comment="mtk-tool drop ssh bruteforce"
add chain=input action=drop in-interface-list=WAN protocol=udp dst-port=53 comment="mtk-tool drop wan dns udp"
add chain=input action=drop in-interface-list=WAN protocol=tcp dst-port=53 comment="mtk-tool drop wan dns tcp"
add chain=input action=drop in-interface-list=WAN comment="mtk-tool drop wan input"
add chain=forward action=accept connection-state=established,related,untracked comment="mtk-tool forward established"
add chain=forward action=drop connection-state=invalid comment="mtk-tool forward invalid"
add chain=forward action=accept in-interface-list=LAN out-interface-list=WAN comment="mtk-tool allow lan to wan"
add chain=forward action=accept connection-nat-state=dstnat in-interface-list=WAN comment="mtk-tool allow dstnat"
add chain=forward action=drop connection-state=new connection-nat-state=!dstnat in-interface-list=WAN comment="mtk-tool drop new wan forward"

/ip firewall nat
add chain=srcnat action=masquerade out-interface=pppoe-out1 comment="mtk-tool nat masquerade"

/ip service
set [find name=winbox] disabled=no
set [find name=ssh] disabled=no
set [find name=www] disabled=yes
set [find name=www-ssl] disabled=yes
set [find name=api] disabled=yes
set [find name=api-ssl] disabled=yes
set [find name=ftp] disabled=yes
set [find name=telnet] disabled=yes

auto lo
iface lo inet loopback

iface nic0 inet manual

iface nic1 inet manual

auto bond0
iface bond0 inet manual
    bond-slaves nic0 nic1
    bond-miimon 100
    bond-mode active-backup
    bond-primary nic0

# WAN Bridge (VLAN 999 - Untagged/Native from Switch)
auto vmbr999
iface vmbr999 inet manual
    bridge-ports bond0
    bridge-stp off
    bridge-fd 0
    # Collegata a OPNsense WAN

# Management / Transit Bridge (VLAN 1)
auto vmbr0
iface vmbr0 inet static
    address 192.168.2.125/24
    gateway 192.168.2.254
    bridge-ports bond0.1
    bridge-stp off
    bridge-fd 0
    # Gateway punta al VIP di OPNsense

# Server Bridge (VLAN 10)
auto vmbr10
iface vmbr10 inet manual
    bridge-ports bond0.10
    bridge-stp off
    bridge-fd 0

# Client Bridge (VLAN 20)
auto vmbr20
iface vmbr20 inet manual
    bridge-ports bond0.20
    bridge-stp off
    bridge-fd 0

# IoT Bridge (VLAN 30)
auto vmbr30
iface vmbr30 inet manual
    bridge-ports bond0.30
    bridge-stp off
    bridge-fd 0

# this is the schema of future nework:

## new Fisical Nodes Proxmox Cluster:
 - pve proxmox installation
    ### Physical ports
    - Port 1: 10Gbs NIC installed on switch10g Vlan 20
    - Port 2: 10Gbs NIC installed on switch10g Vlan 30
    - Port 3: 2.5Gbs NIC installed on switch25gMS Vlan 1
 - pve2 proxmon installation
    ### Physical ports
    - Port 1: 2.5Gbs NIC installed on switch25gML Vlan 20
    - Port 2: 2.5bs NIC installed on switch25g Vlan 30
 - pve3 proxmox installation
    ### Physical ports
    - Port 1: 2.5Gbs NIC installed on switch25gML Vlan 20
    - Port 2: 2.5Gbs NIC installed on switch25g Vlan 30

 ## VM nodes:
    proxmox installed on pve node
    ### Bridge ports from pve node
    - Port 1: 10Gbs NIC installed on switch10g Vlan 20
    - Port 2: 10Gbs NIC installed on switch10g Vlan 30 
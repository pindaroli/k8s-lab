#!/bin/bash

# Configuration
VMID=2100

echo "Configurazione Network per OPNsense VM $VMID..."

# 1. Stop VM (per applicare cambi hardware)
echo "Stopping VM $VMID..."
qm stop $VMID
sleep 5

# 2. Configura Interfacce di Rete
# net0 -> WAN (Native VLAN su switch stupido) -> vmbr999
# net1 -> Management/Transit (VLAN 1) -> vmbr0
# net2 -> Server (VLAN 10) -> vmbr10
# net3 -> Client (VLAN 20) -> vmbr20

echo "Applying Network Interface settings..."
qm set $VMID --net0 virtio,bridge=vmbr999
qm set $VMID --net1 virtio,bridge=vmbr0
qm set $VMID --net2 virtio,bridge=vmbr10
qm set $VMID --net3 virtio,bridge=vmbr20
qm set $VMID --net4 virtio,bridge=vmbr30

# 3. Start VM
echo "Starting VM $VMID..."
qm start $VMID

echo "Done! OPNsense configuration applied."

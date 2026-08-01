#!/bin/bash
# install_gpu_mgmt.sh
# Script di automazione per installare la gestione GPU su PVE2

PVE_IP="10.10.10.21"

echo "Creazione directory scripts su PVE2..."
ssh root@$PVE_IP "mkdir -p /root/scripts"

echo "Copia degli script su PVE2..."
scp $(dirname "$0")/gpu_on.sh $(dirname "$0")/gpu_off.sh root@$PVE_IP:/root/scripts/
ssh root@$PVE_IP "chmod +x /root/scripts/gpu_on.sh /root/scripts/gpu_off.sh"

echo "Configurazione Blacklist Driver..."
ssh root@$PVE_IP 'cat << "EOF" > /etc/modprobe.d/blacklist-nvidia-power.conf
blacklist nouveau
blacklist nvidia
blacklist nvidia_drm
blacklist nvidia_modeset
blacklist i2c_nvidia_gpu
EOF'

echo "Configurazione Regola Udev..."
ssh root@$PVE_IP 'cat << "EOF" > /etc/udev/rules.d/99-remove-nvidia.rules
# Rimuove la GPU NVIDIA e l'\''Audio associato al boot
ACTION=="add", SUBSYSTEM=="pci", ATTR{vendor}=="0x10de", ATTR{class}=="0x03[0-9]*", ATTR{remove}="1"
ACTION=="add", SUBSYSTEM=="pci", ATTR{vendor}=="0x10de", ATTR{class}=="0x040300", ATTR{remove}="1"
EOF'

echo "Aggiornamento initramfs (potrebbe richiedere un minuto)..."
ssh root@$PVE_IP "update-initramfs -u -k all"

echo "Installazione completata con successo."

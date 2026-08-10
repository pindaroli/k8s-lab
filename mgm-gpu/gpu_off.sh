#!/bin/bash
VM_ID=2500

echo "Controllo lo stato della VM $VM_ID..."
VM_STATUS=$(qm status $VM_ID 2>/dev/null | grep -o 'running')
if [ "$VM_STATUS" == "running" ]; then
    echo "ERRORE CRITICO: La VM $VM_ID è attualmente accesa! Spegnere la VM prima di disabilitare la GPU per evitare un Kernel Panic."
    exit 1
fi

echo "Ripristino la regola udev di risparmio energetico..."
if [ -f /etc/udev/rules.d/99-remove-nvidia.rules.disabled ]; then
    mv /etc/udev/rules.d/99-remove-nvidia.rules.disabled /etc/udev/rules.d/99-remove-nvidia.rules
fi

echo "Sgancio la GPU NVIDIA dal bus PCI..."
# Rimozione Logica della GPU
if [ -d /sys/bus/pci/devices/0000:03:00.0 ]; then
    echo 1 > /sys/bus/pci/devices/0000:03:00.0/remove
fi
# Rimozione Logica dell'Audio GPU
if [ -d /sys/bus/pci/devices/0000:03:00.1 ]; then
    echo 1 > /sys/bus/pci/devices/0000:03:00.1/remove
fi

echo "Operazione completata. GPU disabilitata (Power Off Logico)."

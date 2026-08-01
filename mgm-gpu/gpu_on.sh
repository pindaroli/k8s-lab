#!/bin/bash

echo "Forzo la scansione del bus PCI per risvegliare la GPU NVIDIA..."
echo 1 > /sys/bus/pci/rescan
sleep 2

# Verifica del successo controllando se il dispositivo compare nuovamente sul bus
if lspci -nn | grep -i nvidia > /dev/null; then
    echo "Operazione completata con successo: GPU risvegliata e pronta per l'uso."
else
    echo "ERRORE: GPU non trovata sul bus PCI. Il BIOS potrebbe aver bloccato il risveglio PCIe."
    exit 1
fi

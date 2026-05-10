#!/bin/bash
# PROXMOX MAINTENANCE MODE SCRIPT
# Node 1: Talos=1300, Recovery=1900

TALOS_ID=1300
RECOVERY_ID=1900
DISK_PATH="/dev/disk/by-id/nvme-uuid.7a44c5b4-d688-41e3-9aad-3871fbf66b82"
DISK_SLOT="scsi1"

case "$1" in
  on)
    echo ">>> ENTERING MAINTENANCE MODE (Recovery)..."
    # Stop Talos
    qm stop $TALOS_ID
    # Stacca da Talos
    qm set $TALOS_ID --delete $DISK_SLOT

    # Attacca a Recovery
    # (Ignora errore se slot già libero)
    qm set $RECOVERY_ID --delete $DISK_SLOT 2>/dev/null
    qm set $RECOVERY_ID --$DISK_SLOT $DISK_PATH,ssd=1

    # Avvia Recovery
    qm start $RECOVERY_ID
    echo "DONE. Recovery VM ($RECOVERY_ID) started."
    ;;
  off)
    echo ">>> EXITING MAINTENANCE MODE (Talos)..."
    # Stop Recovery
    qm stop $RECOVERY_ID
    # Stacca da Recovery
    qm set $RECOVERY_ID --delete $DISK_SLOT

    # Attacca a Talos
    qm set $TALOS_ID --$DISK_SLOT $DISK_PATH,ssd=1

    # Avvia Talos
    qm start $TALOS_ID
    echo "DONE. Talos VM ($TALOS_ID) started."
    ;;
  *)
    echo "Usage: $0 {on|off}"
    ;;
esac

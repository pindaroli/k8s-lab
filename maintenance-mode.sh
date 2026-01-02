#!/bin/bash
# PROXMOX MAINTENANCE MODE SCRIPT
# Convention: 
# Node 1 (pve) -> Talos 1300, Recovery 1900

# --- CONFIGURATION (NODE 1) ---
TALOS_ID=1300
RECOVERY_ID=1900
DISK_PATH="/dev/disk/by-id/nvme-uuid.7a44c5b4-d688-41e3-9aad-3871fbf66b82" 
DISK_SLOT="scsi1" 
# ------------------------------

case "$1" in
  on)
    echo "ENTERING MAINTENANCE MODE (Recovery)..."
    echo "1. Stopping Talos (VM $TALOS_ID)..."
    qm stop $TALOS_ID
    
    echo "2. Detaching Disk from Talos..."
    qm set $TALOS_ID --delete $DISK_SLOT
    
    echo "3. Attaching Disk to Recovery (VM $RECOVERY_ID)..."
    # Ensure slot is free
    qm set $RECOVERY_ID --delete $DISK_SLOT 2>/dev/null
    # Attach as pass-through
    qm set $RECOVERY_ID --$DISK_SLOT $DISK_PATH,ssd=1
    
    echo "4. Starting Recovery VM..."
    qm start $RECOVERY_ID
    echo "DONE. SSH into VM $RECOVERY_ID to migrate data."
    ;;
  off)
    echo "EXITING MAINTENANCE MODE (Talos)..."
    echo "1. Stopping Recovery (VM $RECOVERY_ID)..."
    qm stop $RECOVERY_ID
    
    echo "2. Detaching Disk from Recovery..."
    qm set $RECOVERY_ID --delete $DISK_SLOT
    
    echo "3. Attaching Disk to Talos (VM $TALOS_ID)..."
    # Attach as pass-through (SSD emulation on)
    qm set $TALOS_ID --$DISK_SLOT $DISK_PATH,ssd=1
    
    echo "4. Starting Talos VM..."
    qm start $TALOS_ID
    echo "DONE. Talos is booting with the Hot Disk."
    ;;
  *)
    echo "Usage: $0 {on|off}"
    echo "  on  = Stop Talos, Move Disk to Recovery, Start Recovery"
    echo "  off = Stop Recovery, Move Disk to Talos, Start Talos"
    ;;
esac

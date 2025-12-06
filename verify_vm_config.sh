#!/bin/bash

VMID=$1
EXPECTED_BOOT_ORDER="ide2;virtio0;net0"
EXPECTED_ISO="local:iso/talos-v1.9.0-metal-amd64.iso"

if [ -z "$VMID" ]; then
  echo "Usage: $0 <vmid>"
  exit 1
fi

echo "Checking configuration for VM $VMID..."

# Get current config
CONFIG=$(qm config $VMID)

# Check Boot Order
CURRENT_BOOT_ORDER=$(echo "$CONFIG" | grep "^boot:" | cut -d'=' -f2 | xargs)
if [ "$CURRENT_BOOT_ORDER" == "$EXPECTED_BOOT_ORDER" ]; then
  echo "[OK] Boot order is correct: $CURRENT_BOOT_ORDER"
else
  echo "[ERROR] Boot order mismatch!"
  echo "  Expected: $EXPECTED_BOOT_ORDER"
  echo "  Actual:   $CURRENT_BOOT_ORDER"
fi

# Check ISO Attachment
if echo "$CONFIG" | grep -q "$EXPECTED_ISO"; then
  echo "[OK] Talos ISO is attached."
else
  echo "[ERROR] Talos ISO not found in configuration!"
fi

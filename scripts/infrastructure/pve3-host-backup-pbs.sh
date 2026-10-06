#!/bin/bash
set -e

# Carica password del datastore PBS da storage.cfg credentials
if [ -f /etc/pve/priv/storage/pbs.pw ]; then
    export PBS_PASSWORD=$(cat /etc/pve/priv/storage/pbs.pw)
fi

export PBS_REPOSITORY="root@pam@10.10.10.100:pbs-store"
export PBS_FINGERPRINT="93:B3:92:68:5C:04:3C:30:18:EF:CB:53:09:6B:A6:1F:0E:4C:94:F6:76:08:CC:56:13:8B:19:31:86:9C:87:EF"

echo "[$(date '+%Y-%m-%d %H:%M:%S')] Starting PVE3 host scripts backup to PBS ($PBS_REPOSITORY)..."

proxmox-backup-client backup \
  scripts.pxar:/usr/local/bin \
  snippets.pxar:/var/lib/vz/snippets \
  --backup-id pve3-host \
  --backup-type host \
  --repository "$PBS_REPOSITORY"

echo "[$(date '+%Y-%m-%d %H:%M:%S')] PVE3 host backup completed successfully."

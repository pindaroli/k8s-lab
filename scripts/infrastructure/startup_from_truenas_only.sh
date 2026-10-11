#!/usr/bin/env bash
# Avvio K8s e Proxmox dalla modalità solo TrueNAS con uncordon sincronizzato.

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"
cd "$ROOT_DIR" || exit 1

echo "🚀 Avvio sequenza di startup K8s e Proxmox VE (con Sync Barrier Uncordon)..."
echo "➡️  Transizione: Da modalità Eco TrueNAS-only a Full Homelab Cluster."
echo ""
ansible-playbook -i ansible/inventory.ini ansible/playbooks/infrastructure/startup_from_truenas_only.yml

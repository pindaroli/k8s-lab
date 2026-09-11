#!/usr/bin/env bash
# Script per spegnere il cluster Kubernetes in sicurezza (Metodo B).

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"
cd "$ROOT_DIR" || exit 1

echo "🔴 Avvio sequenza di spegnimento K8s (Metodo B)..."
ansible-playbook -i ansible/inventory.ini ansible/playbooks/infrastructure/shutdown_talos_graceful.yml

echo ""
echo "✅ Operazione completata. Ora puoi spegnere fisicamente TrueNAS e Proxmox."

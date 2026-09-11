#!/usr/bin/env bash
# Script per avviare il cluster Kubernetes verificando TrueNAS.

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"
cd "$ROOT_DIR" || exit 1

echo "🟢 Avvio sequenza di startup K8s e verifica TrueNAS..."
ansible-playbook -i ansible/inventory.ini ansible/playbooks/infrastructure/startup_talos_graceful.yml

echo ""
echo "✅ Cluster operativo."

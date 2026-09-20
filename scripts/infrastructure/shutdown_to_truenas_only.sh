#!/usr/bin/env bash
# Spegnimento K8s e Proxmox per risparmio energetico (Solo TrueNAS attivo).

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"
cd "$ROOT_DIR" || exit 1

echo "🛑 Avvio sequenza di spegnimento K8s e Proxmox VE..."
echo "➡️  Modalità Eco: TrueNAS rimarrà l'unico host attivo per Servarr e storage."
echo ""
ansible-playbook -i ansible/inventory.ini ansible/playbooks/infrastructure/shutdown_to_truenas_only.yml

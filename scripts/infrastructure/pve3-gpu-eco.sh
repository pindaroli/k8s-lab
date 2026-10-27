#!/usr/bin/env bash
# Imposta la GPU AMD Radeon 890M di PVE3 in modalita' ECO (auto-scaling).

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"
cd "$ROOT_DIR" || exit 1

ansible-playbook -i ansible/inventory.ini ansible/playbooks/infrastructure/pve3_gpu_power.yml -e gpu_mode=eco

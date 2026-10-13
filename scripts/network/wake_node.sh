#!/usr/bin/env bash
# Invio Magic Packet Wake-on-LAN ai nodi fisici dell'Homelab
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"
cd "$ROOT_DIR"

exec python3 "$SCRIPT_DIR/wake_node.py" "$@"

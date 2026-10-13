#!/usr/bin/env bash
# Diagnostica globale e health-check dell'infrastruttura Homelab
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"
cd "$ROOT_DIR"

exec python3 "$SCRIPT_DIR/check_lab.py" "$@"

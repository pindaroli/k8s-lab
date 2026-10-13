#!/usr/bin/env bash
# Validazione congruenza e coerenza dichiarativa di rete.json
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"
cd "$ROOT_DIR"

exec python3 "$SCRIPT_DIR/validate_network.py" "$@"

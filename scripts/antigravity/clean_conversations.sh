#!/usr/bin/env bash
# Pulizia selettiva e compattazione conversazioni storiche Antigravity

set -euo pipefail

# Risoluzione dinamica della directory di root del repository (CWD-independent)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"
cd "$ROOT_DIR"

# Esecuzione del motore Python inoltrando tutti i parametri CLI
exec python3 "$SCRIPT_DIR/clean_conversations.py" "$@"

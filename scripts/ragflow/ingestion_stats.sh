#!/usr/bin/env bash
# Statistiche tempi e latenze di ingestion RAGFlow (CLI e report HTML)
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"
cd "$ROOT_DIR"

# Recupero trasparente della chiave API se non presente nell'ambiente
if [[ -z "${RAGFLOW_API_KEY:-}" ]]; then
  if RAGFLOW_KEY=$(ssh -o BatchMode=yes -o ConnectTimeout=3 truenas "grep RAGFLOW_API_KEY /mnt/stripe/truenas-docker/mcp/.env 2>/dev/null | cut -d= -f2" 2>/dev/null); then
    if [[ -n "$RAGFLOW_KEY" ]]; then
      export RAGFLOW_API_KEY="$RAGFLOW_KEY"
    fi
  fi
fi

exec python3 "$SCRIPT_DIR/ingestion_stats.py" "$@"

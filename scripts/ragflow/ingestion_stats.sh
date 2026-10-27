#!/usr/bin/env bash
# Statistiche tempi e latenze di ingestion RAGFlow (CLI e report HTML)
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"
cd "$ROOT_DIR"

# Recupero trasparente della chiave API se non presente nell'ambiente
if [[ -z "${RAGFLOW_API_KEY:-}" ]]; then
  # 1. Tentativo di lettura da segreto cifrato locale SOPS
  if [[ -f "$ROOT_DIR/secrets-sops/ragflow-secrets.enc.yaml" ]] && command -v sops >/dev/null 2>&1; then
    SOPS_KEY=$(sops -d "$ROOT_DIR/secrets-sops/ragflow-secrets.enc.yaml" 2>/dev/null | awk -F': ' '/api_key:/ {print $2}' | tr -d '"\r\n' || true)
    if [[ -n "$SOPS_KEY" ]]; then
      export RAGFLOW_API_KEY="$SOPS_KEY"
    fi
  fi
  # 2. Fallback via SSH non interattivo su TrueNAS
  if [[ -z "${RAGFLOW_API_KEY:-}" ]]; then
    TRUENAS_TARGET="${TRUENAS_SSH_TARGET:-olindo@10.10.20.50}"
    if RAGFLOW_KEY=$(ssh -o BatchMode=yes -o StrictHostKeyChecking=accept-new -o ConnectTimeout=5 "$TRUENAS_TARGET" "grep RAGFLOW_API_KEY /mnt/stripe/truenas-docker/mcp/.env 2>/dev/null | cut -d= -f2" 2>/dev/null); then
      if [[ -n "$RAGFLOW_KEY" ]]; then
        export RAGFLOW_API_KEY="$RAGFLOW_KEY"
      fi
    fi
  fi
fi

exec python3 "$SCRIPT_DIR/ingestion_stats.py" "$@"

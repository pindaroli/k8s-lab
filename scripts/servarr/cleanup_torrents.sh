#!/usr/bin/env bash
# Pulizia selettiva torrent su qBittorrent per data, percentuale e categoria

set -euo pipefail

# Risoluzione dinamica della root directory per conformità a go-launcher-script-pattern
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"
cd "$ROOT_DIR"

# 1. Verifica disponibilità runtime Python 3
if ! command -v python3 >/dev/null 2>&1; then
    echo -e "\033[0;31m❌ Errore: python3 non è installato o non è presente nel PATH di sistema.\033[0m" >&2
    exit 1
fi

# 2. Esportazione trasparente credenziali SOPS se non già definite nell'ambiente
SOPS_FILE="$ROOT_DIR/secrets-sops/servarr-api-keys.enc.yaml"
if [[ -z "${QBT_PASS:-}" && -f "$SOPS_FILE" ]] && command -v sops >/dev/null 2>&1; then
    QBT_PASS_DECRYPTED="$(sops -d --extract '["stringData"]["qbittorrent-pass"]' "$SOPS_FILE" 2>/dev/null || true)"
    if [[ -n "$QBT_PASS_DECRYPTED" ]]; then
        export QBT_PASS="$QBT_PASS_DECRYPTED"
    fi
fi

if [[ -z "${QBT_USER:-}" && -f "$SOPS_FILE" ]] && command -v sops >/dev/null 2>&1; then
    QBT_USER_DECRYPTED="$(sops -d --extract '["stringData"]["qbittorrent-user"]' "$SOPS_FILE" 2>/dev/null || true)"
    if [[ -n "$QBT_USER_DECRYPTED" ]]; then
        export QBT_USER="$QBT_USER_DECRYPTED"
    fi
fi

# 3. Esecuzione del motore Python passando tutti i parametri CLI
exec python3 "$SCRIPT_DIR/cleanup_torrents.py" "$@"

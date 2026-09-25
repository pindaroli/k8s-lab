#!/usr/bin/env bash
# =============================================================================
# Innesco Normalizzazione Video/Audio su TrueNAS via webhook-normalizer
# USO: ./trigger_normalization.sh "<PERCORSO_O_NOME_FILE>" [CATEGORIA] [--tail-logs]
# =============================================================================

set -euo pipefail

TRUENAS_IP="${TRUENAS_IP:-10.10.20.50}"
NORMALIZER_PORT="${NORMALIZER_PORT:-9000}"
TARGET_PATH="${1:-}"
CATEGORY="${2:-video-filebot}"
TAIL_LOGS=false

if [ -z "$TARGET_PATH" ]; then
    echo "❌ Errore: Specificare il percorso o il nome della cartella da normalizzare."
    echo "Esempio: $0 \"The.Neon.Demon.2016.4K...\" video-filebot --tail-logs"
    exit 1
fi

# Se viene passato solo il nome della cartella, anteponi il percorso standard di download
if [[ "$TARGET_PATH" != /* ]]; then
    TARGET_PATH="/media/downloads/${CATEGORY}/${TARGET_PATH}"
fi

# Flag --tail-logs
if [[ "${3:-}" == "--tail-logs" ]] || [[ "${2:-}" == "--tail-logs" ]]; then
    [ "${2:-}" == "--tail-logs" ] && CATEGORY="video-filebot"
    TAIL_LOGS=true
fi

echo "🚀 Innesco normalizzazione su TrueNAS ($TRUENAS_IP:$NORMALIZER_PORT)..."
echo "📂 Percorso: $TARGET_PATH"
echo "🏷️ Categoria: $CATEGORY"

RESPONSE=$(curl -s -w "\n%{http_code}" -X POST "http://${TRUENAS_IP}:${NORMALIZER_PORT}/hooks/normalize" \
    --data-urlencode "path=${TARGET_PATH}" \
    --data-urlencode "category=${CATEGORY}")

HTTP_CODE=$(echo "$RESPONSE" | tail -n1)
BODY=$(echo "$RESPONSE" | sed '$d')

if [ "$HTTP_CODE" -eq 200 ]; then
    echo "✅ Innesco avvenuto con successo: $BODY"
else
    echo "❌ Errore durante l'innesco (HTTP $HTTP_CODE): $BODY"
    exit 1
fi

if [ "$TAIL_LOGS" = true ]; then
    echo "📡 Connessione streaming log del container webhook-normalizer..."
    ssh -o BatchMode=yes "olindo@${TRUENAS_IP}" "sudo -n docker logs -f --tail=30 webhook-normalizer"
fi

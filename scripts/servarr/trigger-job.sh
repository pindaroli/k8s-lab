#!/usr/bin/env bash
# =============================================================================
# Innesco Webhook Normalizer da qBittorrent Docker su TrueNAS
# =============================================================================
set -euo pipefail

CONTENT_PATH="${1:-}"
CATEGORY="${2:-video-filebot}"
LOG_FILE="/config/qBittorrent/logs/trigger.log"

echo "[$(date '+%Y-%m-%d %H:%M:%S')] Trigger ricevuto per '$CONTENT_PATH' [Categoria: '$CATEGORY']" >> "$LOG_FILE"

if [ -z "$CONTENT_PATH" ]; then
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] ⚠️ ERRORE: CONTENT_PATH non specificato!" >> "$LOG_FILE"
    exit 1
fi

HTTP_RESPONSE=$(curl -s -w "\n%{http_code}" -X POST "http://webhook-normalizer:9000/hooks/normalize" \
    --data-urlencode "path=${CONTENT_PATH}" \
    --data-urlencode "category=${CATEGORY}")

HTTP_CODE=$(echo "$HTTP_RESPONSE" | tail -n1)
BODY=$(echo "$HTTP_RESPONSE" | sed '$d')

echo "[$(date '+%Y-%m-%d %H:%M:%S')] Risposta Webhook (HTTP $HTTP_CODE): $BODY" >> "$LOG_FILE"

if [ "$HTTP_CODE" -eq 200 ]; then
    exit 0
else
    exit 1
fi

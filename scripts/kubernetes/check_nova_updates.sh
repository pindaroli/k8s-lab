#!/usr/bin/env bash
# Controllo aggiornamenti versioni container e fogli Helm tramite Nova

set -e

# PATH setup per Homebrew e binari comuni
export PATH="/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:$PATH"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PYTHON_SCRIPT="$SCRIPT_DIR/utils/format_nova_updates.py"

if ! command -v nova &> /dev/null; then
    echo "Errore: 'nova' non è installato o non è presente nel PATH."
    exit 1
fi

if [ ! -f "$PYTHON_SCRIPT" ]; then
    echo "Errore: Script Python di formattazione non trovato in $PYTHON_SCRIPT"
    exit 1
fi

echo "===================================================================================================="
echo "📦 IMMAGINI CONTAINER (KUBERNETES)"
echo "===================================================================================================="

nova find --containers --format json --show-non-semver -a 2>/dev/null | python3 "$PYTHON_SCRIPT" containers

echo ""
echo "===================================================================================================="
echo "⎈ FOGLI (RELEASE) HELM"
echo "===================================================================================================="

nova find --helm --format json -a 2>/dev/null | python3 "$PYTHON_SCRIPT" helm

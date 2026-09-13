#!/usr/bin/env bash
# Audit libreria film su TrueNAS (ricerca anomalie, DVD e multi-parte)

set -euo pipefail

# Risoluzione dinamica della directory di root del repository (Pattern go.py)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"
cd "$ROOT_DIR"

NAS_HOST="10.10.10.50"
NAS_USER="olindo"
MEDIA_DIR="/mnt/oliraid/arrdata/media/movies"

echo -e "\033[1;36m============================================================\033[0m"
echo -e "\033[1;36m  🔍 Audit Libreria Film — TrueNAS Remote Execution         \033[0m"
echo -e "\033[1;36m============================================================\033[0m\n"

echo -e "Esecuzione pre-flight checks su TrueNAS (\033[1;33m$NAS_HOST\033[0m)..."

# 1. Test Connettività SSH
if ! ssh -o BatchMode=yes -o ConnectTimeout=5 "$NAS_USER@$NAS_HOST" "true" 2>/dev/null; then
    echo -e "\033[0;31m❌ Errore: Impossibile stabilire la sessione SSH verso TrueNAS ($NAS_HOST).\033[0m"
    exit 1
fi
echo -e "  \033[0;32m✓ Connessione SSH stabilita con successo.\033[0m"

# 2. Test Presenza Runtime Python
if ! ssh -o BatchMode=yes "$NAS_USER@$NAS_HOST" "command -v python3 >/dev/null"; then
    echo -e "\033[0;31m❌ Errore: python3 non è installato sul nodo TrueNAS.\033[0m"
    exit 1
fi
echo -e "  \033[0;32m✓ Runtime Python 3 rilevato su TrueNAS.\033[0m"

# 3. Test Storage & Dataset ZFS
if ! ssh -o BatchMode=yes "$NAS_USER@$NAS_HOST" "test -d '$MEDIA_DIR'"; then
    echo -e "\033[0;31m❌ Errore: Il dataset ZFS '$MEDIA_DIR' non esiste o non è montato.\033[0m"
    exit 1
fi
echo -e "  \033[0;32m✓ Dataset ZFS accessibile: $MEDIA_DIR\033[0m"

# 4. Verifica Strumento Ispezione Audio (ffprobe)
if ssh -o BatchMode=yes "$NAS_USER@$NAS_HOST" "test -x /mnt/oliraid/bin/ffprobe || command -v ffprobe >/dev/null" 2>/dev/null; then
    echo -e "  \033[0;32m✓ ffprobe statico rilevato su ZFS (/mnt/oliraid/bin/ffprobe).\033[0m"
else
    echo -e "  \033[1;33m⚠️  ffprobe non rilevato (l'ispezione audio avanzata sarà parziale).\033[0m"
fi

echo -e "\n\033[1;32m🚀 Avvio scansione libreria film in corso...\033[0m\n"

# Esecuzione remota via streaming dello script Python
ssh -o BatchMode=yes "$NAS_USER@$NAS_HOST" "MEDIA_DIR='$MEDIA_DIR' python3 -" < "${SCRIPT_DIR}/audit_movie_duplicates.py"

echo -e "\n\033[1;32m✓ Scansione completata con successo.\033[0m"

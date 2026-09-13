#!/usr/bin/env bash
# Launcher per unificazione versioni multiple film per Jellyfin / FileBot
# Esegue merge_movie_versions.py su TrueNAS in modalità interattiva o batch

set -euo pipefail

# Risoluzione dinamica della directory di root del repository (Pattern go.py)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"
cd "$ROOT_DIR"

NAS_HOST="10.10.10.50"
NAS_USER="olindo"
MEDIA_DIR="/mnt/oliraid/arrdata/media/movies"

echo -e "\033[1;36m============================================================\033[0m"
echo -e "\033[1;36m  🎬 Unificazione Versioni Multiple Film per Jellyfin       \033[0m"
echo -e "\033[1;36m============================================================\033[0m\n"

# 1. Test Connettività SSH
if ! ssh -o BatchMode=yes -o ConnectTimeout=5 "$NAS_USER@$NAS_HOST" "true" 2>/dev/null; then
    echo -e "\033[0;31m❌ Errore: Impossibile stabilire la sessione SSH verso TrueNAS ($NAS_HOST).\033[0m"
    exit 1
fi

# 2. Test Runtime Python
if ! ssh -o BatchMode=yes "$NAS_USER@$NAS_HOST" "command -v python3 >/dev/null"; then
    echo -e "\033[0;31m❌ Errore: python3 non è installato su TrueNAS.\033[0m"
    exit 1
fi

# 3. Test ffprobe
if ssh -o BatchMode=yes "$NAS_USER@$NAS_HOST" "test -x /mnt/oliraid/bin/ffprobe || command -v ffprobe >/dev/null" 2>/dev/null; then
    echo -e "  \033[0;32m✓ ffprobe statico rilevato su ZFS (/mnt/oliraid/bin/ffprobe).\033[0m"
else
    echo -e "  \033[1;33m⚠️  ffprobe non trovato (l'analisi dei flussi sarà parziale).\033[0m"
fi

echo -e "  \033[0;32m✓ Connessione a TrueNAS verificata.\033[0m\n"

# 4. Copia dell'engine Python su TrueNAS in /tmp
ssh -o BatchMode=yes "$NAS_USER@$NAS_HOST" "cat > /tmp/merge_movie_versions.py" < "${SCRIPT_DIR}/merge_movie_versions.py"

# 5. Allocazione TTY se standard input è un terminale interattivo
SSH_TTY_FLAG=""
if [ -t 0 ]; then
    SSH_TTY_FLAG="-t"
fi

# 6. Esecuzione remota con supporto ad argomenti CLI e input interattivo
REMOTE_ARGS="${*:-}"
ssh $SSH_TTY_FLAG -o BatchMode=yes "$NAS_USER@$NAS_HOST" "MEDIA_DIR='$MEDIA_DIR' python3 /tmp/merge_movie_versions.py $REMOTE_ARGS"

#!/usr/bin/env bash
# Launcher per la bonifica intelligente artwork e ripristino locandine Jellyfin
# Esegue fix_movie_posters.py su TrueNAS

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"
cd "$ROOT_DIR"

NAS_HOST="10.10.10.50"
NAS_USER="olindo"
MEDIA_DIR="/mnt/oliraid/arrdata/media/movies"

echo -e "\033[1;36m============================================================\033[0m"
echo -e "\033[1;36m  🖼️  Bonifica Intelligente Artwork per Jellyfin             \033[0m"
echo -e "\033[1;36m============================================================\033[0m\n"

# 1. Test Connettività SSH
if ! ssh -o BatchMode=yes -o ConnectTimeout=5 "$NAS_USER@$NAS_HOST" "true" 2>/dev/null; then
    echo -e "\033[0;31m❌ Errore: Impossibile stabilire la sessione SSH verso TrueNAS ($NAS_HOST).\033[0m"
    exit 1
fi

echo -e "  \033[0;32m✓ Connessione a TrueNAS verificata.\033[0m\n"

# 2. Copia dell'engine Python su TrueNAS in /tmp
ssh -o BatchMode=yes "$NAS_USER@$NAS_HOST" "cat > /tmp/fix_movie_posters.py" < "${SCRIPT_DIR}/fix_movie_posters.py"

# 3. Allocazione TTY se standard input è un terminale interattivo
SSH_TTY_FLAG=""
if [ -t 0 ]; then
    SSH_TTY_FLAG="-t"
fi

# 4. Esecuzione remota con supporto ad argomenti CLI
REMOTE_ARGS="${*:-}"
ssh $SSH_TTY_FLAG -o BatchMode=yes "$NAS_USER@$NAS_HOST" "MEDIA_DIR='$MEDIA_DIR' python3 /tmp/fix_movie_posters.py $REMOTE_ARGS"

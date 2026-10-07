#!/usr/bin/env bash
# =============================================================================
# sanitize_movie_folder.sh
# Launcher locale per la sanificazione di cartelle e versioni multiple su TrueNAS
# =============================================================================
# USO:
#   ./sanitize_movie_folder.sh [NOME_CARTELLA | NOME_FILE_CON_ESTENSIONE] [OPZIONI]
#
# Esempi:
#   ./sanitize_movie_folder.sh "Trainspotting (1996).avi"
#   ./sanitize_movie_folder.sh "Trainspotting (1996) {tmdb-627}"
#   ./sanitize_movie_folder.sh "Trainspotting (1996).avi" --apply
#   ./sanitize_movie_folder.sh (senza argomenti -> prompt interattivo)
# =============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"
cd "$ROOT_DIR"

NAS_HOST="10.10.20.50"
NAS_USER="olindo"
MEDIA_DIR="/mnt/oliraid/arrdata/media/movies"

echo -e "\033[1;36m============================================================\033[0m"
echo -e "\033[1;36m  🎬 Sanificazione Cartelle e Versioni Multiple Jellyfin    \033[0m"
echo -e "\033[1;36m============================================================\033[0m\n"

# 1. Test Connettività SSH Passwordless
if ! ssh -o BatchMode=yes -o ConnectTimeout=5 "$NAS_USER@$NAS_HOST" "true" 2>/dev/null; then
    echo -e "\033[0;31m❌ Errore: Impossibile stabilire la sessione SSH verso TrueNAS ($NAS_HOST).\033[0m"
    echo -e "   Verificare la chiave SSH e lo stato di TrueNAS.\n"
    exit 1
fi

# 2. Test Runtime Python su TrueNAS
if ! ssh -o BatchMode=yes "$NAS_USER@$NAS_HOST" "command -v python3 >/dev/null"; then
    echo -e "\033[0;31m❌ Errore: python3 non è installato su TrueNAS.\033[0m"
    exit 1
fi

# 3. Test ffprobe su TrueNAS
if ssh -o BatchMode=yes "$NAS_USER@$NAS_HOST" "test -x /mnt/oliraid/bin/ffprobe || command -v ffprobe >/dev/null" 2>/dev/null; then
    echo -e "  \033[0;32m✓ ffprobe rilevato su TrueNAS.\033[0m"
else
    echo -e "  \033[1;33m⚠️  ffprobe non trovato (l'analisi tecnica userà fallback euristico).\033[0m"
fi

echo -e "  \033[0;32m✓ Connessione a TrueNAS verificata.\033[0m\n"

# 4. Sincronizzazione dell'engine Python in /tmp su TrueNAS
ssh -o BatchMode=yes "$NAS_USER@$NAS_HOST" "cat > /tmp/sanitize_movie_folder.py" < "${SCRIPT_DIR}/sanitize_movie_folder.py"

# 5. Allocazione TTY se terminale interattivo
SSH_TTY_FLAG=""
if [ -t 0 ]; then
    SSH_TTY_FLAG="-t"
fi

# 6. Esecuzione remota con quoting sicuro degli argomenti
QUOTED_ARGS=""
for arg in "$@"; do
    QUOTED_ARGS+="$(printf "%q " "$arg")"
done

ssh $SSH_TTY_FLAG -o BatchMode=yes "$NAS_USER@$NAS_HOST" "MEDIA_DIR='$MEDIA_DIR' python3 /tmp/sanitize_movie_folder.py $QUOTED_ARGS"

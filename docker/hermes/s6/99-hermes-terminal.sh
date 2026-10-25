#!/usr/bin/with-contenv bash
# ==============================================================================
# 99-hermes-terminal.sh — s6-overlay cont-init.d
# Invarianti:
#   1. Convergenza UID/GID hermes -> 1000:1000 (olindo:k8s) senza collisioni
#   2. Symlink /hermesAgent/common -> /opt/data/common e profilo bash contestuale
#   3. Auto-clean socket UNIX (.sock) e gateway-locks orfani al boot
#   4. Chown rapido su /opt/data con esclusione (-prune) di /opt/data/common
#   5. Git safe.directory universale, cache-busting ?v=2.2 in web_dist/index.html
#   6. Installazione hook FastAPI terminal_proxy.py e avvio servizio s6 ttyd
# ==============================================================================
set -euo pipefail

echo "[cont-init:99-hermes-terminal] Avvio convergenza UID 1000, bonifica IPC e setup Web Terminal..."

# 1. Creazione idempotente symlink /hermesAgent/common -> /opt/data/common
mkdir -p /hermesAgent /opt/data/common/prj
ln -sfn /opt/data/common /hermesAgent/common

# 2. Risoluzione collisioni UID/GID 1000 nella base image Linux e rimappatura hermes -> 1000:1000
if id -u hermes >/dev/null 2>&1; then
    EXISTING_USER="$(getent passwd 1000 | cut -d: -f1 || true)"
    if [ -n "${EXISTING_USER}" ] && [ "${EXISTING_USER}" != "hermes" ]; then
        echo "[cont-init:99-hermes-terminal] Spostamento utente collidente ${EXISTING_USER} (UID 1000 -> 19999)"
        usermod -o -u 19999 "${EXISTING_USER}"
    fi

    EXISTING_GROUP="$(getent group 1000 | cut -d: -f1 || true)"
    if [ -n "${EXISTING_GROUP}" ] && [ "${EXISTING_GROUP}" != "hermes" ]; then
        echo "[cont-init:99-hermes-terminal] Spostamento gruppo collidente ${EXISTING_GROUP} (GID 1000 -> 19999)"
        groupmod -o -g 19999 "${EXISTING_GROUP}"
    fi

    if [ "$(id -u hermes)" != "1000" ] || [ "$(id -g hermes)" != "1000" ]; then
        groupmod -o -g 1000 hermes
        usermod -o -u 1000 -g 1000 hermes
        echo "[cont-init:99-hermes-terminal] Riallineamento file rootfs container da UID/GID 10000 a 1000:1000..."
        find / -xdev \( -uid 10000 -o -gid 10000 \) -exec chown -h hermes:hermes {} + 2>/dev/null || true
    fi
fi

# 3. Auto-Clean al boot di socket UNIX e lock effimeri orfani in /opt/data
if [ -d /opt/data ]; then
    find /opt/data -path /opt/data/common -prune -o -maxdepth 4 -type s -delete 2>/dev/null || true
    rm -f /opt/data/*.sock /opt/data/*.sock.path /opt/data/*.lock
    rm -rf /opt/data/.local/state/hermes/gateway-locks/*

    # 4. Riallineamento selettivo /opt/data (escluso il mount /opt/data/common dei repo Git)
    find /opt/data -path /opt/data/common -prune -o \
        \( ! -user hermes -o ! -group hermes \) \
        -exec chown -h hermes:hermes {} +
fi

# --- Self-Healing SQLite journal_mode (virtiofs / ZFS convergence on /opt/data) ---
if ! command -v sqlite3 >/dev/null 2>&1; then
    cat << 'WRAPPER_EOF' > /usr/local/bin/sqlite3
#!/usr/bin/env python3
import sys, sqlite3

args = sys.argv[1:]
sql_args = []
db = None

i = 0
while i < len(args):
    arg = args[i]
    if arg == "-cmd":
        i += 2
        continue
    elif db is None and not arg.startswith("-"):
        db = arg
    else:
        sql_args.append(arg)
    i += 1

if not db or not sql_args:
    sys.exit(1)

query = " ".join(sql_args)
try:
    con = sqlite3.connect(f"file:{db}?timeout=10", uri=True)
    cur = con.cursor()
    for statement in query.split(";"):
        stmt = statement.strip()
        if not stmt:
            continue
        cur.execute(stmt)
        for row in cur.fetchall():
            print("|".join(str(c) for c in row))
    con.close()
except Exception as e:
    sys.stderr.write(f"sqlite3 wrapper error: {e}\n")
    sys.exit(1)
WRAPPER_EOF
    chmod 0755 /usr/local/bin/sqlite3
fi

if [ -d "/opt/data" ]; then
    echo "[cont-init] Ensuring SQLite databases in /opt/data use journal_mode=DELETE..."
    find /opt/data -path /opt/data/common -prune -o -maxdepth 3 -type f -name "*.db" -print 2>/dev/null | while read -r db_file; do
        [ -f "$db_file" ] || continue
        current_mode=$(sqlite3 -cmd ".timeout 5000" "$db_file" "PRAGMA journal_mode;" 2>/dev/null | tr '[:upper:]' '[:lower:]')
        if [ "$current_mode" = "wal" ]; then
            echo "[cont-init] Converting $db_file from WAL to DELETE (with TRUNCATE checkpoint)..."
            new_mode=$(sqlite3 -cmd ".timeout 10000" "$db_file" "PRAGMA wal_checkpoint(TRUNCATE); PRAGMA journal_mode=DELETE;" 2>/dev/null | tail -n 1 | tr '[:upper:]' '[:lower:]')
            if [ "$new_mode" = "delete" ]; then
                rm -f "${db_file}-wal" "${db_file}-shm"
                chown 1000:1000 "$db_file"
                echo "[cont-init] Successfully converted $db_file to DELETE (uid:gid 1000:1000)."
            else
                echo "[cont-init] WARNING: Failed to convert $db_file (mode is still '$new_mode'). Preserving -wal/-shm to prevent data loss!"
            fi
        elif [ "$current_mode" = "delete" ]; then
            # Rimuove esclusivamente eventuali file orfani -wal/-shm residui su DB già certificati in DELETE
            rm -f "${db_file}-wal" "${db_file}-shm"
            chown 1000:1000 "$db_file"
        fi
    done
fi


# 5. Configurazione prompt bash contestuale per nodo, umask 0002 e Git safe.directory
cat << 'EOF' > /etc/profile.d/hermes_env.sh
umask 0002
export HERMES_NODE="${HERMES_HOST_NODE:-hermes}"
export PS1="\[\033[1;31m\][root@${HERMES_NODE}]\[\033[0m\]:\[\033[1;34m\]\w\[\033[0m\]# "
git config --global --add safe.directory '*' 2>/dev/null || true
EOF
grep -q "hermes_env.sh" /root/.bashrc 2>/dev/null || echo "source /etc/profile.d/hermes_env.sh" >> /root/.bashrc
if command -v git >/dev/null 2>&1; then
    git config --system --add safe.directory '*' 2>/dev/null || true
    git config --global --add safe.directory '*' 2>/dev/null || true
fi

# 6. Aggancio idempotente con cache-buster (?v=2.3) di terminal-inject.js in web_dist/index.html
INDEX_HTML="/opt/hermes/hermes_cli/web_dist/index.html"
if [ -f "${INDEX_HTML}" ]; then
    sed -i '/terminal-inject\.js/d' "${INDEX_HTML}"
    sed -i 's|</body>|  <script src="/terminal-inject.js?v=2.3" defer></script>\n</body>|' "${INDEX_HTML}"
fi

# 7. Aggancio idempotente del modulo terminal_proxy.py nell'app FastAPI di Hermes
if [ -f /opt/hermes/hermes_cli/terminal_proxy.py ]; then
    python3 /opt/hermes/hermes_cli/terminal_proxy.py --install-hook
fi

# 8. Supervisione automatica ttyd sotto s6-overlay v3 (/run/service/ttyd)
if [ -f /etc/services.d/ttyd/run ]; then
    mkdir -p /run/service/ttyd
    cp /etc/services.d/ttyd/run /run/service/ttyd/run
    chmod 0755 /run/service/ttyd/run
    if [ -x /command/s6-svscanctl ]; then
        /command/s6-svscanctl -a /run/service 2>/dev/null || true
    fi
fi

echo "[cont-init:99-hermes-terminal] Completato. Identità attiva: $(id hermes 2>/dev/null || echo 'N/A')"

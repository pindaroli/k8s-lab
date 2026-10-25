#!/usr/bin/env bash
# ==============================================================================
# FILE: scripts/infrastructure/orbstack_failover.sh
# DESCRIZIONE: Libreria KISS idempotente per tutte le 9+1 transizioni tra
#              TrueNAS SCALE (10.10.20.50) e Mac Studio OrbStack (10.10.20.100).
#              - KISS #1: Zero Data Loss (rsync -auz + guardia cartella non vuota)
#              - KISS #2: Preserva restart: unless-stopped su TrueNAS al boot
#              - KISS #3: File .env.ai e .env.mcp separati 1:1 (zero parser awk)
#              - KISS #4: Supporto SSH nativo olindo@10.10.20.50 (con sudo -n) e root
#              - KISS #5: Self-healing su stati parziali/sporchi (riavvio automatico
#                         container TrueNAS se una porta tra 8100/9119/4000/8888 è chiusa)
# ==============================================================================

export FAILOVER_RUNTIME_DIR="${HOME}/.homelab-failover"
export ORBSTACK_COMPOSE_FILE="${ROOT_DIR}/docker/orbstack/docker-compose.yaml"
export HERMES_ROOT_LOCAL="/Users/olindo/hermesAgent"
export HERMES_ROOT_REMOTE="/mnt/stripe/hermesAgent"
export TRUENAS_HOST="10.10.20.50"
export MAC_STUDIO_IP="10.10.20.100"

# Verifica rapida se una porta TCP è aperta su un host
_is_tcp_open() {
    local host="$1"
    local port="$2"
    nc -z -G 2 "$host" "$port" >/dev/null 2>&1
}

# Rileva l'utente SSH passwordless valido verso TrueNAS (olindo standard Wiki oppure root)
_resolve_truenas_ssh_user() {
    if ssh -o BatchMode=yes -o ConnectTimeout=3 "olindo@${TRUENAS_HOST}" "true" >/dev/null 2>&1; then
        echo "olindo"
    elif ssh -o BatchMode=yes -o ConnectTimeout=3 "root@${TRUENAS_HOST}" "true" >/dev/null 2>&1; then
        echo "root"
    else
        echo ""
    fi
}

# Prepara ~/.homelab-failover/{.env.ai,.env.mcp} copiandoli 1:1 da TrueNAS quando è online,
# oppure usando i file locali già presenti (con fallback SOPS minimale solo se assenti a freddo)
prepare_orbstack_runtime_env() {
    echo "🔐 [OrbStack Failover] Verifica directory e file .env runtime in ${FAILOVER_RUNTIME_DIR}..."
    mkdir -p "${FAILOVER_RUNTIME_DIR}/dozzle"
    chmod 700 "${FAILOVER_RUNTIME_DIR}"

    if _is_tcp_open "$TRUENAS_HOST" 22; then
        local ssh_user
        ssh_user="$(_resolve_truenas_ssh_user)"
        if [ -n "$ssh_user" ]; then
            echo "📥 [OrbStack Failover] Copia 1:1 di .env.ai e .env.mcp da TrueNAS (${ssh_user}@${TRUENAS_HOST})..."
            ssh -o BatchMode=yes "${ssh_user}@${TRUENAS_HOST}" \
                "sudo -n cat /mnt/stripe/truenas-docker/.env 2>/dev/null || cat /mnt/stripe/truenas-docker/.env" \
                > "${FAILOVER_RUNTIME_DIR}/.env.ai.tmp" && mv "${FAILOVER_RUNTIME_DIR}/.env.ai.tmp" "${FAILOVER_RUNTIME_DIR}/.env.ai"

            ssh -o BatchMode=yes "${ssh_user}@${TRUENAS_HOST}" \
                "sudo -n cat /mnt/stripe/truenas-docker/mcp/.env 2>/dev/null || cat /mnt/stripe/truenas-docker/mcp/.env" \
                > "${FAILOVER_RUNTIME_DIR}/.env.mcp.tmp" && mv "${FAILOVER_RUNTIME_DIR}/.env.mcp.tmp" "${FAILOVER_RUNTIME_DIR}/.env.mcp"

            mkdir -p "${FAILOVER_RUNTIME_DIR}/acme"
            chmod 700 "${FAILOVER_RUNTIME_DIR}/acme"
            if ssh -o BatchMode=yes "${ssh_user}@${TRUENAS_HOST}" "test -s /mnt/stripe/truenas-docker/mcp/acme/acme.json" 2>/dev/null; then
                ssh -o BatchMode=yes "${ssh_user}@${TRUENAS_HOST}" \
                    "sudo -n cat /mnt/stripe/truenas-docker/mcp/acme/acme.json 2>/dev/null || cat /mnt/stripe/truenas-docker/mcp/acme/acme.json" \
                    > "${FAILOVER_RUNTIME_DIR}/acme/acme.json.tmp" && \
                    chmod 600 "${FAILOVER_RUNTIME_DIR}/acme/acme.json.tmp" && \
                    mv "${FAILOVER_RUNTIME_DIR}/acme/acme.json.tmp" "${FAILOVER_RUNTIME_DIR}/acme/acme.json"
            fi
        fi
    fi

    # Fallback SOPS minimale solo se .env.ai non esiste ancora sul Mac e TrueNAS è già spento
    if [ ! -s "${FAILOVER_RUNTIME_DIR}/.env.ai" ] && command -v sops >/dev/null 2>&1 && command -v yq >/dev/null 2>&1; then
        echo "🔑 [OrbStack Failover] TrueNAS offline: estrazione di emergenza .env.ai da secrets-sops..."
        for f in "${ROOT_DIR}/secrets-sops/litellm-secrets.enc.yaml" "${ROOT_DIR}/secrets-sops/hermes-secrets.enc.yaml"; do
            [ -f "$f" ] || continue
            sops -d "$f" | yq eval '(.stringData // .) | to_entries | .[] | select(.key != "sops") | .key + "=" + (.value | tostring)' - >> "${FAILOVER_RUNTIME_DIR}/.env.ai"
        done
    fi

    touch "${FAILOVER_RUNTIME_DIR}/.env.ai" "${FAILOVER_RUNTIME_DIR}/.env.mcp"
    chmod 600 "${FAILOVER_RUNTIME_DIR}/.env.ai" "${FAILOVER_RUNTIME_DIR}/.env.mcp"

    if [ ! -s "${FAILOVER_RUNTIME_DIR}/.env.ai" ] || [ ! -s "${FAILOVER_RUNTIME_DIR}/.env.mcp" ]; then
        echo "❌ [OrbStack Failover] File .env.ai o .env.mcp vuoto in ${FAILOVER_RUNTIME_DIR}!"
        return 1
    fi

    # Genera .env unificato combinando .env.mcp e .env.ai senza duplicati
    {
        echo "# Generated unified failover environment"
        [ -f "${FAILOVER_RUNTIME_DIR}/.env.mcp" ] && cat "${FAILOVER_RUNTIME_DIR}/.env.mcp"
        echo ""
        [ -f "${FAILOVER_RUNTIME_DIR}/.env.ai" ] && cat "${FAILOVER_RUNTIME_DIR}/.env.ai"
    } | awk '!seen[$0]++ || $0 ~ /^#|^$/' > "${FAILOVER_RUNTIME_DIR}/.env.tmp"
    chmod 600 "${FAILOVER_RUNTIME_DIR}/.env.tmp"
    mv -f "${FAILOVER_RUNTIME_DIR}/.env.tmp" "${FAILOVER_RUNTIME_DIR}/.env"

    if [ ! -s "${FAILOVER_RUNTIME_DIR}/.env" ]; then
        echo "❌ [OrbStack Failover] File .env unificato vuoto in ${FAILOVER_RUNTIME_DIR}!"
        return 1
    fi

    # Esporta le variabili in ambiente per l'interpolazione Compose in modo sicuro
    # (previene fallimenti di 'source' in presenza di valori Docker non quotati con spazi)
    while IFS='=' read -r key val || [ -n "$key" ]; do
        [[ "$key" =~ ^[[:space:]]*# ]] && continue
        [[ -z "$key" ]] && continue
        key="$(echo -n "$key" | xargs)"
        if [[ "$key" =~ ^[a-zA-Z_][a-zA-Z0-9_]*$ ]]; then
            val="${val%\"}"
            val="${val#\"}"
            val="${val%\'}"
            val="${val#\'}"
            export "$key=$val"
        fi
    done < "${FAILOVER_RUNTIME_DIR}/.env"
}

# Eseguito in lab_mode_off.sh PRIMA di ensure_storage_off.yml (Copre FULL->OFF, ECO->OFF, OFF->OFF)
sync_hermes_state_from_truenas() {
    prepare_orbstack_runtime_env
    mkdir -p "${HERMES_ROOT_LOCAL}/HermesMain" "${HERMES_ROOT_LOCAL}/common/prj"

    if _is_tcp_open "$TRUENAS_HOST" 22; then
        local ssh_user
        ssh_user="$(_resolve_truenas_ssh_user)"
        if [ -n "$ssh_user" ]; then
            echo "🛑 [State Sync] Arresto preventivo container su entrambi i nodi per quiescenza SQLite WAL..."
            docker compose --env-file "${FAILOVER_RUNTIME_DIR}/.env" -f "$ORBSTACK_COMPOSE_FILE" stop hermes-agent 2>/dev/null || true
            ssh -o BatchMode=yes "${ssh_user}@${TRUENAS_HOST}" "sudo -n docker stop -t 25 hermes-main 2>/dev/null || true"

            echo "🔧 [State Sync] Pre-normalizzazione permessi su TrueNAS (${HERMES_ROOT_REMOTE})..."
            ssh -o BatchMode=yes "${ssh_user}@${TRUENAS_HOST}" \
                "sudo -n find '${HERMES_ROOT_REMOTE}' -path '${HERMES_ROOT_REMOTE}/common' -prune -o \( ! -uid 1000 -o ! -gid 1000 \) -exec chown -h olindo:k8s {} + && sudo -n chmod -R u+rwX,g+rwX,o+rX '${HERMES_ROOT_REMOTE}'" 2>/dev/null || true

            echo "📥 [State Sync] Sync Stato Istanza (HermesMain, rsync -az senza -u)..."
            rsync -az --itemize-changes -e "ssh -o BatchMode=yes" \
                --rsync-path="sudo -n rsync" \
                --exclude='/common/**' \
                --exclude='*.sock' \
                --exclude='*.sock.*' \
                --exclude='/*.lock' \
                --exclude='gateway-locks/' \
                --exclude='.local/state/hermes/gateway-locks/' \
                --exclude='.DS_Store' \
                --exclude='__pycache__/' \
                --exclude='.pytest_cache/' \
                "${ssh_user}@${TRUENAS_HOST}:${HERMES_ROOT_REMOTE}/HermesMain/" \
                "${HERMES_ROOT_LOCAL}/HermesMain/"

            echo "📥 [State Sync] Sync Workspace Condiviso (common, rsync -auz additivo)..."
            rsync -auz --itemize-changes -e "ssh -o BatchMode=yes" \
                --rsync-path="sudo -n rsync" \
                --exclude='.DS_Store' \
                --exclude='__pycache__/' \
                --exclude='.pytest_cache/' \
                "${ssh_user}@${TRUENAS_HOST}:${HERMES_ROOT_REMOTE}/common/" \
                "${HERMES_ROOT_LOCAL}/common/"

            echo "✅ [State Sync] Stato Hermes Agent allineato in ${HERMES_ROOT_LOCAL}/."
        fi
    else
        echo "ℹ️  [State Sync] TrueNAS è già spento (transizione OFF -> OFF): utilizzo stato locale in ${HERMES_ROOT_LOCAL}/."
    fi
}

# Eseguito in lab_mode_off.sh DOPO ensure_storage_off.yml
activate_orbstack_failover() {
    echo "🚀 [OrbStack Failover] Attivazione stack di failover su Mac Studio (${MAC_STUDIO_IP})..."
    prepare_orbstack_runtime_env

    # 1. Garantisce che il motore OrbStack sia avviato su macOS
    if ! orbctl status >/dev/null 2>&1; then
        echo "⚙️  Avvio motore OrbStack su Mac Studio..."
        orbctl start
    fi

    # 2. Avvio idempotente dello stack Docker Compose (11 container)
    docker compose --env-file "${FAILOVER_RUNTIME_DIR}/.env" -f "$ORBSTACK_COMPOSE_FILE" up -d --remove-orphans

    # 3. Gate di verifica healthcheck sui servizi locali (:4000, :9119, :8100, :8180, :8888, :3000)
    echo "🩺 [OrbStack Failover] Verifica prontezza servizi locali (:4000, :9119, :8100, :8180, :8888, :3000)..."
    local retries=30
    until curl -sf "http://127.0.0.1:4000/health/liveliness" >/dev/null 2>&1 \
       && curl -sf "http://127.0.0.1:9119/health" >/dev/null 2>&1 \
       && _is_tcp_open "127.0.0.1" 8100 \
       && _is_tcp_open "127.0.0.1" 8180 \
       && _is_tcp_open "127.0.0.1" 8888 \
       && _is_tcp_open "127.0.0.1" 3000; do
        retries=$((retries - 1))
        if [ "$retries" -le 0 ]; then
            echo "❌ [OrbStack Failover] Timeout healthcheck sullo stack OrbStack!"
            docker compose --env-file "${FAILOVER_RUNTIME_DIR}/.env" -f "$ORBSTACK_COMPOSE_FILE" ps
            return 1
        fi
        sleep 2
    done

    # 4. Switchover atomico DNS Unbound su OPNsense verso Mac Studio (10.10.20.100)
    python3 "${ROOT_DIR}/scripts/network/switch_failover_dns.py" --target off
    echo "✅ [OrbStack Failover] Stack OrbStack ATTIVO e DNS commutato su ${MAC_STUDIO_IP}."
}

# Configura il backend Traefik su TrueNAS per home-internal:
# - "full": proxy trasparente verso K8s VIP (https://10.10.20.56) per socket HTTP/2 riutilizzati
# - "eco":  inoltro locale al container homepage TrueNAS (:3000)
set_truenas_home_internal_backend() {
    local mode="$1"
    local ssh_user
    ssh_user="$(_resolve_truenas_ssh_user)"
    [ -n "$ssh_user" ] || return 0

    if [ "$mode" = "full" ]; then
        echo "🔀 [Traefik Dynamic] Configurazione backend homepage TrueNAS -> K8s Ingress (https://10.10.20.56)..."
        ssh -o BatchMode=yes "${ssh_user}@${TRUENAS_HOST}" \
            "sudo -n sed -i 's|url: \"http://10.10.20.50:3000\"|url: \"https://10.10.20.56\"|g' /mnt/stripe/truenas-docker/mcp/dynamic.yaml 2>/dev/null || true"
    elif [ "$mode" = "eco" ]; then
        echo "🔀 [Traefik Dynamic] Configurazione backend homepage TrueNAS -> Locale (:3000)..."
        ssh -o BatchMode=yes "${ssh_user}@${TRUENAS_HOST}" \
            "sudo -n sed -i 's|url: \"https://10.10.20.56\"|url: \"http://10.10.20.50:3000\"|g' /mnt/stripe/truenas-docker/mcp/dynamic.yaml 2>/dev/null || true"
    fi
}

# Eseguito in lab_mode_eco.sh e lab_mode_full.sh DOPO ensure_storage_on.yml
# Copre OFF->ECO, OFF->FULL, FULL->ECO, ECO->FULL, ECO->ECO, FULL->FULL e Stati Parziali/Sporchi
deactivate_orbstack_failover_to_truenas() {
    local target_mode="${1:-eco}"
    echo "🔄 [OrbStack Failback] Verifica stato tra Mac Studio e TrueNAS (${TRUENAS_HOST}) per target ${target_mode}..."

    local ssh_user
    ssh_user="$(_resolve_truenas_ssh_user)"

    local orbstack_was_active="false"
    if [ -f "$ORBSTACK_COMPOSE_FILE" ] && [ -n "$(docker compose --env-file "${FAILOVER_RUNTIME_DIR}/.env" -f "$ORBSTACK_COMPOSE_FILE" ps -q 2>/dev/null)" ]; then
        orbstack_was_active="true"
    fi

    # 1. Se hermes-main (o hermes-agent legacy) era attivo su OrbStack (transizione da OFF -> ECO/FULL),
    #    ferma hermes-main locale e sincronizza i file più recenti verso TrueNAS (KISS #1: rsync -auz senza --delete).
    #    Se invece siamo in FULL->ECO, ECO->FULL, ECO->ECO o FULL->FULL, questo blocco viene saltato in 0ms!
    if docker ps --format '{{.Names}}' 2>/dev/null | grep -q -E '^(hermes-main|hermes-agent)$'; then
        echo "🛑 [State Sync] Rilevato hermes attivo su OrbStack: arresto per flush sessioni maturate in OFF..."
        docker compose --env-file "${FAILOVER_RUNTIME_DIR}/.env" -f "$ORBSTACK_COMPOSE_FILE" stop hermes-agent 2>/dev/null || true

        if [ -n "$(ls -A "${HERMES_ROOT_LOCAL}" 2>/dev/null)" ] && [ -n "$ssh_user" ]; then
            echo "🛑 [State Sync] Arresto preventivo hermes-main su TrueNAS..."
            ssh -o BatchMode=yes "${ssh_user}@${TRUENAS_HOST}" "sudo -n docker stop -t 25 hermes-main 2>/dev/null || true"

            echo "🔧 [State Sync] Pre-normalizzazione permessi su TrueNAS prima del push..."
            ssh -o BatchMode=yes "${ssh_user}@${TRUENAS_HOST}" \
                "sudo -n mkdir -p '${HERMES_ROOT_REMOTE}/HermesMain' '${HERMES_ROOT_REMOTE}/common/prj' && sudo -n find '${HERMES_ROOT_REMOTE}' -path '${HERMES_ROOT_REMOTE}/common' -prune -o \( ! -uid 1000 -o ! -gid 1000 \) -exec chown -h olindo:k8s {} + && sudo -n chmod -R u+rwX,g+rwX,o+rX '${HERMES_ROOT_REMOTE}'" 2>/dev/null || true

            echo "📤 [State Sync] Sync Stato Istanza HermesMain (Mac -> TrueNAS, rsync -az senza -u)..."
            rsync -az --no-owner --no-group --itemize-changes -e "ssh -o BatchMode=yes" \
                --rsync-path="sudo -n rsync" \
                --exclude='/common/**' \
                --exclude='*.sock' \
                --exclude='*.sock.*' \
                --exclude='/*.lock' \
                --exclude='gateway-locks/' \
                --exclude='.local/state/hermes/gateway-locks/' \
                --exclude='.DS_Store' \
                --exclude='__pycache__/' \
                --exclude='.pytest_cache/' \
                "${HERMES_ROOT_LOCAL}/HermesMain/" \
                "${ssh_user}@${TRUENAS_HOST}:${HERMES_ROOT_REMOTE}/HermesMain/"

            echo "📤 [State Sync] Sync Workspace Condiviso common (Mac -> TrueNAS, rsync -auz additivo)..."
            rsync -auz --no-owner --no-group --itemize-changes -e "ssh -o BatchMode=yes" \
                --rsync-path="sudo -n rsync" \
                --exclude='.DS_Store' \
                --exclude='__pycache__/' \
                --exclude='.pytest_cache/' \
                "${HERMES_ROOT_LOCAL}/common/" \
                "${ssh_user}@${TRUENAS_HOST}:${HERMES_ROOT_REMOTE}/common/"

            echo "🔧 [State Sync] Post-normalizzazione permessi Git-safe e SGID su TrueNAS..."
            ssh -o BatchMode=yes "${ssh_user}@${TRUENAS_HOST}" \
                "sudo -n find '${HERMES_ROOT_REMOTE}' -path '${HERMES_ROOT_REMOTE}/common' -prune -o \( ! -uid 1000 -o ! -gid 1000 \) -exec chown -h olindo:k8s {} + && sudo -n chmod -R u+rwX,g+rwX,o+rX '${HERMES_ROOT_REMOTE}' && sudo -n find '${HERMES_ROOT_REMOTE}' -type d -exec chmod g+s {} + && (sudo -n docker start hermes-main 2>/dev/null || true)"
        else
            echo "⚠️  [State Sync] Cartella locale ${HERMES_ROOT_LOCAL} vuota o SSH non disponibile: salto rsync verso TrueNAS."
        fi
    else
        echo "ℹ️  [State Sync] Nessun container hermes attivo su OrbStack (transizione tra stati con TrueNAS già primario)."
    fi

    # 1b. Sincronizzazione dichiarativa della configurazione Homepage ECO (Git -> TrueNAS)
    if [ -n "$ssh_user" ] && [ -d "${ROOT_DIR}/homepage/lab_mode_eco" ]; then
        echo "📤 [Homepage Sync] Allineamento homepage/lab_mode_eco/ -> TrueNAS (/mnt/stripe/truenas-docker/homepage/)..."
        rsync -az --no-owner --no-group -e "ssh -o BatchMode=yes" \
            --rsync-path="sudo -n rsync" \
            --exclude='.DS_Store' \
            --exclude='logs/' \
            "${ROOT_DIR}/homepage/lab_mode_eco/" \
            "${ssh_user}@${TRUENAS_HOST}:/mnt/stripe/truenas-docker/homepage/" || true
    fi

    # 2. Auto-Healing KISS #5: Se anche una sola delle 4 porte su TrueNAS (8100, 9119, 4000, 8888)
    #    non è già aperta (es. container fermato manualmente o primo avvio), forza 'docker compose up -d' su TrueNAS
    if ! _is_tcp_open "$TRUENAS_HOST" 8100 || ! _is_tcp_open "$TRUENAS_HOST" 9119 || ! _is_tcp_open "$TRUENAS_HOST" 4000 || ! _is_tcp_open "$TRUENAS_HOST" 8888; then
        if [ -n "$ssh_user" ]; then
            echo "🐳 [Self-Healing] Almeno una porta tra :8100, :9119, :4000, :8888 non è ancora attiva su TrueNAS: esecuzione docker compose up -d..."
            ssh -o BatchMode=yes "${ssh_user}@${TRUENAS_HOST}" \
                "cd /mnt/stripe/truenas-docker && (sudo -n docker compose up -d litellm-postgres litellm hermes-agent dozzle 2>/dev/null || docker compose up -d litellm-postgres litellm hermes-agent dozzle) && cd /mnt/stripe/truenas-docker/mcp && (sudo -n docker compose up -d 2>/dev/null || docker compose up -d)"
        fi
    fi

    # 3. Gate di verifica sulle 4 porte di TrueNAS (:8100, :9119, :4000, :8888) prima dello switch DNS
    echo "🩺 [OrbStack Failback] Verifica porte attive su TrueNAS (${TRUENAS_HOST}:8100, :9119, :4000, :8888)..."
    for port in 8100 9119 4000 8888; do
        local t_wait=30
        until _is_tcp_open "$TRUENAS_HOST" "$port"; do
            t_wait=$((t_wait - 1))
            if [ "$t_wait" -le 0 ]; then
                echo "❌ [OrbStack Failback] Porta ${TRUENAS_HOST}:${port} non risponde su TrueNAS!"
                return 1
            fi
            sleep 2
        done
    done

    # 4. Switchover atomico e idempotente DNS Unbound su OPNsense
    if [ "$orbstack_was_active" = "true" ]; then
        python3 "${ROOT_DIR}/scripts/network/switch_failover_dns.py" --target "$target_mode"
    elif [ "$target_mode" = "eco" ]; then
        python3 "${ROOT_DIR}/scripts/network/switch_failover_dns.py" --target eco
    fi

    # 5. Arresto e rimozione pulita dello stack di failover su OrbStack (solo se ci sono container del progetto)
    if [ "$orbstack_was_active" = "true" ]; then
        echo "🧹 [OrbStack Failback] Spegnimento stack orbstack-failover su Mac Studio..."
        docker compose --env-file "${FAILOVER_RUNTIME_DIR}/.env" -f "$ORBSTACK_COMPOSE_FILE" down --remove-orphans
    fi

    echo "✅ [OrbStack Failback] Servizi verificati su TrueNAS (${TRUENAS_HOST}), DNS allineato e OrbStack in standby."
}

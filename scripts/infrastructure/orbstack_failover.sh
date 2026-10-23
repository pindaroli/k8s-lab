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
    mkdir -p \
        "${FAILOVER_RUNTIME_DIR}/hermes-data" \
        "${FAILOVER_RUNTIME_DIR}/dozzle"
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

    # Esporta le variabili in ambiente per l'interpolazione Compose
    set -a
    source "${FAILOVER_RUNTIME_DIR}/.env.ai"
    set +a
}

# Eseguito in lab_mode_off.sh PRIMA di ensure_storage_off.yml (Copre FULL->OFF, ECO->OFF, OFF->OFF)
sync_hermes_state_from_truenas() {
    prepare_orbstack_runtime_env
    mkdir -p "${HERMES_ROOT_LOCAL}/HermesMain"

    if _is_tcp_open "$TRUENAS_HOST" 22; then
        local ssh_user
        ssh_user="$(_resolve_truenas_ssh_user)"
        if [ -n "$ssh_user" ]; then
            echo "📥 [State Sync] Sincronizzazione incrementale stato Hermes da TrueNAS (${HERMES_ROOT_REMOTE}/) a Mac Studio (${HERMES_ROOT_LOCAL}/)..."
            # Supporto transizione legacy se /mnt/stripe/hermesAgent non esiste ancora ma esiste /mnt/stripe/hermes-agent
            ssh -o BatchMode=yes "${ssh_user}@${TRUENAS_HOST}" \
                "if [ ! -d '${HERMES_ROOT_REMOTE}' ] && [ -d '/mnt/stripe/hermes-agent' ]; then sudo -n mkdir -p '${HERMES_ROOT_REMOTE}' && sudo -n cp -a /mnt/stripe/hermes-agent '${HERMES_ROOT_REMOTE}/HermesMain'; fi" 2>/dev/null || true

            rsync -auz -e "ssh -o BatchMode=yes" \
                --rsync-path="sudo -n rsync" \
                "${ssh_user}@${TRUENAS_HOST}:${HERMES_ROOT_REMOTE}/" \
                "${HERMES_ROOT_LOCAL}/"
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
    docker compose --env-file "${FAILOVER_RUNTIME_DIR}/.env.ai" -f "$ORBSTACK_COMPOSE_FILE" up -d --remove-orphans

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
            docker compose --env-file "${FAILOVER_RUNTIME_DIR}/.env.ai" -f "$ORBSTACK_COMPOSE_FILE" ps
            return 1
        fi
        sleep 2
    done

    # 4. Switchover atomico DNS Unbound su OPNsense verso Mac Studio (10.10.20.100)
    python3 "${ROOT_DIR}/scripts/network/switch_failover_dns.py" --target orbstack
    echo "✅ [OrbStack Failover] Stack OrbStack ATTIVO e DNS commutato su ${MAC_STUDIO_IP}."
}

# Eseguito in lab_mode_eco.sh e lab_mode_full.sh DOPO ensure_storage_on.yml
# Copre OFF->ECO, OFF->FULL, FULL->ECO, ECO->FULL, ECO->ECO, FULL->FULL e Stati Parziali/Sporchi
deactivate_orbstack_failover_to_truenas() {
    echo "🔄 [OrbStack Failback] Verifica stato tra Mac Studio e TrueNAS (${TRUENAS_HOST})..."

    local ssh_user
    ssh_user="$(_resolve_truenas_ssh_user)"

    # 1. Se hermes-main (o hermes-agent legacy) era attivo su OrbStack (transizione da OFF -> ECO/FULL),
    #    ferma hermes-main locale e sincronizza i file più recenti verso TrueNAS (KISS #1: rsync -auz senza --delete).
    #    Se invece siamo in FULL->ECO, ECO->FULL, ECO->ECO o FULL->FULL, questo blocco viene saltato in 0ms!
    if docker ps --format '{{.Names}}' 2>/dev/null | grep -q -E '^(hermes-main|hermes-agent)$'; then
        echo "🛑 [State Sync] Rilevato hermes attivo su OrbStack: arresto per flush sessioni maturate in OFF..."
        docker compose --env-file "${FAILOVER_RUNTIME_DIR}/.env.ai" -f "$ORBSTACK_COMPOSE_FILE" stop hermes-agent 2>/dev/null || true

        if [ -n "$(ls -A "${HERMES_ROOT_LOCAL}" 2>/dev/null)" ] && [ -n "$ssh_user" ]; then
            echo "📤 [State Sync] Sincronizzazione sicura multi-agente (rsync -auz, zero delete) da Mac Studio (${HERMES_ROOT_LOCAL}/) -> TrueNAS (${HERMES_ROOT_REMOTE}/)..."
            ssh -o BatchMode=yes "${ssh_user}@${TRUENAS_HOST}" "sudo -n mkdir -p '${HERMES_ROOT_REMOTE}'" 2>/dev/null || true
            rsync -auz -e "ssh -o BatchMode=yes" \
                --rsync-path="sudo -n rsync" \
                "${HERMES_ROOT_LOCAL}/" \
                "${ssh_user}@${TRUENAS_HOST}:${HERMES_ROOT_REMOTE}/"
            ssh -o BatchMode=yes "${ssh_user}@${TRUENAS_HOST}" \
                "sudo -n docker restart hermes-main 2>/dev/null || sudo -n docker restart hermes-agent 2>/dev/null || true" || true
        else
            echo "⚠️  [State Sync] Cartella locale ${HERMES_ROOT_LOCAL} vuota o SSH non disponibile: salto rsync verso TrueNAS."
        fi
    else
        echo "ℹ️  [State Sync] Nessun container hermes attivo su OrbStack (transizione tra stati con TrueNAS già primario)."
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

    # 4. Switchover atomico e idempotente DNS Unbound su OPNsense verso TrueNAS (10.10.20.50)
    python3 "${ROOT_DIR}/scripts/network/switch_failover_dns.py" --target truenas

    # 5. Arresto e rimozione pulita dello stack di failover su OrbStack (solo se ci sono container del progetto)
    if [ -f "$ORBSTACK_COMPOSE_FILE" ] && [ -n "$(docker compose --env-file "${FAILOVER_RUNTIME_DIR}/.env.ai" -f "$ORBSTACK_COMPOSE_FILE" ps -q 2>/dev/null)" ]; then
        echo "🧹 [OrbStack Failback] Spegnimento stack orbstack-failover su Mac Studio..."
        docker compose --env-file "${FAILOVER_RUNTIME_DIR}/.env.ai" -f "$ORBSTACK_COMPOSE_FILE" down --remove-orphans
    fi

    echo "✅ [OrbStack Failback] Servizi verificati su TrueNAS (${TRUENAS_HOST}), DNS allineato e OrbStack in standby."
}

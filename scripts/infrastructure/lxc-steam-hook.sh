#!/usr/bin/env bash
# ==============================================================================
# PROXMOX LXC HOOKSCRIPT: lxc-steam (CT 301)
# ==============================================================================
# - pre-start: ferma lxc-ollama (CT 300) con timeout, imposta gpu-turbo (2900MHz)
# - post-stop: imposta gpu-eco (auto/600MHz), avvia lxc-ollama (CT 300)
# - Segnalazioni su Telegram ed Email in caso di anomalie
# ==============================================================================

set -u

vmid="$1"
phase="$2"

OLLAMA_VMID=300
SHUTDOWN_TIMEOUT=60
POLL_INTERVAL=2

# Risoluzione directory per source di utils.sh
SCRIPT_DIR="$(dirname "$(readlink -f "$0")")"
if [ -f "$SCRIPT_DIR/utils.sh" ]; then
    # shellcheck source=/dev/null
    source "$SCRIPT_DIR/utils.sh"
elif [ -f "/var/lib/vz/snippets/utils.sh" ]; then
    # shellcheck source=/dev/null
    source "/var/lib/vz/snippets/utils.sh"
fi

notify_error() {
    local title="$1"
    local error_details="$2"
    local action_taken="$3"

    echo "❌ [ALERT] $title: $error_details" >&2

    local table_rows="<tr>
  <td style=\"padding: 8px 12px; font-weight: 600; color: #475569; border-bottom: 1px solid #f1f5f9;\">Host</td>
  <td style=\"padding: 8px 12px; color: #1e293b; border-bottom: 1px solid #f1f5f9; font-family: monospace;\">pve3.pindaroli.org (10.10.10.31)</td>
</tr>
<tr>
  <td style=\"padding: 8px 12px; font-weight: 600; color: #475569; border-bottom: 1px solid #f1f5f9;\">Container Target</td>
  <td style=\"padding: 8px 12px; color: #1e293b; border-bottom: 1px solid #f1f5f9;\">lxc-steam (CT $vmid)</td>
</tr>
<tr>
  <td style=\"padding: 8px 12px; font-weight: 600; color: #475569; border-bottom: 1px solid #f1f5f9;\">Fase Hook</td>
  <td style=\"padding: 8px 12px; color: #1e293b; border-bottom: 1px solid #f1f5f9;\"><code style=\"background:#e2e8f0; padding:2px 6px; border-radius:4px;\">$phase</code></td>
</tr>
<tr>
  <td style=\"padding: 8px 12px; font-weight: 600; color: #475569; border-bottom: 1px solid #f1f5f9;\">Dettagli Errore</td>
  <td style=\"padding: 8px 12px; color: #ef4444; font-weight: 600; border-bottom: 1px solid #f1f5f9;\">$error_details</td>
</tr>
<tr>
  <td style=\"padding: 8px 12px; font-weight: 600; color: #475569; border-bottom: 1px solid #f1f5f9;\">Azione Applicata</td>
  <td style=\"padding: 8px 12px; color: #1e293b; border-bottom: 1px solid #f1f5f9;\">$action_taken</td>
</tr>"

    local email_html
    email_html="$(build_html_email_template "🎮" "$title" "Orchestrazione Carichi PVE3 (Steam / Ollama)" "ERRORE" "#ef4444" "$table_rows")"

    local tg_msg="🚨 <b>[PVE3 Alert] ${title}</b>%0A%0A🖥️ <b>Host:</b> pve3%0A📦 <b>Container:</b> CT ${vmid} (lxc-steam)%0A⚙️ <b>Fase:</b> ${phase}%0A⚠️ <b>Errore:</b> ${error_details}%0A🛡️ <b>Azione:</b> ${action_taken}"

    # Invia sia Telegram sia Email come richiesto dall'utente
    send_telegram "$tg_msg"
    send_summary_email "${DEFAULT_EMAIL_RECIPIENT:-o.pindaro@gmail.com}" "🎮 [PVE3 Alert] $title" "$email_html" "$tg_msg"
}

is_container_running() {
    local target_id="$1"
    pct status "$target_id" 2>/dev/null | grep -q "status: running"
}

is_container_stopped() {
    local target_id="$1"
    pct status "$target_id" 2>/dev/null | grep -q "status: stopped"
}

# ------------------------------------------------------------------------------
# FASE: PRE-START (Prima dell'avvio di lxc-steam)
# ------------------------------------------------------------------------------
if [ "$phase" == "pre-start" ]; then
    echo "[$vmid] [HOOK] Inizio fase pre-start..."

    # 1. Verifica e arresto di lxc-ollama (CT 300)
    if is_container_running "$OLLAMA_VMID"; then
        echo "[$vmid] [HOOK] CT $OLLAMA_VMID (Ollama) è in esecuzione. Richiesta shutdown controllato..."
        if ! pct shutdown "$OLLAMA_VMID" --timeout "$SHUTDOWN_TIMEOUT" 2>&1; then
            echo "[$vmid] [HOOK] pct shutdown fallito. Tentativo stop forzato..."
            pct stop "$OLLAMA_VMID" 2>&1 || true
        fi

        # Polling attesa stato stopped
        start_time=$(date +%s)
        stopped=false
        while [ $(( $(date +%s) - start_time )) -lt "$SHUTDOWN_TIMEOUT" ]; do
            if is_container_stopped "$OLLAMA_VMID"; then
                stopped=true
                break
            fi
            sleep "$POLL_INTERVAL"
        done

        if [ "$stopped" != "true" ]; then
            notify_error "Errore Spegnimento Ollama" \
                         "Timeout di ${SHUTDOWN_TIMEOUT}s: CT $OLLAMA_VMID non si è arrestato." \
                         "Avvio di lxc-steam (CT $vmid) bloccato per prevenire contesa hardware."
            exit 1
        fi
        echo "[$vmid] [HOOK] CT $OLLAMA_VMID arrestato con successo."
    else
        echo "[$vmid] [HOOK] CT $OLLAMA_VMID già spento."
    fi

    # 2. Impostazione GPU in modalità TURBO
    echo "[$vmid] [HOOK] Impostazione GPU Radeon 890M in modalità TURBO (2900MHz)..."
    if [ -x /usr/local/bin/gpu-turbo ]; then
        if ! /usr/local/bin/gpu-turbo; then
            notify_error "Errore Switch GPU Turbo" \
                         "Esecuzione di /usr/local/bin/gpu-turbo fallita." \
                         "Avvio di lxc-steam bloccato."
            exit 1
        fi
    else
        notify_error "Script GPU Non Trovato" \
                     "/usr/local/bin/gpu-turbo mancante o non eseguibile." \
                     "Avvio di lxc-steam bloccato."
        exit 1
    fi

    # 3. Verifica stato nel sysfs kernel
    current_level=$(cat /sys/class/drm/card0/device/power_dpm_force_performance_level 2>/dev/null || echo "unknown")
    if [ "$current_level" != "high" ]; then
        notify_error "Verifica Livello Energetico Fallita" \
                     "power_dpm_force_performance_level è '$current_level' (atteso 'high')." \
                     "Avvio di lxc-steam bloccato."
        exit 1
    fi

    echo "[$vmid] [HOOK] GPU verificata in stato 'high'. Avvio lxc-steam autorizzato."
    exit 0
fi

# ------------------------------------------------------------------------------
# FASE: POST-STOP (Dopo lo shutdown di lxc-steam)
# ------------------------------------------------------------------------------
if [ "$phase" == "post-stop" ]; then
    echo "[$vmid] [HOOK] Inizio fase post-stop: ripristino GPU ECO e riavvio Ollama..."

    # 1. Ripristino GPU ECO
    if [ -x /usr/local/bin/gpu-eco ]; then
        if ! /usr/local/bin/gpu-eco; then
            notify_error "Errore Ripristino GPU Eco" \
                         "Esecuzione di /usr/local/bin/gpu-eco fallita dopo stop di Steam." \
                         "La GPU potrebbe essere rimasta in stato ad alto consumo."
        fi
    else
        notify_error "Script GPU Non Trovato" \
                     "/usr/local/bin/gpu-eco mancante o non eseguibile." \
                     "Impossibile ripristinare il profilo energetico eco."
    fi

    # 2. Riavvio automatico di lxc-ollama (CT 300)
    if is_container_stopped "$OLLAMA_VMID"; then
        echo "[$vmid] [HOOK] Riavvio automatico di CT $OLLAMA_VMID (Ollama)..."
        if ! pct start "$OLLAMA_VMID" 2>&1; then
            notify_error "Errore Riavvio Ollama" \
                         "Comando 'pct start $OLLAMA_VMID' fallito." \
                         "LXC Ollama è rimasto nello stato spento."
        else
            echo "[$vmid] [HOOK] CT $OLLAMA_VMID riavviato con successo."
        fi
    else
        echo "[$vmid] [HOOK] CT $OLLAMA_VMID non è in stato stopped (stato attuale: $(pct status "$OLLAMA_VMID"))."
    fi

    exit 0
fi

exit 0

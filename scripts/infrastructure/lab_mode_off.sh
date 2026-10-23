#!/usr/bin/env bash
# Spegnimento totale del rack Homelab: K8s, PVE e TrueNAS spenti + Failover OrbStack su Mac Studio
set -Eeuo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"
cd "$ROOT_DIR" || exit 1

source "$SCRIPT_DIR/procedure_scope.sh"
source "$SCRIPT_DIR/utils.sh"
source "$SCRIPT_DIR/orbstack_failover.sh"

PROCEDURE_NAME="lab_mode_off"
init_procedure_scope "$PROCEDURE_NAME"

LOG_DIR="${ROOT_DIR}/logs/automation"
mkdir -p "$LOG_DIR"
LOG_FILE="${LOG_DIR}/${PROCEDURE_NAME}_$(date +%Y%m%d_%H%M%S).log"

exec > >(tee -a "$LOG_FILE") 2>&1

on_error() {
    local exit_code=$?
    local err_msg="Procedura ${PROCEDURE_NAME} fallita alla riga $1 (exit code: $exit_code)"
    echo "❌ $err_msg"

    if has_error_been_reported; then
        echo "ℹ️ [NESTED] Errore già segnalato. Uscita senza alert duplicato."
        exit "$exit_code"
    fi
    mark_error_reported

    send_telegram "❌ <b>ERRORE CRITICO HOMELAB</b>%0A${err_msg}%0AConsulta l'email per il log completo dell'errore." "Homelab Alert"

    local table="<tr><td><b>Procedura:</b></td><td>${PROCEDURE_NAME}</td></tr><tr><td><b>Errore:</b></td><td>Riga $1 (Exit Code: $exit_code)</td></tr><tr><td><b>Log Allegato:</b></td><td>$(basename "$LOG_FILE")</td></tr>"
    local html
    html="$(build_html_email_template "🚨" "Errore ${PROCEDURE_NAME}" "Homelab Mode Orchestration" "ERRORE" "#ef4444" "$table")"
    send_summary_email "$DEFAULT_EMAIL_RECIPIENT" "🚨 [ALERT] Errore in ${PROCEDURE_NAME}" "$html" "$err_msg" "$LOG_FILE"
    exit "$exit_code"
}
trap 'on_error $LINENO' ERR

echo "🛑 Avvio convergenza: ${PROCEDURE_NAME}..."
echo "➡️  Stato Target: RACK DARK (K8s, Proxmox VE e TrueNAS Storage SPENTI | Failover OrbStack su Mac Studio ATTIVO)"
echo "📄 Log di sessione: $LOG_FILE"
echo ""

if is_root_procedure; then
    send_telegram "🛑 <b>Avvio ${PROCEDURE_NAME}</b>%0ASpegnimento totale dell'infrastruttura Homelab: K8s -> PVE -> Sync Hermes -> TrueNAS -> Avvio Failover OrbStack..." "Homelab Mode"
fi

# FASE 1: GARANTISCE COMPUTE LAYER OFFLINE (K8S + PVE) PRIMA DI TRUENAS
echo "▶️  [Fase 1/4] Esecuzione: ensure_compute_off..."
ansible-playbook -i ansible/inventory.ini ansible/playbooks/infrastructure/ensure_compute_off.yml

# FASE 2: SINCRONIZZAZIONE STATO HERMES E FILE .ENV PRIMA DELLO SPEGNIMENTO DI TRUENAS
echo "▶️  [Fase 2/4] Esecuzione: sync_hermes_state_from_truenas..."
sync_hermes_state_from_truenas

# FASE 3: FLUSH E SPEGNIMENTO FISICO TRUENAS BARE METAL
echo "▶️  [Fase 3/4] Esecuzione: ensure_storage_off..."
ansible-playbook -i ansible/inventory.ini ansible/playbooks/infrastructure/ensure_storage_off.yml

# FASE 4: ATTIVAZIONE STACK ORBSTACK SU MAC STUDIO E SWITCHOVER DNS UNBOUND (10.10.20.100)
echo "▶️  [Fase 4/4] Esecuzione: activate_orbstack_failover..."
activate_orbstack_failover

# NOTIFICA FINALE RIASSUNTIVA DI SUCCESSO
if is_root_procedure; then
    send_telegram "🌙 <b>${PROCEDURE_NAME} Completato!</b>%0ATutti i nodi fisici e VM sono disattivati in sicurezza. Failover OrbStack attivo su Mac Studio (10.10.20.100)." "Homelab Mode"
    stop_table="<tr><td><b>Modalità:</b></td><td>RACK DARK (Zero Watt Standby + OrbStack Failover)</td></tr><tr><td><b>Kubernetes:</b></td><td>OFFLINE (Cluster Talos disattivato)</td></tr><tr><td><b>Hypervisors:</b></td><td>OFFLINE (pve1, pve2, pve3 spenti)</td></tr><tr><td><b>Storage TrueNAS:</b></td><td>OFFLINE (Bare metal spento)</td></tr><tr><td><b>Failover Mac Studio:</b></td><td>ONLINE (OrbStack 10.10.20.100: MCP :8100 [7 srv], Hermes :9119, LiteLLM :4000, Dozzle :8888)</td></tr>"
    stop_html="$(build_html_email_template "🌙" "Completato: ${PROCEDURE_NAME}" "Homelab Mode Orchestration" "SUCCESSO" "#10b981" "$stop_table")"
    send_summary_email "$DEFAULT_EMAIL_RECIPIENT" "✅ [SUCCESS] ${PROCEDURE_NAME}" "$stop_html" "${PROCEDURE_NAME} completato con successo"
    complete_procedure_scope
else
    echo "ℹ️ [NESTED] Procedura ${PROCEDURE_NAME} completata. Segnalazione finale delegata a ${HOMELAB_PARENT_PROCEDURE}."
fi

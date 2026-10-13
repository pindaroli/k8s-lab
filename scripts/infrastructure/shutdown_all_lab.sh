#!/usr/bin/env bash
# Spegnimento totale del rack Homelab (K8s -> PVE -> TrueNAS)
set -Eeuo pipefail
# ==============================================================================
# shutdown_all_lab.sh
# ==============================================================================
# Procedura globale di spegnimento totale del rack Homelab:
# 1. Quiesce K8s Talos e spegnimento cluster
# 2. Shutdown ACPI nodi Proxmox VE (PVE3, PVE2, PVE1)
# 3. Flush ZFS e shutdown controllato TrueNAS Bare Metal (10.10.20.50)
# 4. Notifiche Start & Stop (Telegram + Email HTML)
# 5. Notifiche intermediari checkpoint spegnimento (Solo Telegram)
# 6. Trap di Errore: notifica immediata Telegram + Email con allegato log completo
# ==============================================================================

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"
cd "$ROOT_DIR" || exit 1

source "$SCRIPT_DIR/procedure_scope.sh"
source "$SCRIPT_DIR/utils.sh"

PROCEDURE_NAME="shutdown_all_lab"
init_procedure_scope "$PROCEDURE_NAME"

LOG_DIR="${ROOT_DIR}/logs/automation"
mkdir -p "$LOG_DIR"
LOG_FILE="${LOG_DIR}/${PROCEDURE_NAME}_$(date +%Y%m%d_%H%M%S).log"

# Cattura output completo su logfile dedicato e terminale
exec > >(tee -a "$LOG_FILE") 2>&1

on_error() {
    local exit_code=$?
    local err_msg="Procedura ${PROCEDURE_NAME} fallita alla riga $1 (exit code: $exit_code)"
    echo "❌ $err_msg"

    # 1. Alert Telegram immediato
    send_telegram "❌ <b>ERRORE CRITICO HOMELAB</b>%0A${err_msg}%0AConsulta l'email per il log completo dell'errore." "Homelab Alert"

    # 2. Email HTML con allegato log completo
    local table="<tr><td><b>Procedura:</b></td><td>${PROCEDURE_NAME}</td></tr><tr><td><b>Errore:</b></td><td>Riga $1 (Exit Code: $exit_code)</td></tr><tr><td><b>Log Allegato:</b></td><td>$(basename "$LOG_FILE")</td></tr>"
    local html
    html="$(build_html_email_template "🚨" "Errore ${PROCEDURE_NAME}" "Homelab Power Automation" "ERRORE" "#ef4444" "$table")"
    send_summary_email "$DEFAULT_EMAIL_RECIPIENT" "🚨 [ALERT] Errore in ${PROCEDURE_NAME}" "$html" "$err_msg" "$LOG_FILE"
    exit "$exit_code"
}
trap 'on_error $LINENO' ERR

echo "🛑 Avvio sequenza: ${PROCEDURE_NAME}..."
echo "➡️  Spegnimento Globale: K8s &rarr; Proxmox VE &rarr; TrueNAS Storage."
echo "📄 Log di sessione: $LOG_FILE"
echo ""

# Ping informativo iniziale (SOLO Telegram, NESSUNA mail di start)
send_telegram "🛑 <b>Avvio ${PROCEDURE_NAME}</b>%0ASpegnimento totale dell'infrastruttura Homelab: K8s -> PVE -> TrueNAS..." "Homelab Power"

# ------------------------------------------------------------------------------
# FASE 1: SPEGNIMENTO CARICHI K8S E HYPERVISOR PVE (Invoca sotto-procedura)
# ------------------------------------------------------------------------------
echo "▶️  [Fase 1/2] Esecuzione sotto-procedura: shutdown_to_truenas_only..."
"$SCRIPT_DIR/shutdown_to_truenas_only.sh"

# ------------------------------------------------------------------------------
# FASE 2: FLUSH E SPEGNIMENTO FISICO TRUENAS BARE METAL
# ------------------------------------------------------------------------------
echo "▶️  [Fase 2/2] Esecuzione spegnimento fisico TrueNAS Bare Metal..."
ansible-playbook -i ansible/inventory.ini ansible/playbooks/infrastructure/shutdown_all_lab.yml --tags truenas

# ------------------------------------------------------------------------------
# NOTIFICA FINALE RIASSUNTIVA DI SUCCESSO (Unica per l'intera sequenza)
# ------------------------------------------------------------------------------
send_telegram "🌙 <b>${PROCEDURE_NAME} Completato!</b>%0ATutti i server fisici e VM del lab sono spenti in sicurezza. Rack offline." "Homelab Power"
stop_table="<tr><td><b>Stato:</b></td><td>SUCCESSO (Rack Spento)</td></tr><tr><td><b>Kubernetes:</b></td><td>OFFLINE (Cluster Talos disattivato)</td></tr><tr><td><b>Hypervisors:</b></td><td>OFFLINE (pve1, pve2, pve3 spenti)</td></tr><tr><td><b>Storage TrueNAS:</b></td><td>OFFLINE (Bare metal spento)</td></tr>"
stop_html="$(build_html_email_template "🌙" "Completato: ${PROCEDURE_NAME}" "Homelab Power Automation" "SUCCESSO" "#10b981" "$stop_table")"
send_summary_email "$DEFAULT_EMAIL_RECIPIENT" "✅ [SUCCESS] ${PROCEDURE_NAME}" "$stop_html" "${PROCEDURE_NAME} completato con successo"

complete_procedure_scope

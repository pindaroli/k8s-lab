#!/usr/bin/env bash
# Spegnimento a risparmio energetico: K8s e PVE OFF (Solo TrueNAS)
set -Eeuo pipefail
# ==============================================================================
# shutdown_to_truenas_only.sh
# ==============================================================================
# Spegnimento K8s e Proxmox per risparmio energetico (Solo TrueNAS attivo).
# - Cordon Talos, Quiesce DB CNPG, Shutdown Talos K8s
# - Shutdown fisico ACPI Hypervisor Proxmox VE (PVE3, PVE2, PVE1)
# - Validazione standalone TrueNAS
# - Notifiche Start & Stop (Telegram + Email HTML)
# - Notifiche intermediari checkpoint spegnimento (Solo Telegram)
# - Trap di Errore: notifica immediata Telegram + Email con allegato log completo
# ==============================================================================

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"
cd "$ROOT_DIR" || exit 1

source "$SCRIPT_DIR/procedure_scope.sh"
source "$SCRIPT_DIR/utils.sh"

PROCEDURE_NAME="shutdown_to_truenas_only"
init_procedure_scope "$PROCEDURE_NAME"

LOG_DIR="${ROOT_DIR}/logs/automation"
mkdir -p "$LOG_DIR"
LOG_FILE="${LOG_DIR}/${PROCEDURE_NAME}_$(date +%Y%m%d_%H%M%S).log"

# Cattura output completo su logfile dedicato e terminale
exec > >(tee -a "$LOG_FILE") 2>&1

on_error() {
    local exit_code=$?
    local err_msg="Procedura ${PROCEDURE_NAME} fallita alla riga $1 (exit code: $exit_code)"
    if ! is_root_procedure; then
        err_msg="Sub-procedura ${PROCEDURE_NAME} (richiamata da ${HOMELAB_PARENT_PROCEDURE}) fallita alla riga $1 (exit code: $exit_code)"
    fi
    echo "❌ $err_msg"

    # 1. Alert Telegram immediato
    send_telegram "❌ <b>ERRORE CRITICO HOMELAB</b>%0A${err_msg}%0AConsulta l'email per il log completo dell'errore." "Homelab Alert"

    # 2. Email HTML con allegato log completo
    local table="<tr><td><b>Procedura:</b></td><td>${PROCEDURE_NAME}</td></tr><tr><td><b>Parent:</b></td><td>${HOMELAB_PARENT_PROCEDURE}</td></tr><tr><td><b>Errore:</b></td><td>Riga $1 (Exit Code: $exit_code)</td></tr><tr><td><b>Log Allegato:</b></td><td>$(basename "$LOG_FILE")</td></tr>"
    local html
    html="$(build_html_email_template "🚨" "Errore ${PROCEDURE_NAME}" "Homelab Power Automation" "ERRORE" "#ef4444" "$table")"
    send_summary_email "$DEFAULT_EMAIL_RECIPIENT" "🚨 [ALERT] Errore in ${PROCEDURE_NAME}" "$html" "$err_msg" "$LOG_FILE"
    exit "$exit_code"
}
trap 'on_error $LINENO' ERR

echo "🛑 Avvio sequenza: ${PROCEDURE_NAME}..."
echo "➡️  Modalità Eco: TrueNAS rimarrà l'unico host attivo per Servarr e storage."
echo "📄 Log di sessione: $LOG_FILE"
echo ""

# Ping informativo iniziale (SOLO Telegram, NESSUNA mail di start)
if is_root_procedure; then
    send_telegram "🛑 <b>Avvio ${PROCEDURE_NAME}</b>%0ATransizione a modalità Eco TrueNAS-only: spegnimento K8s e Proxmox VE..." "Homelab Power"
fi

# Esecuzione Playbook Ansible
ansible-playbook -i ansible/inventory.ini ansible/playbooks/infrastructure/shutdown_to_truenas_only.yml

# Notifica Finale di Successo (SOLO se Root, altrimenti delegata al Parent)
if is_root_procedure; then
    send_telegram "🎉 <b>${PROCEDURE_NAME} Completato!</b>%0AK8s e Proxmox VE disattivati. TrueNAS standalone operativo in modalità Eco." "Homelab Power"
    stop_table="<tr><td><b>Stato:</b></td><td>SUCCESSO (Modalità Eco Attiva)</td></tr><tr><td><b>Kubernetes:</b></td><td>OFFLINE (Cluster spento in sicurezza)</td></tr><tr><td><b>Hypervisors:</b></td><td>OFFLINE (pve1, pve2, pve3 spenti)</td></tr><tr><td><b>Storage TrueNAS:</b></td><td>ONLINE (10.10.20.50, Servarr, ZFS)</td></tr>"
    stop_html="$(build_html_email_template "🎉" "Completato: ${PROCEDURE_NAME}" "Homelab Power Automation" "SUCCESSO" "#10b981" "$stop_table")"
    send_summary_email "$DEFAULT_EMAIL_RECIPIENT" "✅ [SUCCESS] ${PROCEDURE_NAME}" "$stop_html" "${PROCEDURE_NAME} completato con successo"
    complete_procedure_scope
else
    echo "ℹ️ [NESTED] Sotto-procedura ${PROCEDURE_NAME} completata con successo. Segnalazione finale delegata a ${HOMELAB_PARENT_PROCEDURE}."
fi

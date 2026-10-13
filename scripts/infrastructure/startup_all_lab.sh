#!/usr/bin/env bash
# Avvio completo da freddo del rack: TrueNAS -> PVE1/2/3 -> Talos K8s
set -Eeuo pipefail
# ==============================================================================
# startup_all_lab.sh
# ==============================================================================
# Procedura globale di accensione da freddo dell'intero Homelab:
# 1. WoL Idempotente per TrueNAS SCALE Bare Metal (10.10.20.50)
# 2. Gate TrueNAS: SSH, WebUI, integrità pool ZFS (stripe & oliraid) e servizi
# 3. Innesco automatico sequenza: WoL PVE1/2/3, Talos K8s, Sync Barrier, Uncordon, CNPG
# 4. Notifiche Start & Stop (Telegram + Email HTML)
# 5. Notifiche intermediari checkpoint nodi (Solo Telegram)
# 6. Trap di Errore: notifica immediata Telegram + Email con allegato log completo
# ==============================================================================

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"
cd "$ROOT_DIR" || exit 1

source "$SCRIPT_DIR/utils.sh"

PROCEDURE_NAME="startup_all_lab"
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

echo "🚀 Avvio sequenza: ${PROCEDURE_NAME}..."
echo "➡️  Transizione: Da Rack Spento a Full Homelab Operativo (TrueNAS + PVE + K8s)."
echo "📄 Log di sessione: $LOG_FILE"
echo ""

# Notifica Start (Telegram + Email)
send_telegram "🚀 <b>Avvio ${PROCEDURE_NAME}</b>%0AAvvio globale Homelab da freddo: TrueNAS -> PVE1/2/3 -> Talos Cluster..." "Homelab Power"
start_table="<tr><td><b>Procedura:</b></td><td>${PROCEDURE_NAME}</td></tr><tr><td><b>Ambito:</b></td><td>Intero Rack (Storage Bare Metal + Compute Hypervisors + K8s)</td></tr><tr><td><b>Sequenza:</b></td><td>WoL TrueNAS &rarr; ZFS Health &rarr; WoL PVE &rarr; Sync Barrier K8s</td></tr>"
start_html="$(build_html_email_template "🚀" "Avvio ${PROCEDURE_NAME}" "Homelab Power Automation" "IN CORSO" "#3b82f6" "$start_table")"
send_summary_email "$DEFAULT_EMAIL_RECIPIENT" "🚀 [START] ${PROCEDURE_NAME}" "$start_html" "Avvio ${PROCEDURE_NAME}"

# Esecuzione Playbook Ansible
ansible-playbook -i ansible/inventory.ini ansible/playbooks/infrastructure/startup_all_lab.yml

# Notifica Stop (Telegram + Email)
send_telegram "🎉 <b>${PROCEDURE_NAME} Completato!</b>%0AIntero Homelab pienamente operativo: TrueNAS, Proxmox VE e Kubernetes online al 100%." "Homelab Power"
stop_table="<tr><td><b>Stato:</b></td><td>SUCCESSO (100% Gates Superati)</td></tr><tr><td><b>Storage TrueNAS:</b></td><td>ONLINE (Pool stripe & oliraid sani)</td></tr><tr><td><b>Hypervisor PVE:</b></td><td>ONLINE (pve1, pve2, pve3)</td></tr><tr><td><b>Talos Cluster:</b></td><td>READY & UNCORDONATI (cp-01, cp-02, cp-03)</td></tr><tr><td><b>Ingress VIP:</b></td><td>ONLINE (https://10.10.20.56)</td></tr>"
stop_html="$(build_html_email_template "🎉" "Completato: ${PROCEDURE_NAME}" "Homelab Power Automation" "SUCCESSO" "#10b981" "$stop_table")"
send_summary_email "$DEFAULT_EMAIL_RECIPIENT" "✅ [SUCCESS] ${PROCEDURE_NAME}" "$stop_html" "${PROCEDURE_NAME} completato con successo"

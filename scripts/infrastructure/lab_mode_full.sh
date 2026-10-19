#!/usr/bin/env bash
# Homelab a pieno regime: TrueNAS, Proxmox VE e K8s tutti attivi
set -Eeuo pipefail
# ==============================================================================
# lab_mode_full.sh
# ==============================================================================
# Convergenza dichiarativa e idempotente allo stato FULL HOMELAB:
# 1. Hard Gate Storage: TrueNAS Bare Metal ONLINE (ZFS stripe & oliraid sani, export NFS)
# 2. Gate Compute: WoL PVE1/2/3, auto-avvio VM Talos se spente, Sync Barrier & Uncordon
# 3. Notifiche conformi a [[hierarchical-automation-alerting-pattern]]:
#    - Avvio: solo ping Telegram (Zero start emails)
#    - Successo: report unificato Telegram + Email HTML
#    - Errore: fail-fast immediato con log completo allegato
# ==============================================================================

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"
cd "$ROOT_DIR" || exit 1

source "$SCRIPT_DIR/procedure_scope.sh"
source "$SCRIPT_DIR/utils.sh"

PROCEDURE_NAME="lab_mode_full"
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

echo "🚀 Avvio convergenza: ${PROCEDURE_NAME}..."
echo "➡️  Stato Target: FULL LAB (TrueNAS + Proxmox VE + Kubernetes Talos ONLINE)"
echo "📄 Log di sessione: $LOG_FILE"
echo ""

if is_root_procedure; then
    send_telegram "🚀 <b>Avvio ${PROCEDURE_NAME}</b>%0AConvergenza verso Full Homelab: TrueNAS -> PVE1/2/3 -> Talos Cluster..." "Homelab Mode"
fi

# ------------------------------------------------------------------------------
# FASE 1: HARD GATE STORAGE TRUENAS BARE METAL
# ------------------------------------------------------------------------------
echo "▶️  [Fase 1/2] Esecuzione: ensure_storage_on..."
ansible-playbook -i ansible/inventory.ini ansible/playbooks/infrastructure/ensure_storage_on.yml

# ------------------------------------------------------------------------------
# FASE 2: GATELAYER COMPUTE (PROXMOX VE + TALOS KUBERNETES)
# ------------------------------------------------------------------------------
echo "▶️  [Fase 2/2] Esecuzione: ensure_compute_on..."
ansible-playbook -i ansible/inventory.ini ansible/playbooks/infrastructure/ensure_compute_on.yml

# ------------------------------------------------------------------------------
# NOTIFICA FINALE RIASSUNTIVA DI SUCCESSO
# ------------------------------------------------------------------------------
if is_root_procedure; then
    send_telegram "🎉 <b>${PROCEDURE_NAME} Completato!</b>%0AIntero Homelab pienamente operativo: TrueNAS, Proxmox VE e Kubernetes online al 100%." "Homelab Mode"
    stop_table="<tr><td><b>Modalità:</b></td><td>FULL LAB (100% Gates Superati)</td></tr><tr><td><b>Storage TrueNAS:</b></td><td>ONLINE (Pool stripe & oliraid sani)</td></tr><tr><td><b>Hypervisor PVE:</b></td><td>ONLINE (pve1, pve2, pve3)</td></tr><tr><td><b>Talos Cluster:</b></td><td>READY & UNCORDONATI (cp-01, cp-02, cp-03)</td></tr><tr><td><b>Ingress VIP:</b></td><td>ONLINE (https://10.10.20.56)</td></tr>"
    stop_html="$(build_html_email_template "🎉" "Completato: ${PROCEDURE_NAME}" "Homelab Mode Orchestration" "SUCCESSO" "#10b981" "$stop_table")"
    send_summary_email "$DEFAULT_EMAIL_RECIPIENT" "✅ [SUCCESS] ${PROCEDURE_NAME}" "$stop_html" "${PROCEDURE_NAME} completato con successo"
    complete_procedure_scope
else
    echo "ℹ️ [NESTED] Procedura ${PROCEDURE_NAME} completata. Segnalazione finale delegata a ${HOMELAB_PARENT_PROCEDURE}."
fi

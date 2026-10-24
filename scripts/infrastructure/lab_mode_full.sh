#!/usr/bin/env bash
# Homelab a pieno regime: TrueNAS (con failback da OrbStack), Proxmox VE e K8s tutti attivi
set -Eeuo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"
cd "$ROOT_DIR" || exit 1

source "$SCRIPT_DIR/procedure_scope.sh"
source "$SCRIPT_DIR/utils.sh"
source "$SCRIPT_DIR/orbstack_failover.sh"

PROCEDURE_NAME="lab_mode_full"
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

echo "🚀 Avvio convergenza: ${PROCEDURE_NAME}..."
echo "➡️  Stato Target: FULL LAB (TrueNAS + Failback da OrbStack + Proxmox VE + Kubernetes Talos ONLINE)"
echo "📄 Log di sessione: $LOG_FILE"
echo ""

if is_root_procedure; then
    send_telegram "🚀 <b>Avvio ${PROCEDURE_NAME}</b>%0AConvergenza verso Full Homelab: TrueNAS -> Failback OrbStack -> PVE1/2/3 -> Talos Cluster..." "Homelab Mode"
fi

# FASE 1: HARD GATE STORAGE TRUENAS BARE METAL
echo "▶️  [Fase 1/3] Esecuzione: ensure_storage_on..."
ansible-playbook -i ansible/inventory.ini ansible/playbooks/infrastructure/ensure_storage_on.yml

# FASE 2: FAILBACK STATO HERMES, SERVIZI AI/MCP E DNS DA MAC STUDIO (ORBSTACK) A TRUENAS (10.10.20.50)
echo "▶️  [Fase 2/3] Esecuzione: deactivate_orbstack_failover_to_truenas (target full)..."
deactivate_orbstack_failover_to_truenas "full"

# FASE 3: GATELAYER COMPUTE (PROXMOX VE + TALOS KUBERNETES) E SWITCH DNS FULL
echo "▶️  [Fase 3/3] Esecuzione: ensure_compute_on..."
ansible-playbook -i ansible/inventory.ini ansible/playbooks/infrastructure/ensure_compute_on.yml

echo "🌐 [Fase 3/3] Commutazione DNS Unbound -> FULL (K8s Ingress 10.10.20.56)..."
python3 "${ROOT_DIR}/scripts/network/switch_failover_dns.py" --target full
set_truenas_home_internal_backend "full"

# NOTIFICA FINALE RIASSUNTIVA DI SUCCESSO
if is_root_procedure; then
    send_telegram "🎉 <b>${PROCEDURE_NAME} Completato!</b>%0AIntero Homelab pienamente operativo: TrueNAS, Proxmox VE e Kubernetes online al 100%." "Homelab Mode"
    stop_table="<tr><td><b>Modalità:</b></td><td>FULL LAB (100% Gates Superati)</td></tr><tr><td><b>Storage TrueNAS:</b></td><td>ONLINE (Pool stripe & oliraid sani, DNS -> 10.10.20.50)</td></tr><tr><td><b>Failover OrbStack:</b></td><td>STANDBY (Stato Hermes sincronizzato su TrueNAS e container locali spenti)</td></tr><tr><td><b>Hypervisor PVE:</b></td><td>ONLINE (pve1, pve2, pve3)</td></tr><tr><td><b>Talos Cluster:</b></td><td>READY & UNCORDONATI (cp-01, cp-02, cp-03)</td></tr><tr><td><b>Ingress VIP:</b></td><td>ONLINE (https://10.10.20.56)</td></tr>"
    stop_html="$(build_html_email_template "🎉" "Completato: ${PROCEDURE_NAME}" "Homelab Mode Orchestration" "SUCCESSO" "#10b981" "$stop_table")"
    send_summary_email "$DEFAULT_EMAIL_RECIPIENT" "✅ [SUCCESS] ${PROCEDURE_NAME}" "$stop_html" "${PROCEDURE_NAME} completato con successo"
    complete_procedure_scope
else
    echo "ℹ️ [NESTED] Procedura ${PROCEDURE_NAME} completata. Segnalazione finale delegata a ${HOMELAB_PARENT_PROCEDURE}."
fi

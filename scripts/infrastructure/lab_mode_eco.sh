#!/usr/bin/env bash
# Homelab a risparmio energetico: solo TrueNAS attivo (con failback da OrbStack), PVE e K8s spenti
set -Eeuo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"
cd "$ROOT_DIR" || exit 1

source "$SCRIPT_DIR/procedure_scope.sh"
source "$SCRIPT_DIR/utils.sh"
source "$SCRIPT_DIR/orbstack_failover.sh"

PROCEDURE_NAME="lab_mode_eco"
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
echo "➡️  Stato Target: ECO LAB (TrueNAS ONLINE + Failback da OrbStack, Proxmox VE e Kubernetes OFFLINE)"
echo "📄 Log di sessione: $LOG_FILE"
echo ""

if is_root_procedure; then
    send_telegram "🚀 <b>Avvio ${PROCEDURE_NAME}</b>%0AConvergenza verso modalità Eco: TrueNAS ONLINE, Failback da OrbStack, spegnimento K8s e Proxmox VE..." "Homelab Mode"
fi

# FASE 1: GARANTISCE STORAGE TRUENAS BARE METAL ONLINE
echo "▶️  [Fase 1/3] Esecuzione: ensure_storage_on..."
ansible-playbook -i ansible/inventory.ini ansible/playbooks/infrastructure/ensure_storage_on.yml

# FASE 2: FAILBACK STATO HERMES, SERVIZI AI/MCP E DNS DA MAC STUDIO (ORBSTACK) A TRUENAS (10.10.20.50)
echo "▶️  [Fase 2/3] Esecuzione: deactivate_orbstack_failover_to_truenas (target eco)..."
set_truenas_home_internal_backend "eco"
deactivate_orbstack_failover_to_truenas "eco"

# FASE 3: GARANTISCE COMPUTE LAYER OFFLINE (K8S + PVE)
echo "▶️  [Fase 3/3] Esecuzione: ensure_compute_off..."
ansible-playbook -i ansible/inventory.ini ansible/playbooks/infrastructure/ensure_compute_off.yml

# NOTIFICA FINALE RIASSUNTIVA DI SUCCESSO
if is_root_procedure; then
    send_telegram "🎉 <b>${PROCEDURE_NAME} Completato!</b>%0AHomelab a regime di risparmio energetico: TrueNAS attivo (DNS -> 10.10.20.50, OrbStack disattivato), K8s e Proxmox disattivati." "Homelab Mode"
    stop_table="<tr><td><b>Modalità:</b></td><td>ECO LAB (Risparmio Energetico)</td></tr><tr><td><b>Storage TrueNAS:</b></td><td>ONLINE (10.10.20.50, Servarr, ZFS, MCP Fleet, Hermes, LiteLLM, Dozzle)</td></tr><tr><td><b>Failover OrbStack:</b></td><td>STANDBY (Stato Hermes sincronizzato su TrueNAS e container locali spenti)</td></tr><tr><td><b>Hypervisor PVE:</b></td><td>OFFLINE (pve1, pve2, pve3 spenti)</td></tr><tr><td><b>Kubernetes:</b></td><td>OFFLINE (Cluster Talos disattivato)</td></tr>"
    stop_html="$(build_html_email_template "🎉" "Completato: ${PROCEDURE_NAME}" "Homelab Mode Orchestration" "SUCCESSO" "#10b981" "$stop_table")"
    send_summary_email "$DEFAULT_EMAIL_RECIPIENT" "✅ [SUCCESS] ${PROCEDURE_NAME}" "$stop_html" "${PROCEDURE_NAME} completato con successo"
    complete_procedure_scope
else
    echo "ℹ️ [NESTED] Procedura ${PROCEDURE_NAME} completata. Segnalazione finale delegata a ${HOMELAB_PARENT_PROCEDURE}."
fi

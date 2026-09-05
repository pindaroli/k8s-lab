#!/usr/bin/env bash
# Audit SMART Dischi Fisici Cluster Proxmox
# =============================================================================
# Script: check_proxmox_smart.sh
# Categoria: Infrastructure
# Descrizione: Wrapper operativo per l'audit dello stato di salute SMART dei
#              soli dischi fisici del cluster Proxmox VE.
# SSoT: rete.json & ansible/inventory.ini
# =============================================================================

set -euo pipefail

# Determinazione percorsi relativi al repository
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/../.." && pwd)"
INVENTORY="${ROOT_DIR}/ansible/inventory.ini"
PLAYBOOK="${ROOT_DIR}/ansible/playbooks/infrastructure/proxmox_smart_audit.yml"
REPORTS_DIR="${ROOT_DIR}/ansible/reports"

# Colori per formattazione console (ANSI-C quoting)
RED=$'\033[0;31m'
GREEN=$'\033[0;32m'
YELLOW=$'\033[1;33m'
CYAN=$'\033[0;36m'
BOLD=$'\033[1m'
RESET=$'\033[0m'

# Funzione di Help
show_help() {
  cat << EOF
${BOLD}USO:${RESET}
  $(basename "$0") [OPZIONI]

${BOLD}DESCRIZIONE:${RESET}
  Esegue l'audit SMART hardware su tutti i nodi del cluster Proxmox censiti
  nell'inventory. Rileva automaticamente i nodi dal cluster, isola tutti e soli
  i dischi fisici (escludendo ZFS zvol, LVM e volumi virtuali) e produce un
  report sinottico e dettagliato.

${BOLD}OPZIONI:${RESET}
  -c, --check, --syntax-check    Esegue solo il syntax-check del playbook senza connettersi ai nodi
  -l, --limit <HOST/GRUPPO>      Limita l'esecuzione a specifici nodi (es: -l 10.10.10.11)
  -r, --report                   Visualizza l'ultimo report Markdown generato
  -v, --verbose                  Abilita l'output verbose di Ansible (-v)
  -h, --help                     Mostra questo messaggio di aiuto ed esce

${BOLD}ESEMPI:${RESET}
  $(basename "$0")                      # Audit completo su tutti i nodi Proxmox
  $(basename "$0") -c                   # Verifica sintassi del playbook
  $(basename "$0") -l 10.10.10.11       # Audit solo su PVE1
  $(basename "$0") -r                   # Leggi l'ultimo report generato
EOF
  exit 0
}

# Funzione per visualizzare l'ultimo report generato
show_latest_report() {
  if [ ! -d "${REPORTS_DIR}" ]; then
    echo -e "${RED}❌ Nessun report trovato in ${REPORTS_DIR}${RESET}"
    exit 1
  fi

  local latest_file
  latest_file=$(find "${REPORTS_DIR}" -name "proxmox_smart_report_*.md" -type f | sort -r | head -n 1)

  if [ -z "${latest_file}" ]; then
    echo -e "${YELLOW}⚠️ Nessun report di audit SMART trovato in ${REPORTS_DIR}.${RESET}"
    exit 0
  fi

  echo -e "${CYAN}📄 Visualizzazione ultimo report:${RESET} ${BOLD}${latest_file}${RESET}\n"
  cat "${latest_file}"
  exit 0
}

# Parsing argomenti CLI
EXTRA_ARGS=()
SHOW_REPORT=false

while [[ $# -gt 0 ]]; do
  case "$1" in
    -h|--help)
      show_help
      ;;
    -c|--check|--syntax-check)
      EXTRA_ARGS+=("--syntax-check")
      shift
      ;;
    -l|--limit)
      if [[ -z "${2:-}" ]]; then
        echo -e "${RED}Errore: l'opzione $1 richiede un argomento (es: -l 10.10.10.11).${RESET}"
        exit 1
      fi
      EXTRA_ARGS+=("-l" "$2")
      shift 2
      ;;
    -v|--verbose)
      EXTRA_ARGS+=("-v")
      shift
      ;;
    -r|--report)
      SHOW_REPORT=true
      shift
      ;;
    *)
      echo -e "${RED}Opzione non riconosciuta: $1${RESET}"
      echo -e "Usa ${BOLD}$(basename "$0") --help${RESET} per la sintassi."
      exit 1
      ;;
  esac
done

if [ "$SHOW_REPORT" = true ]; then
  show_latest_report
fi

# Pre-flight checks
if [ ! -f "${INVENTORY}" ]; then
  echo -e "${RED}❌ Errore: File inventory non trovato: ${INVENTORY}${RESET}"
  exit 1
fi

if [ ! -f "${PLAYBOOK}" ]; then
  echo -e "${RED}❌ Errore: Playbook non trovato: ${PLAYBOOK}${RESET}"
  exit 1
fi

# Ricerca binario ansible-playbook
ANSIBLE_BIN=""
if command -v ansible-playbook >/dev/null 2>&1; then
  ANSIBLE_BIN="$(command -v ansible-playbook)"
elif [ -x "/opt/homebrew/bin/ansible-playbook" ]; then
  ANSIBLE_BIN="/opt/homebrew/bin/ansible-playbook"
else
  echo -e "${RED}❌ Errore: ansible-playbook non trovato nel PATH o in Homebrew.${RESET}"
  exit 1
fi

# Evita problemi di permessi directory temporanea locale in sandbox macOS
export ANSIBLE_LOCAL_TEMP="${TMPDIR:-/tmp}/ansible"

echo -e "${CYAN}${BOLD}==============================================================================${RESET}"
echo -e "${CYAN}${BOLD}🔍 PROXMOX CLUSTER PHYSICAL DISKS SMART AUDIT${RESET}"
echo -e "${CYAN}${BOLD}==============================================================================${RESET}"
echo -e "📂 Inventory: ${BOLD}${INVENTORY}${RESET}"
echo -e "📜 Playbook:  ${BOLD}${PLAYBOOK}${RESET}"
echo -e "🚀 Ansible:   ${BOLD}${ANSIBLE_BIN}${RESET}"
if [ ${#EXTRA_ARGS[@]} -gt 0 ]; then
  echo -e "⚙️  Opzioni:   ${YELLOW}${EXTRA_ARGS[*]}${RESET}"
fi
echo -e "------------------------------------------------------------------------------"

# Esecuzione Ansible Playbook (gestione set -u per array vuoto su bash macOS)
if [ ${#EXTRA_ARGS[@]} -gt 0 ]; then
  EXEC_CMD=("${ANSIBLE_BIN}" -i "${INVENTORY}" "${PLAYBOOK}" "${EXTRA_ARGS[@]}")
else
  EXEC_CMD=("${ANSIBLE_BIN}" -i "${INVENTORY}" "${PLAYBOOK}")
fi

if "${EXEC_CMD[@]}"; then
  echo -e "------------------------------------------------------------------------------"
  echo -e "${GREEN}✅ Audit SMART completato con successo.${RESET}"

  # Trova e segnala l'ultimo report generato
  if [ -d "${REPORTS_DIR}" ]; then
    latest_report=$(find "${REPORTS_DIR}" -name "proxmox_smart_report_*.md" -type f | sort -r | head -n 1)
    if [ -n "${latest_report}" ]; then
      echo -e "📄 Report salvato in: ${BOLD}${latest_report}${RESET}"
      echo -e "💡 Suggerimento: visualizzalo con ${BOLD}$(basename "$0") --report${RESET}"
    fi
  fi
  echo -e "${CYAN}${BOLD}==============================================================================${RESET}"
else
  echo -e "------------------------------------------------------------------------------"
  echo -e "${RED}❌ Si sono verificati errori durante l'esecuzione dell'audit SMART.${RESET}"
  echo -e "${CYAN}${BOLD}==============================================================================${RESET}"
  exit 1
fi

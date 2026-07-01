#!/usr/bin/env bash
# Test di connettività internet e routing locale
# =============================================================================
# Questo script analizza lo stato della rete del Mac Studio quando scollegato
# dall'hotspot per capire perché la rete locale non fornisce connettività internet.
# =============================================================================

set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
RETE_JSON="${RETE_JSON_PATH}"

# Estrai gli IP dinamicamente da rete.json
OPNSENSE_OOB_IP=$(python3 -c "import json; print(next(n for n in json.load(open('${RETE_JSON}'))['nodi'] if n['id']=='opnsense')['management_ip'])")
OPNSENSE_TRANSIT_DNS=$(python3 -c "import json; print(next(n for n in json.load(open('${RETE_JSON}'))['nodi'] if n['id']=='switch10g')['dns_server'])")

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
BOLD='\033[1m'
RESET='\033[0m'

echo -e "${BOLD}${CYAN}"
echo "============================================================"
echo "  DIAGNOSTICA CONNETTIVITÀ INTERNET & ROUTING"
echo "  Esegui questo script SENZA hotspot attivo"
echo "  $(date '+%Y-%m-%d %H:%M:%S')"
echo "============================================================"
echo -e "${RESET}"

# [1] VERIFICA INTERFACCE ATTIVE
echo -e "${BOLD}[1] Interfacce di rete attive su macOS${RESET}"
active_ifs=$(ifconfig -u | grep -E '^[a-z0-9]+:' | cut -d':' -f1)
for iface in ${active_ifs}; do
  ip=$(ifconfig "${iface}" 2>/dev/null | grep 'inet ' | awk '{print $2}')
  if [[ -n "${ip}" ]]; then
    echo -e "  Interface: ${BOLD}${iface}${RESET} → IP: ${GREEN}${ip}${RESET}"
  fi
done

echo ""

# [2] VERIFICA ROTTE DI DEFAULT
echo -e "${BOLD}[2] Rotte di default (Gateway)${RESET}"
default_route=$(netstat -rn | grep -E '^default' || true)
if [[ -n "${default_route}" ]]; then
  echo -e "  Rotte di default configurate:"
  echo "${default_route}" | while read -r line; do
    echo -e "    ${GREEN}${line}${RESET}"
  done
else
  echo -e "  ${RED}✗ NESSUNA ROTTA DI DEFAULT TROVATA!${RESET} Il Mac non sa come uscire su internet."
fi

echo ""

# [3] PING GATEWAY E RESOLVER LOCALI
echo -e "${BOLD}[3] Connettività verso nodi e gateway locali${RESET}"

check_ping() {
  local ip="$1"
  local desc="$2"
  if ping -c 2 -W 1 -q "${ip}" &>/dev/null; then
    echo -e "  ${GREEN}✓${RESET} ${ip} (${desc}) → ${GREEN}RAGGIUNGIBILE${RESET}"
    return 0
  else
    echo -e "  ${RED}✗${RESET} ${ip} (${desc}) → ${RED}NON RAGGIUNGIBILE${RESET}"
    return 1
  fi
}

check_ping "10.10.20.1" "Switch L3 (Gateway VLAN 20)"
check_ping "${OPNSENSE_TRANSIT_DNS}" "OPNsense Transit IP / DNS"
check_ping "${OPNSENSE_OOB_IP}" "OPNsense OOB IP (VLAN 99)"

echo ""

# [4] CONNETTIVITÀ INTERNET DIRETTA (IP)
echo -e "${BOLD}[4] Connettività Internet diretta (No DNS)${RESET}"
check_ping "8.8.8.8" "Google Public DNS"
check_ping "1.1.1.1" "Cloudflare Public DNS"

echo ""

# [5] RISOLUZIONE DNS (NOMI)
echo -e "${BOLD}[5] Risoluzione DNS dei nomi esterni${RESET}"

# Test via OPNsense Unbound (Transit DNS)
dns_local=$(dig @"${OPNSENSE_TRANSIT_DNS}" +short +time=2 google.com 2>/dev/null | head -1 || true)
if [[ -n "${dns_local}" ]]; then
  echo -e "  ${GREEN}✓${RESET} google.com via OPNsense Transit (${OPNSENSE_TRANSIT_DNS}) → ${GREEN}${dns_local}${RESET}"
else
  echo -e "  ${RED}✗${RESET} google.com via OPNsense Transit (${OPNSENSE_TRANSIT_DNS}) → ${RED}TIMEOUT/ERRORE${RESET}"
fi

# Test via DNS pubblico diretto
dns_public=$(dig @1.1.1.1 +short +time=2 google.com 2>/dev/null | head -1 || true)
if [[ -n "${dns_public}" ]]; then
  echo -e "  ${GREEN}✓${RESET} google.com via Cloudflare (1.1.1.1) → ${GREEN}${dns_public}${RESET}"
else
  echo -e "  ${RED}✗${RESET} google.com via Cloudflare (1.1.1.1) → ${RED}TIMEOUT/ERRORE${RESET}"
fi

echo ""

# [6] TRACEROUTE VERSO INTERNET
echo -e "${BOLD}[6] Tracciamento percorso (Traceroute) verso 8.8.8.8${RESET}"
echo "  Esecuzione traceroute (max 8 salti)..."
trace_out=$(traceroute -m 8 -q 1 -w 2 8.8.8.8 2>&1)
echo "${trace_out}" | while read -r line; do
  echo "    $line"
done

echo ""
echo -e "${BOLD}${CYAN}============================================================${RESET}"
echo "  Diagnostica completata."
echo -e "${BOLD}${CYAN}============================================================${RESET}"

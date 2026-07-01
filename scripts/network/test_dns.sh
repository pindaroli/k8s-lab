#!/usr/bin/env bash
# DNS Health Check per homelab (OPNsense Unbound)
# =============================================================================
# Resolver: OPNsense Unbound @ 10.10.20.254
# Fonte verità: rete.json
# =============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
RETE_JSON="${SCRIPT_DIR}/../../rete.json"

RESOLVER=$(python3 -c "import json; print(next(n for n in json.load(open('${RETE_JSON}'))['nodi'] if n['id']=='switch10g')['dns_server'])")
DOMAIN="pindaroli.org"
TRAEFIK_VIP="10.10.20.56"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
BOLD='\033[1m'
RESET='\033[0m'

pass=0
fail=0
warn=0

check() {
  local label="$1"
  local fqdn="$2"
  local expected="$3"

  result=$(dig @"${RESOLVER}" +short +time=3 "${fqdn}" 2>/dev/null | head -1)

  if [[ "${result}" == "${expected}" ]]; then
    echo -e "  ${GREEN}✓${RESET} ${fqdn} → ${result}"
    pass=$((pass + 1))
  elif [[ -z "${result}" ]]; then
    echo -e "  ${RED}✗${RESET} ${fqdn} → ${RED}NXDOMAIN/TIMEOUT${RESET} (atteso: ${expected})"
    fail=$((fail + 1))
  else
    echo -e "  ${YELLOW}~${RESET} ${fqdn} → ${YELLOW}${result}${RESET} (atteso: ${expected})"
    warn=$((warn + 1))
  fi
}

check_ptr() {
  local ip="$1"
  local expected_ptr="$2"

  result=$(dig @"${RESOLVER}" +short +time=3 -x "${ip}" 2>/dev/null | head -1)

  if [[ "${result}" == "${expected_ptr}." || "${result}" == "${expected_ptr}" ]]; then
    echo -e "  ${GREEN}✓${RESET} PTR ${ip} → ${result}"
    pass=$((pass + 1))
  elif [[ -z "${result}" ]]; then
    echo -e "  ${RED}✗${RESET} PTR ${ip} → ${RED}NXDOMAIN/TIMEOUT${RESET} (atteso: ${expected_ptr})"
    fail=$((fail + 1))
  else
    echo -e "  ${YELLOW}~${RESET} PTR ${ip} → ${YELLOW}${result}${RESET} (atteso: ${expected_ptr})"
    warn=$((warn + 1))
  fi
}

echo -e "${BOLD}${CYAN}"
echo "============================================================"
echo "  DNS Health Check — ${DOMAIN}"
echo "  Resolver: ${RESOLVER}"
echo "  $(date '+%Y-%m-%d %H:%M:%S')"
echo "============================================================"
echo -e "${RESET}"

# --- Servizi Traefik (puntano tutti al VIP 10.10.20.56) ---
echo -e "${BOLD}[1] Servizi Traefik VIP (atteso: ${TRAEFIK_VIP})${RESET}"
for svc in \
  auth traefik-dash radarr lidarr lidarr-classic \
  tdarr-internal prowlarr qbittorrent jellyfin jellyfin-classic \
  home minio nas n8n grafana ap kasmweb prefect tdarr \
  calibre-web firewall pve; do
  check "traefik" "${svc}.${DOMAIN}" "${TRAEFIK_VIP}"
done

echo ""

# --- Alias interni (-internal) ---
echo -e "${BOLD}[2] Alias interni${RESET}"
check "internal" "jellyfin-internal.${DOMAIN}" "${TRAEFIK_VIP}"
check "internal" "tdarr-internal.${DOMAIN}"    "${TRAEFIK_VIP}"

echo ""

# --- VIP Database & P2P ---
echo -e "${BOLD}[3] VIP Database & P2P${RESET}"
check "postgres"    "postgres.${DOMAIN}"     "10.10.20.57"
check "db"          "db.${DOMAIN}"           "10.10.20.57"
check "qbt-lb"      "qbittorrent-lb.${DOMAIN}" "10.10.20.60"

echo ""

# --- Nodi infrastruttura ---
echo -e "${BOLD}[4] Nodi Infrastruttura${RESET}"
check "pve1"     "pve1.${DOMAIN}"      "10.10.10.11"
check "pve2"     "pve2.${DOMAIN}"      "10.10.10.21"
check "pve3"     "pve3.${DOMAIN}"      "10.10.10.31"
check "truenas"  "truenas.${DOMAIN}"   "10.10.10.50"
check "s3"       "s3.${DOMAIN}"        "10.10.10.50"
check "nas-direct" "nas-direct.${DOMAIN}" "10.10.10.50"
check "backup"   "backup.${DOMAIN}"    "10.10.10.100"

echo ""

# --- PTR (Reverse DNS) ---
echo -e "${BOLD}[5] PTR (Reverse DNS)${RESET}"
check_ptr "10.10.20.56" "traefik-lb.${DOMAIN}"
check_ptr "10.10.20.57" "postgres-lb.${DOMAIN}"
check_ptr "10.10.20.60" "qbittorrent-lb.${DOMAIN}"

echo ""

# --- Connettività DNS esterno (via Unbound forwarding) ---
echo -e "${BOLD}[6] Connettività DNS Esterno (via Unbound)${RESET}"
ext_result=$(dig @"${RESOLVER}" +short +time=5 google.com 2>/dev/null | head -1)
if [[ -n "${ext_result}" ]]; then
  echo -e "  ${GREEN}✓${RESET} google.com → ${ext_result} (Unbound forwarding OK)"
  pass=$((pass + 1))
else
  echo -e "  ${YELLOW}~${RESET} google.com → ${YELLOW}NESSUNA RISPOSTA da ${RESOLVER}${RESET}"
  echo -e "    ${YELLOW}(Verifica: Unbound > Query Forwarding oppure modalità ricorsiva pura)${RESET}"
  warn=$((warn + 1))
fi

# Fallback diretto 1.1.1.1
ext_direct=$(dig @1.1.1.1 +short +time=3 google.com 2>/dev/null | head -1)
if [[ -n "${ext_direct}" ]]; then
  echo -e "  ${GREEN}✓${RESET} google.com via 1.1.1.1 → ${ext_direct} (internet OK)"
  pass=$((pass + 1))
else
  echo -e "  ${RED}✗${RESET} google.com via 1.1.1.1 → ${RED}NESSUNA RISPOSTA${RESET} (internet KO!)"
  fail=$((fail + 1))
fi

# --- Sommario ---
echo ""
echo -e "${BOLD}${CYAN}============================================================${RESET}"
total=$((pass + fail + warn))
echo -e "${BOLD}  Risultati: ${total} test — ${GREEN}${pass} OK${RESET}  ${YELLOW}${warn} WARN${RESET}  ${RED}${fail} FAIL${RESET}"
echo -e "${BOLD}${CYAN}============================================================${RESET}"

if [[ ${fail} -gt 0 ]]; then
  exit 1
fi
exit 0

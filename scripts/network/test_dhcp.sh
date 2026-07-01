#!/usr/bin/env bash
# DHCP Health Check per homelab (OPNsense Kea API)
# =============================================================================
# Server: OPNsense Kea DHCP @ https://192.168.2.254
# Fonte verità: rete.json + ansible/OPNsense.internal_root_apikey.txt
# =============================================================================
#
# Cosa testa:
#   [1] Kea API — Raggiungibilità API OPNsense
#   [2] Kea API — Subnet attive e configurazione
#   [3] Kea API — Reservation statiche configurate
#   [4] ARP/Ping — Verifica che gli host noti rispondano all'IP corretto
#   [5] ARP     — Verifica MAC address delle reservation critiche
#
# =============================================================================

set -euo pipefail

# --- Configurazione ---
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(dirname "${SCRIPT_DIR}")"
export APIKEY_FILE="${ROOT_DIR}/ansible/OPNsense.internal_root_apikey.txt"
RETE_JSON="${ROOT_DIR}/rete.json"

if [ -z "${OPNSENSE_URL:-}" ]; then
  OPNSENSE_IP=$(python3 -c "import json; print(next(n for n in json.load(open('${RETE_JSON}'))['nodi'] if n['id']=='opnsense')['management_ip'])")
  export OPNSENSE_URL="https://${OPNSENSE_IP}"
fi

# Leggi credenziali dal file
API_KEY=$(grep '^key=' "${APIKEY_FILE}" | cut -d'=' -f2-)
API_SECRET=$(grep '^secret=' "${APIKEY_FILE}" | cut -d'=' -f2-)

# --- Colori ---
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
BLUE='\033[0;34m'
BOLD='\033[1m'
RESET='\033[0m'

pass=0
fail=0
warn=0

# --- Helper: chiamata API OPNsense (Basic Auth, no TLS verify) ---
api_get() {
  local endpoint="$1"
  curl -4 -sk --max-time 10 \
    -u "${API_KEY}:${API_SECRET}" \
    "${OPNSENSE_URL}${endpoint}"
}

api_post() {
  local endpoint="$1"
  local body="${2:-{}}"
  curl -4 -sk --max-time 10 \
    -u "${API_KEY}:${API_SECRET}" \
    -X POST \
    -H 'Content-Type: application/json' \
    -d "${body}" \
    "${OPNSENSE_URL}${endpoint}"
}

ok()   { echo -e "  ${GREEN}✓${RESET} $*"; pass=$((pass + 1)); }
fail() { echo -e "  ${RED}✗${RESET} $*"; fail=$((fail + 1)); }
warn() { echo -e "  ${YELLOW}~${RESET} $*"; warn=$((warn + 1)); }
info() { echo -e "  ${BLUE}ℹ${RESET} $*"; }

# =============================================================================
echo -e "${BOLD}${CYAN}"
echo "============================================================"
echo "  DHCP Health Check — pindaroli.org"
echo "  Server: OPNsense Kea @ ${OPNSENSE_URL}"
echo "  $(date '+%Y-%m-%d %H:%M:%S')"
echo "============================================================"
echo -e "${RESET}"

# =============================================================================
# [1] RAGGIUNGIBILITÀ API OPNSENSE
# =============================================================================
echo -e "${BOLD}[1] Kea API — Raggiungibilità${RESET}"

status=0
api_resp=$(api_get "/api/kea/dhcpv4/searchSubnet" 2>/dev/null) || status=$?
if [[ $status -eq 0 ]] && echo "${api_resp}" | python3 -c "import sys,json; d=json.load(sys.stdin); sys.exit(0 if 'rows' in d else 1)" 2>/dev/null; then
  ok "OPNsense API raggiungibile (${OPNSENSE_URL})"
else
  fail "OPNsense API NON raggiungibile (Status curl: $status)"
  if [[ $status -ne 0 ]]; then
    info "Errore curl: il server potrebbe essere offline o le credenziali errate (Timeout/Connessione rifiutata)."
  else
    info "La risposta dell'API non è in formato JSON valido: ${api_resp:0:100}"
  fi
  exit 1
fi

# =============================================================================
# [2] SUBNET KEA ATTIVE
# =============================================================================
echo ""
echo -e "${BOLD}[2] Kea API — Subnet attive${RESET}"

status=0
subnets_json=$(api_get "/api/kea/dhcpv4/searchSubnet") || status=$?
if [[ $status -ne 0 ]]; then
  fail "Impossibile recuperare le subnet da Kea API (Status curl: $status)"
  exit 1
fi

subnet_count=$(echo "${subnets_json}" | python3 -c "import sys,json; d=json.load(sys.stdin); print(len(d.get('rows',[])))" 2>/dev/null || echo "0")

if [[ "${subnet_count}" -gt 0 ]]; then
  ok "${subnet_count} subnet Kea trovata/e"
  echo "${subnets_json}" | python3 -c "
import sys, json
d = json.load(sys.stdin)
for s in d.get('rows', []):
    print(f\"    {'✓':>2} Subnet: {s.get('subnet','?'):<20}  Pool: {s.get('pool','N/A'):<25}  IF: {s.get('interface','?')}\")
"
else
  fail "Nessuna subnet Kea trovata"
fi

# Verifica subnet VLAN 20 (10.10.20.0/24)
vlan20_present=$(echo "${subnets_json}" | python3 -c "
import sys, json
d = json.load(sys.stdin)
found = any('10.10.20' in s.get('subnet','') for s in d.get('rows',[]))
print('yes' if found else 'no')
" 2>/dev/null || echo "no")

if [[ "${vlan20_present}" == "yes" ]]; then
  ok "Subnet VLAN 20 (10.10.20.0/24) presente"
else
  fail "Subnet VLAN 20 (10.10.20.0/24) MANCANTE"
fi

# =============================================================================
# [3] RESERVATION STATICHE (Kea API)
# =============================================================================
echo ""
echo -e "${BOLD}[3] Kea API — Reservation Statiche${RESET}"

status=0
reservations_json=$(api_get "/api/kea/dhcpv4/searchReservation") || status=$?
if [[ $status -ne 0 ]]; then
  fail "Impossibile recuperare le reservation da Kea API (Status curl: $status)"
  exit 1
fi

res_count=$(echo "${reservations_json}" | python3 -c "import sys,json; d=json.load(sys.stdin); print(len(d.get('rows',[])))" 2>/dev/null || echo "0")

if [[ "${res_count}" -gt 0 ]]; then
  ok "${res_count} reservation statiche configurate in Kea"
  echo "${reservations_json}" | python3 -c "
import sys, json
d = json.load(sys.stdin)
rows = sorted(d.get('rows', []), key=lambda x: x.get('ip_address',''))
for r in rows:
    hostname = r.get('hostname') or r.get('description') or '(no hostname)'
    ip       = r.get('ip_address','?')
    mac      = r.get('hw_address','?')
    print(f\"    {'':>2} {hostname:<25} {ip:<16} {mac}\")
"
else
  warn "Nessuna reservation statica trovata in Kea (o API non supportata)"
fi

# Verifica che le reservation critiche (da rete.json) siano presenti
echo ""
echo -e "  ${BOLD}Verifica reservation critiche da rete.json:${RESET}"

python3 - <<'EOF'
import json, sys

EXPECTED = [
    # (hostname, ip, mac)
    ("talos-cp-01", "10.10.20.141", "bc:24:11:81:6a:19"),
    ("talos-cp-02", "10.10.20.142", "bc:24:11:77:40:fc"),
    ("talos-cp-03", "10.10.20.143", "bc:24:11:0b:e0:61"),
    ("mac-studio",   "10.10.20.100", "a4:fc:14:10:5b:80"),
    ("ap11000",      "10.10.20.103", "80:af:ca:c0:2e:5a"),
    ("printer",      "10.10.20.127", "d8:b3:2f:1e:0f:1c"),
    ("ipad",         "10.10.20.205", "4e:55:65:8b:8d:e6"),
]

try:
    import urllib.request, ssl, base64, os

    url     = os.environ["OPNSENSE_URL"]
    key     = open(os.environ["APIKEY_FILE"]).read()
    api_key    = next(l.split("=",1)[1].strip() for l in key.splitlines() if l.startswith("key="))
    api_secret = next(l.split("=",1)[1].strip() for l in key.splitlines() if l.startswith("secret="))

    auth = "Basic " + base64.b64encode(f"{api_key}:{api_secret}".encode()).decode()
    ctx  = ssl.create_default_context(); ctx.check_hostname = False; ctx.verify_mode = ssl.CERT_NONE

    req  = urllib.request.Request(f"{url}/api/kea/dhcpv4/searchReservation", headers={"Authorization": auth})
    with urllib.request.urlopen(req, context=ctx, timeout=5) as resp:
        data = json.load(resp)

    rows = data.get("rows", [])
    reserved_ips  = {r.get("ip_address","").lower() for r in rows}
    reserved_macs = {r.get("hw_address","").lower() for r in rows}

    ok_count = fail_count = warn_count = 0
    for hostname, ip, mac in EXPECTED:
        ip_found  = ip.lower() in reserved_ips if ip  else True
        mac_found = mac.lower() in reserved_macs if mac else True

        if ip_found and mac_found:
            print(f"    \033[0;32m✓\033[0m {hostname:<20} {ip:<16} {mac or '(skip)'}")
            ok_count += 1
        elif ip_found and not mac_found:
            print(f"    \033[1;33m~\033[0m {hostname:<20} {ip:<16} MAC {mac} NON trovato")
            warn_count += 1
        else:
            print(f"    \033[0;31m✗\033[0m {hostname:<20} {ip:<16} RESERVATION MANCANTE")
            fail_count += 1

    print(f"\n  Risultato: {ok_count} OK  {warn_count} WARN  {fail_count} FAIL")

except Exception as e:
    print(f"    \033[1;33m~\033[0m Impossibile interrogare Kea API per verifica: {e}")
EOF

# =============================================================================
# [4] PING — Verifica risposta host con reservation statica
# =============================================================================
echo ""
echo -e "${BOLD}[4] Ping — Verifica raggiungibilità host noti${RESET}"

HOSTS="talos-cp-01:10.10.20.141 talos-cp-02:10.10.20.142 talos-cp-03:10.10.20.143 mac-studio:10.10.20.100 ap11000:10.10.20.103 jellyfin-srv:10.10.20.32 pve1:10.10.10.11 pve3:10.10.10.31 truenas:10.10.10.50"

for item in ${HOSTS}; do
  hostname="${item%%:*}"
  ip="${item#*:}"
  if ping -c 1 -W 1 -q "${ip}" &>/dev/null; then
    ok "${hostname} (${ip}) risponde al ping"
  else
    warn "${hostname} (${ip}) NON risponde — potrebbe essere spento o in VLAN diversa"
  fi
done

# =============================================================================
# [5] ARP — Verifica MAC address reservation critiche
# =============================================================================
echo ""
echo -e "${BOLD}[5] ARP — Verifica MAC address${RESET}"

# Aggiorna la tabella ARP pingSweep leggero
for ip in 10.10.20.141 10.10.20.142 10.10.20.143 10.10.20.100 10.10.20.103; do
  ping -c 1 -W 1 -q "${ip}" &>/dev/null || true
done

MACS_CHECK="10.10.20.141:bc:24:11:81:6a:19:talos-cp-01 10.10.20.142:bc:24:11:77:40:fc:talos-cp-02 10.10.20.143:bc:24:11:0b:e0:61:talos-cp-03 10.10.20.100:a4:fc:14:10:5b:80:mac-studio 10.10.20.103:80:af:ca:c0:2e:5a:ap11000"

for item in ${MACS_CHECK}; do
  ip=$(echo "${item}" | cut -d':' -f1)
  expected_mac=$(echo "${item}" | cut -d':' -f2-7)
  label=$(echo "${item}" | cut -d':' -f8)

  # macOS: arp -n <ip>
  arp_output=$(arp -n "${ip}" 2>/dev/null || echo "")
  actual_mac=$(echo "${arp_output}" | grep -oE '([0-9a-f]{1,2}:){5}[0-9a-f]{1,2}' | head -1 | tr '[:upper:]' '[:lower:]' || echo "")

  if [[ -z "${actual_mac}" ]]; then
    warn "${label} (${ip}) — MAC non in tabella ARP (host offline?)"
  elif [[ "${actual_mac}" == "${expected_mac}" ]]; then
    ok "${label} (${ip}) — MAC ${actual_mac} ✓"
  else
    fail "${label} (${ip}) — MAC atteso ${expected_mac}, trovato ${YELLOW}${actual_mac}${RESET} ← MISMATCH!"
  fi
done

# =============================================================================
# [6] LEASE ATTIVI (via Kea API)
# =============================================================================
echo ""
echo -e "${BOLD}[6] Kea — Lease DHCP attivi${RESET}"

leases_json=$(api_get "/api/kea/leases4/search?limit=200" 2>/dev/null) || leases_json='{}'
lease_count=$(echo "${leases_json}" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('total', len(d.get('rows',[]))))" 2>/dev/null || echo "?")

if [[ "${lease_count}" != "?" && "${lease_count}" -gt 0 ]]; then
  ok "${lease_count} lease DHCP attivi"
  # Mostra i lease attivi su VLAN 20
  echo "${leases_json}" | python3 -c "
import sys, json
d = json.load(sys.stdin)
rows = [r for r in d.get('rows', []) if r.get('address','').startswith('10.10.20')]
rows.sort(key=lambda x: tuple(int(n) for n in x.get('address','0.0.0.0').split('.')))
print(f'  Lease attivi su 10.10.20.0/24 ({len(rows)}):')
for r in rows:
    ip       = r.get('address','?')
    mac      = r.get('hw-address', r.get('hwaddr','?'))
    hostname = r.get('hostname','') or '(dynamic)'
    expire   = r.get('expire','?')
    print(f\"    {ip:<16} {mac:<20} {hostname}\")
" 2>/dev/null || warn "Impossibile parsare i lease (API potrebbe richiedere parametri diversi)"
else
  warn "API lease non disponibile o 0 lease attivi — prova: Services > Kea DHCP > Leases su OPNsense GUI"
fi

# =============================================================================
# SOMMARIO FINALE
# =============================================================================
echo ""
echo -e "${BOLD}${CYAN}============================================================${RESET}"
total=$((pass + fail + warn))
echo -e "${BOLD}  Risultati: ${total} test — ${GREEN}${pass} OK${RESET}  ${YELLOW}${warn} WARN${RESET}  ${RED}${fail} FAIL${RESET}"
echo -e "${BOLD}${CYAN}============================================================${RESET}"
echo ""

if [[ ${fail} -gt 0 ]]; then
  echo -e "${RED}  ⚠ Ci sono ${fail} FAILURE — controlla i dettagli sopra.${RESET}"
  exit 1
fi

if [[ ${warn} -gt 0 ]]; then
  echo -e "${YELLOW}  ℹ Ci sono ${warn} WARNING — probabilmente host spenti, non critici.${RESET}"
fi

exit 0

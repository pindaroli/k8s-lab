#!/usr/bin/env bash
# PVE Cluster Connectivity Diagnostic Script
# =============================================================================
# Verifies connectivity to all PVE nodes on Management and OOB networks.
# SSoT: rete.json
# =============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
RETE_JSON="${SCRIPT_DIR}/../rete.json"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
BOLD='\033[1m'
RESET='\033[0m'

if [ ! -f "${RETE_JSON}" ]; then
  echo -e "${RED}Error: rete.json not found at ${RETE_JSON}${RESET}"
  exit 1
fi

# Parse PVE nodes from rete.json
NODES_JSON=$(python3 -c "
import json
try:
    with open('${RETE_JSON}') as f:
        data = json.load(f)
    pve_nodes = []
    for n in data.get('nodi', []):
        if n.get('type') == 'Hypervisor' or 'pve' in n.get('id', ''):
            oob_ip = None
            for p in n.get('ports', []):
                if 'ip' in p and p['ip'].startswith('192.168.100.'):
                    oob_ip = p['ip']
                    break
            pve_nodes.append({
                'id': n['id'],
                'label': n.get('label', n['id']),
                'mgmt_ip': n.get('management_ip'),
                'oob_ip': oob_ip
            })
    print(json.dumps(pve_nodes))
except Exception as e:
    import sys
    print(f'Error parsing rete.json: {e}', file=sys.stderr)
    sys.exit(1)
")

pass_count=0
fail_count=0

# Detect OS for routing diagnostics
OS_TYPE="linux"
if [[ "$OSTYPE" == "darwin"* ]]; then
  OS_TYPE="macos"
fi

run_diagnostics() {
  local ip="$1"
  local network_name="$2"
  echo -e "    ${YELLOW}Running diagnostics for unreachable IP ${ip} (${network_name})...${RESET}"

  # 1. ARP Cache check
  echo -n "    - [ARP Check]: "
  local arp_res=""
  if [ "$OS_TYPE" = "macos" ]; then
    arp_res=$(arp -n "${ip}" 2>/dev/null || arp "${ip}" 2>/dev/null || true)
  else
    arp_res=$(ip neighbor show to "${ip}" 2>/dev/null || arp -n "${ip}" 2>/dev/null || true)
  fi

  if [[ -n "${arp_res}" ]]; then
    echo -e "${GREEN}MAC resolved${RESET} -> ${arp_res}"
  else
    echo -e "${RED}MAC NOT resolved (No ARP entry)${RESET}"
  fi

  # 2. Routing Table Check
  echo -n "    - [Routing Route]: "
  if [ "$OS_TYPE" = "macos" ]; then
    route get "${ip}" 2>/dev/null | grep -E "interface:|gateway:" | tr '\n' ' ' || echo "No route"
    echo ""
  else
    ip route get "${ip}" 2>/dev/null || echo "No route"
  fi

  # 3. Traceroute
  echo "    - [Traceroute (max 5 hops)]:"
  if [ "$OS_TYPE" = "macos" ]; then
    traceroute -n -q 1 -m 5 -w 1 "${ip}" 2>&1 | sed 's/^/        /' || true
  else
    traceroute -n -q 1 -m 5 -w 1 "${ip}" 2>&1 | sed 's/^/        /' || tracepath -n -m 5 "${ip}" 2>&1 | sed 's/^/        /' || true
  fi

  # 4. TCP Port fallback scan
  echo "    - [TCP Fallback check (SSH/GUI)]:"
  for port in 22 8006; do
    if nc -zv -w 1 "${ip}" "${port}" >/dev/null 2>&1; then
      echo -e "        ${GREEN}✓${RESET} Port ${port} is reachable (Ping is blocked/disabled on host/firewall)"
    else
      echo -e "        ${RED}✗${RESET} Port ${port} is unreachable"
    fi
  done
}

test_ip_connectivity() {
  local node_id="$1"
  local ip="$2"
  local network_name="$3"

  if [ -z "${ip}" ]; then
    return
  fi

  echo -e "${BOLD}Checking ${node_id} on ${network_name} (${ip})...${RESET}"

  # Ping check (3 packets, 1 sec timeout)
  local ping_args=""
  if [ "$OS_TYPE" = "macos" ]; then
    ping_args="-c 3 -t 1"
  else
    ping_args="-c 3 -W 1"
  fi

  if ping ${ping_args} "${ip}" >/dev/null 2>&1; then
    echo -e "  ${GREEN}✓${RESET} Ping OK"
    pass_count=$((pass_count + 1))

    # Check TCP/UDP ports
    echo -e "  Checking Ports:"
    # TCP Ports
    for port in 22 8006 111 2049 3128; do
      local desc=""
      case "${port}" in
        22) desc="SSH" ;;
        8006) desc="PVE Web GUI" ;;
        111) desc="RPCbind" ;;
        2049) desc="NFS" ;;
        3128) desc="SPICE Proxy" ;;
      esac

      if nc -zv -w 1 "${ip}" "${port}" >/dev/null 2>&1; then
        echo -e "    ${GREEN}✓${RESET} TCP/${port} (${desc}) - OPEN"
      else
        echo -e "    ${YELLOW}~${RESET} TCP/${port} (${desc}) - CLOSED"
      fi
    done

    # UDP Ports (Corosync)
    for port in 5404 5405; do
      local desc=""
      case "${port}" in
        5404) desc="Corosync LRM" ;;
        5405) desc="Corosync Cluster" ;;
      esac

      if nc -zuv -w 1 "${ip}" "${port}" >/dev/null 2>&1; then
        echo -e "    ${GREEN}✓${RESET} UDP/${port} (${desc}) - OPEN/RESPONDING"
      else
        echo -e "    ${YELLOW}~${RESET} UDP/${port} (${desc}) - NO ANSWER (expected if quiet)"
      fi
    done
  else
    echo -e "  ${RED}✗${RESET} Ping Failed!"
    fail_count=$((fail_count + 1))

    # Run diagnostic command
    run_diagnostics "${ip}" "${network_name}"
  fi
  echo ""
}

echo -e "${BOLD}${CYAN}"
echo "============================================================"
echo "  PVE Cluster Connectivity Diagnostics"
echo "  SSoT: ${RETE_JSON}"
echo "  $(date '+%Y-%m-%d %H:%M:%S')"
echo "============================================================"
echo -e "${RESET}"

# Loop over nodes
for row in $(echo "${NODES_JSON}" | python3 -c "
import json, sys
for n in json.load(sys.stdin):
    print(f\"{n['id']}|{n['mgmt_ip']}|{n['oob_ip'] or ''}\")
"); do
  IFS='|' read -r node_id mgmt_ip oob_ip <<< "${row}"

  # Test Management IP (VLAN 10)
  test_ip_connectivity "${node_id}" "${mgmt_ip}" "Management (VLAN 10)"

  # Test OOB IP (VLAN 99)
  if [ -n "${oob_ip}" ]; then
    test_ip_connectivity "${node_id}" "${oob_ip}" "OOB (VLAN 99)"
  fi
done

# Summary
echo -e "${BOLD}${CYAN}============================================================${RESET}"
total_checks=$((pass_count + fail_count))
echo -e "${BOLD}  Summary: ${total_checks} checks run — ${GREEN}${pass_count} OK${RESET}  ${RED}${fail_count} FAILED${RESET}"
echo -e "${BOLD}${CYAN}============================================================${RESET}"

if [[ ${fail_count} -gt 0 ]]; then
  echo -e "${RED}Critical: Unhealthy connectivity detected on PVE nodes!${RESET}"
  exit 1
fi

echo -e "${GREEN}All nodes connected successfully.${RESET}"
exit 0

#!/usr/bin/env bash
# Diagnostica dello stato operativo dell'Homelab: FULL, ECO, OFF o INCONGRUENTE
set -Eeuo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"
cd "$ROOT_DIR" || exit 1

# ==============================================================================
# OPZIONI CLI E INTERATTIVITÀ
# ==============================================================================
RAW_OUTPUT=false
VERBOSE=false
FLAG_PASSED=false

for arg in "$@"; do
    case "$arg" in
        --raw)
            RAW_OUTPUT=true
            FLAG_PASSED=true
            ;;
        -v|--verbose)
            VERBOSE=true
            FLAG_PASSED=true
            ;;
        -h|--help)
            echo "Uso: $0 [--raw] [-v|--verbose]"
            echo "  --raw       Stampa solo la parola di stato: FULL, ECO, OFF, INCONGRUENTE"
            echo "  -v, --verbose Mostra i risultati di tutti i singoli controlli"
            exit 0
            ;;
    esac
done

# Se siamo in un terminale interattivo e non sono stati passati flag espliciti, chiedi se mostrare verbose
if [ "$FLAG_PASSED" = false ] && [ -t 0 ] && [ "$RAW_OUTPUT" = false ]; then
    read -r -p "Vuoi mostrare il dettaglio verbose dei controlli? [s/N]: " ask_verbose || true
    case "$ask_verbose" in
        [sSyY]*)
            VERBOSE=true
            echo ""
            ;;
        *)
            VERBOSE=false
            ;;
    esac
fi

# ==============================================================================
# INDIRIZZI TARGET
# ==============================================================================
TRUENAS_HOST="10.10.20.50"
PVE1_HOST="10.10.10.11"
PVE2_HOST="10.10.10.21"
PVE3_HOST="10.10.10.31"
K8S_VIP="10.10.20.55"
TRAEFIK_VIP="10.10.20.56"
MAC_STUDIO_IP="10.10.20.100"
DNS_SERVER="10.10.20.1"

# ==============================================================================
# PROBE TCP RAPIDI (PARALLELI, TIMEOUT 1s)
# ==============================================================================
SYS_TMPDIR="${TMPDIR:-/tmp}"
SYS_TMPDIR="${SYS_TMPDIR%/}"
TMP_DIR="$(mktemp -d "${SYS_TMPDIR}/homelab_status_XXXXXX")"
trap 'rm -rf "$TMP_DIR"' EXIT

_probe() {
    local key="$1"
    local host="$2"
    local port="$3"
    if nc -z -w 1 "$host" "$port" >/dev/null 2>&1; then
        echo "1" > "$TMP_DIR/$key"
    else
        echo "0" > "$TMP_DIR/$key"
    fi
}

# Lancio probe in background
_probe "tn_ssh" "$TRUENAS_HOST" 22 &
_probe "tn_web" "$TRUENAS_HOST" 443 &
_probe "pve1" "$PVE1_HOST" 8006 &
_probe "pve2" "$PVE2_HOST" 8006 &
_probe "pve3" "$PVE3_HOST" 8006 &
_probe "k8s_vip" "$K8S_VIP" 6443 &
_probe "traefik_vip" "$TRAEFIK_VIP" 443 &

wait

TN_SSH=$(cat "$TMP_DIR/tn_ssh" 2>/dev/null || echo "0")
TN_WEB=$(cat "$TMP_DIR/tn_web" 2>/dev/null || echo "0")
PVE1_UP=$(cat "$TMP_DIR/pve1" 2>/dev/null || echo "0")
PVE2_UP=$(cat "$TMP_DIR/pve2" 2>/dev/null || echo "0")
PVE3_UP=$(cat "$TMP_DIR/pve3" 2>/dev/null || echo "0")
K8S_VIP_UP=$(cat "$TMP_DIR/k8s_vip" 2>/dev/null || echo "0")
TRAEFIK_VIP_UP=$(cat "$TMP_DIR/traefik_vip" 2>/dev/null || echo "0")

# Valutazione aggregata Storage
if [ "$TN_SSH" = "1" ] || [ "$TN_WEB" = "1" ]; then
    STORAGE_UP=true
else
    STORAGE_UP=false
fi

# Valutazione aggregata PVE
PVE_ONLINE_COUNT=0
[ "$PVE1_UP" = "1" ] && ((PVE_ONLINE_COUNT++)) || true
[ "$PVE2_UP" = "1" ] && ((PVE_ONLINE_COUNT++)) || true
[ "$PVE3_UP" = "1" ] && ((PVE_ONLINE_COUNT++)) || true

if [ "$PVE_ONLINE_COUNT" -eq 3 ]; then
    PVE_STATE="ALL_UP"
elif [ "$PVE_ONLINE_COUNT" -eq 0 ]; then
    PVE_STATE="ALL_DOWN"
else
    PVE_STATE="PARTIAL"
fi

# Valutazione aggregata K8s
if [ "$K8S_VIP_UP" = "1" ] && [ "$TRAEFIK_VIP_UP" = "1" ]; then
    K8S_STATE="ALL_UP"
elif [ "$K8S_VIP_UP" = "0" ] && [ "$TRAEFIK_VIP_UP" = "0" ]; then
    K8S_STATE="ALL_DOWN"
else
    K8S_STATE="PARTIAL"
fi

# ==============================================================================
# PROBE DNS UNBOUND (OPNsense)
# ==============================================================================
# Usa la risoluzione DNS standard del sistema (che punta a OPNsense 192.168.2.254)
_resolve_host() {
    local host="$1"
    local res=""
    if command -v dig >/dev/null 2>&1; then
        res=$(dig +short +time=1 +tries=1 "$host" 2>/dev/null | grep -E '^[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+$' | tail -n1)
    fi
    if [ -z "$res" ] && command -v nslookup >/dev/null 2>&1; then
        res=$(nslookup "$host" 2>/dev/null | awk '/^Address: / { print $2 }' | grep -E '^[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+$' | tail -n1)
    fi
    echo "$res"
}

DNS_HOME_INTERNAL=$(_resolve_host "home-internal.pindaroli.org")
DNS_MCP=$(_resolve_host "mcp.pindaroli.org")

# ==============================================================================
# PROBE CONTAINER FAILOVER ORBSTACK (Mac Studio locale o remoto)
# ==============================================================================
ORBSTACK_ACTIVE=false
if command -v docker >/dev/null 2>&1; then
    running_failover=$(docker ps --filter "name=homepage-mac" --filter "name=hermes-agent" --filter "name=litellm-proxy" --format '{{.Names}}' 2>/dev/null || true)
    if [ -n "$running_failover" ]; then
        ORBSTACK_ACTIVE=true
    fi
fi
if [ "$ORBSTACK_ACTIVE" = false ]; then
    if nc -z -w 1 "$MAC_STUDIO_IP" 9119 >/dev/null 2>&1 || nc -z -w 1 "$MAC_STUDIO_IP" 8180 >/dev/null 2>&1; then
        ORBSTACK_ACTIVE=true
    fi
fi

# ==============================================================================
# LOGICA DI VALUTAZIONE REGOLE E RILEVAMENTO CONTRADDIZIONI
# ==============================================================================
declare -a CONTRADICTIONS=()

# 1. Controlli PVE e Storage
if [ "$PVE_STATE" = "PARTIAL" ]; then
    CONTRADICTIONS+=("Nodi PVE solo parzialmente accesi ($PVE_ONLINE_COUNT/3 online: pve1=$PVE1_UP, pve2=$PVE2_UP, pve3=$PVE3_UP)")
fi

if [ "$PVE_STATE" != "ALL_DOWN" ] && [ "$STORAGE_UP" = false ]; then
    CONTRADICTIONS+=("Nodi Compute PVE accesi ma Storage TrueNAS ($TRUENAS_HOST) è offline (incoerenza storage NFS)")
fi

if [ "$PVE_STATE" = "ALL_UP" ] && [ "$K8S_STATE" != "ALL_UP" ]; then
    CONTRADICTIONS+=("Tutti i nodi PVE sono accesi ma il cluster K8s non risponde (VIP K8s API 6443=$K8S_VIP_UP, VIP Traefik Ingress 443=$TRAEFIK_VIP_UP)")
fi

if [ "$PVE_STATE" = "ALL_DOWN" ] && [ "$K8S_STATE" != "ALL_DOWN" ]; then
    CONTRADICTIONS+=("I nodi fisici PVE risultano spenti ma l'IP/VIP K8s risponde su rete (conflitto IP o fantasma)")
fi

# 2. Controlli OrbStack vs TrueNAS
if [ "$STORAGE_UP" = true ] && [ "$ORBSTACK_ACTIVE" = true ]; then
    CONTRADICTIONS+=("Split-brain: TrueNAS è online ma i container di failover OrbStack su Mac Studio sono ancora attivi")
fi

if [ "$STORAGE_UP" = false ] && [ "$ORBSTACK_ACTIVE" = false ]; then
    CONTRADICTIONS+=("TrueNAS è offline ma i container di failover OrbStack su Mac Studio non sono attivi (servizi scoperti)")
fi

# 3. Controlli DNS vs Hardware
if [ "$DNS_HOME_INTERNAL" = "$TRAEFIK_VIP" ] && [ "$K8S_STATE" != "ALL_UP" ]; then
    CONTRADICTIONS+=("Il DNS home-internal punta al K8s Ingress ($TRAEFIK_VIP) ma K8s/Traefik è offline")
fi

if [ "$DNS_HOME_INTERNAL" = "$TRUENAS_HOST" ] && [ "$STORAGE_UP" = false ]; then
    CONTRADICTIONS+=("Il DNS home-internal punta a TrueNAS ($TRUENAS_HOST) ma TrueNAS è offline")
fi

if [ "$DNS_HOME_INTERNAL" = "$MAC_STUDIO_IP" ] && [ "$STORAGE_UP" = true ]; then
    CONTRADICTIONS+=("Il DNS home-internal punta a Mac Studio ($MAC_STUDIO_IP) nonostante TrueNAS sia online")
fi

if [ -n "$DNS_HOME_INTERNAL" ] && [ "$DNS_HOME_INTERNAL" != "$TRAEFIK_VIP" ] && [ "$DNS_HOME_INTERNAL" != "$TRUENAS_HOST" ] && [ "$DNS_HOME_INTERNAL" != "$MAC_STUDIO_IP" ]; then
    CONTRADICTIONS+=("Il DNS home-internal punta a un IP imprevisto: $DNS_HOME_INTERNAL")
fi

# Controlli asimmetria tra home-internal e mcp
if [ "$DNS_HOME_INTERNAL" = "$TRAEFIK_VIP" ] && [ -n "$DNS_MCP" ] && [ "$DNS_MCP" != "$TRUENAS_HOST" ]; then
    CONTRADICTIONS+=("DNS asimmetrico: home-internal punta a K8s ($TRAEFIK_VIP) ma mcp non punta a TrueNAS ($DNS_MCP != $TRUENAS_HOST)")
fi

if [ "$DNS_HOME_INTERNAL" = "$TRUENAS_HOST" ] && [ -n "$DNS_MCP" ] && [ "$DNS_MCP" != "$TRUENAS_HOST" ]; then
    CONTRADICTIONS+=("DNS asimmetrico: home-internal punta a TrueNAS ma mcp punta altrove ($DNS_MCP)")
fi

if [ "$DNS_HOME_INTERNAL" = "$MAC_STUDIO_IP" ] && [ -n "$DNS_MCP" ] && [ "$DNS_MCP" != "$MAC_STUDIO_IP" ]; then
    CONTRADICTIONS+=("DNS asimmetrico: home-internal punta a Mac Studio ma mcp punta altrove ($DNS_MCP)")
fi

# ==============================================================================
# VERIFICA STATI CANONICI
# ==============================================================================
FINAL_STATUS="INCONGRUENTE"

if [ ${#CONTRADICTIONS[@]} -eq 0 ]; then
    # Verifica FULL
    if [ "$STORAGE_UP" = true ] && [ "$PVE_STATE" = "ALL_UP" ] && [ "$K8S_STATE" = "ALL_UP" ] && \
       [ "$ORBSTACK_ACTIVE" = false ] && [ "$DNS_HOME_INTERNAL" = "$TRAEFIK_VIP" ]; then
        FINAL_STATUS="FULL"
    # Verifica ECO
    elif [ "$STORAGE_UP" = true ] && [ "$PVE_STATE" = "ALL_DOWN" ] && [ "$K8S_STATE" = "ALL_DOWN" ] && \
         [ "$ORBSTACK_ACTIVE" = false ] && [ "$DNS_HOME_INTERNAL" = "$TRUENAS_HOST" ]; then
        FINAL_STATUS="ECO"
    # Verifica OFF
    elif [ "$STORAGE_UP" = false ] && [ "$PVE_STATE" = "ALL_DOWN" ] && [ "$K8S_STATE" = "ALL_DOWN" ] && \
         [ "$ORBSTACK_ACTIVE" = true ] && [ "$DNS_HOME_INTERNAL" = "$MAC_STUDIO_IP" ]; then
        FINAL_STATUS="OFF"
    else
        FINAL_STATUS="INCONGRUENTE"
        CONTRADICTIONS+=("I componenti non soddisfano interamente i requisiti di alcuno stato canonico (FULL, ECO, OFF)")
    fi
fi

# ==============================================================================
# OUTPUT
# ==============================================================================
if [ "$VERBOSE" = true ]; then
    echo "--- DETTAGLIO CONTROLLI HOMELAB ---"
    echo "Storage TrueNAS ($TRUENAS_HOST): SSH=$TN_SSH, WebUI=$TN_WEB -> $([ "$STORAGE_UP" = true ] && echo "ONLINE" || echo "OFFLINE")"
    echo "Hypervisors PVE: pve1=$PVE1_UP, pve2=$PVE2_UP, pve3=$PVE3_UP -> $PVE_STATE ($PVE_ONLINE_COUNT/3)"
    echo "Kubernetes Talos: API VIP ($K8S_VIP)=$K8S_VIP_UP, Ingress VIP ($TRAEFIK_VIP)=$TRAEFIK_VIP_UP -> $K8S_STATE"
    echo "OrbStack Failover (Mac Studio): $([ "$ORBSTACK_ACTIVE" = true ] && echo "ATTIVO" || echo "STANDBY")"
    echo "DNS Unbound ($DNS_SERVER): home-internal=${DNS_HOME_INTERNAL:-N/D}, mcp=${DNS_MCP:-N/D}"
    echo "-----------------------------------"
fi

if [ "$RAW_OUTPUT" = true ]; then
    echo "$FINAL_STATUS"
else
    case "$FINAL_STATUS" in
        FULL)
            echo "🟢 STATO: FULL"
            ;;
        ECO)
            echo "🟡 STATO: ECO"
            ;;
        OFF)
            echo "⚫ STATO: OFF"
            ;;
        INCONGRUENTE)
            echo "⚠️ STATO: INCONGRUENTE"
            for c in "${CONTRADICTIONS[@]}"; do
                echo "- $c"
            done
            ;;
    esac
fi

exit 0

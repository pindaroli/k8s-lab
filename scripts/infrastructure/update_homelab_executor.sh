#!/bin/bash
set -euo pipefail

# ==============================================================================
# Script: update_homelab_executor.sh
# Purpose: Safe rollout of homelab-executor container on TrueNAS SCALE
# Security Constraint: Executable EXCLUSIVELY from Mac Studio CLI
# ==============================================================================

# 1. Guardrail di Contesto
if [[ -f /.dockerenv ]] || [[ -f /run/.containerenv ]]; then
    echo "[FATAL] update_homelab_executor.sh cannot be executed inside a container!"
    echo "This operation must be executed exclusively from Mac Studio CLI."
    exit 1
fi

FORCE=false
while [[ $# -gt 0 ]]; do
    case "$1" in
        --force|-f)
            FORCE=true
            shift
            ;;
        *)
            echo "Unknown argument: $1"
            echo "Usage: $0 [--force]"
            exit 1
            ;;
    esac
done

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
TRUENAS_HOST="10.10.20.50"
TRUENAS_USER="olindo"
REMOTE_MCP_DIR="/mnt/stripe/truenas-docker/mcp"

echo "========================================================"
echo "🚀 Starting Homelab Executor Rollout"
echo "   Target Host: ${TRUENAS_HOST}"
echo "   Compose Dir: ${REMOTE_MCP_DIR}"
echo "========================================================"

# 2. Synchronize declarative Compose and Dynamic routing
echo "[INFO] Syncing docker-compose.yaml and dynamic.yaml to TrueNAS..."
scp -o BatchMode=yes "${REPO_ROOT}/docker/mcp/docker-compose.yaml" "${TRUENAS_USER}@${TRUENAS_HOST}:${REMOTE_MCP_DIR}/docker-compose.yaml"
scp -o BatchMode=yes "${REPO_ROOT}/docker/mcp/dynamic.yaml" "${TRUENAS_USER}@${TRUENAS_HOST}:${REMOTE_MCP_DIR}/dynamic.yaml"

# 3. Pre-flight Drain Check
RUNNING_CONTAINER=$(ssh -o BatchMode=yes "${TRUENAS_USER}@${TRUENAS_HOST}" "docker ps -q -f name=homelab-executor")

if [[ -n "$RUNNING_CONTAINER" ]] && [[ "$FORCE" != "true" ]]; then
    echo "[INFO] homelab-executor is currently active. Checking for running automation jobs..."
    DRAIN_TIMEOUT=180
    START_TIME=$(date +%s)

    while true; do
        ACTIVE_PIDS=$(ssh -o BatchMode=yes "${TRUENAS_USER}@${TRUENAS_HOST}" "docker exec homelab-executor pgrep -af 'ansible-playbook|python3.*go\.py|sops' 2>/dev/null" || true)

        if [[ -z "$ACTIVE_PIDS" ]]; then
            echo "[INFO] No active automation tasks running. Proceeding with rollout."
            break
        fi

        CURRENT_TIME=$(date +%s)
        ELAPSED=$(( CURRENT_TIME - START_TIME ))

        if [[ $ELAPSED -ge $DRAIN_TIMEOUT ]]; then
            echo "[ERROR] Drain timeout ($DRAIN_TIMEOUT s) reached. Active tasks still present:"
            echo "$ACTIVE_PIDS"
            echo "Aborting rollout. Use --force to proceed regardless."
            exit 1
        fi

        echo "[INFO] Active tasks detected (${ELAPSED}/${DRAIN_TIMEOUT} s elapsed). Waiting..."
        sleep 5
    done
elif [[ "$FORCE" == "true" ]]; then
    echo "[WARN] --force flag enabled. Skipping pre-flight drain check."
fi

# 4. Pull Latest Container Image
echo "[INFO] Pulling latest ghcr.io/pindaroli/homelab-executor image on TrueNAS..."
ssh -o BatchMode=yes "${TRUENAS_USER}@${TRUENAS_HOST}" "cd ${REMOTE_MCP_DIR} && docker compose pull homelab-executor"

# 5. Rollout with nohup
echo "[INFO] Launching decoupled rollout with nohup..."
ssh -o BatchMode=yes "${TRUENAS_USER}@${TRUENAS_HOST}" "cd ${REMOTE_MCP_DIR} && nohup docker compose up -d homelab-executor > /tmp/homelab-executor-rollout.log 2>&1 &"

# 6. Readiness and Health Verification
echo "[INFO] Waiting for service to become healthy..."
READY=false
for i in {1..30}; do
    HEALTH_RESP=$(curl -fs --max-time 3 "http://${TRUENAS_HOST}:8100/executor/health" 2>/dev/null || true)

    if [[ -z "$HEALTH_RESP" ]]; then
        # Fallback check directly via docker exec in case Traefik is reloading
        HEALTH_RESP=$(ssh -o BatchMode=yes "${TRUENAS_USER}@${TRUENAS_HOST}" "docker exec homelab-executor curl -fs http://127.0.0.1:8000/health 2>/dev/null" || true)
    fi

    if [[ -n "$HEALTH_RESP" ]] && echo "$HEALTH_RESP" | grep -q '"status":"healthy"'; then
        VERSION=$(echo "$HEALTH_RESP" | jq -r '.version // "unknown"')
        echo "========================================================"
        echo "✅ Homelab Executor successfully updated and healthy!"
        echo "   Version: ${VERSION}"
        echo "   HTTP Health: http://${TRUENAS_HOST}:8100/executor/health"
        echo "   SSH Gateway: ssh -p 2222 executor@${TRUENAS_HOST}"
        echo "========================================================"
        READY=true
        break
    fi

    echo "  -> Waiting for readiness (attempt ${i}/30)..."
    sleep 3
done

if [[ "$READY" != "true" ]]; then
    echo "[ERROR] Health check failed after 90 seconds. Dumping container logs:"
    ssh -o BatchMode=yes "${TRUENAS_USER}@${TRUENAS_HOST}" "docker logs --tail 40 homelab-executor"
    exit 1
fi

#!/bin/bash
set -eo pipefail

echo "========================================================"
echo "🚀 Starting Homelab Executor Container"
echo "========================================================"

# 1. Setup required directories in tmpfs mounts
mkdir -p /run/sshd /tmp/host_keys
chmod 0755 /run/sshd

mkdir -p /home/executor/.ssh /home/executor/.config/sops/age /home/executor/.ansible/tmp
chown -R executor:executor /home/executor
chmod 0700 /home/executor /home/executor/.ssh /home/executor/.config /home/executor/.config/sops /home/executor/.config/sops/age /home/executor/.ansible

# 2. Secret staging from /run/host-secrets (tmpfs isolation)
HOST_SECRETS_DIR="/run/host-secrets"
if [ -d "$HOST_SECRETS_DIR" ]; then
    echo "[INFO] Staging secrets from $HOST_SECRETS_DIR into /home/executor/..."

    if [ -f "$HOST_SECRETS_DIR/authorized_keys" ]; then
        install -o executor -g executor -m 0600 "$HOST_SECRETS_DIR/authorized_keys" /home/executor/.ssh/authorized_keys
        echo "  -> Installed authorized_keys"
    fi

    if [ -f "$HOST_SECRETS_DIR/id_ed25519" ]; then
        install -o executor -g executor -m 0600 "$HOST_SECRETS_DIR/id_ed25519" /home/executor/.ssh/id_ed25519
        echo "  -> Installed id_ed25519"
    fi

    if [ -f "$HOST_SECRETS_DIR/id_ed25519.pub" ]; then
        install -o executor -g executor -m 0644 "$HOST_SECRETS_DIR/id_ed25519.pub" /home/executor/.ssh/id_ed25519.pub
        echo "  -> Installed id_ed25519.pub"
    fi

    if [ -f "$HOST_SECRETS_DIR/id_rsa" ]; then
        install -o executor -g executor -m 0600 "$HOST_SECRETS_DIR/id_rsa" /home/executor/.ssh/id_rsa
        echo "  -> Installed id_rsa"
    fi

    if [ -f "$HOST_SECRETS_DIR/id_rsa.pub" ]; then
        install -o executor -g executor -m 0644 "$HOST_SECRETS_DIR/id_rsa.pub" /home/executor/.ssh/id_rsa.pub
        echo "  -> Installed id_rsa.pub"
    fi

    if [ -f "$HOST_SECRETS_DIR/id_rsa_extreme" ]; then
        install -o executor -g executor -m 0600 "$HOST_SECRETS_DIR/id_rsa_extreme" /home/executor/.ssh/id_rsa_extreme
        echo "  -> Installed id_rsa_extreme"
    fi

    if [ -f "$HOST_SECRETS_DIR/known_hosts" ]; then
        install -o executor -g executor -m 0644 "$HOST_SECRETS_DIR/known_hosts" /home/executor/.ssh/known_hosts
        echo "  -> Installed known_hosts"
    fi

    if [ -f "$HOST_SECRETS_DIR/config" ]; then
        install -o executor -g executor -m 0600 "$HOST_SECRETS_DIR/config" /home/executor/.ssh/config
        echo "  -> Installed custom user ssh config"
    fi

    if [ -f "$HOST_SECRETS_DIR/keys.txt" ]; then
        install -o executor -g executor -m 0600 "$HOST_SECRETS_DIR/keys.txt" /home/executor/.config/sops/age/keys.txt
        echo "  -> Installed age keys.txt"
    fi
else
    echo "[WARN] Host secrets directory $HOST_SECRETS_DIR does not exist. Running in unauthenticated mode."
fi

# Ensure user known_hosts exists
touch /home/executor/.ssh/known_hosts
chown executor:executor /home/executor/.ssh/known_hosts
chmod 0644 /home/executor/.ssh/known_hosts

# 3. Host Key verification
HOST_KEY_PATH="/etc/ssh/host_keys/ssh_host_ed25519_key"
if [ -f "$HOST_KEY_PATH" ]; then
    echo "[INFO] Persistent host key verified at $HOST_KEY_PATH"
else
    echo "[WARN] Persistent host key not found at $HOST_KEY_PATH"
    echo "[INFO] Generating ephemeral test host key in /tmp/host_keys/..."
    ssh-keygen -t ed25519 -f /tmp/host_keys/ssh_host_ed25519_key -N "" -C "ephemeral-executor" >/dev/null 2>&1
    chmod 0600 /tmp/host_keys/ssh_host_ed25519_key
    HOST_KEY_PATH="/tmp/host_keys/ssh_host_ed25519_key"
fi

# 4. Supervision & graceful drain handling
_term() {
    echo ""
    echo "[INFO] Received SIGTERM/SIGINT. Initiating graceful drain..."
    if [ -n "$UVICORN_PID" ]; then
        echo "[INFO] Sending SIGTERM to Uvicorn (PID: $UVICORN_PID)..."
        kill -TERM "$UVICORN_PID" 2>/dev/null || true
    fi
    if [ -n "$SSHD_PID" ]; then
        echo "[INFO] Sending SIGTERM to OpenSSH daemon (PID: $SSHD_PID)..."
        kill -TERM "$SSHD_PID" 2>/dev/null || true
    fi
    wait "$UVICORN_PID" 2>/dev/null || true
    wait "$SSHD_PID" 2>/dev/null || true
    echo "[INFO] All processes stopped. Clean exit."
    exit 0
}

trap _term SIGTERM SIGINT

# 5. Start OpenSSH Daemon in background
echo "[INFO] Starting OpenSSH server..."
/usr/sbin/sshd -D -e -h "$HOST_KEY_PATH" &
SSHD_PID=$!
echo "[INFO] OpenSSH server active (PID: $SSHD_PID)"

# 6. Start Uvicorn as executor user in background
echo "[INFO] Starting FastMCP + FastAPI Uvicorn server as user executor..."
cd /app
gosu executor uvicorn server.main:app --host 0.0.0.0 --port 8000 --timeout-graceful-shutdown 90 &
UVICORN_PID=$!
echo "[INFO] Uvicorn server active (PID: $UVICORN_PID)"

# 7. Wait for any process to exit (fail-fast / wait -n)
wait -n $SSHD_PID $UVICORN_PID
EXIT_CODE=$?
echo "[WARN] Critical process terminated with exit code $EXIT_CODE."
_term

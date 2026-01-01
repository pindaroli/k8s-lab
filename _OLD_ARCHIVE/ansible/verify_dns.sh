#!/bin/bash

# verification_targets defined from rete.json
HOSTS=(
    "switch10g.pindaroli.org"
    "switch25gMLetto.pindaroli.org"
    "switch25gMServer.pindaroli.org"
    "opnSense.pindaroli.org"
    "mac mini.pindaroli.org"
    "pve.pindaroli.org"
    "pve2.pindaroli.org"
    "pve3.pindaroli.org"
    "ap11000.pindaroli.org"
)

echo "--- Starting DNS Resolution Verification ---"

for host in "${HOSTS[@]}"; do
    # Try to ping once, wait max 1 second
    if ping -c 1 -W 1000 "$host" &> /dev/null; then
        # Extract IP to show it resolved
        IP=$(ping -c 1 -W 1000 "$host" | head -n 1 | awk -F'[()]' '{print $2}')
        echo "[OK] $host resolved to $IP"
    else
        echo "[FAIL] $host could not be reached or resolved"
    fi
done

echo "--- Verification Complete ---"

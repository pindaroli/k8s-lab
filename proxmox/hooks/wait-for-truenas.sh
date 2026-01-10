#!/bin/bash

# Configuration
TRUENAS_IP="10.10.10.50"
TIMEOUT_SECONDS=240  # 4 Minutes
CHECK_INTERVAL=5

# Telegram Configuration
TELEGRAM_BOT_TOKEN="6548622283:AAHUfcvGWfj8LBdd_V4420uctNCKk3-D_Xs"
TELEGRAM_CHAT_ID="554585346"

# Helper function to send Telegram message
send_telegram() {
    local message="$1"
    curl -s -X POST "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/sendMessage" \
        -d chat_id="${TELEGRAM_CHAT_ID}" \
        -d text="${message}" > /dev/null
}

vmid="$1"
phase="$2"

if [ "$phase" == "pre-start" ]; then
    send_telegram "⏳ **Proxmox Hook**: VM $vmid is starting... Checking TrueNAS ($TRUENAS_IP)."
    echo "[$vmid] Hook Script: Checking availability of TrueNAS ($TRUENAS_IP)..."

    start_time=$(date +%s)
    end_time=$((start_time + TIMEOUT_SECONDS))

    while [ $(date +%s) -lt $end_time ]; do
        # Check if TrueNAS is pingable
        if ping -c 1 -W 1 "$TRUENAS_IP" &> /dev/null; then
            echo "[$vmid] TrueNAS is UP. Allowing VM start."
            send_telegram "✅ **Proxmox Hook**: TrueNAS is UP. Starting VM $vmid."
            exit 0
        fi
        
        # Optional: Check wait progress logging
        current_time=$(date +%s)
        elapsed=$((current_time - start_time))
        # echo "[$vmid] Waiting for TrueNAS... ($elapsed / $TIMEOUT_SECONDS)"
        
        sleep $CHECK_INTERVAL
    done

    # Timeout Reached!
    echo "[$vmid] TIMEOUT waiting for TrueNAS!"
    send_telegram "⚠️ **Proxmox Alert** ⚠️%0A%0AVM $vmid is forcing startup but TrueNAS ($TRUENAS_IP) is NOT reachable after ${TIMEOUT_SECONDS}s.%0A%0APlease check storage/network immediately."

    # We exit 0 to allow the VM to start anyway (Fail-Safe), preventing a boot lock.
    exit 0
fi

exit 0

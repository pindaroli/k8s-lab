#!/bin/sh
USER_NAME="$1"
CALLING="$2"
REASON="$3"
LOG=/var/log/patrizia_lock.log
echo "$(date -u +%Y-%m-%dT%H:%M:%SZ) invoke user=$USER_NAME reason=$REASON" >> "$LOG"
case "$REASON" in
    *already\ logged\ in*|*Multiple\ logins*) ;;
    *) exit 0 ;;
esac
if [ "$USER_NAME" != "patrizia" ]; then
    exit 0
fi
(
    sleep 2
    echo "$(date -u +%Y-%m-%dT%H:%M:%SZ) lock user=$USER_NAME reason=$REASON" >> "$LOG"
    python3 /usr/local/opnsense/scripts/freeradius/patrizia_lock.py "$CALLING"
) >/dev/null 2>&1 &
exit 0

#!/bin/bash
# wrappers/fetch_exports.sh

HOST="$1"
USER="$2"
PASS="$3"

if [ -z "$HOST" ] || [ -z "$USER" ] || [ -z "$PASS" ]; then
    echo "Usage: $0 <host> <user> <password>"
    exit 1
fi

expect -c "
set timeout 10
log_user 0
spawn ssh -o StrictHostKeyChecking=no $USER@$HOST \"cat /etc/exports\"
expect {
    \"password:\" {
        send \"$PASS\r\"
        exp_continue
    }
    eof
}
log_user 1
puts [string trim \$expect_out(buffer)]
"

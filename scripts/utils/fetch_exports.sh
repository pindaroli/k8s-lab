#!/bin/bash
# wrappers/fetch_exports.sh

HOST="${1:-10.10.10.50}"
USER="${2:-olindo}"

exec ssh -o BatchMode=yes -o StrictHostKeyChecking=no -o ConnectTimeout=5 "$USER@$HOST" "cat /etc/exports"

#!/usr/bin/env bash
# Diagnostica esaustiva e verifica salute del cluster Talos & K8s
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"
cd "$ROOT_DIR"

exec python3 "$SCRIPT_DIR/check_k8s.py" "$@"

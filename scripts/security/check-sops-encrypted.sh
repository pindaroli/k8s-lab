#!/usr/bin/env bash
# check-sops-encrypted.sh
# Verifica che i file che dovrebbero essere cifrati contengano i metadati SOPS.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"

EXIT_CODE=0
FILES=("$@")

if [[ ${#FILES[@]} -eq 0 ]]; then
    # Fallback deterministico sull'intero corpus secrets-sops
    shopt -s nullglob
    FILES=("$ROOT_DIR"/secrets-sops/*.enc.yaml)
    shopt -u nullglob
fi

if [[ ${#FILES[@]} -eq 0 ]]; then
    echo "⚠️ Nessun file da verificare."
    exit 0
fi

for file in "${FILES[@]}"; do
    if [[ -f "$file" ]]; then
        if ! grep -q "sops:" "$file"; then
            echo "❌ ERRORE: Il file $file non sembra essere cifrato con SOPS!"
            EXIT_CODE=1
        fi
    fi
done

if [[ $EXIT_CODE -eq 0 ]]; then
    echo "✅ Tutti i file (${#FILES[@]}) risultano regolarmente cifrati con SOPS."
fi

exit $EXIT_CODE

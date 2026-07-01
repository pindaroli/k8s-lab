#!/bin/bash
# check-sops-encrypted.sh
# Verifica che i file che dovrebbero essere cifrati contengano i metadati SOPS.

EXIT_CODE=0

for file in "$@"; do
    if ! grep -q "sops:" "$file"; then
        echo "❌ ERRORE: Il file $file non sembra essere cifrato con SOPS!"
        EXIT_CODE=1
    fi
done

exit $EXIT_CODE

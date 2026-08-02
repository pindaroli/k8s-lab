#!/bin/bash
set -e

# Directory del progetto (radice)
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
SECRETS_DIR="${PROJECT_DIR}/secrets-sops"
TALOS_CONFIG_SRC="${PROJECT_DIR}/talos-config/talosconfig"
SECRET_DEST="${SECRETS_DIR}/hermes-kubeconfig.enc.yaml"

echo "=== Sincronizzazione Talosconfig per Hermes Agent ==="

# Verifica esistenza talosconfig
if [ ! -f "$TALOS_CONFIG_SRC" ]; then
    echo "[ERRORE] Il file $TALOS_CONFIG_SRC non esiste. Verifica di avere configurato Talos sul tuo Mac."
    exit 1
fi

echo "1. Lettura di $TALOS_CONFIG_SRC..."
TALOS_CONTENT=$(cat "$TALOS_CONFIG_SRC")

PLAIN_DEST="${SECRETS_DIR}/hermes-kubeconfig-plain.yaml"

echo "2. Creazione Secret Kubernetes (formato YAML non cifrato)..."
cat <<EOF > "${PLAIN_DEST}"
apiVersion: v1
kind: Secret
metadata:
  name: hermes-kube-config
  namespace: hermes
type: Opaque
stringData:
  talosconfig: |-
$(echo "$TALOS_CONTENT" | sed 's/^/    /')
EOF

echo "3. Crittografia tramite SOPS..."
sops -e \
    --encrypted-regex '^(data|stringData)$' \
    --mac-only-encrypted \
    "${PLAIN_DEST}" > "$SECRET_DEST"

echo "4. Pulizia file temporanei..."
rm "${PLAIN_DEST}"

echo "5. Applicazione Secret nel cluster..."
sops -d "$SECRET_DEST" | kubectl apply -f -

echo "=== Sincronizzazione completata con successo! ==="
echo "Il file $SECRET_DEST è stato aggiornato ed applicato al cluster."

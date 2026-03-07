#!/bin/bash
set -e

# Configurazione percorsi relativi alla posizione dello script
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Assicurati che i path dei binari comuni siano inclusi (Homebrew, etc)
export PATH="/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin:$PATH"

# Imposta KUBECONFIG esplicitamente
export KUBECONFIG="$PROJECT_ROOT/talos-config/kubeconfig"

# Verifica se il file esiste
if [ ! -f "$KUBECONFIG" ]; then
    echo "Errore: KUBECONFIG non trovato in $KUBECONFIG"
    exit 1
fi

# Find Primary Pod
POD=$(kubectl get pods -n cnpg-system -l cnpg.io/cluster=postgres-main,cnpg.io/instanceRole=primary -o jsonpath='{.items[0].metadata.name}' || true)

if [ -z "$POD" ]; then
    echo "Errore: Impossibile trovare il pod Primario di Postgres."
    exit 1
fi

echo "Found Primary Pod: $POD"

# Function to create user and db
create_db() {
    APP=$1
    PASS=$2
    echo "Creating Database and User for $APP..."
    kubectl exec -n cnpg-system $POD -- psql -c "CREATE USER $APP WITH PASSWORD '$PASS';" || true
    kubectl exec -n cnpg-system $POD -- psql -c "CREATE DATABASE $APP OWNER $APP;" || true
    kubectl exec -n cnpg-system $POD -- psql -c "GRANT ALL PRIVILEGES ON DATABASE $APP TO $APP;" || true
}

create_db "prowlarr" "prowlarr"
create_db "radarr" "radarr"
create_db "lidarr" "lidarr"
create_db "jellyseerr" "jellyseerr"
# create_db "qbittorrent" "qbittorrent" # Keep qbit on sqlite for now or experimental?

echo "Databases Created."

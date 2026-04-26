#!/bin/bash
set -e

echo "🚀 Inizio installazione di Prefect..."

# Carico le configurazioni del cluster
export KUBECONFIG=../talos-config/kubeconfig

echo "1. Creazione namespace 'prefect'..."
kubectl apply -f namespace.yaml || { echo "❌ Errore nella creazione del namespace"; exit 1; }

echo "2. Creazione del database in postgres-main..."
# Trovo il pod primario del cluster CloudNativePG
PRIMARY_POD=$(kubectl get cluster postgres-main -n cnpg-system -o jsonpath='{.status.currentPrimary}')
if [ -z "$PRIMARY_POD" ]; then
  echo "❌ Errore: Impossibile trovare il pod primario di postgres-main."
  exit 1
fi
echo "   Pod primario identificato: $PRIMARY_POD"
# Eseguo i comandi SQL direttamente nel pod ignorando l'errore se esistono già
kubectl exec -n cnpg-system $PRIMARY_POD -- psql -U postgres -c "CREATE USER prefect WITH PASSWORD 'prefect_secure_password';" || true
kubectl exec -n cnpg-system $PRIMARY_POD -- psql -U postgres -c "CREATE DATABASE prefect_db OWNER prefect;" || true
echo "   ✅ Database preparato."

echo "3. Aggiunta repository Helm di Prefect..."
helm repo add prefect https://prefecthq.github.io/prefect-helm
helm repo update

echo "4. Deploy di Prefect Server tramite Helm..."
# Recupero l'host dal values.yaml per testarlo
DB_HOST=$(grep "host:" values.yaml | cut -d'"' -f2)
echo "   Verifica connettività verso il database ($DB_HOST)..."
# Uso un pod temporaneo per testare la porta 5432
kubectl run db-check-$(date +%s) -it --rm --restart=Never -n prefect --image=busybox -- nc -zv $DB_HOST 5432 || { echo "❌ Errore: Database non raggiungibile su $DB_HOST:5432. Verifica lo stato del nodo o della rete."; exit 1; }

helm upgrade --install prefect prefect/prefect-server \
  --namespace prefect \
  -f values.yaml

echo "   Attesa che il pod di Prefect sia pronto..."
kubectl rollout status deployment prefect-server -n prefect --timeout=120s || { echo "❌ Errore: Prefect Server non è andato in Ready entro 120s."; exit 1; }

echo "5. Creazione IngressRoute..."
kubectl apply -f ingress.yaml || { echo "❌ Errore nell'applicazione dell'Ingress"; exit 1; }

echo "6. Aggiornamento dashboard Homepage (link Prefect in categoria GitOps)..."
kubectl apply -f ../homepage/homepage-local.yaml || { echo "❌ Errore nell'aggiornamento homepage-local"; exit 1; }
kubectl apply -f ../homepage/homepage.yaml || { echo "❌ Errore nell'aggiornamento homepage"; exit 1; }

echo "✅ Installazione Fase 1 completata!"

echo "--- FASE 2: PREFECT KUBERNETES WORKER ---"

echo "7. Creazione Work Pool 'k8s-pool'..."
# Usiamo l'URL via Traefik per stabilità
PREFECT_API_URL="https://prefect-internal.pindaroli.org/api"
if ! kubectl run prefect-cli-check --rm -it --restart=Never -n prefect --image=prefecthq/prefect:3.6.28-python3.11 --env="PREFECT_API_URL=$PREFECT_API_URL" -- prefect work-pool ls | grep -q "k8s-pool"; then
  echo "   Creazione nuovo pool..."
  kubectl run prefect-cli-create --rm -it --restart=Never -n prefect --image=prefecthq/prefect:3.6.28-python3.11 --env="PREFECT_API_URL=$PREFECT_API_URL" -- prefect work-pool create "k8s-pool" --type kubernetes || { echo "❌ Errore nella creazione del Work Pool"; exit 1; }
else
  echo "   ✅ Work Pool 'k8s-pool' già esistente."
fi

echo "8. Aggiunta repository Helm per il Worker..."
helm repo add prefect https://prefecthq.github.io/prefect-helm
helm repo update

echo "9. Deploy del Prefect Worker tramite Helm..."
helm upgrade --install prefect-worker prefect/prefect-worker \
  --namespace prefect \
  -f values-worker.yaml || { echo "❌ Errore nel deploy del Worker"; exit 1; }

echo "   Verifica stato del Worker..."
kubectl rollout status deployment prefect-worker -n prefect --timeout=120s || { echo "❌ Errore: Prefect Worker non è andato in Ready."; exit 1; }

echo "✅ FASE 2 completata con successo!"
echo "--- INSTALLAZIONE GLOBALE PREFECT TERMINATA ---"


#!/bin/bash
# safe_shutdown_cp.sh
# Script interattivo per lo spegnimento in sicurezza dei nodi Control Plane Talos

echo "====================================================="
echo "  Talos Control Plane - Procedura di Spegnimento"
echo "====================================================="
echo "Seleziona il nodo Control Plane da spegnere in sicurezza:"
echo "1) talos-cp-01 (10.10.20.141)"
echo "2) talos-cp-02 (10.10.20.142)"
echo "3) talos-cp-03 (10.10.20.143)"
echo "a) TUTTI i Control Plane (Spegnimento Intero Cluster)"
echo ""
read -p "Scelta [1/2/3/a]: " scelta

# Funzione per lo spegnimento in sicurezza di un singolo nodo (con controlli)
shutdown_single_node() {
    local NODE_ID=$1
    local NODE_NAME="talos-cp-0${NODE_ID}"
    local NODE_IP="10.10.20.14${NODE_ID}"

    echo ""
    echo "=========================================="
    echo "Inizio procedura per $NODE_NAME"
    echo "=========================================="

    # Controllo stato Postgres (CNPG)
    echo "[1/4] Controllo presenza di istanze Postgres critiche sul nodo..."
    PG_PODS=$(kubectl get pods -A --field-selector spec.nodeName=${NODE_NAME} 2>/dev/null | grep postgres)

    if [ -n "$PG_PODS" ]; then
        echo "⚠️ ATTENZIONE: Trovate istanze Postgres in esecuzione su $NODE_NAME!"
        echo "$PG_PODS"
        echo ""
        echo "Il comando drain forzerà lo spostamento o il riavvio del pod (rispettando il PodDisruptionBudget)."
        read -p "Vuoi continuare con il drain? [y/N]: " conf
        if [[ ! "$conf" =~ ^[Yy]$ ]]; then
            echo "Operazione annullata. Nessuna modifica effettuata."
            exit 1
        fi
    else
        echo "Nessun pod Postgres critico trovato."
    fi

    # Esecuzione Drain
    echo "[2/4] Esecuzione DRAIN (Svuotamento) su $NODE_NAME..."
    kubectl drain ${NODE_NAME} --ignore-daemonsets --delete-emptydir-data --force --grace-period=60

    if [ $? -eq 0 ]; then
        echo "Drain completato con successo."
    else
        echo "⚠️ ATTENZIONE: Il drain ha riportato un errore o un timeout."
        echo "Questo è normale se ci sono PodDisruptionBudget che bloccano lo spegnimento (es. repliche mancanti)."
        read -p "Vuoi procedere COMUNQUE con lo spegnimento fisico? [y/N]: " conf
        if [[ ! "$conf" =~ ^[Yy]$ ]]; then
            echo "Operazione annullata. Rimuovo il cordon..."
            kubectl uncordon ${NODE_NAME}
            exit 1
        fi
    fi

    # Spegnimento ACPI / Talos
    echo "[3/4] Invio comando di spegnimento ACPI/Talos a $NODE_IP..."
    talosctl shutdown -n ${NODE_IP}

    echo "[4/4] ✅ Nodo $NODE_NAME in fase di spegnimento."
}

# Flusso Principale
if [[ "$scelta" =~ ^[1-3]$ ]]; then
    shutdown_single_node "$scelta"

elif [ "$scelta" == "a" ]; then
    echo ""
    echo "🚨 ATTENZIONE CRITICA: Hai scelto di spegnere TUTTI i control plane contemporaneamente!"
    echo "Questo porterà l'intero cluster Kubernetes offline."
    echo "Poiché non è possibile fare il 'drain' dell'intero cluster (i pod non avrebbero nodi su cui spostarsi e andrebbe in timeout), i nodi verranno ignorati dal routing e spenti direttamente per evitare il blocco di etcd."
    echo ""
    read -p "Sei ASSOLUTAMENTE SICURO di voler spegnere l'intero cluster? [y/N]: " conf
    if [[ ! "$conf" =~ ^[Yy]$ ]]; then
         echo "Annullato. Il cluster rimane attivo."
         exit 1
    fi

    echo "[1/2] Evito lo scheduling di nuovi pod (Cordon)..."
    for i in {1..3}; do
        kubectl cordon talos-cp-0${i} 2>/dev/null || true
    done

    echo "[2/2] Invio segnali di spegnimento simultanei..."
    for i in {1..3}; do
        echo "Spegnimento talos-cp-0${i} (10.10.20.14${i})..."
        talosctl shutdown -n 10.10.20.14${i}
    done

    echo "✅ Comando di spegnimento inviato a tutti i Control Plane. Addio e grazie per tutto il pesce."

else
    echo "Scelta non valida."
    exit 1
fi

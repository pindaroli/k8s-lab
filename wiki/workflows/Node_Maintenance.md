# Workflow: Node Maintenance & Safe Shutdown

Questa procedura descrive come preparare un nodo del cluster per la manutenzione fisica o lo spegnimento senza causare deadlock nei servizi critici (specialmente il Database).

## 1. Identificazione dei Carichi (Discovery)
Prima di spegnere il nodo (es. `talos-cp-02`), verifica cosa ci gira sopra:
```bash
kubectl get pods -A -o wide | grep <NOME_NODO>
```

> [!IMPORTANT]
> **Check Database (CNPG)**: Controlla se il nodo ospita un'istanza di `postgres-main`.
> ```bash
> kubectl get pods -n cnpg-system -o wide
> ```
> Se il nodo ospita un'istanza (es. `postgres-main-2`), segui il punto 2.

## 2. Preparazione Database (Solo per nodi con Postgres)
Se devi spegnere il nodo per più di qualche minuto, hai due opzioni:

### Opzione A: Mantenere l'Alta Affidabilità (Consigliato)
Se hai altri nodi liberi, sposta l'istanza:
1.  **Scala il cluster**: Aumenta temporaneamente le istanze (es. da 3 a 4).
2.  **Attendi**: Aspetta che la nuova istanza sia `Ready` su un altro nodo.
3.  **Elimina il PVC sul nodo da spegnere**: Cancella il PVC dell'istanza che sta sul nodo in manutenzione. L'operatore la ricreerà altrove.

### Opzione B: Riduzione Carico (Se non hai nodi extra)
1.  **Scala il cluster a 2**: `kubectl edit cluster postgres-main -n cnpg-system`.
2.  L'operatore eliminerà una delle istanze. Assicurati che quella eliminata sia quella sul nodo da spegnere.

## 3. Svuotamento del Nodo (Drain)
Esegui il drain per spostare tutti gli altri pod (Lidarr, n8n, ecc.) su altri nodi:
```bash
kubectl drain <NOME_NODO> --ignore-daemonsets --delete-emptydir-data
```

## 4. Spegnimento Fisico
Ora puoi spegnere l'host o la VM in sicurezza.

## 5. Ritorno alla Normalità
Dopo aver riacceso il nodo e verificato che sia `Ready` in Kubernetes:
1.  **Uncordon**: `kubectl uncordon <NOME_NODO>`.
2.  **Ri-scala il database**: Riporta le istanze al numero originale (es. 3).

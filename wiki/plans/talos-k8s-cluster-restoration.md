# Piano: Ripristino Cluster Kubernetes Talos (Post-Proxmox Recovery)

> [!IMPORTANT]
> **PREREQUISITO ASSOLUTO**: Questo piano viene eseguito **SOLO** dopo il completamento integrale di:
> 1. `[[pve2-reinstallation-migration]]` — PVE2 con newPVE2 online, cluster Proxmox a 3 nodi in quorum.
> 2. `[[pve3-10g-migration-recovery]]` — PVE3 migrato su switch 10G, Proxmox 3 nodi allineati.
> 3. VM `talos-cp-02` (ID 2300) **ripristinata da PBS su PVE2** ma **non ancora avviata**.
>
> Non avviare talos-cp-02 finché il cluster Proxmox non è completamente stabile.

## Contesto Critico

### Stato pre-ripristino (documentato)
- `talos-cp-02` è stato **rimosso formalmente dal quorum etcd** il 2026-05-01 via `talosctl etcd remove-member` (vedi [[2026-05-01-network-asymmetry-incident]]).
- Il cluster K8s opera attualmente in modalità degradata con **2 CP** (`talos-cp-01` + `talos-cp-03`).
- Il database `postgres-main` (CloudNativePG) ha la replica `postgres-main-2` inaccessibile perché i suoi dati locali sono su `talos-cp-02`.

### Strategia di Reintegrazione

> [!NOTE]
> **Approccio scelto: Ripristino da PBS + Re-apply Config Talos**
>
> La VM `talos-cp-02` viene ripristinata da backup PBS (non reinstallazione da zero). Poiché il membro etcd è stato rimosso, **Talos non si auto-reintegra** al boot. Sarà necessario:
> 1. Avviare la VM e verificare il boot di Talos in modalità "maintenance" o con etcd in stato `learner`.
> 2. Riapplicare la configurazione dedicata `controlplane-cp-02.yaml` in modalità insecure per forzare il bootstrap fresh su disco.
> 3. Il Talos Etcd Manager degli altri nodi accetterà il nuovo membro automaticamente.

---

## Fase A: Verifica Pre-Kondizioni

### Step A.1: Verifica Cluster Proxmox (3 Nodi)

```bash
# Da Mac Studio
ssh root@10.10.10.11 "pvecm status && pvecm nodes"
```
**Risultato atteso**: `Quorum: 3`, tutti e 3 i nodi (pve, pve2, pve3) Online.

```bash
# Verifica VM 2300 presente su PVE2 ma ancora spenta
ssh root@10.10.10.21 "qm list"
```
**Risultato atteso**: VM 2300 (talos-cp-02) presente con stato `stopped`.

### Step A.2: Verifica Stato Cluster K8s Attuale (2 CP)

```bash
export TALOSCONFIG=talos-config/talosconfig
export KUBECONFIG=talos-config/kubeconfig

# Controlla i nodi K8s (ci aspettiamo cp-02 assente o NotReady)
kubectl get nodes -o wide

# Controlla etcd — ci aspettiamo solo 2 membri
talosctl -n 10.10.20.141 etcd members
```

**Risultato atteso**: 2 membri etcd attivi (`talos-cp-01`, `talos-cp-03`). `talos-cp-02` assente o NotReady.

```bash
# Verifica che i servizi critici funzionino (2 CP sono sufficienti per quorum etcd)
kubectl get pods -A | grep -v Running | grep -v Completed
```
**Nota**: Alcuni servizi che dipendono da `postgres-main` possono essere in CrashLoopBackOff — è previsto in questa fase.

---

## Fase B: Avvio e Bootstrap di talos-cp-02

### Step B.1: Avvio della VM su PVE2

```bash
ssh root@10.10.10.21 "qm start 2300"
```

**CHECK** — attendi 90 secondi per il boot di Talos:
```bash
ping -c 3 10.10.20.142
```

### Step B.2: Verifica Stato di Boot di Talos

```bash
# Tenta la connessione via talosctl (potrebbe essere in maintenance mode)
talosctl -n 10.10.20.142 version 2>/dev/null && echo "TALOS OK" || echo "In maintenance mode o non raggiungibile"
```

**Scenario A — Talos risponde normalmente**: procedi al Step B.3.
**Scenario B — Talos non risponde o è in maintenance**: procedi direttamente al Step B.4 (re-apply config).

### Step B.3: Verifica Se etcd si è Auto-Reintegrato

> [!NOTE]
> Se il backup PBS conteneva un'immagine recente del disco con state etcd intatto, Talos potrebbe tentare di rientrare nel cluster da solo. Verificare prima.

```bash
# Controlla i membri etcd — vedi se cp-02 è già visibile
talosctl -n 10.10.20.141 etcd members
```

**Se cp-02 è già presente e `Healthy`**: salta al Step B.5 (verifica K8s).
**Se cp-02 NON è presente o è in stato `unstarted`/`learner`**: procedi al Step B.4.

### Step B.4: Re-Apply Configurazione Talos (Modalità Insecure)

Questo step forza la reinstallazione del sistema Talos sul disco della VM (sovrascrive solo OS, non i dati K8s/PVC).

```bash
# Applica la configurazione specifica di CP02 in modalità insecure
talosctl apply-config \
  -n 10.10.20.142 \
  --file talos-config/controlplane-cp-02.yaml \
  --insecure
```

> [!IMPORTANT]
> `controlplane-cp-02.yaml` contiene l'hostname `talos-cp-02` hardcoded (Infrastructure as Code). Non usare `controlplane.yaml` generico.

**CHECK** — attendi 2-3 minuti per il riavvio e bootstrap:
```bash
# Aspetta che Talos sia raggiungibile
for i in {1..20}; do talosctl -n 10.10.20.142 version 2>/dev/null && break; sleep 10; done
```

### Step B.5: Verifica Reintegrazione etcd

```bash
# Attendi che il Talos Etcd Manager accetti il nuovo membro (fino a 5 min)
talosctl -n 10.10.20.141 etcd members
```

**Risultato atteso**: 3 membri (`talos-cp-01`, `talos-cp-02`, `talos-cp-03`) tutti `started` e `Healthy`.

> [!WARNING]
> Se dopo 5 minuti `talos-cp-02` non appare nei membri etcd, esegui il bootstrap manuale:
> ```bash
> talosctl -n 10.10.20.142 bootstrap
> ```
> Questo comando non deve essere eseguito se gli altri nodi etcd sono già attivi — verificare prima.

---

## Fase C: Verifica Kubernetes e Nodi

### Step C.1: Verifica Stato Nodi K8s

```bash
kubectl get nodes -o wide
```

**Risultato atteso**: Tutti e 3 i CP (`talos-cp-01`, `talos-cp-02`, `talos-cp-03`) in stato `Ready`.

```bash
# Controllo salute del nodo talos-cp-02
talosctl -n 10.10.20.142 health --wait-timeout 5m
```

### Step C.2: Verifica Pod di Sistema

```bash
# Tutti i pod di sistema devono essere Running
kubectl get pods -n kube-system -o wide
kubectl get pods -n talos-system -o wide 2>/dev/null || true
```

**Verifica specifica KubePrism** (la causa dell'incidente precedente):
```bash
# Verifica che KubePrism ora includa cp-02 come endpoint
talosctl -n 10.10.20.142 containers -k | grep kube-apiserver
```

---

## Fase D: Ripristino PostgreSQL CloudNativePG

> [!CAUTION]
> Esegui questo step solo dopo aver confermato che `talos-cp-02` è `Ready` in K8s (Step C.1).

### Step D.1: Verifica Stato Cluster PostgreSQL

```bash
kubectl get cluster postgres-main -n cnpg-system -o wide
kubectl get pods -n cnpg-system -o wide
kubectl get pvc -n cnpg-system
```

**Stato atteso pre-ripristino**:
- Cluster `postgres-main` in stato `Healthy` o `Degraded` (2/3 repliche).
- PVC `postgres-main-2` potrebbe risultare `Pending` (il nodo era offline).

### Step D.2: Rimozione Fencing (se presente)

Se il pod `postgres-main-2` è stato fenced durante la manutenzione:

```bash
# Controlla se ci sono fencing annotations
kubectl get pod postgres-main-2 -n cnpg-system -o jsonpath='{.metadata.annotations}' 2>/dev/null || echo "Pod non trovato"

# Se presente, rimuovi il fencing
kubectl annotate pod postgres-main-2 -n cnpg-system \
  cnpg.io/fencingOn- --overwrite 2>/dev/null || echo "Nessun fencing da rimuovere"
```

### Step D.3: Verifica Auto-Recovery CNPG

L'operatore CNPG dovrebbe rilevare automaticamente `talos-cp-02` e schedulare `postgres-main-2` su di esso.

```bash
# Attendi fino a 10 minuti per il recovery automatico
watch kubectl get pods -n cnpg-system -o wide
```

Se dopo 5 minuti `postgres-main-2` non si avvia:
```bash
# Controlla i log dell'operatore CNPG per capire il blocco
kubectl logs -n cnpg-system -l app.kubernetes.io/name=cloudnative-pg --tail=50
```

### Step D.4: Verifica PVC e StorageClass

```bash
# Verifica che il PVC per postgres-main-2 sia Bound
kubectl get pvc -n cnpg-system

# Verifica che la StorageClass local-postgres funzioni su cp-02
kubectl get storageclass
kubectl describe pvc -n cnpg-system | grep -A5 "Node Affinity"
```

**Risultato atteso**: PVC `postgres-main-2` in stato `Bound`, montato su `talos-cp-02`.

### Step D.5: Verifica Salute Finale del Cluster PostgreSQL

```bash
# Status completo del cluster CNPG
kubectl cnpg status postgres-main -n cnpg-system

# Oppure tramite kubectl
kubectl get cluster postgres-main -n cnpg-system
```

**Risultato atteso**: Cluster `postgres-main` in stato `Healthy` con `3/3` istanze attive.

---

## Fase E: Verifica Servizi Applicativi

### Step E.1: Verifica Pod in Errore

```bash
# Tutti i pod che non sono Running o Completed
kubectl get pods -A | grep -v -E "Running|Completed|Succeeded"
```

**Risultato atteso**: Nessun pod in `CrashLoopBackOff` o `Pending` a regime.

### Step E.2: Verifica Servizi Dipendenti da PostgreSQL

I servizi seguenti dipendono da `postgres-main` e potrebbero richiedere un riavvio dopo il ripristino del DB:

```bash
# n8n
kubectl get pods -n n8n
# Prefect
kubectl get pods -n prefect
# Lidarr (se usa pg)
kubectl get pods -n arr | grep -i lidarr
```

Se un servizio è ancora in errore dopo 5 minuti dal ripristino del DB:
```bash
# Forza il rollout restart per ricaricare la connessione
kubectl rollout restart deployment/<nome-deployment> -n <namespace>
```

### Step E.3: Test End-to-End

```bash
# Verifica raggiungibilità servizi web
curl -s -o /dev/null -w "%{http_code}" https://home.pindaroli.org
curl -s -o /dev/null -w "%{http_code}" https://grafana.internal.pindaroli.org
```

**Risultato atteso**: HTTP 200 o 302.

---

## Fase F: Aggiornamento Documentazione

- [ ] Aggiornare `wiki/entities/Talos_Cluster.md`: stato di tutti e 3 i nodi → `Ready`.
- [ ] Aggiornare `wiki/entities/Storage_Registry.md`: rimuovere nota DEGRADED su `postgres-main-2`.
- [ ] Aggiornare `rete.json`: status `talos-cp-02` da `OFFLINE` a operativo.
- [ ] Creare report di completamento in `wiki/incidents/` se ci sono stati problemi notevoli.

---

## Checklist di Accettazione Finale

| # | Test | Comando | Risultato Atteso |
|---|------|---------|-----------------|
| 1 | Proxmox quorum | `pvecm status` da PVE1 | 3 nodi, Quorum OK |
| 2 | talos-cp-02 raggiungibile | `ping -c 3 10.10.20.142` | 0% packet loss |
| 3 | K8s nodi Ready | `kubectl get nodes` | 3 × `Ready` |
| 4 | etcd 3 membri | `talosctl -n 10.10.20.141 etcd members` | 3 × `Healthy` |
| 5 | PostgreSQL Healthy | `kubectl get cluster postgres-main -n cnpg-system` | `Healthy` 3/3 |
| 6 | Nessun pod in errore | `kubectl get pods -A \| grep -v Running` | 0 CrashLoop |
| 7 | Servizi web | `curl -I https://home.pindaroli.org` | HTTP 200/302 |
| 8 | Grafana metriche | Accedi a Grafana, verifica target Prometheus | tutti i target Up |

---

## Dipendenze tra Piani

```
[[plan-out-of-band-service-access]]   → Infrastruttura OOB (COMPLETATO)
        ↓
[[pve2-reinstallation-migration]]     → PVE2 nuovo SSD, re-join cluster Proxmox
        ↓
[[pve3-10g-migration-recovery]]       → PVE3 migrazione 10G, Proxmox 3 nodi stabili
        ↓
[[talos-k8s-cluster-restoration]]     ← QUESTO PIANO (eseguire per ultimo)
```

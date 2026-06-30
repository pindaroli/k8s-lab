---
title: "Piano: Ripristino Cluster Kubernetes Talos (Post-Proxmox Recovery)"
type: plan
status: archived
certified_for_ai: false
created_at: 2026-06-27
tags:
  - "#plan"
  - "#network"
  - "#storage"
  - "#proxmox"
  - "#talos"
  - "#opnsense"
---

# Piano: Ripristino Cluster Kubernetes Talos (Post-Proxmox Recovery)

> [!IMPORTANT]
> **PREREQUISITO ASSOLUTO**: Questo piano viene eseguito **SOLO** dopo il completamento di:
> 1. `[[pve2-reinstallation-migration]]` — PVE2 (newPVE2) online e re-join al cluster Proxmox completato.
> 2. `[[pve3-10g-migration-recovery]]` — PVE3 migrato su switch 10G e re-join al cluster Proxmox completato.
> 3. Il cluster Proxmox deve essere fully operational con **3 nodi in quorum stabile** (`pve1`, `pve2`, `pve3`).
> 4. Il nodo master originale `pve` deve essere stato rinominato con successo in `pve1` (come da [[pve1-hostname-rename]]).
> 5. La VM `talos-cp-02` (ID 2300) deve essere stata ripristinata da PBS su `pve2` (per recuperare la definizione hardware e il MAC address) ma **non ancora avviata**.

## Contesto Critico

### Stato pre-ripristino (documentato)
- `talos-cp-02` è stato **rimosso formalmente dal quorum etcd** il 2026-05-01 via `talosctl etcd remove-member` (vedi [[2026-05-01-network-asymmetry-incident]]).
- Il cluster K8s opera attualmente in modalità degradata con **2 CP** (`talos-cp-01` + `talos-cp-03`).
- Il database `postgres-main` (CloudNativePG) ha la replica `postgres-main-2` inaccessibile perché i suoi dati locali sono su `talos-cp-02`.
- **Stato File Configurazione (Symmetric Routing)**: Le modifiche ai file di configurazione locali (`controlplane-cp-01.yaml`, `controlplane-cp-02.yaml`, `controlplane-cp-03.yaml`) sono state completate al 100% nel repository locale impostando il DNS su `192.168.2.254`. Anche il file `talosconfig` è stato aggiornato per includere nuovamente `10.10.20.142` (talos-cp-02) negli endpoint e nei nodi.

### Strategia di Reintegrazione

> [!NOTE]
> **Approccio scelto: Ripristino Hardware VM da PBS + Installazione Pulita via ISO**
>
> Per evitare conflitti con il vecchio database etcd locale e garantire una reintegrazione pulita di `talos-cp-02`:
> 1. Si ripristina la VM da PBS per recuperare la definizione dell'hardware (in particolare il MAC address, necessario per l'IP statico `10.10.20.142` da OPNsense).
> 2. Prima dell'avvio, si monta l'ISO di Talos (`talos-amd64.iso`) nella VM e si avvia in RAM (modalità insecure).
> 3. Si applica la configurazione `controlplane-cp-02.yaml` con `--insecure` per formattare il disco virtuale e installare l'OS fresco.
> 4. Il Talos Etcd Manager degli altri nodi accetterà il nuovo membro pulito automaticamente.
> 5. CloudNativePG sincronizzerà la replica database via rete su un nuovo volume locale pulito senza alcuna perdita di dati.

---

## Fase A: Verifica Pre-Kondizioni

### Step A.1: Verifica Cluster Proxmox (3 Nodi in Quorum)

```bash
# Da Mac Studio, verifica lo stato di Corosync e dei membri del cluster Proxmox
ssh root@10.10.10.11 "pvecm status && pvecm nodes"
```
**Risultato atteso**:
- `Quorum: 3` (o `Quorum acquired`)
- Elenco nodi online che mostra esattamente: `pve1` (`10.10.10.11`), `pve2` (`10.10.10.21`), `pve3` (`10.10.10.31`).

```bash
# Verifica che la VM 2300 sia presente su pve2 ma ancora spenta
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

## Fase B: Avvio, Boot da ISO e Installazione Pulita di talos-cp-02

### Step B.1: Configurazione Lettore CD virtuale e Avvio da ISO su pve2

1. Accedi alla Web UI di `pve2` (`https://10.10.10.21:8006`) o via terminale.
2. Assicurati che l'ISO di Talos (`talos-amd64.iso`) sia caricata sullo storage locale.
3. Associa l'ISO al lettore CD della VM `2300`:
   ```bash
   ssh root@10.10.10.21 "qm set 2300 --cdrom local:iso/talos-amd64.iso"
   ```
4. Imposta l'ordine di boot per dare priorità al lettore CD (per il primo avvio):
   ```bash
   ssh root@10.10.10.21 "qm set 2300 --boot order=cdn"
   ```
5. Avvia la VM `2300`:
   ```bash
   ssh root@10.10.10.21 "qm start 2300"
   ```

**CHECK** — attendi 90 secondi per il boot di Talos in RAM:
```bash
ping -c 3 10.10.20.142
```

### Step B.2: Verifica Connettività Installer Insecure

```bash
# Talos in modalità installazione deve rispondere alla porta API in modalità insecure
talosctl -n 10.10.20.142 version --insecure
```
**Risultato atteso**: Output con la versione di Talos in esecuzione in RAM.

### Step B.3: Applicazione Configurazione (Installazione Pulita su Disco)

Questo step esegue l'installazione pulita di Talos sul disco virtuale della VM.

```bash
# Invia la configurazione specifica di CP02 via interfaccia insecure
talosctl apply-config \
  -n 10.10.20.142 \
  --file talos-config/controlplane-cp-02.yaml \
  --insecure
```

> [!IMPORTANT]
> `controlplane-cp-02.yaml` contiene l'hostname `talos-cp-02` hardcoded. Non utilizzare `controlplane.yaml` generico.

**CHECK** — Attendi 2-3 minuti per la scrittura su disco, il riavvio automatico e il bootstrap:
```bash
# Attendi che Talos riparta dal disco locale e la sua API sia raggiungibile con configurazione cifrata
for i in {1..20}; do talosctl -n 10.10.20.142 version 2>/dev/null && break; sleep 10; done
```

### Step B.4: Rimozione ISO e Ripristino Ordine Boot

Per evitare che la VM parta nuovamente da CD in caso di riavvii futuri, scolleghiamo l'ISO.

```bash
# Rimuovi l'ISO dal lettore virtuale
ssh root@10.10.10.21 "qm set 2300 --ide2 none,media=cdrom"
# Ripristina l'ordine di boot standard (es. disk prima)
ssh root@10.10.10.21 "qm set 2300 --boot order=disk"
```

### Step B.5: Verifica Reintegrazione nel Quorum etcd

L'Etcd Manager di Talos sui due nodi attivi (`talos-cp-01` e `talos-cp-03`) deve accettare automaticamente il nuovo nodo pulito.

```bash
# Controlla lo stato dei membri etcd dal Mac Studio
talosctl -n 10.10.20.141 etcd members
```

**Risultato atteso**: 3 membri (`talos-cp-01`, `talos-cp-02`, `talos-cp-03`) tutti `started` e `Healthy`.

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

### Step C.3: Allineamento DNS (Symmetric Routing) su talos-cp-01 e talos-cp-03

Poiché le modifiche ai file di configurazione locali sono state completate per tutte e 3 le VM Talos, andiamo ad allineare a caldo i nodi attivi per finalizzare la transizione al Symmetric Routing.

```bash
# Applica la configurazione DNS aggiornata a talos-cp-01 (a caldo)
talosctl apply-config -n 10.10.20.141 -f talos-config/controlplane-cp-01.yaml

# Applica la configurazione DNS aggiornata a talos-cp-03 (a caldo)
talosctl apply-config -n 10.10.20.143 -f talos-config/controlplane-cp-03.yaml
```

**Verifica della corretta risoluzione DNS sui nodi**:
```bash
# Verifica la risoluzione DNS nei file dei nodi
talosctl read /etc/resolv.conf -n 10.10.20.141
talosctl read /etc/resolv.conf -n 10.10.20.143
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
| 1 | Proxmox quorum | `pvecm status` da `pve1` | 3 nodi (`pve1`, `pve2`, `pve3`) online, Quorum OK |
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
[[pve2-reinstallation-migration]]     → PVE2 nuovo SSD, ripristino VM talos-cp-02 (COMPLETATO)
        ↓
[[pve3-10g-migration-recovery]]       → PVE3 migrazione 10G (COMPLETATO)
        ↓
[[pve1-hostname-rename]]              → Rinomina Hostname PVE1 (COMPLETATO)
        ↓
[[talos-k8s-cluster-restoration]]     ← QUESTO PIANO (Fase Attiva)
```

---

## 💾 Stato di Ripristino (AI Save-State)
- **Fase Attiva**: COMPLETATO
- **Ultima Azione Completata**: Ripristino completo del quorum etcd, accensione nodi CP, allineamento DNS a caldo e scaling del database CNPG a 3 repliche completato con successo.
- **Prossimo Passo Operativo**: Nessuno. Tutti gli step del piano sono stati completati con successo ed il cluster è in salute.
- **Blocchi/Decisioni Pendenti**: Nessuno.

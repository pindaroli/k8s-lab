---
status: active
certified_for_ai: true
---
# Piano Operativo Ingegneristico: Aggiornamento Rolling del Control Plane Kubernetes (v1.34.1 -> v1.36.2) su Talos Linux v1.13.5

L'obiettivo strategico del presente piano è la migrazione sicura del piano di controllo e del data plane del cluster Kubernetes dalla versione **v1.34.1** alla versione stabile **v1.36.2**. 

L'operazione è vincolata dalla *API Skew Policy* di Kubernetes, che vieta il salto di versioni minori durante l'aggiornamento. Di conseguenza, l'avanzamento avverrà in due fasi sequenziali:
1. **Fase 1**: Aggiornamento a **v1.35.5** (versione intermedia stabile).
2. **Fase 2**: Aggiornamento a **v1.36.2** (versione target finale).

---

## 1. Analisi di Compatibilità e Vincoli Architetturali

### 1.1. Cgroup v2 e compatibilità OS
Kubernetes v1.35 rimuove definitivamente il supporto per i cgroup v1. Poiché Talos Linux v1.13.5 adotta nativamente i cgroup v2 come standard predefinito, non si registrano rischi di blocco per il demone `kubelet`.

### 1.2. Deprecazione di `Service.spec.externalIPs`
In Kubernetes v1.36 inizia la deprecazione del campo `.spec.externalIPs` (CVE-2020-8554). Nel nostro cluster, l'assegnazione degli IP per i servizi esposti avviene tramite **MetalLB** (che scrive in `.status.loadBalancer.ingress` via RBAC). Pertanto, la rete locale risulta del tutto immune da questa deprecazione.

### 1.3. Blocco Incompatibilità: Cert-Manager
L'attuale installazione di **Cert-Manager** (`v1.13.3`) è deprecata e incompatibile con Kubernetes 1.35/1.36. Prima di iniziare l'upgrade di Kubernetes, è **tassativo** effettuare l'upgrade di Cert-Manager alla versione **v1.19.1** (LTS) via Helm, includendo l'aggiornamento delle Custom Resource Definitions (CRD).

### 1.4. Resilienza Storage Locale (CloudNativePG)
Il database PostgreSQL (`postgres-main` in namespace `cnpg-system`) utilizza storage locale su `/dev/sdb1` (montato in `/var/mnt/postgres`). Durante l'upgrade del kubelet su ciascun nodo, il container runtime locale verrà riavviato. L'operatore CNPG gestirà questo comportamento tramite elezione del leader (Lease): il pod Primario verrà temporaneamente disconnesso, e una delle repliche attive e in sync verrà istantaneamente promossa a nuovo Primario per garantire lo zero-downtime.

---

## 2. Fase 0: Preparazione e Pre-requisiti (Pre-flight)

### 2.1. Aggiornamento Cert-Manager (Prerequisito Bloccante)
```bash
helm repo update
helm upgrade cert-manager jetstack/cert-manager \
  --namespace cert-manager \
  --version v1.19.1 \
  --set installCRDs=true \
  --wait
```
*Verifica*: Assicurarsi che i pod di Cert-Manager siano tutti in stato `Running`.

### 2.2. Backup di Sicurezza (etcd & Velero)
1. Connettersi via CLI e lanciare lo snapshot di etcd:
   ```bash
   talosctl --nodes 10.10.20.141 etcd snapshot pre-134-upgrade.snapshot
   ```
2. Generare un backup Velero comprensivo di tutti i namespace applicativi critici:
   ```bash
   velero backup create pre-k8s-upgrade-backup --include-namespaces=cnpg-system,arr,n8n --wait
   ```
3. Verificare lo stato di salute di CNPG prima di procedere:
   ```bash
   kubectl cnpg status postgres-main -n cnpg-system
   ```

---

## 3. Fase 1: Aggiornamento a Kubernetes v1.35.5

### 3.1. Esecuzione Dry-run (Simulazione)
```bash
talosctl --nodes 10.10.20.141 upgrade-k8s --to 1.35.5 --dry-run
```

### 3.2. Aggiornamento Reale
```bash
talosctl --nodes 10.10.20.141 upgrade-k8s --to 1.35.5
```
*Nota*: Durante l'aggiornamento del kube-apiserver, la connessione `kubectl` andrà momentaneamente in timeout. È un comportamento atteso.

### 3.3. Convalida Post-Fase 1
```bash
# 1. Verifica versione nodi
kubectl get nodes -o wide

# 2. Verifica pod di sistema (Flannel, custom CoreDNS)
kubectl get pods -n kube-system
kubectl get pods -n kube-flannel

# 3. Verifica stato di salute CNPG
kubectl cnpg status postgres-main -n cnpg-system
```

---

## 4. Fase 2: Aggiornamento a Kubernetes v1.36.2

### 4.1. Snapshot Intermedio (etcd)
```bash
talosctl --nodes 10.10.20.141 etcd snapshot post-135-stable.snapshot
```

### 4.2. Esecuzione Dry-run
```bash
talosctl --nodes 10.10.20.141 upgrade-k8s --to 1.36.2 --dry-run
```

### 4.3. Aggiornamento Reale
```bash
talosctl --nodes 10.10.20.141 upgrade-k8s --to 1.36.2
```

### 4.4. Convalida Post-Fase 2
```bash
# 1. Nodi in Ready su v1.36.2
kubectl get nodes -o wide

# 2. Test Risoluzione DNS CoreDNS personalizzato verso OPNsense
kubectl run -i --tty --rm debug-dns --image=alpine --restart=Never -- sh -c "nslookup kubernetes.default.svc.cluster.local && nslookup www.google.com"

# 3. Stato CNPG
kubectl cnpg status postgres-main -n cnpg-system
```

---

## 5. Strategia di Disaster Recovery / Rollback

Il rollback diretto del control-plane non è supportato da Kubernetes. In caso di corruzione o guasto irreversibile, si procederà con il ripristino da snapshot etcd:

1. **Wipe Ephemeral**: Eseguire il wipe della partizione ephemeral su tutti i nodi:
   ```bash
   talosctl --nodes 10.10.20.141,10.10.20.142,10.10.20.143 reset --graceful=false --reboot --system-labels-to-wipe=EPHEMERAL
   ```
2. **Restore Bootstrap**: Innescare il bootstrap a partire dallo snapshot etcd precedentemente salvato in locale:
   ```bash
   talosctl --nodes 10.10.20.141 bootstrap --recover-from=./pre-134-upgrade.snapshot
   ```
3. **Restart Kubelet**: Forzare il riavvio del kubelet su tutti i nodi:
   ```bash
   talosctl --nodes 10.10.20.141,10.10.20.142,10.10.20.143 service kubelet restart
   ```

---

## 💾 Stato di Ripristino (AI Save-State)
- **Fase Attiva**: [x] COMPLETATO - Aggiornamento Cluster K8s a v1.36.2
- **Ultima Azione Completata**: Aggiornamento a Kubernetes v1.36.2 e verifiche globali superate con successo (nodi Ready, DNS custom e CNPG sani).
- **Prossimo Passo Operativo**: Nessuno. Il piano di upgrade è completamente chiuso con successo.
- **Blocchi/Decisioni Pendenti**: Nessuno.

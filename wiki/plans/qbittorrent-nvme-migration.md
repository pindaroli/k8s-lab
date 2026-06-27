---
title: "Piano: Migrazione qBittorrent Incomplete su NVMe"
type: plan
status: archived
certified_for_ai: false
created_at: 2026-06-27
archived_at: 2026-06-27
---

# Piano di Migrazione: qBittorrent Temporary Storage (HDD -> NVMe)

L'obiettivo è spostare i download incompleti dal pool meccanico `oliraid` allo stripe NVMe `stripe` per migliorare le IOPS, ridurre il carico sui dischi durante il seeding/download contemporaneo e massimizzare il throughput del network lab.

---

## 1. Preparazione Storage & Ottimizzazioni ZFS
*   [x] **Creazione Dataset su TrueNAS**: Dataset ZFS `stripe/qb_temp` creato via Ansible.
*   [x] **Rettifica Namespace PVC**: Corretta l'incongruenza in `storage/incomplete-dw-pvc.yaml` impostando `namespace: arr` (allineato con il pod qBittorrent).
*   [x] **Ottimizzazione ZFS NVMe (Valori Raccomandati)**:
    *   **Recordsize**: **`1M`** (ZFS gestisce dinamicamente i file piccoli, mentre i moderni client come libtorrent accumulano i blocchi da 16KiB in buffer di memoria e li scrivono sequenzialmente pari alla dimensione del "piece". Impostare 16k aumenterebbe a dismisura i metadati dell'ARC e frammenterebbe lo spazio libero).
    *   **Sync**: **`disabled`** (Massimizza il throughput di scrittura su NVMe eliminando le latenze di fsync; in caso di crash la coerenza del filesystem è preservata dalla natura Copy-on-Write di ZFS, mentre qBittorrent si limiterà ad eseguire un hash check dei soli blocchi persi negli ultimi 5 secondi).
    *   **Atime**: **`off`** (Elimina le riscritture di metadati associate alla sola lettura dei blocchi in fase di seeding).
    *   **Compression**: **`lz4`** (Overhead CPU irrilevante, garantisce risparmio di spazio sui blocchi adiacenti).

---

## 2. Playbook Operativo (Fasi di Esecuzione)

### Fase 1: Congelamento e Messa in Sicurezza del Cluster
Per evitare scritture concorrenti o inconsistenze nei database SQLite dei Servarr (Connection Refused / Retry infiniti / anomalie di importazione), viene sospeso l'intero namespace `arr`:
1.  Sospendere temporaneamente la riconciliazione automatica del controller GitOps (Flux CD / Argo CD) per impedire il ripristino automatico dei pod.
2.  Arrestare tutti i pod del namespace `arr`:
    ```bash
    KUBECONFIG=talos-config/kubeconfig kubectl scale deployment -n arr --all --replicas=0
    ```
3.  Verificare la completa terminazione di tutti i pod (nessun lock NFS attivo su TrueNAS):
    ```bash
    KUBECONFIG=talos-config/kubeconfig kubectl get pods -n arr
    ```

### Fase 2: Configurazione Dataset & Abilitazione Share NFS (TrueNAS SCALE)
Connettersi via SSH a TrueNAS (`10.10.10.50`) ed impostare sia le proprietà ottimali del dataset ZFS sia l'esportazione NFSv4.2 via API:
```bash
ssh olindo@10.10.10.50

# 1. Applicazione proprietà ZFS (usando sudo per l'utente olindo)
sudo zfs set recordsize=1M stripe/qb_temp
sudo zfs set sync=disabled stripe/qb_temp
sudo zfs set atime=off stripe/qb_temp
sudo zfs set compression=lz4 stripe/qb_temp

# 2. Creazione dell'esportazione NFS via API TrueNAS (midclt) con Maproot: root e subnet abilitata
sudo midclt call sharing.nfs.create '{"path": "/mnt/stripe/qb_temp", "comment": "qBittorrent Incomplete Downloads ZFS stripe", "networks": ["10.10.10.0/24"], "hosts": ["10.10.20.141", "10.10.20.142", "10.10.20.143", "10.10.20.100"], "ro": false, "maproot_user": "root", "maproot_group": "wheel", "enabled": true}'

# 3. Riavvio/Ricaricamento del servizio NFS per propagare la nuova share
sudo midclt call service.restart "nfs"
```
*Nota: Questa configurazione garantisce il mount NFSv4.2 ad alta prestazione e con i giusti permessi amministrativi per il cluster Talos.*

### Fase 3: Migrazione Fisica dei Dati a Livello Server
- [ ] **Migrazione Fisica dei Dati (SSH su TrueNAS)**: Connettersi via SSH a TrueNAS (`10.10.10.50`) utilizzando l'utente `olindo` ed eseguire il trasferimento resiliente con privilegi elevati (`sudo`):
  ```bash
  ssh olindo@10.10.10.50

  # 1. Copia resiliente del contenuto da HDD a NVMe (usando sudo per preservare gli owner)
  sudo rsync -aHAXxv --numeric-ids --progress /mnt/oliraid/arrdata/media/downloads/incomplete/ /mnt/stripe/qb_temp/

  # 2. Allineamento proprietario e permessi per UID/GID 1000
  sudo chown -R 1000:1000 /mnt/stripe/qb_temp
  sudo chmod -R 775 /mnt/stripe/qb_temp
  ```

### Fase 4: Patching Automatico a Freddo di `qBittorrent.conf`
Per superare i limiti di permessi riscontrati sui mount NFS locali di macOS (mappatura `nobody`), applichiamo il patching in-place direttamente sul server TrueNAS (`10.10.10.50`) via SSH con l'utente `olindo` e `sudo`. Questo assicura permessi di scrittura assoluti sul file di configurazione senza dover accedere alla WebUI.

- [ ] **Esecuzione Patching via SSH (TrueNAS)**:
  Eseguire la copia di backup di sicurezza ed applicare le 4 modifiche mirate via `sed` (sintassi GNU sed nativa su TrueNAS):
  ```bash
  ssh olindo@10.10.10.50

  # 1. Copia di backup preventiva
  sudo cp /mnt/stripe/k8s-arr/servarr-qbittorrent/qBittorrent/qBittorrent.conf /mnt/stripe/k8s-arr/servarr-qbittorrent/qBittorrent/qBittorrent.conf.bak

  # 2. Aggiornamento TempPath nella sessione BitTorrent
  sudo sed -i 's|Session\\\\TempPath=.*|Session\\\\TempPath=/data/incomplete|' /mnt/stripe/k8s-arr/servarr-qbittorrent/qBittorrent/qBittorrent.conf

  # 3. Aggiornamento/Abilitazione TempPathEnabled della sessione
  sudo sed -i 's|Session\\\\TempPathEnabled=.*|Session\\\\TempPathEnabled=true|' /mnt/stripe/k8s-arr/servarr-qbittorrent/qBittorrent/qBittorrent.conf

  # 4. Aggiornamento TempPath nelle preferenze Download
  sudo sed -i 's|Downloads\\\\TempPath=.*|Downloads\\\\TempPath=/data/incomplete/|' /mnt/stripe/k8s-arr/servarr-qbittorrent/qBittorrent/qBittorrent.conf

  # 5. Inserimento di Downloads\TempPathEnabled (se non esistente, viene accodato sotto [Preferences])
  sudo grep -qF 'Downloads\\TempPathEnabled' /mnt/stripe/k8s-arr/servarr-qbittorrent/qBittorrent/qBittorrent.conf || sudo sed -i '/^\[Preferences\]/a Downloads\\\\TempPathEnabled=true' /mnt/stripe/k8s-arr/servarr-qbittorrent/qBittorrent/qBittorrent.conf
  ```

- [ ] **Test di Verifica (Live Config)**:
  Controllare che le sole righe modificate corrispondano allo standard Qt atteso da qBittorrent:
  ```bash
  ssh olindo@10.10.10.50 "sudo cat /mnt/stripe/k8s-arr/servarr-qbittorrent/qBittorrent/qBittorrent.conf | grep -E 'TempPath'"
  ```

### Fase 5: Provisioning Risorse K8s & Tuning Helm
1.  **Applicare il Manifest PVC Ottimizzato (NFSv4.2)**:
    Il manifest [storage/incomplete-dw-pvc.yaml](file:///Users/olindo/prj/k8s-lab/storage/incomplete-dw-pvc.yaml) deve includere parametri ad alte prestazioni per mitigare l'overhead dell'I/O cross-volume (`EXDEV` tra pool diversi):
    ```yaml
    # storage/incomplete-dw-pvc.yaml
    apiVersion: v1
    kind: PersistentVolume
    metadata:
      name: pv-incomplete-dw
    spec:
      capacity:
        storage: 500Gi
      accessModes:
        - ReadWriteMany
      persistentVolumeReclaimPolicy: Retain
      nfs:
        server: 10.10.10.50
        path: /mnt/stripe/qb_temp
      mountOptions:
        - nfsvers=4.2
        - rsize=1048576
        - wsize=1048576
        - hard
        - timeo=600
        - retrans=3
        - noresvport
    ---
    apiVersion: v1
    kind: PersistentVolumeClaim
    metadata:
      name: pvc-incomplete-dw
      namespace: arr
    spec:
      accessModes:
        - ReadWriteMany
      resources:
        requests:
          storage: 500Gi
      volumeName: pv-incomplete-dw
    ```
    Applicare il file:
    ```bash
    KUBECONFIG=talos-config/kubeconfig kubectl apply -f storage/incomplete-dw-pvc.yaml
    ```

2.  **Tuning I/O libtorrent (`arr-values.yaml`)**:
    Modificare `servarr/arr-values.yaml` per disabilitare la OS Cache di Linux sul nodo Kubernetes, limitando drasticamente i picchi di I/O Wait e l'accumulo di "dirty pages" in RAM durante i completamenti di massa (spostamenti cross-volume):
    ```yaml
    # Aggiungere o unire in servarr/arr-values.yaml sotto qbittorrent:
    qbittorrent:
      persistence:
        incomplete:
          enabled: true
          type: pvc
          existingClaim: pvc-incomplete-dw
          mountPath: /data/incomplete
      # Ottimizzazione I/O interna per bypassare la Page Cache dell'host
      qbittorrentConf:
        enabled: true
        entries:
          BitTorrent:
            Session\DiskIOType: "Posix"
            Session\DiskIOReadMode: "DisableOSCache"
            Session\DiskIOWriteMode: "DisableOSCache"
            Session\MaxActiveCheckingTorrents: "1"
    ```

3.  **Helm Upgrade**:
    ```bash
    helm upgrade servarr pindaroli/servarr -n arr -f servarr/arr-values.yaml
    ```

### Fase 6: Verifica Funzionale e Ripristino Stack
1.  **Avvio qBittorrent**:
    ```bash
    KUBECONFIG=talos-config/kubeconfig kubectl scale deployment -n arr servarr-qbittorrent --replicas=1
    ```
2.  **Verifica Mount & Parametri NFSv4.2**:
    ```bash
    KUBECONFIG=talos-config/kubeconfig kubectl exec -it -n arr deploy/servarr-qbittorrent -c servarr -- df -h /data/incomplete
    KUBECONFIG=talos-config/kubeconfig kubectl exec -it -n arr deploy/servarr-qbittorrent -c servarr -- mount | grep /data/incomplete
    ```
3.  **Ripristino della suite Servarr**:
    ```bash
    KUBECONFIG=talos-config/kubeconfig kubectl scale deployment -n arr servarr-sonarr servarr-radarr servarr-lidarr --replicas=1
    ```
4.  **Riattivare GitOps**: Riabilitare la riconciliazione automatica di Flux/Argo CD.
5.  **Parcheggio e Backup Vecchia Directory**: Una volta confermata la stabilità dei download sul nuovo NVMe, non elimineremo i vecchi file temporanei ma li conserveremo in sicurezza rinominando atomicamente la directory sul pool HDD (operazione istantanea di rename dell'inode):
    ```bash
    ssh olindo@10.10.10.50 "sudo mv /mnt/oliraid/arrdata/media/downloads/incomplete /mnt/oliraid/arrdata/media/downloads/incomplete_backup && sudo mkdir -p /mnt/oliraid/arrdata/media/downloads/incomplete && sudo chown 1000:1000 /mnt/oliraid/arrdata/media/downloads/incomplete"
    ```

---

## 🛡️ Guardrail & Rischi
*   **Errore EXDEV (Spostamento Cross-Pool)**: Poiché le due share `/data/incomplete` (NVMe) e `/media/downloads` (HDD) appartengono a pool fisici diversi, lo spostamento finale del file non sarà un rename istantaneo a livello di inode, ma comporterà una copia fisica guidata dal client (NFSv4.2 Server-Side Copy non può operare tra pool ZFS distinti). Le impostazioni `DisableOSCache` e le opzioni NFS rsize/wsize a 1M evitano che questo traffico saturi la CPU del nodo o congeli l'host.
*   **Integrità Database SQLite**: Lo scale-down preventivo di Sonarr/Radarr/Lidarr elimina ogni potenziale race condition o scrittura corrotta nei database SQLite locali dovuto all'interruzione momentanea del client torrent.

# Piano di Aggiornamento TrueNAS SCALE a 25.10.4

Questo piano descrive i passaggi operativi per aggiornare l'appliance di storage **TrueNAS SCALE** (VMID 1100 su PVE1) dalla versione **25.10.3.1 (Goldeye)** alla versione **25.10.4**, gestendo in sicurezza le dipendenze hardware (PCI passthrough) e applicative (cluster Kubernetes/Talos Linux).

---

## 🚨 Punti Critici e Mitigazioni

> [!IMPORTANT]
> **1. Regressione driver `virtio-scsi` (TrueNAS SCALE 25.10.4)**
> Il kernel `6.12.91` introdotto in questa versione presenta una regressione nota in ambiente QEMU/KVM: il modulo `virtio-scsi` non viene caricato nella fase iniziale di boot (`initramfs`). Di conseguenza, la VM non riesce a importare il `boot-pool` da 50 GB (su disco virtuale `scsi0`) e cade in una shell di emergenza con l'errore:
> `cannot import 'boot-pool': no such pool available`.
> **Mitigazione**: Prima di avviare il riavvio per l'aggiornamento, inietteremo permanentemente il parametro kernel `modules_load=virtio-scsi` tramite il middleware di TrueNAS.

> [!WARNING]
> **2. Rallentamenti e Blocchi UEFI con PCI Passthrough (Option ROMs)**
> I tre controller LSI HBA fisici passati in passthrough alla VM (`03:00`, `04:00`, `05:00.0`) possono tentare di caricare il proprio firmware BIOS/UEFI durante la fase di POST virtuale, causando rallentamenti o blocchi infiniti.
> **Mitigazione**: Disabiliteremo il parametro `rombar` (`rombar=0`) nella configurazione PCI passthrough di Proxmox per impedire l'esposizione delle Option ROM fisiche.

> [!IMPORTANT]
> **3. Gestione del Downtime dello Storage (Cluster Kubernetes)**
> TrueNAS eroga storage NFS/SMB critico (tramite l'IP veloce `10.10.20.50` sulla VLAN 20 e `10.10.10.50` sulla VLAN 10). Lo spegnimento di TrueNAS causerà errori di tipo *Stale File Handle* (`ESTALE`) e filesystem in sola lettura sui nodi Kubernetes.
> **Mitigazione**: Spegneremo in modo ordinato il cluster Kubernetes (prima i nodi worker tramite `talosctl`, poi il control plane `talos-cp-01` VM 1300) prima di procedere all'aggiornamento.

> [!CAUTION]
> **4. Aggiornamento dei ZFS Feature Flags**
> L'aggiornamento del sistema operativo introduce OpenZFS 2.3.4, che suggerirà l'aggiornamento dei feature flags sui pool di dati.
> **Mitigazione**: **È TASSATIVAMENTE VIETATO aggiornare i Feature Flags dei pool dati**. L'operazione è irreversibile e impedirebbe sia il rollback di TrueNAS sia l'importazione di emergenza del pool direttamente sull'host Proxmox o in scenari di Disaster Recovery.

---

## 📋 Fasi Esecutive del Piano

### FASE 1: Salvataggio Configurazioni e Backup Coerente (Modalità Stop)

1. **Backup configurazione TrueNAS**:
   - Accedere alla Web GUI di TrueNAS -> *System Settings* -> *General* -> *Manage Configuration* -> *Download File*.
   - Selezionare l'opzione **Export Password Secret Seed** per includere le chiavi di decodifica simmetrica.
2. **Esportazione delle chiavi ZFS**:
   - Per ogni pool/dataset ZFS criptato, andare su *Datasets* -> *ZFS Encryption* -> *Export All Keys* e salvare il file JSON.
3. **Backup a freddo della VM 1100 su Proxmox Backup Server (PBS)**:
   - Poiché la VM ha schede PCI in passthrough, gli snapshot a caldo con RAM non sono affidabili.
   - Avviare il backup manuale impostando la modalità su **Stop**:
     ```bash
     velero backup create backup-truenas-pre-upgrade-$(date +%F) --wait # Se integrato, oppure procedere via GUI Proxmox / CLI Proxmox Backup
     ```
     O via CLI di Proxmox:
     ```bash
     vzdump 1100 --mode stop --storage pbs --compress zstd
     ```

### FASE 2: Spegnimento Ordinato del Cluster Kubernetes (Talos)

1. **Cordon e Drain dei nodi Worker**:
   ```bash
   kubectl cordon <nome-worker>
   kubectl drain <nome-worker> --ignore-daemonsets --delete-emptydir-data --grace-period=120 --timeout=300s
   ```
2. **Shutdown dei nodi Worker**:
   ```bash
   talosctl shutdown --nodes <IP-worker> --endpoints <IP-worker>
   ```
3. **Verifica dello stato di etcd e Spegnimento Control Plane (`VM 1300`)**:
   - Controllare la salute di etcd:
     ```bash
     talosctl etcd members --nodes 10.10.20.1300 --endpoints 10.10.20.1300
     ```
   - Eseguire il drain ed il shutdown di `talos-cp-01` (VM 1300):
     ```bash
     kubectl drain talos-cp-01 --ignore-daemonsets --delete-emptydir-data --timeout=300s
     talosctl shutdown --nodes 10.10.20.1300 --endpoints 10.10.20.1300
     ```
   - Verificare su Proxmox che la VM 1300 sia in stato `stopped`.

### FASE 3: Interventi Preventivi di Configurazione

1. **Iniezione del modulo kernel `virtio-scsi` su TrueNAS**:
   - Accedere via SSH a TrueNAS (`10.10.10.50`) ed eseguire il comando del middleware:
     ```bash
     midclt call system.advanced.update '{"kernel_extra_options": "modules_load=virtio-scsi"}'
     ```
   - Verificare che l'opzione sia registrata correttamente.
2. **Disattivazione Option ROM (ROM-Bar) su Proxmox**:
   - Accedere via SSH a PVE1 (`10.10.10.11`) e modificare il file `/etc/pve/qemu-server/1100.conf`.
   - Modificare le righe `hostpciX` aggiungendo il parametro `,rombar=0`. Ad esempio:
     ```text
     hostpci0: 0000:03:00,rombar=0
     hostpci1: 0000:04:00,rombar=0
     hostpci2: 0000:05:00.0,rombar=0
     ```

### FASE 4: Esecuzione dell'Aggiornamento TrueNAS

1. Accedere alla Web GUI di TrueNAS SCALE -> *System Settings* -> *Update*.
2. Selezionare **Check for Updates**, scaricare ed applicare la release **25.10.4**.
3. Confermare la creazione del nuovo Boot Environment ed avviare l'installazione. La VM si riavvierà.
4. Monitorare il boot tramite la console NoVNC su Proxmox per verificare che la VM superi la fase di POST UEFI in pochi secondi ed esegua correttamente l'importazione del `boot-pool` ZFS.

### FASE 5: Validazione Post-Upgrade e Accensione Ordinata

1. **Verifiche su TrueNAS**:
   - Accedere via SSH a TrueNAS (`10.10.10.50`).
   - Verificare che le interfacce `ens18` (VLAN 10) e `ens19` (VLAN 20) siano attive con gli IP corretti (`10.10.10.50` e `10.10.20.50`):
     ```bash
     ip addr show ens18
     ip addr show ens19
     ```
   - Verificare lo stato dei pool ZFS (che devono essere in stato `ONLINE` senza aggiornare i feature flags):
     ```bash
     zpool status
     ```
   - Verificare l'ascolto delle porte SMB (445) e NFS (2049):
     ```bash
     ss -tlnp | grep -E '2049|445'
     ```
2. **Avvio dei nodi Kubernetes**:
   - Avviare la VM 1300 (`talos-cp-01`) da Proxmox.
   - Verificare che i nodi del Control Plane tornino online e nello stato `Ready`:
     ```bash
     kubectl get nodes
     ```
   - Avviare le VM dei nodi worker su Proxmox.
   - Rimettere in servizio i nodi worker:
     ```bash
     kubectl uncordon <nome-worker>
     ```
   - Monitorare che i pod che consumano i volumi NFS si riavviino regolarmente senza errori di montaggio.

---

## ↩️ Piano di Rollback di Emergenza

### Caso A: Mancato avvio della VM o instabilità del Kernel
1. Accedere alla console NoVNC della VM 1100 su Proxmox.
2. Inviare un reset hardware alla VM.
3. Nel menu di avvio GRUB di TrueNAS, selezionare il Boot Environment precedente (**25.10.3.1**) e premere Invio.
4. Se il sistema si avvia correttamente, andare su *System Settings* -> *Boot* ed impostare il vecchio Boot Environment come attivo.

### Caso B: Corruzione o impossibilità di rollback tramite GRUB
1. Arrestare la VM 1100 da Proxmox.
2. Ripristinare il solo disco virtuale di boot da 50 GB (`vm-1100-disk-1`) dal backup eseguito in modalità Stop nella Fase 1.
3. Riavviare la VM 1100.

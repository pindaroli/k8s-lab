# Dettaglio Operativo - Opzione B: Restore Integrale da PBS

Questo documento contiene i passi sequenziali e ultra-dettagliati per riportare online il cluster Proxmox ei servizi Kubernetes (Talos) partendo dall'assunto che PVE2 e PVE3 sono freschi di installazione e la rete (`vmbr10`, `vmbr20`) è già allineata per evitare asymmetric routing.

## ✅ Fase 1: Ricostruzione del Cluster Proxmox (COMPLETATA)
Dato che PVE1 è rimasto operativo ma senza quorum, e PVE2/PVE3 sono nuovi:
1. **Rimuovere vecchie tracce su PVE1:**
   Se i vecchi nodi `pve2` e `pve3` risultano rossi/offline nel datacenter GUI, vanno rimossi forzando temporaneamente l'expect di quorum su 1:
   ```bash
   pvecm expected 1
   pvecm delnode pve2
   pvecm delnode pve3
   ```
   Rimuovere anche le loro impronte SSH dal nodo master: `nano /root/.ssh/known_hosts` (oppure `ssh-keygen -R 10.10.10.21` e `10.10.10.31`).
2. **Join dei nuovi nodi:**
   Da terminale SSH del *nuovo* PVE2:
   ```bash
   pvecm add 10.10.10.11
   ```
   Da terminale SSH del *nuovo* PVE3:
   ```bash
   pvecm add 10.10.10.11
   ```
3. **Controllo:** Verificare da GUI (o con `pvecm status`) che i nodi siano online e il Quorum sia soddisfatto (3 nodi, *expected 3*).

## ✅ Fase 2: Configurazione Storage Pre-Restore (COMPLETATA)
1. Unendosi al cluster, i nuovi nodi erediteranno le definizioni a livello di Datacenter (inclusi gli storage di rete `pbs` e gli NFS Server). Assicurarsi in *Datacenter -> Storage -> pbs -> Nodes* che entrambi i nuovi server siano "spuntati" e abilitati a leggerlo.
2. In PVE2 e PVE3, dal ramo di sinistra selezionare lo storage `pbs`. Dovrebbero comparire tutti i vecchi snapshot delle virtual machine.
3. **Specifico per PVE3:** Dato che abbiamo fatto un upgrade hardware fisico (Singolo SSD NVMe da 1TB testato e funzionante), assicurarsi da GUI (sotto *PVE3 -> Disks -> ZFS* o *LVM/Directory*) che l'unità da 1TB sia allocata come pool per ospitare le VM (es. chiamandolo `local-nvme` o mantenendo il nome standard di rito di Proxmox). Ospiterà la VM Talos 3200 ripristinata.

## ➡️ Fase 3: Il Restore delle Macchine da PBS (IN ATTESA)

### Nodo PVE2
1. Navigare nella GUI su PVE2 -> accedere allo storage `pbs` -> tab **Backups**.
2. Selezionare l'ultimo backup utile della VM **2300 (Talos CP02)** -> **Restore**.
   * **Target Storage**: Selezionare lo storage locale di PVE2 (es. `local-zfs`).
   * **Unique MAC address**: **DEVE ESSERE SPUNTATO "NO" (o deselezionato)**. Mantenere l'indirizzo MAC originale è critico: DHCP assegnerà lo stesso IP e Talos manterrà la stessa identità all'interno del DB Etcd di Kubernetes.
3. Ripetere il processo sul backup della VM **2200 (Jellyfin)**, ripristinandola sempre su PVE2.

### Nodo PVE3
1. Su PVE3 -> storage `pbs` -> tab **Backups**.
2. Selezionare l'ultimo backup della VM **3200 (Talos CP03)** -> **Restore**.
   * **Target Storage**: Selezionare lo storage derivante dal disco NVMe da 1TB appena appurato in PVE3.
   * **Unique MAC address**: **NO**.

## Fase 4: Post-Restore Check & Allineamento Hardware
Prima di schiacciare il tasto "Start" sulle VM appena ripristinate:
1. **Verifica Interfacce di Rete**: Se nei backup i network device delle VM salvate puntavano al vecchio `vmbr0`, occorre aprire la scheda *Hardware* delle VM 2200, 2300, e 3200 e cambiare la tendina con il nuovo switch virtuale: **`vmbr10`**.
2. **RAM limit**: Dato che sia PVE2 che PVE3 hanno hardware robusto (64GB RAM), verificare semplicemente che le allocazioni RAM delle VM non saturino il nodo sommate all'overhead OS. Correggere alla bisogna.
3. **Hook Scripts (PVE3)**: Nei file passati si evinceva l'uso dello script `wait-for-truenas.sh` agganciato a PVE3 per proteggere le accensioni di Talos. Occorre propagare dal nodo vivo questo hook snippet:
   ```bash
   scp root@10.10.10.11:/var/lib/vz/snippets/wait-for-truenas.sh root@10.10.10.31:/var/lib/vz/snippets/
   ```
   E agganciarlo alla VM `3200` editando via terminale in PVE3 il file `qm set 3200 --hookscript local:snippets/wait-for-truenas.sh` se non è già persistito.

## Fase 5: Avvio Sequenziale
Essendo PVE1 già online e con i servizi core attivi (TrueNAS e PBS girano già):
1. **PVE2**: Avviare la VM 2300 (Talos CP02) e attendere che entri in rete.
2. **PVE3**: Avviare la VM 3200 (Talos CP03).
3. **Verifica Talos K8s**:
   Da terminale bash sul tuo Mac:
   ```bash
   talosctl dmesg -n 10.10.20.141
   talosctl get members
   kubectl get nodes -o wide
   ```
   Tutte le macchine dovrebbero allinearsi, ristabilire il Quorum dei Control Plane, e far avviare i restanti DaemonSet (come Xray, CSI driver NFS, Jellyfin su PVE2, *arr stack).

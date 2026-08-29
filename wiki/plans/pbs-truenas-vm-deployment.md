---
title: "Deploy VM Proxmox Backup Server (PBS) su TrueNAS SCALE"
type: plan
status: active
certified_for_ai: true
created_at: 2026-08-29
tags:
  - "#plan"
  - "#storage"
  - "#truenas"
  - "#pbs"
  - "#proxmox"
---

# Piano: Deploy VM Proxmox Backup Server (PBS) su TrueNAS SCALE
## Architettura ad Alte Prestazioni: Zvol Thin-Provisioned via VirtIO + Filesystem ext4

Questo piano definisce i passaggi operativi per implementare **Proxmox Backup Server (PBS)** come Virtual Machine KVM direttamente su **TrueNAS SCALE Bare Metal**, superando i limiti e i blocchi NFS riscontrati in precedenza e massimizzando le performance di I/O tramite **VirtIO Zero-Copy** e filesystem **ext4** dedicato su **Zvol thin-provisioned**.

---

## 🏛️ Architettura di Riferimento

```text
+-------------------------------------------------------------------+
| TrueNAS SCALE (Host KVM - 10.10.10.50)                            |
|                                                                   |
|  Pool ZFS: oliraid (RAID-Z2 + Special VDEV Mirror 64K)            |
|  ├── Zvol OS: pbs-os (32 GiB, Sparse)       ──> /dev/vda (PBS OS) |
|  └── Zvol Dati: pbs-store-vol               ──> /dev/vdb (Datastore)|
|      (volblocksize=64k, sparse, noatime)                          |
+---------------------------------+---------------------------------+
                                  |
                           VirtIO (Zero-Copy)
                                  |
+---------------------------------v---------------------------------+
| VM Guest: Proxmox Backup Server (10.10.10.100)                    |
|                                                                   |
|  - RAM: 6 - 8 GB ECC                                              |
|  - CPU: 4 vCPU Host Passthrough (AES-NI / SHA accelerati)         |
|  - Mount: /mnt/datastore/pbs-store (ext4 su /dev/vdb, noatime)   |
|  - Service User: backup:backup (UID:GID 34:34)                    |
+---------------------------------+---------------------------------+
                                  | TLS (Porta 8007)
+---------------------------------v---------------------------------+
| Proxmox Virtual Environment (PVE1, PVE2, PVE3)                    |
+-------------------------------------------------------------------+
```

---

## 📋 Checklist delle Attività

### [ ] **Fase 1: Preparazione Storage ZFS su TrueNAS (Host)**
- [x] **1.1**: Creazione Zvol per il sistema operativo: (Completata ✅)
  - Dataset: `oliraid/pbs-os`
  - Dimensione: `32 GiB`
  - Proprietà: `sparse=true`, `volblocksize=16k`
- [x] **1.2**: Creazione Zvol per il Datastore dei backup: (Completata ✅)
  - Dataset: `oliraid/pbs-store-vol`
  - Dimensione: `1.5 TiB` (sparse, allocazione dinamica)
  - Proprietà: `sparse=true`, `volblocksize=64k`
- [x] **1.3**: Download dell'immagine ISO ufficiale di Proxmox Backup Server 4.2-1 in TrueNAS (`/mnt/oliraid/iso/proxmox-backup-server_4.2-1.iso` da `https://enterprise.proxmox.com/iso/proxmox-backup-server_4.2-1.iso`). (Completata ✅)

### [x] **Fase 2: Creazione e Provisioning VM su TrueNAS SCALE KVM (Completata ✅)**
- [x] **2.1**: Creazione della VM `pbs` dalla Web GUI di TrueNAS (VirtIO, Host Passthrough, 6GB RAM, Zvol OS e Datastore) ✅
- [x] **2.2**: Avvio della VM e completamento dell'installazione di PBS 4.2 ✅

### [x] **Fase 3: Configurazione Guest OS & Filesystem Datastore (Completata ✅)**
- [x] **3.1**: Configurazione parametri di rete statica nel guest: (`10.10.10.100/24`, GW `10.10.10.1`, DNS `192.168.2.254`, FQDN `pbs.pindaroli.org`) ✅
- [x] **3.2**: Partizionamento e formattazione ottimizzata ext4 su `/dev/vdb` (`UUID=0e25010b-4fa1-4fb6-bdb9-71d4e0c6ab23`) ✅
- [x] **3.3**: Configurazione mount persistente in `/etc/fstab` (`defaults,noatime,barrier=0,commit=60`) ✅
- [x] **3.4**: Creazione directory `/mnt/datastore/pbs-store`, mount ed assegnazione permessi `backup:backup` (750) ✅

### [x] **Fase 4: Inizializzazione Datastore & Migrazione Backup Esistenti (Completata ✅)**
- [x] **4.1**: Creazione del datastore tramite CLI / WebUI PBS (`pbs-store` su `/mnt/datastore/pbs-store`) ✅
- [x] **4.2**: Migrazione dello storico backup esistente completata con successo (413 GB di chunk, VM e container trasferiti) ✅
- [x] **4.3**: Configurazione job automatici in PBS (Daily Prune 7/4/3, GC settimanale dom 03:00, Monthly Verify) ✅

### [ ] **Fase 5: Integrazione con i Nodi Proxmox VE (PVE2, PVE3, PVE1)**
- [x] **5.1**: Recupero del Fingerprint TLS del certificato PBS: (`93:b3:92:68:5c:04:3c:30:18:ef:cb:53:09:6b:a6:1f:0e:4c:94:f6:76:08:cc:56:13:8b:19:31:86:9c:87:ef`) ✅
- [ ] **5.2**: Configurazione dello storage PBS sui nodi Proxmox VE (`pve2` e `pve3`):
  ```bash
  pvesm add pbs pbs --server 10.10.10.100 --datastore pbs-store --fingerprint 93:b3:92:68:5c:04:3c:30:18:ef:cb:53:09:6b:a6:1f:0e:4c:94:f6:76:08:cc:56:13:8b:19:31:86:9c:87:ef --username root@pam --password
  ```
- [ ] **5.3**: Esecuzione backup di test da PVE2 / PVE3 per validare il throughput VirtIO e la deduplicazione:
  ```bash
  vzdump <VMID> --storage pbs --mode snapshot --compress zstd
  ```
- [ ] **5.4**: Bonifica e Dismissione Vecchio Dataset NFS (`oliraid/pbs-store`):
  - Esecuzione Verify Job su PBS per validare che tutti i chunk migrati siano integri al 100%.
  - Rimozione dell'export NFS `/mnt/oliraid/pbs-store` da TrueNAS (GUI/CLI).
  - Distruzione definitiva del vecchio dataset per liberare i ~400 GB su `oliraid`:
    ```bash
    zfs destroy -r oliraid/pbs-store
    ```

### [ ] **Fase 6: Allineamento Documentazione & Registry**
- [ ] **6.1**: Aggiornamento `storage.json`: rimozione definitiva della voce `pbs_store_legacy_nfs` e consolidamento dello Zvol VirtIO `pbs_store`.
- [x] **6.2**: Aggiornamento `rete.json` con i dettagli della VM `pbs` su TrueNAS host ✅
- [ ] **6.3**: Aggiornamento del piano principale `wiki/plans/truenas-baremetal-migration-pve1-reconfig.md`.
- [ ] **6.4**: Esecuzione script di validazione e rigenerazione:
  `python3 scripts/network/validate_network.py && python3 scripts/wiki/build_wiki_context.py`

---

## 💾 Stato di Ripristino (AI Save-State)
- **Fase Attiva**: FASE 5 - INTEGRAZIONE CON I NODI PROXMOX VE (PVE2, PVE3, PVE1)
- **Ultima Azione Completata**: PBS 4.2 operativo al 100% su TrueNAS KVM (`10.10.10.100`). Datastore Zvol VirtIO ext4 montato su `/mnt/datastore/pbs-store` (413 GB caricati, 514k chunk e tutte le VM storiche presenti). Job di manutenzione configurati (Daily Prune, GC settimanale dom 03:00, Monthly Verify). Fingerprint TLS estratto (`93:b3:92:68:5c:04:3c:30:18:ef:cb:53:09:6b:a6:1f:0e:4c:94:f6:76:08:cc:56:13:8b:19:31:86:9c:87:ef`).
- **Prossimo Passo Operativo**: All'accensione dei nodi Proxmox (PVE2, PVE3, PVE1), aggiornare la configurazione dello storage `pbs` con il nuovo TLS Fingerprint ed eseguire backup/restore di validazione (Fase 5.2 / 5.3).
- **Blocchi/Decisioni Pendenti**: In attesa dell'accensione e della lavorazione sui nodi Proxmox VE da parte dell'utente.

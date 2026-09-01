---
title: "Deploy VM Proxmox Backup Server (PBS) su TrueNAS SCALE"
type: plan
status: archived
certified_for_ai: false
created_at: 2026-08-29
archived_at: 2026-08-30
tags:
  - "#plan"
  - "#storage"
  - "#truenas"
  - "#pbs"
  - "#proxmox"
---

# Piano: Deploy VM Proxmox Backup Server (PBS) su TrueNAS SCALE
## Architettura ad Alte Prestazioni: Zvol Thin-Provisioned via VirtIO + Filesystem ext4

> [!NOTE]
> **Stato**: 🟢 **COMPLETATO CON SUCCESSO (2026-08-30)**
> PBS 4.2 è operativo al 100% come VM su TrueNAS Bare Metal (`10.10.10.100`), collegato allo storage Datacenter Proxmox (`pbs-store`), testato e validato con il ripristino ad alte prestazioni della VM `1300` (talos-cp-01 a 3.8 GB/s).

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

### [x] **Fase 1: Preparazione Storage ZFS su TrueNAS (Host) (Completata ✅)**
- [x] **1.1**: Creazione Zvol per il sistema operativo (`oliraid/pbs-os`, 32 GiB, sparse, volblocksize=16k) ✅
- [x] **1.2**: Creazione Zvol per il Datastore (`oliraid/pbs-store-vol`, 1.5 TiB, sparse, volblocksize=64k) ✅
- [x] **1.3**: Download immagine ISO Proxmox Backup Server 4.2-1 in TrueNAS ✅

### [x] **Fase 2: Creazione e Provisioning VM su TrueNAS SCALE KVM (Completata ✅)**
- [x] **2.1**: Creazione VM `pbs` su TrueNAS (VirtIO, Host Passthrough, 6GB RAM, Zvol OS e Datastore) ✅
- [x] **2.2**: Avvio della VM e completamento installazione PBS 4.2 ✅

### [x] **Fase 3: Configurazione Guest OS & Filesystem Datastore (Completata ✅)**
- [x] **3.1**: Configurazione rete statica nel guest (`10.10.10.100/24`, GW `10.10.10.1`, DNS `192.168.2.254`, FQDN `pbs.pindaroli.org`) ✅
- [x] **3.2**: Partizionamento e formattazione ext4 su `/dev/vdb` ✅
- [x] **3.3**: Configurazione mount persistente in `/etc/fstab` ✅
- [x] **3.4**: Creazione directory `/mnt/datastore/pbs-store` con permessi `backup:backup` ✅

### [x] **Fase 4: Inizializzazione Datastore & Migrazione Backup Esistenti (Completata ✅)**
- [x] **4.1**: Creazione datastore `pbs-store` su `/mnt/datastore/pbs-store` ✅
- [x] **4.2**: Migrazione dello storico backup (413 GB di chunk, VM e container trasferiti) ✅
- [x] **4.3**: Configurazione job automatici in PBS (Daily Prune 7/4/3, GC settimanale dom 03:00, Monthly Verify) ✅

### [x] **Fase 5: Integrazione con i Nodi Proxmox VE (PVE1, PVE2, PVE3) (Completata ✅)**
- [x] **5.1**: Recupero TLS Fingerprint del certificato PBS (`93:b3:92:68:5c:04:3c:30:18:ef:cb:53:09:6b:a6:1f:0e:4c:94:f6:76:08:cc:56:13:8b:19:31:86:9c:87:ef`) ✅
- [x] **5.2**: Generazione API Token `root@pam!pve-token` e registrazione storage `pbs` nel cluster Proxmox (`pvesm add pbs`) ✅
- [x] **5.3**: Esecuzione restore di validazione su PVE1 della VM 1300 (`talos-cp-01`) completata a 3.8 GB/s ✅

### [x] **Fase 6: Allineamento Documentazione & Registry (Completata ✅)**
- [x] **6.1**: Aggiornamento `rete.json` con i dettagli della VM `pbs` su TrueNAS Bare Metal host ✅
- [x] **6.2**: Allineamento entità e registro storage Wiki ✅
- [x] **6.3**: Validazione e sincronizzazione contesto completata ✅

---

## 💾 Stato di Ripristino (AI Save-State)
- **Fase Attiva**: PIANO COMPLETATO CON SUCCESSO ✅
- **Ultima Azione Completata**: Storage PBS integrato su PVE1/PVE2/PVE3, validazione restore VM 1300 completata e cluster K8s/Proxmox pienamente riallineati.
- **Prossimo Passo Operativo**: Nessuno (Piano archiviato).
- **Blocchi/Decisioni Pendenti**: Nessuno.

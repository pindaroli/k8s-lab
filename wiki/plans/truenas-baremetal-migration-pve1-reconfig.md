---
title: "Migrazione TrueNAS su Bare Metal e Riconfigurazione PVE1"
type: plan
status: active
certified_for_ai: true
created_at: 2026-08-11
tags:
  - "#plan"
  - "#storage"
  - "#proxmox"
  - "#truenas"
---

# Piano: Migrazione TrueNAS su Bare Metal + Riconfigurazione PVE1

Questo piano documenta i passaggi per spostare TrueNAS SCALE da una VM su PVE1 a un nodo fisico dedicato (Ryzen 5 PRO 5650G, ASRock X570M Pro4, 32GB ECC, Intel X710 10G) e la successiva reinstallazione di PVE1 su un disco di boot dedicato da 512GB, liberando il Crucial P3 Plus 1TB come storage locale per le VM.

---

## 📋 Stato delle Attività ( Checklist )

- [x] **Fase 0: Raccolta Dati Pre-Migrazione (Completata ✅)**
  - [x] 0-A: Verifica struttura pool ZFS e dischi (oliraid ha 7 dischi SATA: 5 HDD + 2 SSD mirror; stripe ha 1 NVMe M.2)
  - [x] 0-B: Inventario completo dataset e proprietà ZFS (sync disabled per qb_temp, zstd per trickplay, ecc.)
  - [x] 0-C: Inventario share NFS (export attivi per K8s, PBS, classical, qb_temp, ecc.)
  - [x] 0-D: Inventario share SMB (arrdata, time-machine, olindo, k8s-arr, backup)
  - [x] 0-E: Inventario utenti e gruppi (olindo UID 1000/GID 3000, k8s GID 1000)
  - [x] 0-F: Configurazione VM talos-cp-01 su PVE1 (MAC: BC:24:11:81:6A:19, bridge vmbr20)
  - [x] 0-G: Creazione snapshot ZFS di sicurezza su tutti i pool (`pre-baremetal-20260811`)
  - [x] 0-H: Esecuzione backup config (`truenas-config.tar`), chiavi ZFS ed export pulito dei pool (Rif: [[truenas-backup-restore]])
- [x] **Fase 1: Spostamento Hardware (Completata ✅)**
  - [x] 1-A: Spegnimento ordinato VM/LXC su PVE1 (`talos-cp-01`, `pbs`, `truenas`)
  - [x] 1-B: Rimozione fisica LSI HBA e Samsung NVMe da PVE1
  - [x] 1-C: Installazione nuovo NVMe 512GB boot su PVE1
  - [x] 1-D: Assemblaggio nuovo bare metal (8 HDD direct SATA, Samsung NVMe M.2_2, X710 PCIe1)
  - [x] 1-E: Connessione di rete del nuovo bare metal a Extreme X620 (VLAN 10)
- [x] **Fase 2: Installazione TrueNAS SCALE su Bare Metal (Completata ✅)**
  - [x] 2-A: Preparazione USB boot con TrueNAS SCALE 25.x
  - [x] 2-B: Installazione su NVMe 128GB del nuovo bare metal
  - [x] 2-B1: Verifica impostazione SATA Mode su **AHCI** e Typical Current Idle nel BIOS (Rif: [[truenas-backup-restore]])
  - [x] 2-C: Configurazione interfaccia di rete primaria (`10.10.10.50/24`) e OOB (`192.168.100.50/24`)
  - [x] 2-D: Import pool ZFS (`oliraid` e `stripe`) dalla GUI/CLI
- [x] **Fase 3: Ripristino Configurazione TrueNAS (Completata ✅)**
  - [x] 3-A: Upload archivio `truenas-config.tar` via WebUI e aggiornamento versione 25.10.6 (Rif: [[truenas-backup-restore]])
  - [x] 3-B: Verifica e applicazione permessi dataset (NFS Storage Schema: `chown olindo:k8s`, `chmod 777`, 22T liberi su oliraid e 3.5T su stripe)
  - [x] 3-C: Configurazione e avvio servizi NFS, SMB, SSH (passwordless per olindo e truenas_admin)
  - [x] 3-D: Identificazione e configurazione App Garage S3
  - [x] 3-E: Verifica mount NFS e share SMB da Mac Studio (Time Machine attivo)
- [x] **Fase 4: VM PBS su TrueNAS SCALE (Completata ✅)** (Rif: [[pbs-truenas-vm-deployment]])
  - [x] 4-A: Creazione Zvol per boot VM (`oliraid/pbs-os`) e Zvol datastore (`oliraid/pbs-store-vol`) ✅
  - [x] 4-B: Scaricamento ISO Proxmox Backup Server 4.2-1 ✅
  - [x] 4-C: Creazione e configurazione VM PBS su TrueNAS GUI/KVM (VirtIO, 4 vCPU Host Passthrough, 6GB RAM) ✅
  - [x] 4-D: Installazione OS, partizionamento ext4 (`/dev/vdb`) ed impostazione IP statico `10.10.10.100` ✅
  - [x] 4-E: Inizializzazione Datastore PBS e migrazione chunk da vecchio storage (413 GB trasferiti, cron job configurati) ✅
  - [ ] 4-F: Verifica raggiungibilità e configurazione storage PBS da PVE2 e PVE3 (In attesa di accensione nodi PVE)
- [ ] **Fase 5: Reinstallazione PVE1**
  - [x] 5-A: Backup definitivo config VM talos-cp-01 (`/etc/pve/qemu-server/1300.conf`)
  - [x] 5-B: Installazione Proxmox VE 9.2 su NVMe 512GB ext4 (Crucial P3 Plus 1TB escluso)
  - [x] 5-C: Riconfigurazione rete (bridge `vmbr10` statico e `vmbr20` manuale su X710 Quad-Port, porta OOB `nic0` 2.5G)
  - [x] 5-D: Piallatura e bonifica totale Crucial P3 Plus 1TB: backup configurazioni legacy salvato su boot NVMe 512GB e Mac, azzeramento GPT (`sgdisk --zap-all`) e creazione pool ZFS pulito nativo `local-zfs-1tb` a disco intero con dataset `data` per VM/LXC
  - [ ] 5-E: Re-integrazione nel Cluster Proxmox `HomeLab` e ricreazione VM `talos-cp-01` (1300) con MAC address originale
  - [ ] 5-F: Avvio VM e verifica stato cluster Kubernetes
- [ ] **Fase 6: Verifica Finale e Aggiornamento Registry**
  - [ ] 6-A: Checklist di verifica completa (TrueNAS, K8s, PBS, Jellyfin)
  - [x] 6-B: Aggiornamento `rete.json` (truenas bare metal, pbs VM, nuove porte switch) ✅
  - [ ] 6-C: Aggiornamento `wiki/entities/TrueNAS.md`
  - [ ] 6-D: Esecuzione script di validazione e rigenerazione wiki context

---

## 💾 Stato di Ripristino (AI Save-State)
- **Fase Attiva**: FASE 5-E - RE-JOIN PVE1 & RIPRISTINO TALOS CP1 / FASE 4-F - INTEGRATION PBS PVE
- **Ultima Azione Completata**: TrueNAS SCALE Bare Metal operativo al 100%. VM PBS 4.2 deployata su KVM con Zvol VirtIO ext4 da 1.5 TB (`/mnt/datastore/pbs-store`), 413 GB di backup storici migrati con successo, job di manutenzione configurati e TLS Fingerprint registrato (`93:b3:92:68:5c:04:3c:30:18:ef:cb:53:09:6b:a6:1f:0e:4c:94:f6:76:08:cc:56:13:8b:19:31:86:9c:87:ef`).
- **Prossimo Passo Operativo**: All'accensione dei nodi Proxmox (PVE2, PVE3, PVE1), procedere con il re-join di PVE1 nel cluster Proxmox (`pvecm join`), il ripristino della VM `talos-cp-01` (1300) su `local-zfs-1tb` e l'aggiornamento dello storage PBS.
- **Blocchi/Decisioni Pendenti**: Lavorazione manuale/locale dell'utente sui nodi fisici Proxmox VE. Piano sospeso in attesa dell'accensione host PVE.

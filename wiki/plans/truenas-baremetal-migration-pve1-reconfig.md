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
- [x] **Fase 1: Spostamento Hardware (Prossima Fase ⏳)**
  - [x] 1-A: Spegnimento ordinato VM/LXC su PVE1 (`talos-cp-01`, `pbs`, `truenas`)
  - [ ] 1-B: Rimozione fisica LSI HBA e Samsung NVMe da PVE1
  - [ ] 1-C: Installazione nuovo NVMe 512GB boot su PVE1
  - [ ] 1-D: Assemblaggio nuovo bare metal (8 HDD direct SATA, Samsung NVMe M.2_2, X710 PCIe1)
  - [ ] 1-E: Connessione di rete del nuovo bare metal a Extreme X620 (VLAN 10)
- [ ] **Fase 2: Installazione TrueNAS SCALE su Bare Metal**
  - [ ] 2-A: Preparazione USB boot con TrueNAS SCALE 25.x
  - [ ] 2-B: Installazione su NVMe 128GB del nuovo bare metal
  - [ ] 2-B1: Verifica impostazione SATA Mode su **AHCI** nel BIOS (Rif: [[truenas-backup-restore]])
  - [ ] 2-C: Configurazione interfaccia di rete primaria (`10.10.10.50/24`)
  - [ ] 2-D: Import pool ZFS (`oliraid` e `stripe`) dalla GUI
- [ ] **Fase 3: Ripristino Configurazione TrueNAS**
  - [ ] 3-A: Upload archivio `truenas-config.tar` via WebUI e riassegnazione NIC da console (Rif: [[truenas-backup-restore]])
  - [ ] 3-B: Verifica e applicazione permessi dataset (NFS Storage Schema: `chown olindo:k8s`, `chmod 777`)
  - [ ] 3-C: Configurazione e avvio servizi NFS, SMB, SSH
  - [ ] 3-D: Reinstallazione e configurazione App MinIO (S3)
  - [ ] 3-E: Verifica mount NFS e share SMB da Mac Studio
- [ ] **Fase 4: VM PBS su TrueNAS SCALE**
  - [ ] 4-A: Creazione ZVOL per boot VM e dataset per i backup su `oliraid`
  - [ ] 4-B: Scaricamento ISO Proxmox Backup Server 3.x
  - [ ] 4-C: Creazione e configurazione VM PBS su TrueNAS GUI
  - [ ] 4-D: Installazione ed impostazione IP statico `10.10.10.100`
  - [ ] 4-E: Collegamento datastore PBS ai backup NFS esistenti
  - [ ] 4-F: Verifica raggiungibilità e storage da PVE2 e PVE3
- [ ] **Fase 5: Reinstallazione PVE1**
  - [ ] 5-A: Backup definitivo config VM talos-cp-01 (`/etc/pve/qemu-server/1300.conf`)
  - [ ] 5-B: Installazione Proxmox VE 9.2 su NVMe 512GB (Crucial P3 Plus 1TB escluso)
  - [ ] 5-C: Riconfigurazione rete (bridge `vmbr10` statico e `vmbr20` manuale su X710)
  - [ ] 5-D: Aggiunta Crucial P3 Plus 1TB come storage local-lvm (importazione ed avvio pool ZFS rinominato in `local-zfs-1tb` per evitare conflitti)
  - [ ] 5-E: Ricreazione VM `talos-cp-01` (1300) con MAC address originale
  - [ ] 5-F: Avvio VM e verifica stato cluster Kubernetes
- [ ] **Fase 6: Verifica Finale e Aggiornamento Registry**
  - [ ] 6-A: Checklist di verifica completa (TrueNAS, K8s, PBS, Jellyfin)
  - [ ] 6-B: Aggiornamento `rete.json` (truenas bare metal, pbs VM, nuove porte switch)
  - [ ] 6-C: Aggiornamento `wiki/entities/TrueNAS.md`
  - [ ] 6-D: Esecuzione script di validazione e rigenerazione wiki context

---

## 💾 Stato di Ripristino (AI Save-State)

- **Fase Attiva**: FASE 1 - SPOSTAMENTO HARDWARE (Intervento Fisico)
- **Ultima Azione Completata**: Fase 1-A completata. Smontati gli NFS e spente correttamente tutte le macchine virtuali su PVE1, inclusa TrueNAS.
- **Prossimo Passo Operativo**: Spegnere fisicamente il server PVE1 (`poweroff`) e procedere all'apertura del case per estrarre la scheda LSI HBA e il disco Samsung NVMe.
- **Blocchi/Decisioni Pendenti**: Attesa fine intervento hardware da parte dell'utente.

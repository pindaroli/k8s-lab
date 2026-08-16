---
title: "Storage Registry (storage.json)"
last_updated: "2026-06-07"
confidence: "High"
tags:
  - "#storage"
  - "#core"
  - "#nfs"
provenance:
  - "storage.json"
---

# Storage Registry

Questo nodo del Wiki definisce le **regole** e la topologia dello storage condiviso nell'Homelab.

> [!WARNING]
> **SOURCE OF TRUTH**: I dati effettivi per i path e i mountpoint sono in `storage.json` (nella root del progetto). L'agente IA deve consultare e modificare `storage.json` per mappare nuovi volumi. Questo documento spiega la logica dietro l'allocazione.

## 1. Topologia Storage
Lo storage primario è fornito da [[TrueNAS]] tramite protocollo NFS.
Ci sono due pool principali:
- **`oliraid`**: Pool HDD primario, alta capacità. Usato per i media (`arrdata`), backup, musica classica e documenti a lungo termine.
  - **Dataset Trickplay (`oliraid/jellyfin-trickplay`)**: Dataset specializzato per i file `.bif` di Jellyfin configurato con **Recordsize: 1M**, **Compression: zstd**, **Atime: off** e **Quota: 500G**. Escluso dagli snapshot e dai backup di sistema.
- **`stripe`**: Pool NVMe ad alte prestazioni. Usato per cache K8s, transcodifica temporanea di [[Tdarr]] (`k8s-arr/tdarr-cache`), storage temporaneo qBittorrent (`qb_temp`), PVC NFS per la suite n8n (`k8s-n8n`) e libreria Steam/Games (`games`).
  - **Ottimizzazione qB Temp**: Dataset `stripe/qb_temp` configurato con **Recordsize: 16k** e **Sync: Disabled** per gestire burst di IOPS a 20 MB/s.
- **MinIO (S3-compatibile)** su TrueNAS: Usato come storage persistente e versionato per il database SQLite della pipeline classica (`classical_musiclibrary.db`). Il DB viene scaricato in `emptyDir` K8s durante l'esecuzione e ri-caricato atomicamente al termine del flow Prefect (sempre, anche in caso di errore). Il versioning nativo di MinIO permette rollback istantanei in caso di corruzione dell'ontologia.

> [!NOTE]
## 2. Integrazione Kubernetes
Il [[Talos_Cluster]] accede allo storage tramite il CSI Driver NFS (Local Path Provisioner customizzato o mount diretti nei container).
I PersistentVolume (PV) e PersistentVolumeClaim (PVC) che richiedono grandi capacità o persistenza off-cluster devono essere mappati sulle share NFS di TrueNAS, prendendo i riferimenti esatti da `storage.json`.

## 3. Storage Locale Hypervisor (Proxmox PVE)
I nodi Proxmox mantengono dischi dedicati locali per il boot dell'hypervisor e i dischi virtuali delle VM/LXC:
- **PVE1**:
  - **Boot OS**: NVMe 512GB (`nvme0n1`) formattato in `ext4`/LVM (`pve-root` + `local-lvm`).
  - **VM Storage**: Crucial P3 Plus 1TB NVMe (`nvme1n1`) interamente dedicato al pool ZFS **`local-zfs-1tb`** (`ashift=12`, `compression=on`, `xattr=sa`, dataset `local-zfs-1tb/data` per le VM e nodi Talos).

## Relazioni
- Governa: `storage.json`
- Fornito da: [[TrueNAS]], Proxmox Hypervisor
- Utilizzato da: [[Talos_Cluster]], [[Tdarr]], Servarr Stack.
- DB Pipeline Classica: MinIO → [[prefect-beets-adaptation]].

---
title: "Storage Registry (storage.json)"
last_updated: "2026-05-11"
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
- **`oliraid`**: Pool HDD primario, alta capacità. Usato per i media (`arrdata`), backup e documenti a lungo termine.
- **`stripe`**: Pool NVMe ad alte prestazioni. Usato per cache K8s, transcodifica temporanea di [[Tdarr]] (`k8s-arr/tdarr-cache`) e storage temporaneo qBittorrent (`qb_temp`).
  - **Ottimizzazione qB Temp**: Dataset `stripe/qb_temp` configurato con **Recordsize: 16k** e **Sync: Disabled** per gestire burst di IOPS a 20 MB/s.

> [!CRITICAL]
> **Database e Local Storage**: Il database `postgres-main` (CloudNativePG) NON usa NFS di TrueNAS, ma utilizza **Local Storage** (`rancher.io/local-path`) per massimizzare le performance IOPS. Questo introduce un **Single Point of Failure (SPOF) a livello di nodo fisico**: i dischi del database sono vincolati ai nodi specifici (es. `talos-cp-02`).
> **STATO ATTUALE (2026-05-11)**: Il sistema è in stato **DEGRADED (Missing Nodes)**. I dati di `postgres-main-2` sono inaccessibili poiché il nodo `talos-cp-02` è ospitato su PVE2 (attualmente offline). Il cluster DB non può avviarsi correttamente fino al ripristino dell'hardware. I dettagli sono in `storage.json` alla voce `nas.local.postgres_disk`.

## 2. Integrazione Kubernetes
Il [[Talos_Cluster]] accede allo storage tramite il CSI Driver NFS (Local Path Provisioner customizzato o mount diretti nei container).
I PersistentVolume (PV) e PersistentVolumeClaim (PVC) che richiedono grandi capacità o persistenza off-cluster devono essere mappati sulle share NFS di TrueNAS, prendendo i riferimenti esatti da `storage.json`.

## Relazioni
- Governa: `storage.json`
- Fornito da: [[TrueNAS]]
- Utilizzato da: [[Talos_Cluster]], [[Tdarr]], Servarr Stack.

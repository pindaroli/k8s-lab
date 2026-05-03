---
title: "Storage Registry (storage.json)"
last_updated: "2026-05-03"
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
- **`stripe`**: Pool NVMe ad alte prestazioni. Usato per cache K8s e transcodifica temporanea di [[Tdarr]] (`k8s-arr/tdarr-cache`).

> [!CRITICAL]
> **Database e Local Storage**: Il database `postgres-main` (CloudNativePG) NON usa NFS di TrueNAS, ma utilizza **Local Storage** (`rancher.io/local-path`) per massimizzare le performance IOPS. Questo introduce un **Single Point of Failure (SPOF) a livello di nodo fisico**: i dischi del database sono vincolati ai nodi specifici (es. `talos-cp-02`). Se l'hypervisor fisico che ospita il nodo (es. **PVE2**) viene spento per manutenzione, i dischi diventano irraggiungibili e il database va in crash, rompendo tutti i servizi dipendenti (Lidarr, etc). I dettagli sui mount point locali sono in `storage.json` alla voce `nas.local.postgres_disk`.

## 2. Integrazione Kubernetes
Il [[Talos_Cluster]] accede allo storage tramite il CSI Driver NFS (Local Path Provisioner customizzato o mount diretti nei container).
I PersistentVolume (PV) e PersistentVolumeClaim (PVC) che richiedono grandi capacità o persistenza off-cluster devono essere mappati sulle share NFS di TrueNAS, prendendo i riferimenti esatti da `storage.json`.

## Relazioni
- Governa: `storage.json`
- Fornito da: [[TrueNAS]]
- Utilizzato da: [[Talos_Cluster]], [[Tdarr]], Servarr Stack.

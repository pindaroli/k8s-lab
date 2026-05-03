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

## 1. Topologia Storage (TrueNAS)
Lo storage primario è fornito da [[TrueNAS]] tramite protocollo NFS.
Ci sono due pool principali:
- **`oliraid`**: Pool HDD primario, alta capacità. Usato per i media (`arrdata`), backup e documenti a lungo termine.
- **`stripe`**: Pool NVMe ad alte prestazioni. Usato per cache K8s, transcodifica temporanea di [[Tdarr]] (`k8s-arr/tdarr-cache`) e database.

## 2. Integrazione Kubernetes
Il [[Talos_Cluster]] accede allo storage tramite il CSI Driver NFS (Local Path Provisioner customizzato o mount diretti nei container).
I PersistentVolume (PV) e PersistentVolumeClaim (PVC) che richiedono grandi capacità o persistenza off-cluster devono essere mappati sulle share NFS di TrueNAS, prendendo i riferimenti esatti da `storage.json`.

## Relazioni
- Governa: `storage.json`
- Fornito da: [[TrueNAS]]
- Utilizzato da: [[Talos_Cluster]], [[Tdarr]], Servarr Stack.

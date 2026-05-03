---
title: "Tdarr (Distributed Transcoding)"
last_updated: "2026-05-03"
confidence: "High"
tags:
  - "#app"
  - "#media"
  - "#transcoding"
provenance:
  - "tdarr/configs/Tdarr_Node_Config.json"
---

# Tdarr (Distributed Media Processing)

Tdarr è il sistema di transcodifica distribuito utilizzato per convertire la libreria media in formato HEVC (H265) in modo automatizzato.

## 1. Architettura
Il sistema è diviso in due componenti principali:
1.  **Tdarr Server & Internal Node**: Gira come container nel [[Talos_Cluster]] (Namespace `arr`). Gestisce il database e la dashboard.
2.  **External Node (Mac Studio)**: Un nodo esterno ad alte prestazioni (`10.10.20.100`) che utilizza la potenza della GPU/VideoToolbox del Mac Studio M2 Ultra.

## 2. Configurazione Nodo Mac Studio
- **Script di Avvio**: `tdarr/node/start_node.sh`.
- **Automazione Mount**: Utilizza `sudoers` per montare le share NFS senza password (Vedi [[TrueNAS]]).
- **Path Translators**: Mappa i percorsi interni del server (`/media`, `/temp`) con quelli locali del Mac (`/Volumes/arrdata/media`, `/Volumes/k8s-arr/tdarr-cache`).

## 3. Storage e Cache
- **Libreria**: `/Volumes/arrdata/media` (NFS su TrueNAS).
- **Cache (NVMe)**: `/Volumes/k8s-arr/tdarr-cache`. È fondamentale che la cache sia su uno storage veloce (Pool Stripe NVMe) per non strozzare le performance di transcodifica.

## 4. Logica di Transcodifica (Flows)
- Si utilizzano i **Tdarr Flows** invece dei plugin classici per una gestione più granulare.
- Workflow: `Check Health` -> `Backup` -> `HEVC Transcode` -> `Verify` -> `Replace`.

## Relazioni
- Dashboard accessibile via: [[Traefik]] (`tdarr-internal.pindaroli.org`).
- Dipende da: [[TrueNAS]] per i file sorgente.
- Comunica con: API Server su `tdarr-api.pindaroli.org` (Porta 8266).

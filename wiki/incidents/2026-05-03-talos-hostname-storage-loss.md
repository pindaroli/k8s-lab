---
title: "Incident: Talos Reinstallation, Hostname Loss & Local Storage Affinity"
date: "2026-05-03"
status: "Resolved"
tags:
  - "#incident"
  - "#talos"
  - "#storage"
  - "#postgresql"
---

# Incident: Talos Hostname Loss & Local Storage Affinity Block

## Sintomi
- Dopo una reinstallazione completa del control plane (nodi `141` e `143`), il cluster si è riavviato ma i servizi dipendenti da database (es. Lidarr) sono entrati in CrashLoopBackOff.
- Eseguendo `kubectl get nodes`, i vecchi nodi (`talos-cp-01`, `talos-cp-03`) risultavano in stato `NotReady`, mentre apparivano due nuovi nodi con nomi casuali (es. `talos-ate-kwz`) in stato `Ready`.
- I pod di `postgres-main` (CloudNativePG) non venivano schedulati.

## Root Cause (Causa Radice)
Il problema nasce dall'intersezione tra la gestione identità di Talos e le regole di sicurezza di Kubernetes per il Local Storage:
1. **Perdita di Identità**: Durante la reinstallazione, è stata fornita a Talos la configurazione generica `controlplane.yaml`. Mancando una direttiva esplicita per l'`hostname`, Talos ha generato nomi host casuali.
2. **Node Affinity**: I database nel cluster usano la StorageClass `local-postgres` (Local Path Provisioner su `/dev/sdb`). Kubernetes mappa indissolubilmente i `PersistentVolume` (PV) generati localmente all'**esatto hostname** del nodo su cui sono stati creati (tramite `nodeAffinity`).
3. **Il Blocco**: Quando i nodi si sono ripresentati con nomi diversi, Kubernetes ha considerato i vecchi nodi come "offline". Per proteggere l'integrità dei dati, ha rifiutato di montare i dischi sui nodi nuovi, causando il blocco totale del database. I dati su `/dev/sdb` erano intatti (la reinstallazione formatta solo `/dev/sda`), ma bloccati a livello logico.

## Risoluzione & Infrastructure as Code
Invece di intervenire manualmente sui manifest di Kubernetes, il problema è stato risolto alla radice a livello di sistema operativo (Talos):
1. Sono stati creati dei file di "Patch" specifici per ogni nodo nella directory `talos-config/` (es. `patch-talos-cp-01.yaml`), contenenti esclusivamente la direttiva per forzare l'identità:
   ```yaml
   machine:
     network:
       hostname: talos-cp-01
   ```
2. La patch è stata applicata a caldo sui nodi: `talosctl patch machineconfig -n <IP> --patch @talos-config/patch-talos-cp-01.yaml`
3. Al riavvio, i nodi si sono ricollegati a Kubernetes con la loro identità storica. Kubernetes ha riconosciuto i nomi e ha sbloccato automaticamente l'accesso ai dischi `/dev/sdb`, riportando il database online senza alcuna perdita di dati.

## Lesson Learned (Prevenzione)
- **MAI** affidarsi a hostname generati dinamicamente o dal DHCP per i nodi del cluster, specialmente se si utilizza Local Storage.
- L'identità dei nodi deve essere gestita in ottica **Infrastructure as Code (IaC)**. In caso di reinstallazione da zero (Disaster Recovery), la procedura obbligatoria prevede l'applicazione del `controlplane.yaml` generico seguita **immediatamente** dall'applicazione della `patch` specifica per il nodo, prima ancora di eseguire il bootstrap di Kubernetes.

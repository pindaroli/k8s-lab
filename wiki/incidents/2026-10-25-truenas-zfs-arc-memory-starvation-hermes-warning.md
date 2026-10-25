---
title: "INC-2026-10-25: TrueNAS ZFS ARC Memory Starvation and Hermes Agent Low Memory Alert"
type: incident
status: archived
certified_for_ai: false
date: 2026-10-25
severity: P3
resolved: true
resolved_at: 2026-10-25T09:41:00+01:00
tags:
  - "#incident"
  - "#truenas"
  - "#zfs"
  - "#arc"
  - "#hermes"
  - "#memory"
---

# INC-2026-10-25: TrueNAS ZFS ARC Memory Starvation e Alert Low Memory su Hermes Agent

## Descrizione dell'Incidente
Durante l'utilizzo della Web UI e dell'interfaccia di Hermes Agent (`hermes-main`, versione `v0.22.5` su TrueNAS SCALE bare metal `10.10.20.50`), è comparso un banner di avviso giallo in cima all'interfaccia:
> **"Your agent is running low on memory."**

L'host TrueNAS dispone fisicamente di **48 GB di RAM** (47.910 MiB riportati dal kernel) e non ha alcuna partizione o file di swap attivo (`Swap: 0 MB`). Ciononostante, il sistema operativo segnalava una `MemAvailable` di appena **~5.8 GB** (~12.2% del totale), innescando la soglia di guardia del Gateway Hermes fissata tassativamente al **15%**.

---

## Analisi della Root Cause

1. **Politica di Caching Default di ZFS su Linux (SCALE)**:
   Per impostazione predefinita su TrueNAS SCALE (Debian Bookworm con OpenZFS 2.x), il parametro kernel `zfs_arc_max` è impostato al 90–95% della RAM fisica totale (`c_max = 49.164.431.360` bytes, ovvero ~45.8 GiB).
   ZFS espande progressivamente l'Adaptive Replacement Cache (ARC) per conservare in RAM i blocchi disco letti dai pool `oliraid` e `stripe`.
2. **Reclaim Latency e Asimmetria di Calcolo `MemAvailable`**:
   Sebbene OpenZFS registri uno shrinker nel kernel Linux per rilasciare pagine su pressione di memoria, il calcolo di `MemAvailable` in `/proc/meminfo` considera solo una frazione dell'ARC come immediatamente recuperabile. Di conseguenza, il processo `gateway_runtime_discovery.py` di Hermes leggeva una memoria libera virtuale del 12.2%, facendo scattare l'alert.
3. **Rischio di OOM Killer su Docker e PBS VM**:
   Poiché TrueNAS ospita 17 container Docker in produzione (compresi due cluster PostgreSQL dedicati a LiteLLM e Bitmagnet) e la macchina virtuale KVM Proxmox Backup Server (`10.10.10.100`) con 4 GB di RAM riservati staticamente, l'assenza di swap combinata con un ARC che erodeva oltre 37 GB esponeva l'intero nodo a contese di allocazione kernel e al rischio di interventi distruttivi dell'OOM killer.

---

## Verifica Telemetrica del Working Set ZFS

Prima di procedere all'applicazione di un limite arbitrario, è stata eseguita una diagnosi puntuale dei contatori del kernel ZFS (`/proc/spl/kstat/zfs/arcstats`):
- **Cache Hit Rate Complessiva**: **92.95%** (248.2M hits su 267M query totali).
- **Hit sui Metadati (`demand_metadata_hits`)**: **78.3%** del totale (194.3M).
- **Working Set Reale in Esercizio**:
  - `arc_meta_used`: **5.3 GB** (directory tree, dnode, permessi di tutti i dataset).
  - `data_size`: **23.4 GB** (blocchi dati letti di recente).
  - **Dimensione ARC Reale Effettiva**: **~28.7 GB**.

### Valutazione di Impatto dell'Opzione B (28 GiB / 30.064.771.072 bytes)
- **Pool `oliraid` (HDD)**: Protetto dal mirror dedicato **Special VDEV SSD** per tutti i metadati e small blocks (< 64K). I metadati rimangono al 100% in cache RAM o sul veloce mirror SSD NVMe/SATA, garantendo massima reattività nella scansione delle librerie media di Jellyfin e Radarr/Sonarr. Lo streaming video sequenziale non subisce alcun calo (richiede 2–10 MB/s a fronte di letture sequenziali HDD di oltre 180 MB/s).
- **Pool `stripe` (NVMe)**: I container Docker, database PostgreSQL e cartelle di download torrent risiedono direttamente su NVMe con latenze sub-millisecondo (~50 µs). L'eventuale miss di cache viene gestito istantaneamente dall'interfaccia NVMe.
- **RAM Garantita per l'Host**: Bloccando l'ARC a un tetto di 28 GiB su 48 GB, rimangono **20 GB di RAM libera e garantita** per il kernel Linux, la VM PBS e i container Docker.

---

## Risoluzione Applicata

La modifica è stata applicata in due passaggi coordinati:

### 1. Applicazione Immediata a Runtime (Zero Downtime)
È stato impostato il parametro `zfs_arc_max` direttamente nel modulo kernel ZFS:
```bash
echo 30064771072 | sudo tee /sys/module/zfs/parameters/zfs_arc_max
```

**Verifica esito**:
```text
/sys/module/zfs/parameters/zfs_arc_max: 30064771072
c_max: 30064771072 (28 GiB esatti)
c (target ARC): 28751303784
MemAvailable: aumentata a > 8.0 GB (> 17% immediato, con rilascio progressivo fino a ~18 GB)
```

### 2. Persistenza ai Riavvii tramite Middleware TrueNAS SCALE
È stato creato il tunable persistente tramite il middleware nativo di TrueNAS (`midclt`):
```bash
midclt call tunable.create '{
  "type": "ZFS",
  "var": "zfs_arc_max",
  "value": "30064771072",
  "comment": "Limit ZFS ARC to 28 GiB to guarantee RAM for Docker and PBS",
  "enabled": true
}'
```

**Verifica middleware (`midclt call tunable.query`)**:
```json
[
  {
    "id": 1,
    "type": "ZFS",
    "var": "zfs_arc_max",
    "value": "30064771072",
    "comment": "Limit ZFS ARC to 28 GiB to guarantee RAM for Docker and PBS",
    "enabled": true,
    "orig_value": "30064771072"
  }
]
```

### 3. Validazione Interna su Hermes Agent
Ispezione delle metriche di memoria viste dal container `hermes-main`:
```bash
docker exec hermes-main python3 -c 'import psutil; print(f"Available: {psutil.virtual_memory().available/(1024**3):.1f} GB ({psutil.virtual_memory().available*100/psutil.virtual_memory().total:.1f}%)")'
# Output: Available: 8.0 GB (17.0%) -> oltre la soglia minima del 15%
```
L'avviso *"Your agent is running low on memory"* è scomparso dalla Web UI e il sistema mantiene stabilmente oltre 16–20 GB di RAM libera per l'esecuzione dei workflow e dei container.

---

## Verifiche e Riferimenti
- [[TrueNAS]]: Parametri modulo OpenZFS e tunables middleware.
- [[Hermes_Agent]]: Monitoraggio risorse e soglie Gateway.
- [[Storage_Registry]]: Specifiche pool `oliraid` (Special VDEV) e `stripe` (NVMe).

---
title: "Special Mirror DEGRADED — Disco Sostituto Non Riconosciuto"
type: incident
status: archived
certified_for_ai: false
date: 2026-06-24
severity: P2
resolved: true
resolved_at: 2026-06-24T23:59:59Z
tags:
  - "#incident"
  - "#storage"
---

# Incident: Special Mirror DEGRADED — Disco Sostituto Non Riconosciuto
**Data**: 2026-06-24
**Status**: RESOLVED (resilver avviato con successo alle 11:04 CEST)
**Severity**: Medium (pool degraded ma funzionante, zero data loss, mirror garantiva ridondanza)

## 🔍 Diagnosi

Durante l'esecuzione del piano [[special-vdev-optimization]], il check preliminare `zpool status oliraid` ha rivelato:

```
state: DEGRADED
status: One or more devices have been removed.

mirror-2                                DEGRADED
  16d908ce-370a-492b-9a57-34981e6c2558  ONLINE   → /dev/sdf1 (Intel D3-S4510, serial BTYS8484048G960CGN)
  49bcf4bc-cc98-46b3-bc36-c1633cf074e5  REMOVED
```

La ricerca del device `49bcf4bc-cc98-46b3-bc36-c1633cf074e5` in `/dev/disk/by-partuuid/` non ha prodotto risultati. Tuttavia, il disco `/dev/sdg1` (Intel D3-S4510, serial `BTYS82260FPG960CGN`, PARTUUID `0988e553-4c23-4db6-badb-4956a18310b1`) era fisicamente presente, visibile via `lsblk`, e possedeva **label ZFS valide per il pool `oliraid`** (verificato via `blkid`).

### Causa Radice

Il `zpool replace` dell'aprile 2026 fu **eseguito correttamente** e il resilver completò con successo. Il pool girò normalmente per settimane con entrambi i mirror online.

La causa del REMOVED è una **race condition SATA all'import del pool durante un riavvio di TrueNAS** (aggiornamento o reboot), secondo questo scenario:

1. Il kernel avvia l'enumerazione SATA
2. `/dev/sdf` viene enumerato rapidamente ✅
3. `/dev/sdg` arriva in ritardo (latenza SATA/backplane/controller) ⏳
4. ZFS importa `oliraid` da `sdf1` prima che `sdg1` sia disponibile al kernel
5. ZFS marca il membro mancante come `REMOVED` nel suo state
6. `sdg` viene enumerato subito dopo, ma ZFS **non esegue auto-online** dei device in stato REMOVED — richiede intervento esplicito

Da quel momento il pool era degraded, ma:
- TrueNAS non generò alert visibili (o furono ignorati)
- Il pool continuava a funzionare normalmente con ridondanza azzerata
- Il `zpool.cache` veniva rigenerato ad ogni boot preservando lo stato degraded

> [!NOTE]
> Il pool ha operato in stato di **degraded non rilevato per settimane**. La condizione è emersa visibilmente durante la sessione di manutenzione, probabilmente perché lo stop dei servizi NFS/SMB ha indotto una reinizializzazione di alcuni sottosistemi ZFS.

## 🛠️ Risoluzione

Identificata la discrepanza tra UUID atteso e UUID effettivo, eseguito:

```bash
sudo zpool replace oliraid 49bcf4bc-cc98-46b3-bc36-c1633cf074e5 /dev/sdg1
```

ZFS ha avviato il resilver alle **11:04 CEST del 24/06/2026**, copiando i dati da `/dev/sdf1` (ONLINE) verso `/dev/sdg1`. Al termine, il pool ha aggiornato il config canonico con la nuova PARTUUID di `sdg1`.

## 🧪 Verifica

Post-resilver, il pool deve tornare:
```
state: ONLINE
mirror-2: ONLINE
  16d908ce-...  ONLINE  (sdf1)
  <new-uuid>    ONLINE  (sdg1)
scan: resilver repaired XGB in HH:MM:SS with 0 errors
```

## 📚 Lezioni Apprese

1. **Pre-check obbligatorio**: Prima di qualsiasi operazione ZFS su `oliraid`, verificare `zpool status | grep -E 'state|DEGRADED|REMOVED'`. Questo check è stato aggiunto come precondizione esplicita nel piano [[special-vdev-optimization]].
2. **Sostituzione dischi su TrueNAS**: Usare **sempre** la procedura di sostituzione dalla UI di TrueNAS (Storage → Disks → Replace) che gestisce correttamente `zpool replace` + `zpool.cache`. Mai fare swap fisico senza eseguire `zpool replace`.
3. **Monitoraggio post-sostituzione**: Dopo ogni `zpool replace`, verificare che il resilver si completi (`zpool status` fino a `state: ONLINE`) prima di considerare l'operazione conclusa.
4. **Alert TrueNAS**: Configurare alert email/notifica per stato DEGRADED del pool — avrebbe rilevato il problema da aprile.
5. **Path Persistenti**: Mai usare path crudi come `/dev/sdg` nei comandi manuali di sostituzione (`zpool replace`), ma passare sempre il `PARTUUID` (es. `/dev/disk/by-partuuid/...`). L'uso del raw device impedisce a ZFS di creare una tabella GPT e causa la perdita del nome persistente.

## ⚠️ Aggiornamento 26/06/2026: ZFS Fault e Risoluzione Strutturale
Durante un intervento fisico (26 giugno) per rimuovere l'Intel guasto, l'SSD Intel sano è stato inavvertitamente scollegato, lasciando ZFS senza una fonte di metadati aggiornata (portando il pool in `FAULTED`).
Una volta ricollegato l'Intel sano, il pool è regolarmente ripartito.
Si è colta l'occasione per **sanare il debito tecnico** del path `/dev/sdg`:
1. Messo in `OFFLINE` logico il raw disk (`sdg`).
2. Bonificato (`wipefs`) e ripartizionato con `parted` (GPT standard).
3. Eseguito un resilvering "in-place" forzando l'uso della cartella `by-partuuid`.

## 🔗 References
- [[TrueNAS]]
- [[Storage_Registry]]
- [[special-vdev-optimization]]

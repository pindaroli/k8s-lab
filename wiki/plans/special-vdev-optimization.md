# Piano di Ottimizzazione Special VDEV (oliraid) a 64K

Questo piano descrive le azioni operative per ridurre la proprietà `special_small_blocks` del pool `oliraid` da `1M` a `64K` e avviare la bonifica dello spazio sul vdev `special` (SSD mirror da 888 GiB, attualmente al 75.2%).

**Data creazione**: 2026-06-23
**Stato**: ✅ COMPLETATO (25/06/2026)

---

## 📊 Checkpoint di Esecuzione (25/06/2026 — 21:08 CEST)

| Passo | Descrizione | Stato | Note |
| :--- | :--- | :--- | :--- |
| **PASSO 0** | Messa in sicurezza ambiente | ✅ COMPLETATO | NFS/SMB fermati, VM PBS 1400 spenta, backup job disabilitato, replication e snapshot disabilitati |
| **PASSO 1** | `zfs set special_small_blocks=64K oliraid` | ✅ COMPLETATO | 64K ereditato da tutti i 50 dataset figli |
| **PASSO 2** | Distruzione `backup-stripe` (2.30T replica) | ✅ COMPLETATO | SSD: 668G → 658G (-10G). La maggior parte dei dati era sugli HDD. Ricreazione replica rinviata al PASSO 5. |
| **PASSO 2f** | Ricreazione replica `backup-stripe` | ✅ COMPLETATO | Task di replication riabilitato e avviato al PASSO 5. |
| **INCIDENT** | Mirror special DEGRADED | ✅ RISOLTO | Resilver completato al 100% con successo e 0 errori il 24/06/2026. Vedi [[2026-06-24-special-mirror-degraded-replaced-disk]] |
| **PASSO 3** | Migrazione `pbs-store` (297G) | ✅ COMPLETATO | Swap del dataset completato con successo. `pbs-store` a 64K attivo e montato. |
| **PASSO 4** | Verifica obiettivo (SSD < 40%) | 🔄 SUPERATO | Spazio Special VDEV a 652G (73.4%). La bonifica di `arrdata` viene eseguita attivamente tramite riscrittura nel piano [[oliraid-expansion-special-vdev-evacuation]]. |
| **PASSO 5** | Ripristino ambiente | ✅ COMPLETATO | NFS/SMB attivi, LXC PBS avviato, Backup Job abilitato, backup di test superato. |

### Dati SSD Special (Baseline vs Attuale)

| Metrica | Baseline (23/06) | Dopo PASSO 2 | Attuale (25/06) | Obiettivo finale |
| :--- | :--- | :--- | :--- | :--- |
| **ALLOC** | 668G | 658G | 652G | ~250-350G (attraverso evacuazione attiva) |
| **CAP%** | 75.2% | 74.1% | 73.4% | < 40% (attraverso evacuazione attiva) |
| **HEALTH** | ONLINE | DEGRADED (resilver) | ONLINE | ONLINE |

### Prossima azione
La bonifica passiva di `arrdata` è stata superata dal nuovo piano di evacuazione attiva ed espansione pool: [[oliraid-expansion-special-vdev-evacuation]].

---

## 🔍 Contesto e Motivazione

Il vdev `special` del pool [[TrueNAS]] `oliraid` è un mirror SSD SATA da circa 888 GiB composto da:
- `/dev/sdf`: Intel D3-S4510 960GB — Vita residua: 99%
- `/dev/sdh`: Crucial MX500 2TB (partizione da 892 GiB) — Vita residua: 87%

La proprietà `special_small_blocks=1M` impostata al momento della creazione del vdev (giugno 2025) ha causato la scrittura di **tutti i blocchi dati** (inclusi quelli da 128K dei dataset media) sul vdev SSD anziché sugli HDD `raidz2`. Questo ha portato il vdev `special` al **75.2% di utilizzo** (668 GiB su 888 GiB), una soglia di allarme.

**Obiettivo**: Ridurre la proprietà a `64K` (metadati + file ≤ 64KB, es. copertine, file torrent, config SQLite) e riscrivere i dataset principali per spostare i blocchi dati sugli HDD, riportando il vdev SSD a circa il **13-20% di utilizzo** a regime.

---

## 🚨 Punti Critici e Mitigazioni

> [!IMPORTANT]
> **Non retroattività di ZFS**: La modifica di `special_small_blocks` ha effetto solo sui nuovi dati scritti. I blocchi esistenti sul vdev `special` devono essere riallocati tramite riscrittura dei dataset (via `zfs destroy + replica` o `zfs send/recv`).

> [!WARNING]
> **DOWNTIME PIANIFICATO**: Lo stop del servizio NFS su TrueNAS renderà temporaneamente irraggiungibili tutti i servizi K8s che usano storage NFS (Arr Stack, Jellyfin, qBittorrent, n8n). Pianificare in una finestra di manutenzione.

> [!IMPORTANT]
> **PBS su NFS**: Il datastore PBS (`oliraid/pbs-store`, 297 GB) è montato via NFS dalla VM PBS (`10.10.10.100`). La VM PBS deve essere **spenta** prima di qualsiasi operazione sul dataset. Usare Shutdown ordinato da Proxmox, non Power Off.

> [!CAUTION]
> **`backup-stripe` è una replica passiva**: Il dataset `oliraid/backup-stripe` (2.30 TB) è la replica locale del pool NVMe `stripe`. Distruggerlo non comporta perdita di dati live. La replica verrà ricreata al termine.

---

## 📋 Inventario dei Job Automatici da Inibire

| Sistema | Job | Schedule | Azione nel Piano |
| :--- | :--- | :--- | :--- |
| **Proxmox** | Backup VMs → PBS (ID: `e46da171-...`) | Ogni giorno alle **02:00** | Disabilitare in PASSO 0, riabilitare in PASSO 5 |
| **Proxmox** | VM PBS (`10.10.10.100`, VMID: **1400** su PVE1) | — | Shutdown in PASSO 0, Start in PASSO 5 |
| **TrueNAS** | Servizio NFS | Continuo | Stop in PASSO 0, Start in PASSO 5 |
| **TrueNAS** | Servizio SMB | Continuo | Stop in PASSO 0, Start in PASSO 5 |
| **TrueNAS** | Replication: `stripe → oliraid/backup-stripe` | Al completamento snapshot | Disabilitare in PASSO 0, riabilitare in PASSO 5 |
| **TrueNAS** | Snapshot Periodici: dataset `stripe` ogni 12h | `0 */12 * * *` | Disabilitare in PASSO 0, riabilitare in PASSO 5 |
| **TrueNAS** | Scrub: `oliraid` e `stripe` | Ogni domenica alle 00:00 | Nessuna azione (avviene di notte, non interferisce) |

---

## 📋 Fasi Esecutive del Piano

Il piano si articola in 6 passi sequenziali con check di precondizione e di efficacia per ogni operazione critica.

### PASSO 0 — Messa in Sicurezza dell'Ambiente

**Ordine di esecuzione (non alterare la sequenza):**

1. Verifica integrità pool `oliraid` e `stripe`.
2. Verifica nessun backup Proxmox in corso (next run: 24/06/2026 ore 02:00).
3. Disabilitare Backup Job Proxmox verso PBS.
4. Shutdown ordinato VM PBS da Proxmox UI.
5. Stop servizio NFS su TrueNAS.
6. Stop servizio SMB su TrueNAS.
7. Disabilitare Task Replication TrueNAS.
8. Disabilitare Task Snapshot Periodici TrueNAS.
9. Annotare baseline spazio vdev `special` (668G / 75.2%).

**Check di efficacia**: NFS `STOPPED`, SMB `STOPPED`, VM PBS `stopped`.

**Recovery PASSO 0**:
- NFS non si ferma → non procedere, verificare client attivi con `sudo lsof | grep nfs`.
- VM PBS non risponde → attendere 2min, poi Power Off. Verificare integrità datastore al riavvio.

---

### PASSO 1 — Applicazione Nuova Policy `special_small_blocks=64K`

```bash
sudo zfs set special_small_blocks=64K oliraid
```

**Check precondizione**: Pool ONLINE, no scrub in corso, valore attuale `1M`.
**Check efficacia**: Valore `64K` ereditato da tutti i dataset figli.

---

### PASSO 2 — Bonifica `backup-stripe` (2.30 TB, replica passiva)

1. Verifica che `backup-stripe` sia solo una replica passiva di `stripe`.
2. `sudo zfs destroy -r oliraid/backup-stripe`
3. Attendere deallocazione (10-30 secondi).
4. Avviare manualmente il task di Replication da TrueNAS UI per ricreare `oliraid/backup-stripe`.

**Check precondizione**: Nessun job replica in RUNNING, baseline spazio annotato.
**Check efficacia**: Dataset rimosso, poi ricreato con policy `64K` ereditata. Spazio vdev `special` ridotto significativamente (atteso -150/300 GB).

**Recovery PASSO 2**: In caso di errore nel `zfs destroy`, verificare snapshot pendenti con `zfs list -t snapshot oliraid/backup-stripe`. Distruggerli prima con `zfs destroy oliraid/backup-stripe@<snap>`.

---

### PASSO 3 — Bonifica Datastore PBS (`pbs-store`, 297 GB)

> La VM PBS è già spenta dal PASSO 0. NFS è già fermo. Si può operare direttamente.

1. `sudo zfs snapshot oliraid/pbs-store@migration-64k`
2. `sudo zfs send -R oliraid/pbs-store@migration-64k | sudo zfs recv oliraid/pbs-store-temp` (30-90 min)
3. `sudo zfs destroy -r oliraid/pbs-store`
4. `sudo zfs rename oliraid/pbs-store-temp oliraid/pbs-store`

**Check precondizione**: Spazio libero su oliraid > 400 GB, VM PBS confermata spenta.
**Check efficacia**: Nuovo dataset con policy `64K` ereditata. Ulteriore riduzione spazio vdev `special`.

**Recovery PASSO 3**: Se `zfs recv` fallisce a metà, il dataset `-temp` potrebbe essere parziale. Distruggerlo con `zfs destroy -r oliraid/pbs-store-temp` e ripetere dall'inizio del PASSO 3.

---

### PASSO 4 — Verifica Obiettivo (Aggiornato)

> [!NOTE]
> L'evoluzione passiva inizialmente prevista per il dataset `arrdata` (9.51 TB) è stata sostituita da una procedura di evacuazione attiva tramite `zfs rewrite` in combinazione con l'espansione geometrica del pool a 5 dischi.
> Vedi il nuovo piano: [[oliraid-expansion-special-vdev-evacuation]].

---

### PASSO 5 — Ripristino dell'Ambiente

**Ordine di esecuzione (inverso rispetto al PASSO 0):**

1. Riabilitare Task Snapshot Periodici TrueNAS (`stripe`, ogni 12h).
2. Riabilitare Task Replication TrueNAS (`stripe → oliraid/backup-stripe`).
3. Avviare servizio SMB su TrueNAS.
4. Avviare servizio NFS su TrueNAS.
5. Start VM PBS da Proxmox UI (attendere 30-60 secondi).
6. Riabilitare Backup Job Proxmox verso PBS.

**Check efficacia**: NFS `RUNNING`, datastore PBS visibile e accessibile, backup manuale di test su PBS completato con successo.

**Recovery PASSO 5**:
- NFS non si avvia → verificare log `journalctl -u nfs-kernel-server`.
- PBS non vede il datastore → verificare mount NFS dentro la VM con `df -h | grep pbs`, forzare con `mount -a`.

---

## Relazioni
- Riguarda: [[TrueNAS]] (pool `oliraid`, vdev `special`)
- Impatta temporaneamente: [[Servarr]], [[Tdarr]], PBS
- Documentazione storage: [[Storage_Registry]]

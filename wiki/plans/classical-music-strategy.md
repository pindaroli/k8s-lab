# Piano: Strategia di Ingestione e Bonifica per la Musica Classica

**Stato**: 🔵 Implementato — Pipeline operativa
**Data**: 2026-05-17
**Obiettivo**: Segregazione fisica e logica della musica classica dal raggio d'azione di Lidarr, con una pipeline batch autonoma che preserva l'ontologia classica (Compositore → Opera → Direttore/Orchestra → Movimenti).

> [!NOTE]
> **Architettura Storage**: staging e library sono **subdirectory dello stesso dataset ZFS** (`oliraid/arrdata/classical`). Questo abilita i hardlink ZFS (`import.link: yes` in Beets), preservando il seeding qBittorrent a zero costo di spazio disco.


---

## Razionale: Perché la Classica Non Può Stare con Lidarr

Il modello "Artista-Album-Traccia" di Lidarr è incompatibile con la musica classica:
- Il compositore storico (es. Beethoven) viene confuso con l'esecutore (es. Karajan)
- I movimenti sinfonici vengono trattati come tracce pop indipendenti
- I mega-boxset (Mozart 225, 200 CD) saturano le API MusicBrainz con rate limiting
- Lidarr rinomina/sposta le cartelle distruggendo la struttura gerarchica

**Soluzione**: Pipeline parallela, dataset ZFS separati, beets con config dedicata.

---

## 1. Layout di Storage (TrueNAS SCALE — ZFS)

| Dataset / Mount Point | Recordsize | Compressione | Snapshot | Accesso K8s | Ruolo |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `.../music/pop_rock` | `1M` | `lz4` | Giornaliera | Lidarr (RW) | Pipeline standard automatizzata |
| `/Volumes/classical/library` | `1M` | `lz4` | Oraria (in import) | Jellyfin/Navidrome (RO) | **Destinazione finale classica** |
| `/Volumes/classical/staging` | `1M` | `lz4` | Nessuna | Solo Mac Studio | Area transazionale temporanea |

> [!IMPORTANT]
> Lidarr NON ha mount su `.../music/classical`. Il dataset classico è invisibile al daemon Lidarr.
>
> **Nota Sistemistica (Duplicazione Storage & Seeding)**:
> A causa del funzionamento di Beets/Mutagen (riscrittura fisica del file per i nuovi tag `.m4a` via NFS che non sfrutta in-place copy o `copy_file_range` macOS-side), la creazione iniziale dell'hardlink viene rotta durante la scrittura dei metadati.
> - **Scelta Operativa**: Si accetta la duplicazione temporanea dello spazio su ZFS per preservare l'integrità dei tag interni (`write: yes`) e il seeding su qBittorrent.
> - **Cleanup Staging**: Sarà cura dell'utente ripulire manualmente l'area `/Volumes/classical/staging` una volta completato l'intero processo di importazione e seeding.
> - **Evoluzione Futura (Automazione)**: Sviluppare un meccanismo di cleanup automatico dei file in staging post-seeding o uno script di deduplica differita direttamente sul NAS (`jdupes`/`duperemove` che fonde i blocchi duplicati tramite il ZFS Block Cloning locale del pool `oliraid`).

---

## 2. Struttura dell'Isola Operativa

Tutti i file della pipeline risiedono in un'unica directory autocontenuta:

```
k8s-lab/import_music/import_classical/
│
├── run_import.sh                  ← Entry point unico (launcher)
├── segregate_classical.py         ← Fase 1: identifica e isola la classica
├── import_classical_batches.py    ← Fase 2: import beets con resume automatico
├── beets_classical_config.yaml    ← Config beets dedicata (DB, path, plugin)
│
├── [classical_targets.txt]        ← Generato da reset: lista master dello staging
├── [classical_success.log]        ← Generato dall'import: traccia il resume
├── [classical_anomalies.log]      ← Generato dall'import: cartelle con problemi
├── [classical_musiclibrary.db]    ← Database SQLite beets classica
├── [classical_state.pickle]       ← Stato incrementale beets
├── [classical_raw.log]            ← Output grezzo di beets per debug
└── [beets_classical_batch.log]    ← Log interno beets
```

> [!NOTE]
> I file tra `[...]` sono generati automaticamente durante l'esecuzione.

---

## 3. Comandi Operativi

Tutto viene invocato tramite il launcher unico:

```bash
cd /Users/olindo/prj/k8s-lab/import_music/import_classical
./run_import.sh <comando>
```

| Comando | Fase | Effetto | Modifica FS? |
| :--- | :--- | :--- | :--- |
| `segregate-dry` | 1 | Stampa le cartelle classiche identificate nelle anomalie | ❌ |
| `segregate` | 1 | Sposta fisicamente le cartelle in `classical_staging` | ✅ (chiede conferma) |
| `reset` | 2 | Cancella DB/log/stato e ri-scansiona staging | ✅ |
| `batch <N>` | 2 | Importa le prossime N cartelle (riprende da dove era rimasto) | ✅ |
| `control` | 2 | Mostra avanzamento: totali / successi / anomalie / % | ❌ |
| `recover <N>` | 2 | Re-importa N cartelle con errori tecnici (crash/timeout) | ✅ |
| `import-dry` | 2 | Preview beets senza modifiche | ❌ |
| `status` | — | Statistiche DB beets (`beet stats`) | ❌ |
| `triage` | — | Lista file in `_Triage_Unmatched` per Picard | ❌ |

---

## 4. Flusso Dati End-to-End

```
import_anomalies.log           ← prodotta dalla pipeline pop/rock (già esistente)
        │
        │  Fase 1: segregate_classical.py
        │  Euristiche: keyword nel path + tag mutagen (COMPOSER, genre=classical)
        │  shutil.move() → atomico su ZFS (nessuna copia di dati)
        ▼
/Volumes/arrdata/classical/staging/           ← stessa dataset di library → hardlink possibili
        │
        │  Fase 2: import_classical_batches.py → beet import -q (link: yes)
        │  Plugin: parentwork, inline, chroma, discogs
        │  Match sicuro → classical/library/$clean_composer/$parentwork/...
        │  Match fallito → classical/library/_Triage_Unmatched/...
        │  Resume: classical_success.log + classical_targets.txt
        ▼
/Volumes/arrdata/classical/library/                   ← Beets hardlinka qui (stesso inode)
├── Ludwig van Beethoven/
│   └── Symphony No. 9 in D minor [1824] - Karajan, Berliner Philharmoniker/
│       ├── 101 - Allegro ma non troppo.flac
│       └── ...
├── Wolfgang Amadeus Mozart/
│   └── Don Giovanni [1787] - Abbado, Wiener Philharmoniker/
└── _Triage_Unmatched/         ← per revisione manuale con Picard

# Staging: /Volumes/arrdata/classical/staging/
# i file originali restano qui (stesso inode via hardlink), seeding qBT attivo
```

---

## 5. Meccanismo di Resume

Il resume funziona tramite due file log persistenti:

- **`classical_targets.txt`**: lista master delle cartelle da processare (generata da `reset`, immutabile).
- **`classical_success.log`**: ogni cartella elaborata (successo *o* anomalia) viene scritta qui. Al prossimo `batch`, il set viene caricato e sottratto dalla lista master.

```
Se interrotto con Ctrl+C:
  → La cartella corrente NON viene scritta nel log
  → Il prossimo ./run_import.sh batch N riprende esattamente da quella cartella
```

---

## 6. Config Beets — Ontologia Classica

Il file `beets_classical_config.yaml` è il cuore della pipeline. Differenze chiave rispetto alla config standard:

| Parametro | Config standard | Config classica | Motivo |
| :--- | :--- | :--- | :--- |
| `quiet_fallback` | `skip` | `asis` | I fallimenti vanno in _Triage_, non persi |
| `paths.default` | `$albumartist/...` | `$clean_composer/$parentwork/...` | Compositore come radice gerarchica |
| Plugin `parentwork` | assente | `force: yes, auto: yes` | Risale all'opera madre su MusicBrainz |
| Plugin `inline` | assente | custom fields | `clean_composer`, `clean_conductor`, `clean_title` |
| `strong_rec_thresh` | `0.17` | `0.15` | Più conservativo: meglio il triage che i metadati sbagliati |
| `TIMEOUT_SECONDS` | 600s | 900s | I cofanetti richiedono più tempo sulle API |

---

## 7. Workflow Overnight (Esempio Pratico)

```bash
cd /Users/olindo/prj/k8s-lab/import_music/import_classical

# Step 1: verifica quante cartelle vengono identificate come classica
./run_import.sh segregate-dry

# Step 2: esegui la segregazione fisica (sposta in /Volumes/arrdata/classical/staging/)
./run_import.sh segregate

# Step 3: inizializza la lista master dei target
./run_import.sh reset

# Step 4: avvia il batch (lascia girare overnight)
./run_import.sh batch 500

# Il giorno dopo: stato
./run_import.sh control

# Riprendi i rimanenti
./run_import.sh batch 500

# Verifica gli scarti
./run_import.sh triage
```

---

## 8. Fase 3: Kubernetes — Mount del Dataset Classico (TODO)

Una volta completato l'import, aggiornare i manifest Helm per esporre la libreria classica ai client di streaming:

```yaml
# In arr-values.yaml — Jellyfin e Navidrome
additionalVolumes:
  - name: music-classical
    nfs:
      server: <IP_TRUENAS>
      path: /mnt/oliraid/arrdata/classical/library
additionalMounts:
  - name: music-classical
    mountPath: /media/music/classical
    readOnly: true
```

In Jellyfin: creare una libreria dedicata "Musica Classica" che punta a `/media/music/classical`, con preferenza per i tag interni (no scraping esterno).

---

## 9. Triage Manuale con Picard + Classical Extras

Le cartelle in `_Triage_Unmatched` richiedono elaborazione manuale:

1. Aprire con **MusicBrainz Picard** + plugin **Classical Extras**
2. Il plugin risale automaticamente all'opera madre e popola le variabili `_cwp_*` e `_cea_*`
3. Mappare le variabili nascoste nei tag ID3v2.4 / Vorbis Comment tramite le regole di tag mapping
4. Salvare e ri-importare con `./run_import.sh batch 1` sulla singola cartella

---

## Dipendenze Software (Mac Studio)

| Tool | Installazione | Ruolo |
| :--- | :--- | :--- |
| `beet` | `pipx install beets` | Engine di tagging e organizzazione |
| `fpcalc` | `brew install chromaprint` | Fingerprinting acustico (AcoustID) |
| `mutagen` | `pip install mutagen` | Ispezione tag audio per le euristiche |
| `python3` | sistema | Runtime script |

---

*Piano redatto da Antigravity AI Engineering — 2026-05-17*
*Ref: [[beets-music-rescue-pipeline]] per la pipeline pop/rock standard*

# Piano: Strategia di Ingestione e Bonifica per la Musica Classica

**Stato**: 🟢 Operativo — Pipeline migrata con successo su Python 3.12 isolato | 🏗️ Estensione K8s & Prefect in corso
**Data**: 2026-06-07
**Obiettivo**: Segregazione fisica e logica della musica classica dal raggio d'azione di Lidarr, con una pipeline batch autonoma che preserva l'ontologia classica (Compositore → Opera → Direttore/Orchestra → Movimenti).

> [!NOTE]
> **Architettura Storage (Isolamento Fisico)**: staging e library sono **subdirectory dello stesso dataset ZFS** (`oliraid/arrdata/classical`). Per garantire l'integrità dei dati e l'isolamento completo, Beets è configurato per eseguire una **copia fisica** (`copy: yes`), permettendo di svuotare lo staging in sicurezza e modificare i tag senza corrompere il seeding qBittorrent.


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
| `/mnt/oliraid/arrdata/classical/library` (o `/Volumes/classical/library`) | `1M` | `lz4` | Oraria (in import) | Jellyfin-Classic/Navidrome (RO) + Prefect Worker (RW) | **Destinazione finale classica** |
| `/mnt/oliraid/arrdata/classical/staging` (o `/Volumes/classical/staging`) | `1M` | `lz4` | Nessuna | qBittorrent/Lidarr-Classic/Prefect Worker (RW) | Area transazionale temporanea |

> [!IMPORTANT]
> Lidarr NON ha mount su `.../music/classical`. Il dataset classico è invisibile al daemon Lidarr.
>
> **Nota Sistemistica (Duplicazione Operativa & Copia Fisica)**:
> L'uso dei symlink e hardlink è stato **ufficialmente deprecato**. Per garantire la sicurezza totale dei dati (isolamento) e l'integrità dei torrent in seeding, la libreria viene popolata tramite copia fisica.
> - **Scelta Operativa**: Si accetta il raddoppio temporaneo dello spazio su ZFS.
> - **Cleanup Staging**: L'utente può svuotare liberamente e senza rischi l'area `/Volumes/classical/staging` una volta completato il seeding.
> - **Evoluzione Futura (Automazione)**: Sviluppare uno script di deduplica differita direttamente sul NAS (`jdupes`/`duperemove` che fonde i blocchi identici tramite il ZFS Block Cloning locale del pool `oliraid`) per azzerare il costo della copia.

---

## 2. Struttura dell'Isola Operativa

Tutti i file della pipeline risiedono in un'unica directory autocontenuta:

```
k8s-lab/import_music/import_classical/
│
├── run_import.sh                  ← Entry point unico (launcher, rileva venv locale)
├── segregate_classical.py         ← Fase 1: identifica e isola la classica
├── import_classical_batches.py    ← Fase 2: import beets con resume automatico
├── beets_classical_config.yaml    ← Config beets dedicata (DB, path, plugin)
│
├── venv/                          ← Ambiente Python 3.12 isolato dedicato (ignorato in .gitignore)
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
| `setup-env` | — | Inizializza/Ripristina l'ambiente locale Python 3.12 (venv) | ✅ |
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
        │  Fase 2: import_classical_batches.py → beet import -q (copy: yes)
        │  Plugin: parentwork, inline, chroma, discogs
        │  Match sicuro → classical/library/$clean_composer/$parentwork/...
        │  Match fallito → classical/library/_Triage_Unmatched/...
        │  Resume: classical_success.log + classical_targets.txt
        ▼
/Volumes/arrdata/classical/library/                   ← Beets copia qui fisicamente (indipendenza)
├── Ludwig van Beethoven/
│   └── Symphony No. 9 in D minor [1824] - Karajan, Berliner Philharmoniker/
│       ├── 101 - Allegro ma non troppo.flac
│       └── ...
├── Wolfgang Amadeus Mozart/
│   └── Don Giovanni [1787] - Abbado, Wiener Philharmoniker/
└── _Triage_Unmatched/         ← per revisione manuale con Picard

# Staging: /Volumes/arrdata/classical/staging/
# i file originali restano qui per il seeding qBT attivo, e possono essere cancellati a piacere
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

## 8. Fase 3: Kubernetes — Mount del Dataset Classico

Una volta completato l'import, aggiornare i manifest Helm per esporre la libreria classica a Jellyfin-Classic e Navidrome in modalità di sola lettura:

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

* **Jellyfin-Classic**: Creare una libreria dedicata "Musica Classica" che punta a `/media/music/classical`, con preferenza per i tag interni (no scraping esterno).
* **Navidrome**: Configurare una library dedicata puntando allo stesso path `/media/music/classical` montato in sola lettura.

---

## 9. Triage Manuale con Picard + Classical Extras

Le cartelle in `_Triage_Unmatched` richiedono elaborazione manuale:

1. Aprire con **MusicBrainz Picard** + plugin **Classical Extras**
2. Il plugin risale automaticamente all'opera madre e popola le variabili `_cwp_*` e `_cea_*`
3. Mappare le variabili nascoste nei tag ID3v2.4 / Vorbis Comment tramite le regole di tag mapping
4. Salvare e ri-importare con `./run_import.sh batch 1` sulla singola cartella

---

## 10. Deviazioni e Segregazioni Straordinarie

Nel corso dell'esecuzione delle altre pipeline, possono essere intercettati falsi positivi di musica classica sfuggiti alle scansioni iniziali:

### 🎼 Giovanni Paisiello & Estratti Soft Recovery (Salvato da Pop/Rock Rescue)
* **Incidente**: Durante la Fase 2 di Soft Recovery Pop/Rock, alcuni artisti e album classici o crossover sono stati rilevati nella lista della soft recovery.
* **Azione correttiva (2026-05-19)**:
  1. Rimozione dei relativi percorsi dal database e dalla lista della soft recovery pop/rock (`paths_to_recover.txt`).
  2. Spostamento delle cartelle identificate alla directory di staging classica `/Volumes/classical/staging/` per essere elaborate dalla pipeline classica dedicata.
  3. **Cartelle Segregate**:
     - `Paisiello/Il Barbiere di Siviglia` -> `/Volumes/classical/staging/Paisiello/Il Barbiere di Siviglia`
     - `Paisiello/La passione` -> `/Volumes/classical/staging/Paisiello/La passione`
     - `Verdi/Verdi - La Traviata [2CD] ... FLAC/CD 1` -> `/Volumes/classical/staging/Verdi/.../CD 1`
     - `Verdi/Verdi - La Traviata [2CD] ... FLAC/CD 2` -> `/Volumes/classical/staging/Verdi/.../CD 2`
  4. Ingestione programmata tramite la pipeline classica (`./run_import.sh batch` dedicato su staging).

---

## Dipendenze Software (Mac Studio — Ambiente Isolato Python 3.12)

> [!IMPORTANT]
> L'ambiente globale `pipx` basato su **Python 3.14.4** causava eccezioni bloccanti (`KeyError: 'aliases'` / `KeyError: 'tracks'`) con AcoustID e MusicBrainz.
> La pipeline è stata migrata con successo su un **ambiente virtuale locale isolato (Python 3.12.13)**.

| Tool / Libreria | Installazione | Ruolo / Dettaglio |
| :--- | :--- | :--- |
| `python3.12` | `brew install python@3.12` | Interprete stabile nel `venv` locale |
| `beet` | Interno al `venv` | Beets versione `2.11.0` (eseguito sotto Python 3.12) |
| `fpcalc` | `brew install chromaprint` | Fingerprinting acustico globale (AcoustID) |
| `mutagen` | Interno al `venv` | Ispezione tag audio per le euristiche |
| `musicbrainzngs` | Interno al `venv` | API Client per lookup metadati MusicBrainz |

---

## 11. Evoluzione Architetturale: Orchestrazione Stateless con Prefect & Dual Media Server

Per estendere l'automazione ed eliminare la dipendenza dall'esecuzione locale sul Mac Studio, l'architettura evolve verso una gestione dichiarativa e stateless su Kubernetes orchestrata da **Prefect**.

### Componenti e Topologia dello Storage
* **Media Storage (File Audio):** Ospitato su TrueNAS via NFS. I download completati da qBittorrent atterrano in `/mnt/oliraid/arrdata/classical/staging`.
* **Database di Stato (Beets DB):** Il database SQLite `classical_musiclibrary.db` è archiviato in modo persistente su **MinIO (S3)** ospitato da TrueNAS.
* **Media Servers (Presentazione):**
  * `jellyfin-classic`: Pod K8s con PVC in **sola lettura** su `/media/music/classical`.
  * `navidrome`: Pod K8s in esecuzione in parallelo, che monta lo **stesso identico PVC** in **sola lettura** puntando al medesimo dataset ZFS della libreria classica.
* **Motore di Esecuzione:** Worker **Prefect** (`prefect-kubernetes`) per l'esecuzione di Job effimeri.

### Il Ciclo di Vita dell'Elaborazione (Workflow)
1. **Fase 1 (Ingestione):** `lidarr-classic` invia il torrent a qBittorrent (categoria `lidarr-classic`). I file atterrano in staging. La gestione automatica di Lidarr rimane disabilitata.
2. **Fase 2 (Innesco):** A download ultimato, qBittorrent usa un webhook per inserire il percorso del file nella **Work Queue di Prefect**. La coda ha un limite di concorrenza = 1 per evitare *rate limiting* e corruzioni di stato.
3. **Fase 3 (Esecuzione Stateless su K8s via Prefect):**
  * **Pull (initContainer):** Scarica il DB SQLite da MinIO e lo posiziona in un volume iper-veloce `emptyDir` del nodo K8s.
  * **Execute (Main Container):** Prefect lancia Beets import in modalità silenziosa per processare il percorso. Beets copia fisicamente i file nella libreria NFS (`/media/music/classical`).
  * **Post-Import (Main Container):** Istruzioni REST API inviate a `lidarr-classic` per rimuovere il monitoraggio sull'album (silenzio). Trigger HTTP di refresh inviati contemporaneamente a `jellyfin-classic` (Jellyfin REST) e `navidrome` (Subsonic `/rest/startScan.view`).
  * **Push (Finally Block):** Salva lo stato del database di Beets ricaricandolo su MinIO S3, assicurando che lo stato persista anche se l'import di una cartella specifica fallisce, per tracciare il resume e i successivi checkpoint.

Vedi anche il piano di refactoring dettagliato: [[prefect-beets-adaptation]].

---

*Piano redatto da Antigravity AI Engineering — 2026-06-07*
*Ref: [[beets-music-rescue-pipeline]] per la pipeline pop/rock standard*

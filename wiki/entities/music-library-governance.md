---
title: "Music Library Governance"
status: archived
certified_for_ai: false
last_updated: "2026-07-05"
confidence: "High"
tags:
  - "#core"
  - "#storage"
provenance:
  - "beets-music-rescue-pipeline.md"
  - "album-directory-standardization.md"
  - "classical-music-standardization.md"
  - "prefect-beets-adaptation.md"
---

> [!WARNING]
> **DOCUMENTO OBSOLETO / DEPRECATED**
> Questo documento è obsoleto e deprecato. Le procedure di bonifica musicale basate su **Beets** e le directory Landing Zone **`music_backup`** e **`staging`** sono state dismesse e non sono più operative nell'infrastruttura del homelab. Non deve essere utilizzato dagli agenti IA come riferimento operativo.

# Music Library Governance


Questo documento definisce gli standard e le convenzioni per la gestione della libreria musicale nel progetto GEMINI, strutturata secondo il paradigma **Dual-Pipeline (Pop/Rock standard vs Isola Classica)**.

---

## 📂 Struttura del File System

La libreria è organizzata fisicamente in due dataset ZFS separati per garantire la massima compatibilità con **Lidarr**, **Beets**, e **Jellyfin**, prevenendo collisioni ontologiche.

### 1. Modern Music (Pop/Rock/Electronic)
Gestito autonomamente da `lidarr-pop` in lettura/scrittura.
* **Percorso**: `/Volumes/arrdata/media/music/pop_rock/{Artista}/{Album} ({Anno})/{Artista} - {Album} - {Traccia} - {Titolo}`
* **Esempio**: `Akon/Freedom (2008)/Akon - Freedom - 01 - Right Now (Na Na Na).mp3`
* **Compilation e Colonne Sonore (OST)**:
  * **Percorso**: `Compilations/{Album} ({Anno})/{Traccia} - {Titolo}`
  * **Regola**: L'album deve avere il flag `compilation: True` e l'artista dell'album impostato su `Various Artists`.
* **Singoli e Brani Sparsi**:
  * **Percorso**: `Non-Album/{Artista}/{Titolo}`

### 2. Classical Music (Isola Classica Curata)
Pristine e isolata da Lidarr. Curata tramite Beets CLI + Picard.
* **Percorso**: `/Volumes/classical/library/{Compositore}/{Opera} [{Anno}] - {Esecutori}/{CD-Traccia} - {Titolo Movimento}`
* **Regola**: Il tag `genre` deve essere impostato esplicitamente su `classical`.
* **Esempio**: `Ludwig van Beethoven/Symphony No. 9 in D minor [1824] - Karajan, Berliner Philharmoniker/101 - Allegro ma non troppo.flac`

> [!IMPORTANT]
> **ISOLAMENTO FISICO (COPY)**: La libreria classica è strutturata tramite copie fisiche isolate dall'area di staging (`copy: yes` in Beets). Questo garantisce che la libreria sia indipendente e prevenga la perdita di dati in caso di cancellazione dello staging, permettendo inoltre l'editing sicuro dei tag ID3 senza corrompere i file in seeding. L'uso dei symlink o hardlink è formalmente deprecato (vedi [[nfs-symlink-portability]]).

---

## 🏷️ Standard di Metadati

### Naming Convention
- **Formato dei File delle Tracce (Standard Unificato)**:
  Tutte le tracce audio seguono rigidamente il pattern **`[Prefisso] - [Titolo].[Estensione]`**, garantendo consistenza e leggibilità ottimali:
  - **Album CD Singolo** (o disctotal = 1):
    * Prefisso: `{track:02}` (Traccia a due cifre).
    * Pattern: `[Traccia] - [Titolo].[Estensione]` (es. `01 - Hells Bells.mp3`)
  - **Album CD Multiplo** (se disctotal > 1 o disc > 1):
    * Prefisso: `{disc:02}-{track:02}` (CD a due cifre + Traccia a due cifre, uniti da trattino `-`).
    * Pattern: `[CD]-[Traccia] - [Titolo].[Estensione]` (es. `01-02 - One Woman.flac`)
- Tutti i file utilizzano il **Leading Zero** per le tracce (es. `01`, `02`) per mantenere l'ordine alfabetico corretto nel file system.
- L'anno dell'album è sempre incluso nel nome della cartella tra parentesi tonde (quadre per la classica per indicare l'anno di composizione dell'opera).

### Qualità e Formati
- **FLAC**: Formato preferito per l'archiviazione (Lossless).
- **MP3/AAC**: Accettati per materiale raro o in attesa di upgrade via Lidarr (solo pipeline modern).
- **Note**: Gli album non-FLAC pubblicati negli ultimi 15 anni sono considerati candidati prioritari per il rimpiazzo con versioni ad alta qualità.

---

## 🎨 Regole di Standardizzazione e Bonifica Avanzata

Per garantire che la Landing Zone `/Volumes/arrdata/media/music_backup/` sia sempre pulita, priva di doppioni e coerente, sono state codificate le seguenti regole e automatismi:

### 1. Standardizzazione Nomi Cartelle (`[Anno] Titolo Album`)
* **Regola**: Tutte le cartelle degli album devono tassativamente seguire il formato `[Anno] Titolo Album` (es. `[2003] Trouble`) al posto del formato storico `Titolo Album (Anno)`.
* **Automazione**: Lo script `standardize_album_paths.py` sposta fisicamente i file, aggiorna i percorsi a database Beets per mantenere la consistenza relazionale e rimuove le cartelle vuote residue.
* **Eccezioni**: Se l'anno nei metadati Beets è `0` o mancante, lo script tenta di estrarre l'anno dal nome della cartella originale prima di ripiegare su `[0000]`.

### 2. Fattorizzazione dei Featuring (`feat.`) nei Nomi Artista
* **Problema**: L'inserimento dei featuring nel tag dell'artista (es. `Akon Feat. 2Pac`) frammenta la libreria in decine di cartelle madri separate sul disco (es. `/Akon Feat. 2Pac`, `/Akon Feat. Styles P`).
* **Regola**: L'artista dell'album e l'artista del brano devono essere **fattorizzati all'artista principale** (es. `Akon`). L'artista ospite viene rimosso dal nome artista e **spostato in coda al titolo del brano** nel formato `(feat. NomeOspite)` (es. `Lonely (Unreleased) (feat. 2Pac)`).
* **Automazione**: Lo script `factorize_features.py` esegue questa pulizia in modo generalizzato su tutta la libreria a database. Successivamente, la standardizzazione dei percorsi sposta e rinomina fisicamente i file nella cartella dell'artista principale.

### 3. Allineamento Database & Bonifica Duplicati Orfani
* **Integrità del DB**: Qualunque modifica fisica dei file o dei percorsi deve avvenire **sempre** tramite script o API Beets per mantenere il database `musiclibrary.db` sincronizzato. È vietato fare spostamenti massivi con comandi bash manuali (`mv`, `rename`).
* **Rimozione File Orfani**: I file fisici sul disco che non risultano tracciati nel database Beets (confrontati tramite scansione della libreria e set dei percorsi del DB) e che sono duplicati di tracce corrette, devono essere eliminati.
* **Risoluzione Duplicazioni DB**: In caso di doppie importazioni dello stesso album (es. una tracciata correttamente e una con tracce minuscole o parziali), il set duplicato/incompleto deve essere rimosso dal database con `item.remove()` e i rispettivi file fisici eliminati dal disco.

### 4. Risoluzione dei file con Anno `[0000]` (Strategia B - Consolidamento Singoli)
* **Contesto**: La presenza di cartelle `[0000]` o `[0000] Unknown Album` indica metadati mancanti (anno `0`) a database Beets. Questo disordine è causato dall'importazione "as-is" di singoli brani o album reali senza matching su MusicBrainz.
* **Regola di Consolidamento**: Per evitare di avere decine di finti album con anno zero sul disco:
  * **Brani Sparsi (<= 2 tracce per gruppo)**: Vengono estratti dall'album fittizio, privati dell'associazione album (`album = ""`, `albumartist = ""`, `album_id = None`) e trasformati ufficialmente in **Singletons**.
  * **Spostamento Fisico**: Vengono consolidati nella cartella unificata per artista under `/Non-Album/` (es. `/Non-Album/{Artista}/{Titolo}.ext`).
  * **Album Reali (> 2 tracce)**: Non vengono convertiti in singletons. Vengono mantenuti temporaneamente come `[0000]` in attesa di un tag manuale dell'anno corretto via `beet modify album="..." year=YYYY` o di re-importazione con MusicBrainz, che li sposterà in automatico nel percorso corretto.
* **Automazione**: Lo script `consolidate_singles.py` automatizza l'intero ciclo di pre-analisi, backup, conversione in singleton a database, spostamento fisico e rimozione delle cartelle vuote residue.

### 5. Eliminazione dei File e Metadati Totalmente Anonimi (Purge)
* **Regola**: Se un file musicale non ha né un artista identificabile (es. `Unknown Artist` o vuoto) né un titolo/traccia identificabile (es. `Track 12`, `Unknown Title` o vuoto), il file è considerato privo di qualsiasi utilità e valore archivistico.
* **Azione**: Tali elementi devono essere eliminati in modo definitivo sia dal database Beets (`item.remove()`) sia dal filesystem (`os.remove()`).
* **Automazione**: Lo script `purge_anonymous.py` esegue una scansione relazionale per identificare tali file spuri, esegue un backup preventivo del database e procede all'elimazione totale logica e fisica, rimuovendo anche le cartelle madre rimaste vuote.

### 6. Risoluzione Conflitti Compilation vs Album Singolo Artista (Caso "The Who - Tommy")
* **Problema**: Album realizzati da un singolo gruppo/artista (es. `Tommy` dei `The Who`) che vengono erroneamente taggati o importati con `albumartist` impostato su `Artisti Vari` (compilation). Questo li frammenta sul disco sotto `/Artisti Vari/` e causa l'isolamento di singole tracce orfane (es. `Tommy (overture)`) che finiscono erroneamente in `/Non-Album/` poiché prive del corretto `album_id`.
* **Regola di Risoluzione**:
  * **Allineamento Record Album**: Il record dell'album nella tabella `albums` deve avere `albumartist` uguale all'artista reale (es. `The Who`).
  * **Allineamento Tracce (Items)**: Tutte le tracce associate devono avere `albumartist` dell'artista reale. Eventuali tracce orfane o isolate devono essere collegate all'album corretto compilando il rispettivo `album_id` (che punta al record album) e impostando il numero traccia corretto (`track`).
  * **Riposizionamento Fisico**: L'esecuzione di `standardize_album_paths.py --artist "Nome Artista" --run` sposterà fisicamente l'album intero (incluse le tracce precedentemente orfane) sotto il percorso dell'artista (`/{Artista}/[Anno] Album/`) e ripulirà le cartelle vuote residue.

### 7. Bonifica Intelligente dei Duplicati ad Anno 0 (Mirror Clean)
* **Problema**: La case-sensitivity dei filesystem Linux (ZFS su TrueNAS SCALE) combinata con importazioni Beets non allineate può causare la creazione di duplicati speculari interi ad Anno 0. Questo avviene in due forme: cartelle separate ad anno `[0000]` vs `[YYYY]`, oppure file duplicati con differenze di case nella stessa cartella (es. `01 - Mi Fai Stare Bene.mp3` vs `01 - Mi fai stare bene.mp3`).
* **Regola di Sicurezza (Thresholding)**: Un album ad Anno 0 è considerato un duplicato sicuro da eliminare solo se esiste già una copia pulita (con anno > 0) dello stesso album che contiene almeno lo stesso numero di tracce della copia sporca (e con un minimo di 3 tracce). Se la copia sporca ha più tracce (es. album incompleto con anno), l'operazione viene saltata per prevenire perdite.
* **Azione**:
  * Rimozione logica delle tracce ad Anno 0 dal database Beets.
  * Rimozione fisica dei file duplicati (evitando di toccare file condivisi in caso di collisioni case-clash).
  * Rimozione ricorsiva delle cartelle orfane residue rimaste vuote.
* **Automazione**: Lo script `clean_all_zeros_duplicates.py` automatizza il rilevamento, il thresholding e la bonifica sia a DB che a filesystem.

### 8. Bonifica dei File Audio Orfani / Residui di Importazione (Orphan Clean)
* **Problema**: Importazioni storiche incomplete o cambi di convenzione di naming eseguiti senza l'opzione "move" nativa di Beets possono lasciare sul filesystem migliaia di file audio non tracciati ma fisicamente duplicati di quelli corretti (es. file con il vecchio nome che coesiste come sibling del file tracciato con il nuovo standard).
* **Regola di Rilevamento**: Se una directory contiene almeno un file audio tracciato a DB, tutti gli altri file con estensione audio presenti nella stessa cartella che *non* compaiono nella tabella `items` del DB Beets sono considerati residui spuri sicuri da rimuovere.
* **Azione**: Scansione ricorsiva del filesystem, confronto con i percorsi relativi del DB, eliminazione fisica dei file audio orfani identificati (preservando i metadati non audio come copertine o log) e conservazione delle cartelle di triage/staging.
* **Automazione**: Lo script `clean_untracked_orphans.py` automatizza l'audit del filesystem e la bonifica massiva dello spazio sprecato.

### 9. Standardizzazione Unificata dei File Traccia (Track Filename Standardization)
* **Problema**: Convenzioni di naming storiche disomogenee (es. prefissi CD ridondanti negli album singoli, mancanza di separatori coerenti prima del titolo) che compromettono l'ordine e la pulizia estetica delle cartelle album.
* **Regola**: Tutte le tracce audio sul filesystem devono uniformarsi al formato standardizzato `[Prefisso] - [Titolo].[Estensione]`, rimuovendo il prefisso CD se l'album è a disco singolo e utilizzando il trattino `-` come unificatore nei CD multipli.
* **Azione**: Ridenominazione fisica dei file sul disco e contestuale aggiornamento a DB per prevenire disallineamenti logici.
* **Automazione**: Lo script `standardize_track_filenames.py` automatizza l'audit, il rinominamento fisico ed il caricamento dei percorsi a database Beets.

---

## 🛠️ Strumenti e Plugin (Beets)

La bonifica e la gestione sono affidate a **Beets** con i seguenti plugin critici a seconda del dominio:

| Plugin | Dominio | Scopo |
| :--- | :--- | :--- |
| `chroma` | Entrambi | Fingerprinting audio (AcoustID) per identificare brani con metadati errati. |
| `lastgenre` | Modern | Recupero automatico dei generi musicali da Last.fm. |
| `ihate` | Modern | Filtro automatico per escludere bootleg, video o formati indesiderati. |
| `zero` | Entrambi | Pulizia di tag superflui o commenti inseriti dai cracker/ripper. |
| `scrub` | Entrambi | Rimozione di tutti i tag non standard prima della riscrittura. |
| `parentwork` | Classica | Risale all'opera canonica e al compositore padre interrogando MusicBrainz. |
| `inline` | Classica | Esegue codice Python inline per formattare cartelle e tracklist multi-disc. |

---

## 📜 Procedure Operative

### Aggiunta di Nuova Musica (Modern)
La musica scaricata passa per la "Landing Zone" (`music_backup`) tramite il comando `beet import` prima di essere esposta ai media server e importata in `lidarr-pop`.

### Unificazione Artisti
In caso di nomi duplicati (es. `Us3` vs `US3`), utilizzare `beet modify` per uniformare al nome ufficiale presente su MusicBrainz (vedere [[beets-music-rescue-pipeline]]).

### Modifica Massiva dei Dati (Regola di Sopravvivenza)
> [!CAUTION]
> **MAI eseguire `beet modify` usando query generiche o parziali (es. `album="Nome Album"`).** Questo può causare match collaterali distruttivi sull'intera libreria.
> - Usare SEMPRE query esatte se basate su testo (es. `album::^Nome Esatto$`) o, preferibilmente, identificatori univoci e percorsi assoluti.
> - Prima di eseguire un `modify`, si DEVE SEMPRE fare un `beet ls` con la stessa identica query per verificare preventivamente la lista dei file interessati.

### Pipeline di Migrazione Massiva (Automated Import)
Per importare grosse librerie frammentate (Fase di Migrazione), utilizziamo uno script in Python (`import_music_batches.py`) che orchestra Beets in modo massivo e isolato, secondo questa logica:
1. **Pre-Analisi (Reset)**: Il comando `python3 import_music_batches.py reset` azzera il database, scansiona il disco e crea un file `import_targets.txt` contenente solo le "cartelle foglia" con file audio reali. Viene distrutto anche il file `state.pickle` per evitare falsi skip.
2. **Batch Processing**: Il comando `python3 import_music_batches.py 100` elabora le cartelle in lotti da 100 per non sovraccaricare le API di MusicBrainz o il disco.
3. **Thresholding (Soglia)**: La tolleranza di match (`strong_rec_thresh`) è impostata a `0.17` (83% di confidenza). Gli album sopra questa soglia vengono auto-accettati (`import_success.log`).
4. **Anomalie**: Le cartelle sotto l'83% (o che violano regole come bootleg/promozionali) vengono saltate e loggate in `import_anomalies.log` assieme ai punteggi esatti (Distance) e al comando CLI preimpostato (`CMD: beet import -i ...`) per la risoluzione manuale.

### Ciclo Dual-Pipeline & API Loopback (Classica)
La pipeline classica opera secondo un modello disaccoppiato ("Blackhole") orchestrato da **Prefect** su Kubernetes:
1. L'istanza K8s `lidarr-classic` inoltra i download a qBittorrent (categoria `classical`). I file atterrano in staging. La gestione automatica di Lidarr rimane disabilitata.
2. A download ultimato, qBittorrent usa un webhook per inserire il percorso nella **Work Queue di Prefect** (concorrenza = 1 per evitare rate limiting MusicBrainz e race conditions sul DB).
3. Il worker Prefect (`prefect-kubernetes`) lancia un Job K8s effimero:
   - **Pull (initContainer):** Scarica `classical_musiclibrary.db` da **MinIO (S3)** in un volume `emptyDir` locale al nodo (veloce, no lock NFS).
   - **Execute:** Beets importa lo staging ed esegue una copia fisica del materiale nella libreria NFS (`/media/music/classical`), con metadati ID3/Vorbis ottimizzati per la tassonomia Compositore → Opera.
   - **Post-Import:** Il Task `sync_media_servers` invia via REST API:
     - A `lidarr-classic`: rimozione di `monitored` **esclusivamente sul singolo album appena elaborato** (non su tutta la discografia), evitando loop infiniti di download.
     - A `jellyfin-classic`: trigger refresh libreria (REST Jellyfin).
     - A `navidrome`: trigger refresh libreria (Subsonic API `/rest/startScan.view`).
   - **Push (Finally):** Lo stato del DB Beets viene ricaricato atomicamente su MinIO, garantendo persistenza anche in caso di errore parziale.
4. **Dual-Stack (Jellyfin + Navidrome):** Entrambi i media server montano il **medesimo PVC in sola lettura** sul dataset ZFS classico. Jellyfin opera con tutti gli scraper disabilitati (metadati embedded da Beets). Navidrome funge da server Subsonic per client mobili.

Vedi il piano di refactoring dettagliato: [[prefect-beets-adaptation]].

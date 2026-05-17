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

---

## 🏷️ Standard di Metadati

### Naming Convention
- Tutti i file utilizzano il **Leading Zero** per le tracce (es. `01`, `02`) per mantenere l'ordine alfabetico corretto nel file system.
- L'anno dell'album è sempre incluso nel nome della cartella tra parentesi tonde (quadre per la classica per indicare l'anno di composizione dell'opera).

### Qualità e Formati
- **FLAC**: Formato preferito per l'archiviazione (Lossless).
- **MP3/AAC**: Accettati per materiale raro o in attesa di upgrade via Lidarr (solo pipeline modern).
- **Note**: Gli album non-FLAC pubblicati negli ultimi 15 anni sono considerati candidati prioritari per il rimpiazzo con versioni ad alta qualità.

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
La pipeline classica opera secondo un modello disaccoppiato ("Blackhole"):
1. L'istanza K8s `lidarr-classical` inoltra i download a qBittorrent con la categoria `music-classical`.
2. Una volta completati in `/staging/classical`, `lidarr-classical` NON esegue l'importazione (Completed Download Handling disabilitato).
3. Beets processa lo staging ed esporta la traccia pulita nel dataset ZFS classico (`/media/music/classical`).
4. Uno script di unmonitoring API (`segregate_classical.py` richiamato come hook post-import) interroga `lidarr-classical` via REST e spegne il monitoraggio dell'album per evitare loop di download infiniti.
5. Jellyfin monta il dataset classico in **Sola Lettura** e con tutti gli **scraper disabilitati** (via ConfigMap `options.xml`), forzando l'utilizzo esclusivo dei metadati embedded di Beets.

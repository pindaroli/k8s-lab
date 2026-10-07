---
title: "Unificazione Versioni Multiple Film Jellyfin & Gestione Automatica Release Preesistenti"
type: plan
status: active
certified_for_ai: true
created_at: 2026-10-07
tags:
  - "#servarr"
  - "#jellyfin"
  - "#filebot"
  - "#normalizer"
---

# Piano Operativo: Unificazione Versioni Multiple Film Jellyfin & Gestione Automatica Release Preesistenti (v2)

> [!IMPORTANT]
> **Stato del Piano**: In attesa di approvazione finale da parte dell'utente per avviare l'esecuzione.
> **Obiettivo**: 
> 1. Creare uno script shell/python parametrico per Mac/TrueNAS (`sanitize_movie_folder.sh`) che accetti in input il nome della cartella o il nome del file completo di estensione (anche via prompt interattivo). Se la **cartella genitore non è normalizzata**, la normalizza nel formato canonico `Titolo (Anno) {tmdb-ID}` (o la fonde con quella normalizzata già esistente). Dopodiché sani i video legacy non normalizzati (`ffprobe` risoluzione + codec), allinei i sottotitoli `.srt`, elimini gli artwork ridondanti ed effettui il refresh di Jellyfin per esporre una singola scheda con menu a tendina.
> 2. Integrare tale logica di sanificazione e pulizia artwork direttamente nella pipeline di normalizzazione video (`normalize-video.sh` in `custom-normalizer`), gestendo in automatico qualsiasi caso futuro in cui una nuova release finisca in una cartella con versioni preesistenti non normalizzate.

---

## 🗺️ 1. Decisioni Architetturali Approvate dall'Utente

| Decisione | Scelta Utente | Dettaglio Operativo |
| :--- | :--- | :--- |
| **Etichetta Versione Legacy** | **Opzione A** (Risoluzione + Codec) | `ffprobe` rileva altezza e video codec: es. `[576p XviD]`, `[480p MPEG4]`, `[720p H264]`. |
| **Sincronizzazione Subtitles** | **Confermata** | Tutti i file `.srt`/`.sub` associati al vecchio file seguono la nuova denominazione del video (es. `... - [576p XviD].it.srt`). |
| **Purge Artwork Ridondanti** | **Confermata** | Rimozione selettiva dei file `*-poster.jpg`, `*-backdrop.jpg`, `*-landscape.jpg`, `*-logo.png`. Mantenimento dei soli file canonici di cartella (`poster.jpg`, `fanart.jpg`/`backdrop.jpg`, `folder.jpg`, `logo.png`, `disc.png`, `clearart.png`). |
| **Modalità Script `.sh`** | **Opzione A Parametrica** | Script launcher per Mac (`sanitize_movie_folder.sh`) via SSH BatchMode verso TrueNAS `10.10.20.50`. |
| **Parametrizzazione Input** | **Flessibile (CLI + Prompt)** | Accetta come argomento o prompt: nome cartella, path cartella o **nome del file completo di estensione** (es. `Trainspotting (1996).avi`). Se non fornito da CLI, richiede l'input all'utente tramite prompt interattivo. |
| **Normalizzazione Cartella** | **Aggiunta (Requisito 4)** | Se la cartella del film non rispetta il formato `Titolo (Anno) {tmdb-ID}`, lo script ne ricava l'identità TMDb (da file interni, da Jellyfin API o da lookup TMDb), **rinomina la cartella al formato canonico**, oppure la unifica a quella canonica se già presente sul NAS. |

---

## 🏗️ 2. Deliverable e Dettaglio Tecnico

### Deliverable 1: Script `scripts/servarr/sanitize_movie_folder.sh` (e modulo Python associato)

#### 1. Input Handling
- **Argomento CLI (`$1`)**:
  - Se specificato: può essere il nome della cartella (es. `Trainspotting (1996) {tmdb-627}` oppure `Trainspotting (1996)`), il path completo `/mnt/...`, oppure il nome del file con estensione (es. `Trainspotting (1996).avi`).
  - Se non specificato: entra in modalità interattiva chiedendo all'utente:
    ```text
    👉 Inserisci il nome della cartella o il nome del film completo di estensione (es. 'Trainspotting (1996).avi'):
    ```
- **Risoluzione del Percorso Target su TrueNAS**:
  - Se l'input contiene un'estensione video (`.avi`, `.mkv`, `.mp4`, etc.):
    1. Se il percorso esiste direttamente sul filesystem, ne ricava la cartella genitore (`dirname`).
    2. Se è stato passato solo il basename del file (es. `Trainspotting (1996).avi`), esegue una ricerca mirata in `/mnt/oliraid/arrdata/media/movies/` per individuare la cartella genitore contenente quel file.
  - Se l'input è il nome di una cartella, risolve `/mnt/oliraid/arrdata/media/movies/<NomeCartella>`.

#### 2. Normalizzazione Preventiva della Cartella Genitore
Prima di lavorare sui file interni, lo script verifica la conformità della cartella:
1. **Verifica Regex Standard**:
   - Formato canonico atteso: `^(.+) \((\d{4})\) \{tmdb-\d+\}$`
2. **Se la cartella NON è normalizzata** (es. `Trainspotting (1996)`, `Trainspotting (1996) [tmdbid-627]`, o formati raw torrent):
   - **Estrazione TMDb ID**:
     - Se un file video interno contiene già il tag `{tmdb-XXX}` o `[tmdbid-XXX]`, lo estrae direttamente.
     - Altrimenti, interroga l'API di Jellyfin (`/Items?searchTerm=...`) o effettua lookup rapido per recuperare il TMDb ID ufficiale, il titolo e l'anno.
   - **Costruzione Nome Canonico**:
     `${CANONICAL_TITLE} (${YEAR}) {tmdb-${TMDB_ID}}`
   - **Rinomina o Merge**:
     - Se la cartella canonica non esiste ancora: rinomina la cartella (`os.rename(old_dir, canonical_dir)`).
     - Se la cartella canonica esiste già sul filesystem (es. creata da un download recente e sdoppiata da quella vecchia): sposta i file della vecchia cartella dentro quella canonica e rimuove la vecchia cartella svuotata.

#### 3. Logica di Sanificazione Interna (File Video, Subtitles, Artwork)
1. **Identificazione File Video**:
   - Rileva tutti i file video nella cartella normalizzata (escludendo `.trickplay`, `EXTRAS`, etc.).
   - Distingue:
     - **File già conformi**: iniziano con `${CARTELLA_CANONICA} - [`.
     - **File legacy da sanare**: non iniziano con `${CARTELLA_CANONICA} - [` (es. `Trainspotting (1996).avi`).
2. **Analisi Tecnica (`ffprobe`)**:
   - Estrae la risoluzione video:
     - `>= 2100` -> `4K` o `2160p`
     - `>= 1000` -> `1080p`
     - `>= 700` -> `720p`
     - Altrimenti -> `576p` (o `480p` in base alle dimensioni effettive).
   - Estrae il codec video: `xvid`, `mpeg4`, `h264`, `hevc`, etc.
   - Genera l'etichetta canonica: `[${RES} ${CODEC}]` (es. `[576p XviD]`).
3. **Rinomina Video e Sottotitoli**:
   - Rinomina il video: `${CARTELLA_CANONICA} - [${LABEL}].${ext}`.
   - Cerca i sottotitoli aventi lo stesso stem del vecchio video e li rinomina:
     `${VECCHIO_STEM}.it.srt` -> `${CARTELLA_CANONICA} - [${LABEL}].it.srt`.
4. **Pulizia Artwork Duplicati**:
   - Elimina selettivamente tutti i file immagine che terminano con `-poster.jpg`, `-backdrop.jpg`, `-landscape.jpg`, `-logo.png`.
   - Preserva intatti i soli metadati di cartella canonici: `poster.jpg`, `folder.jpg`, `fanart.jpg`, `backdrop.jpg`, `logo.png`, `disc.png`, `clearart.png`.
5. **Jellyfin Refresh API**:
   - Invia la richiesta di refresh HTTP a Jellyfin (`${JELLYFIN_URL}/Library/Refresh`) per ricalcolare istantaneamente le versioni ed esporre il menu a tendina.
6. **Supporto Dry-Run e Conferma**:
   - Modalità simulazione per verificare l'anteprima delle modifiche prima dell'applicazione reale (con opzione `--apply` o conferma interattiva `[s/N]`).

---

### Deliverable 2: Integrazione nel Normalizzatore Automatico (`normalize-video.sh`)

**File target**: `pindaroli-arr-helm/custom-docker-images/custom-normalizer/normalize-video.sh`

#### Modifiche nel flusso di normalizzazione:
Subito dopo l'esecuzione del blocco `process_filebot`:
```bash
# 1. Pulizia post-processo NFO (già presente)
find "$TARGET_DIR" -maxdepth 2 -type f -name "*.nfo" -delete

# 2. Sanificazione automatica release preesistenti nella cartella del film
#    - Individua la cartella creata/aggiornata da FileBot in $TARGET_DIR
#    - Se la cartella del film o i file preesistenti contengono anomalie di naming:
#      * Allinea eventuali file video senza prefisso "${FOLDER_NAME} - ["
#      * Esegue ffprobe per ris+codec e rinomina video e relativi .srt
#      * Rimuove gli artwork generati con prefisso video (*-poster.jpg, etc.)
```
In questo modo, ogni volta che un nuovo download viene processato da FileBot AMC e collocato in una cartella in cui era già presente un file con nome vecchio (o se esisteva una cartella da unificare), tutto viene normalizzato al volo e gli artwork ripuliti in automatico, senza alcun intervento manuale.

---

## 📋 3. Piano di Intervento e Sequenza Operativa

### Fase 1: Implementazione Script di Sanificazione Locale/TrueNAS
1. Creazione dell'engine `scripts/servarr/sanitize_movie_folder.py` su TrueNAS/locale:
   - Risoluzione flessibile dell'input (da nome cartella, path o nome file video con estensione).
   - Controllo e normalizzazione della cartella genitore in `Titolo (Anno) {tmdb-ID}` (con eventuale merge).
   - Analisi `ffprobe`, rinomina video/sub e purge artwork file-specific.
   - Chiamata API Jellyfin per il refresh.
2. Creazione del launcher Bash `scripts/servarr/sanitize_movie_folder.sh`:
   - Gestione input CLI / prompt interattivo se omesso.
   - Esecuzione trasparente su TrueNAS `10.10.20.50` via SSH passwordless.

### Fase 2: Test-Driven Verification sul Caso Reale (*Trainspotting*)
1. Esecuzione in modalità dry-run passando il nome del file:
   ```bash
   ./scripts/servarr/sanitize_movie_folder.sh "Trainspotting (1996).avi"
   ```
   *Verifica*: Ispezione del piano di rinomina generato (verifica che la cartella sia `Trainspotting (1996) {tmdb-627}`, rinomina a `Trainspotting (1996) {tmdb-627} - [576p XviD].avi`, allineamento `.it.srt` e `.en.srt`, lista artwork da rimuovere).
2. Esecuzione reale con applicazione (`--apply` o conferma):
   *Verifica Filesystem*:
   - Cartella normalizzata a `Trainspotting (1996) {tmdb-627}`.
   - I file video presenti nella cartella devono essere due, entrambi con prefisso `Trainspotting (1996) {tmdb-627} - [...]`.
   - Gli artwork duplicati `*-poster.jpg` devono essere stati rimossi.
3. *Verifica Jellyfin*:
   - Controllo interfaccia web di Jellyfin: la scheda film deve essere **una sola**, provvista di menu a tendina con le due versioni (`[2160p HEVC] [NAHOM]` e `[576p XviD]`).

### Fase 3: Modifica e Distribuzione Normalizzatore Automatico
1. Modifica di `normalize-video.sh` in `pindaroli-arr-helm/custom-docker-images/custom-normalizer/`:
   - Aggiunta della routine di post-sanificazione per cartella/versioni preesistenti e pulizia artwork di file.
2. Bump versione in `custom-docker-images/custom-normalizer/VERSION` a `1.7.0`.
3. Commit e build/push dell'immagine su GHCR (`ghcr.io/pindaroli/custom-normalizer:1.7.0`).
4. Aggiornamento del file `servarr/truenas-docker/docker-compose.yaml` su TrueNAS con la nuova tag `1.7.0` e riavvio del container `webhook-normalizer`.

### Fase 4: Chiusura e Documentazione
1. Aggiornamento del pattern architetturale `wiki/patterns/movie-metadata-and-artwork-architecture.md` documentando la regola di sanificazione per cartelle e versioni legacy preesistenti.
2. Validazione sintassi con `validate_network.py` e rigenerazione `build_wiki_context.py`.

---

## 💾 4. Stato di Ripristino (AI Save-State)
- **Fase Attiva**: **COMPLETATO CON SUCCESSO** ✅
- **Ultima Azione Completata**: Test reale su Trainspotting superato (Jellyfin mostra 1 singola scheda con 2 versioni nel menu a tendina), container TrueNAS webhook-normalizer aggiornato a caldo, commit e push su pindaroli-arr-helm (v1.7.0) e k8s-lab completati.
- **Prossimo Passo Operativo**: Nessuno.
- **Blocchi/Decisioni Pendenti**: Nessuno. Lavori conclusi con successo.

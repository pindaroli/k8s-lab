---
title: "Piano: Upgrade Risoluzione 1080p e Remux Audio Italiano di Blackout (1997) {tmdb-25690}"
type: plan
status: archived
archived_at: 2026-10-25
certified_for_ai: false
created_at: 2026-10-13
tags:
  - "#plan"
  - "#servarr"
  - "#remux"
  - "#qbittorrent"
  - "#filebot"
  - "#jellyfin"
---

# Piano: Upgrade Risoluzione 1080p e Remux Audio Italiano di Blackout (1997) {tmdb-25690}

Questo piano definisce la procedura end-to-end per l'aggiornamento qualitativo del film cult ***The Blackout*** (1997) di Abel Ferrara (**TMDb ID: 25690**) all'interno della libreria cinematografica del homelab su TrueNAS SCALE bare-metal (`/media/movies/`).

---

## 🎯 Contesto e Obiettivo Architetturale

1. **Stato Iniziale della Libreria**:
   - Cartella: `/mnt/oliraid/arrdata/media/movies/Blackout (1997) {tmdb-25690}/`
   - File presente: `Blackout (1997).avi` (961 MB, video SD 640x336 Xvid a 25 fps, 2 tracce MP3 stereo) con `Blackout (1997).en.srt`.
2. **Problema**:
   - In Italia *The Blackout* (1997) non è mai stato distribuito in Blu-ray né in digitale HD con master italiano (esiste solo il DVD Cecchi Gori del 2006). Tutte le release 1080p mondiali (da Amazon US o Blu-ray francesi) hanno esclusivamente audio in lingua originale (Inglese).
3. **Strategia Operativa**:
   - Scaricare la migliore versione ad alta risoluzione 1080p disponibile su qBittorrent (**`The Blackout 1997 1080p AMZN WEB-DL H264-GPRS`**, 7.3 GB) assegnando la categoria **`video-filebot`**.
   - Preservare **entrambe le versioni** all'interno della directory del film in modo che coesistano senza sovrascritture.
   - Analizzare le tracce audio del file AVI per il remux.

---

## 🗺️ Matrice Componenti & Release

| Componente | Valore / Dettaglio |
| :--- | :--- |
| **Film** | *The Blackout* (1997) di Abel Ferrara |
| **TMDb ID** | `25690` |
| **Release Target 1080p** | `The Blackout 1997 1080p AMZN WEB-DL H264-GPRS` (7.3 GB) |
| **Indexer Prowlarr** | The Pirate Bay (id: 10) / LimeTorrents (id: 6) |
| **Client Torrent** | qBittorrent su TrueNAS (`10.10.20.50:8080`) |
| **Categoria Download** | `video-filebot` (percorso: `/media/downloads/video-filebot/`) |
| **Normalizzatore** | `webhook-normalizer` (FileBot AMC) porta 9000 su TrueNAS |
| **Libreria Finale** | `/mnt/oliraid/arrdata/media/movies/Blackout (1997) {tmdb-25690}/` |

---

## 🏗️ Fasi Operative

### FASE 1: Grab Release 1080p & Download su qBittorrent (Categoria `video-filebot`)
- [x] Ricerca mirata del rilascio su Prowlarr via MCP `prowlarr_search` (indexer The Pirate Bay / LimeTorrents).
- [x] Invio del torrent a qBittorrent via MCP `prowlarr_grab` specificando `category: "video-filebot"`.
- [x] Verifica aggiunta su qBittorrent con stato `downloading` e percorso `/media/downloads/video-filebot/` (Hash: `a177c28747b39473832f1f928f477ff3014bf932`).
- [x] Monitoraggio del download fino al raggiungimento del 100% (completamento e passaggio a seeding).

#### 🛑 CHECKPOINT FASE 1:
- [x] Torrent completato al 100% in qBittorrent nella cartella `/media/downloads/video-filebot/`.

---

### FASE 2: Ingestion & Coesistenza Multi-Versione in `/media/movies/`
- [x] Innesco del Job di normalizzazione FileBot AMC tramite la skill `video-ingestor` (trigger automatico post-download su TrueNAS).
- [x] Monitoraggio log di FileBot AMC su container Docker `webhook-normalizer` per verificare la creazione dell'hardlink ZFS a costo zero di storage.
- [x] Ispezione filesystem in `/mnt/oliraid/arrdata/media/movies/Blackout (1997) {tmdb-25690}/` per validare che **entrambe le versioni coesistano**:
  1. Versione legacy SD: `Blackout (1997) {tmdb-25690} - [SD XviD].avi`
  2. Versione new 1080p: `Blackout (1997) {tmdb-25690} - [AMZN WEB-DL 1080p AVC] [GPRS].mkv`
- [x] Conferma rimozione automatica file `.nfo` e persistenza artwork canonici (`poster.jpg`, `fanart.jpg`, ecc.).

#### 🛑 CHECKPOINT FASE 2:
- [x] Entrambi i file video (SD e 1080p) presenti e riproducibili nella directory del film.

---

### FASE 3: Analisi Linguistica Tracce Audio dell'AVI Preesistente
- [x] Esecuzione `ffprobe` e campionamento dei due flussi audio MP3 dell'AVI.
- [x] Trascrizione fonetica (Whisper) e verifica utente: accertato che lo `Stream #0:1` è in Inglese e lo `Stream #0:2` è un doppiaggio in Spagnolo castigliano (*"Si me hace una pregunta... Al repasar tu vida..."*).
- [x] Conferma assenza del doppiaggio italiano all'interno del rilascio AVI archiviato.

#### 🛑 CHECKPOINT FASE 3:
- [x] Natura linguistica delle tracce dell'AVI chiarita e documentata.

---

### FASE 4: Bonifica, Risoluzione Scelta Utente (Opzione 1) & Pulizia SD
- [x] Su indicazione dell'utente, adozione dell'Opzione 1: conservazione esclusiva della release in alta definizione 1080p Amazon WEB-DL in lingua originale inglese con sottotitoli.
- [x] Eliminazione del remux errato e rimozione del file a bassa risoluzione `Blackout (1997) {tmdb-25690} - [SD XviD].avi` e relativo `.srt`.
- [x] Directory pulita con solo la release 1080p e artwork master (`poster.jpg`, `fanart.jpg`, `folder.jpg`, `landscape.jpg`, `logo.png`).

#### 🛑 CHECKPOINT FASE 4:
- [x] Libreria sanificata con la sola versione 1080p WEB-DL ad alta qualità.

---

### FASE 5: Validazione Test-Driven & Rescan Jellyfin
- [x] Trigger del rescan della libreria `Movies` in Jellyfin via API REST (`/Items/f137a2dd.../Refresh`).
- [x] Reperimento e sincronizzazione frame-perfect dei sottotitoli italiani (992 cue, PAL-to-NTSC linear time transform `25/23.976` con offset iniziale al millisecondo).
- [x] Materializzazione di `Blackout (1997) {tmdb-25690} - [AMZN WEB-DL 1080p AVC] [GPRS].it.srt` con permessi `olindo:k8s` (`777`).
- [x] Verifica scheda su Jellyfin: visualizzazione pulita della versione 1080p con audio originale E-AC3 e sottotitoli italiani e inglesi.
- [x] Pulizia di tutti i file di test temporanei.

#### 🛑 CHECKPOINT FINALE:
- [x] Film fruibile in 1080p ad alta risoluzione con sottotitoli italiani sincronizzati su Jellyfin.

---

## 💾 Stato di Ripristino (AI Save-State)
- **Fase Attiva**: **PIANO COMPLETATO CON SUCCESSO** ✅ (Fasi 1-5 completate).
- **Ultima Azione Completata**: Clean slate ingestion completata tramite FileBot AMC. Aggiunti i sottotitoli italiani sincronizzati al millisecondo `Blackout (1997) {tmdb-25690} - [AMZN WEB-DL 1080p AVC] [GPRS].it.srt`. Permessi `olindo:k8s` (`777`) impostati e refresh Jellyfin completato.
- **Prossimo Passo Operativo**: Nessuno.
- **Blocchi/Decisioni Pendenti**: Nessuno.

---
title: "Piano: Upgrade Risoluzione 1080p e Remux Audio Italiano di Blackout (1997) {tmdb-25690}"
type: plan
status: active
certified_for_ai: true
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
   - File presente: `Blackout (1997).avi` (961 MB, video SD 640x336 Xvid a 25 fps, 2 tracce MP3 stereo dual audio ITA/ENG) con `Blackout (1997).en.srt`.
2. **Problema**:
   - In Italia *The Blackout* (1997) non è mai stato distribuito in Blu-ray né in digitale HD con master italiano (esiste solo il DVD Cecchi Gori del 2006). Tutte le release 1080p mondiali (da Amazon US o Blu-ray francesi) hanno esclusivamente audio in lingua originale (Inglese).
3. **Strategia Operativa**:
   - Scaricare la migliore versione ad alta risoluzione 1080p disponibile su qBittorrent (**`The Blackout 1997 1080p AMZN WEB-DL H264-GPRS`**, 7.3 GB) assegnando la categoria **`video-filebot`**.
   - Preservare **entrambe le versioni** all'interno della directory del film in modo che coesistano senza sovrascritture.
   - Solo a valle del download e dell'ingestion multi-versione, procedere all'estrazione dell'audio italiano dal file AVI e al remux/sincronizzazione sulla traccia video 1080p, realizzando un **MKV 1080p Dual Audio (ITA / ENG)** conforme agli standard Jellyfin.

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

### FASE 3: Estrazione e Analisi Traccia Audio Italiana dall'AVI Esistente
- [x] Esecuzione `ffprobe` tramite container Jellyfin per analizzare le 2 tracce MP3 stereo del file `Blackout (1997) {tmdb-25690} - [SD XviD].avi`.
- [x] Identificazione della traccia con doppiaggio italiano (Stream 0:1, stereo 48kHz, PAL DVD Cecchi Gori).
- [x] Estrazione della traccia audio italiana e calcolo del rapporto di PAL speedup (`0.959041`).

#### 🛑 CHECKPOINT FASE 3:
- [x] Traccia audio italiana isolata, analizzata e sincronizzata al millisecondo.

---

### FASE 4: Sincronizzazione, Muxing e Creazione MKV 1080p Dual Audio (ITA/ENG)
- [x] Verifica del framerate e dell'offset temporale:
  - Video 1080p WEB-DL: 23.976 fps (offset iniziale al primo parlato a 34.402s).
  - Audio AVI DVD: a 25.000 fps (parlato iniziale a 19.859s).
  - Applicazione correzione temporale `atempo=0.959041` e delay `adelay=13695|13695` (sincronia labiale identica da inizio a fine film).
- [x] Muxing definitivo con `ffmpeg`:
  - Traccia Video: 1080p AVC da Amazon WEB-DL (stream copy senza ricodifica).
  - Traccia Audio 1: Italiano (doppiaggio) AC3 224 kbps con tag `ita` e default.
  - Traccia Audio 2: Inglese (originale) E-AC3 224 kbps con tag `eng`.
  - Sottotitoli: Inglese e Francese inclusi da WEB-DL.
- [x] Posizionamento del nuovo file dual audio MKV nella directory del film:
  `Blackout (1997) {tmdb-25690} - [AMZN WEB-DL 1080p AVC Remux ITA-ENG].mkv`.

#### 🛑 CHECKPOINT FASE 4:
- [x] File MKV 1080p Dual Audio generato e sincronizzato con successo.

---

### FASE 5: Validazione Test-Driven & Rescan Jellyfin
- [x] Trigger del rescan della libreria `Movies` in Jellyfin via API REST (`/Items/f137a2dd.../Refresh`).
- [x] Verifica visualizzazione su Jellyfin:
  - Presenza delle versioni disponibili con switch rapido di qualità.
  - Traccia audio italiana selezionata e sincronizzata.
- [x] Aggiornamento documentazione nel Wiki ed eventuale allineamento archivio.

#### 🛑 CHECKPOINT FINALE:
- [x] Film fruibile in 1080p con audio italiano sincronizzato su Jellyfin.

---

## 💾 Stato di Ripristino (AI Save-State)
- **Fase Attiva**: **PIANO COMPLETATO CON SUCCESSO** ✅ (Fasi 1-5 completate).
- **Ultima Azione Completata**: Generato il remux `Blackout (1997) {tmdb-25690} - [AMZN WEB-DL 1080p AVC Remux ITA-ENG].mkv` (7.0 GB) con video 1080p AVC, audio italiano AC3 (PAL speedup fix applicato a 0.959041 con delay 13.695s) e audio originale inglese. Permessi `olindo:k8s` impostati e refresh Jellyfin avviato.
- **Prossimo Passo Operativo**: Nessuno.
- **Blocchi/Decisioni Pendenti**: Nessuno. Lavori conclusi con successo.

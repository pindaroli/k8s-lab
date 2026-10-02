---
title: "Riprogettazione Reportistica ed Email Normalizzatori (Audio & Video)"
type: plan
status: active
certified_for_ai: true
created_at: 2026-10-01
tags:
  - "#normalizer"
  - "#songkong"
  - "#filebot"
  - "#email"
  - "#reporting"
  - "#apprise"
---

# Riprogettazione Reportistica ed Email Normalizzatori (Audio & Video)

Questo piano definisce la riprogettazione completa del sistema di reportistica e notifica email per entrambi i motori di normalizzazione del homelab:
1. **Audio Normalizer** (`normalize.sh`): splitting CUE/FLAC con `fmedia` e taggatura acustica intelligente con `SongKong Premium`.
2. **Video Normalizer** (`normalize-video.sh`): renaming, tagging TMDb e artwork con `FileBot AMC`.

---

## 🔍 Analisi Approfondita delle Problematiche Rilevate

### Problema 1: Allegato visualizzato come testo grezzo / codice HTML
- **Causa in Gmail**: Quando un utente apre un allegato con estensione `.html` all'interno della webmail di Gmail, Gmail per motivi di sicurezza (anti-XSS) non renderizza la pagina come browser interattivo, ma la apre nel suo visualizzatore integrato in modalità codice sorgente (`<pre>`).
- **Assenza di CSS incorporato (Broken Assets)**: I report nativi di SongKong poggiano su file CSS e JavaScript esterni posizionati in cartelle relative (es. `../style/canvasjs.min.js`, `oxygen-webhelp/resources/css/...`). Inviando solo il singolo file `.html` come allegato, tali risorse risultano mancanti e la pagina risulta illeggibile anche se scaricata in locale.
- **Corpo Email in solo Testo (Plain Text)**: In `utils.sh`, il comando Apprise (`apprise -t "$title" -b "$body" "$apprise_smtp_url"`) non specifica il flag `-i html`. Di conseguenza l'intero corpo della mail viaggia in `text/plain`, costringendo l'utente ad affidarsi unicamente all'allegato per consultare i dettagli.

### Problema 2: Allegato riporta l'Help/Manuale (`toc.html`) invece del report reale
- **Audio Normalizer (`normalize.sh`)**:
  - In `normalize.sh`, la ricerca del report avviene tramite:
    ```bash
    LATEST_REPORT="$(find "$REPORT_DIR" -name "*.html" -type f | sort | tail -n 1 || echo "")"
    ```
  - SongKong include nella cartella `/opt/songkong/webhelp` (e in `/root/.songkong/Reports/webhelp/`) l'intero manuale utente (in formato Oxygen WebHelp).
  - Tra questi file c'è `webhelp/toc.html` (*Table of Contents* del manuale utente di SongKong).
  - Poiché `find` effettua una scansione ricorsiva senza escludere `webhelp/` e `sort | tail -n 1` ordina alfabeticamente, `toc.html` (inizia con la 't') si posiziona in fondo all'elenco alfabetico dopo i report effettivi, venendo selezionato erroneamente come "ultimo report".
  - Il vero report di SongKong risiede invece in sottocartelle dedicate (`/root/.songkong/Reports/FixSongsXXXXX/FixSongsXXXXX.html` o `StatusReportXXXXX/StatusReportXXXXX.html`).
- **Video Normalizer (`normalize-video.sh`)**:
  - Il normalizzatore video non produce e non allega **alcun report** (`send_summary_email ... ""`).
  - L'output di FileBot AMC (che include il match TMDb, il titolo italiano, l'anno, il formato, la traccia audio/video e gli artwork scaricati) viene stampato solo nei log del container e viene perso.
  - L'email di riepilogo per i video contiene unicamente 4 righe generiche senza indicare quale film sia stato elaborato o rinominato.

---

## 🎯 Obiettivi di Riprogettazione

1. **Email HTML Rich & Responsive (Zero-Click Reading)**:
   - Aggiornare `utils.sh` per usare `apprise -i html`.
   - Inserire il report dettagliato (formattato con stile CSS inline pulito e scuro/moderno, card riassuntive, badge di stato ed elenchi tracce/film) **direttamente nel corpo dell'email**. In questo modo Gmail e qualsiasi client mail renderizzano immediatamente i dettagli senza che l'utente debba cliccare su alcun allegato.
2. **Audio Normalizer (`normalize.sh`)**:
   - Correggere la ricerca del report SongKong per escludere tassativamente `webhelp/`, `index.html` e sottomenu `_*`.
   - Puntare con precisione al file principale `FixSongs*.html` o estrarre il sommario delle modifiche direttamente per il corpo email.
   - Creare un allegato autonomo (*self-contained*) con CSS inline denominato esplicitamente `Report_SongKong_<NomeAlbum>.html`.
3. **Video Normalizer (`normalize-video.sh`)**:
   - Catturare l'output di FileBot AMC in un log di sessione.
   - Generare una card HTML dedicata con locandina/poster (se presente in destinazione), titolo film con link a TMDb, tag di risoluzione/codec e percorso del file hardlinkato.
   - Allegare il file riassuntivo `Report_FileBot_<NomeFilm>.html` e includere il riepilogo grafico nel corpo dell'email.

---

## 🏗️ Architettura e Dettaglio delle Modifiche

### 1. `custom-docker-images/custom-normalizer/utils.sh`
- Aggiunta del flag `-i html` nella chiamata `apprise`:
  ```bash
  local apprise_cmd=(apprise -i html -t "$title" -b "$body" "$apprise_smtp_url")
  ```
- Introduzione di una funzione helper per generare il template HTML responsive delle email (con header homelab, card con sfondo neutro, tabelle di riepilogo e footer).

### 2. `custom-docker-images/custom-normalizer/normalize.sh` (Audio)
- **Selezione del vero report SongKong**:
  ```bash
  # Esclusione esplicita di webhelp e selezione del FixSongs più recente per tempo di modifica (mtime)
  LATEST_DIR="$(find "$REPORT_DIR" -mindepth 1 -maxdepth 1 -type d ! -name "webhelp" ! -name "style" 2>/dev/null | sort -V | tail -n 1)"
  if [ -n "$LATEST_DIR" ] && [ -d "$LATEST_DIR" ]; then
      MAIN_HTML="$(find "$LATEST_DIR" -maxdepth 1 -name "*.html" ! -name "*_*" | head -n 1)"
  fi
  ```
- **Estrazione metriche chiave**:
  - Canzoni caricate, tracce matchate (MusicBrainz / Discogs), compositori/artisti identificati.
- **Costruzione corpo email HTML**:
  - Card con stato verde, badge "SongKong Premium", tabella con sorgente, destinazione, tracce e link al report.

### 3. `custom-docker-images/custom-normalizer/normalize-video.sh` (Video)
- Esecuzione FileBot con cattura log in `/tmp/filebot_${BASENAME}.log`:
  ```bash
  filebot -script fn:amc ... | tee "$LOG_FILE"
  ```
- Parser dell'output per estrarre:
  - File sorgente $\rightarrow$ File destinazione finale
  - Titolo film riconosciuto, anno e TMDb ID
  - Artwork scaricati (poster, fanart, ecc.)
- Generazione del report HTML autonomo `/tmp/report_filebot_${BASENAME}.html` con tabella hardlink e dettagli tecnici.
- Inclusione della card nel corpo dell'email e allegato parlante `Report_FileBot_${BASENAME}.html`.

### 4. Gestione Deployment su TrueNAS
- Possibilità di montare gli script aggiornati come bind-mount in `servarr/truenas-docker/docker-compose.yaml` (come già fatto per `webhook_server.py` e `categories.yaml`) per test immediati a caldo, con successivo rilascio dell'immagine Docker ufficiale `custom-normalizer:1.6.0`.

---

## 📋 Fasi Sequenziali di Implementazione

### Fase 1: Riprogettazione `utils.sh` & Supporto Email HTML
- Aggiornare `send_summary_email` in `utils.sh` per utilizzare `-i html`.
- Creare il template HTML unificato per l'invio delle notifiche.

### Fase 2: Riprogettazione `normalize.sh` (Audio & SongKong)
- Sanare la ricerca del report escludendo categoricamente la documentazione di `webhelp`.
- Costruire il corpo email HTML con le statistiche audio e allegato corretto.

### Fase 3: Riprogettazione `normalize-video.sh` (Video & FileBot)
- Aggiungere cattura log e parser per FileBot AMC.
- Costruire il corpo email HTML per i video e l'allegato report HTML.

### Fase 4: Validazione a Caldo su TrueNAS
- Montare a caldo gli script in `webhook-normalizer` su TrueNAS.
- Eseguire test di elaborazione audio e video simulati e verificare la ricezione delle email su Gmail (sia visualizzazione nativa HTML che correttezza dell'allegato).

### Fase 5: Tag Release Immagine Docker `1.6.0` & Consolidamento
- Bump di versione a `1.6.0` in `custom-docker-images/custom-normalizer/VERSION`.
- Commit e push per build CI/CD su GHCR.

---

## 🛑 Checkpoint di Verifica
- [x] Il corpo dell'email in Gmail viene visualizzato nativamente con formattazione HTML ricca (tabelle, stili, card), senza aprire allegati.
- [x] L'allegato dell'Audio Normalizer non contiene più `toc.html` o pagine del manuale, ma il vero report di sessione SongKong.
- [x] Il Video Normalizer produce un'email dettagliata con titolo, anno, TMDb e percorso finale, allegando il log/report dell'elaborazione.
- [x] Nessun errore di invio email con Apprise.

---

## 💾 Stato di Ripristino (AI Save-State)
- **Fase Attiva**: Fase 5: Tag Release Immagine Docker `1.6.0` & Consolidamento
- **Ultima Azione Completata**: Push su GitHub `main` e avvio build GHCR di `ghcr.io/pindaroli/custom-normalizer:1.6.0`
- **Prossimo Passo Operativo**: Monitoraggio completamento build GHCR, aggiornamento `docker-compose.yaml` su TrueNAS all'immagine `1.6.0` definitiva e rimozione bind-mount provvisori.
- **Blocchi/Decisioni Pendenti**: Nessuno. Build GitHub Actions in corso.

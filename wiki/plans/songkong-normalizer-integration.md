---
title: "Integrazione SongKong Premium nel Normalizzatore Audio"
type: plan
status: active
certified_for_ai: true
date: 2026-07-18
provenance:
  - "custom-docker-images/custom-normalizer/Dockerfile"
  - "custom-docker-images/custom-normalizer/normalize.sh"
---

# Integrazione SongKong Premium nel Normalizzatore Audio

L'obiettivo di questo piano è integrare **SongKong Premium** (versione Linux Headless) all'interno dell'immagine Docker `custom-normalizer`. Questo consentirà di eseguire la taggatura intelligente dei metadati, ottimizzandoli specificamente per la **Musica Classica** e per l'indicizzazione su **MinimServer**, subito dopo la fase di splitting dei mega-FLAC guidata da `fmedia` e `cuefix`.

## 🏗️ Architettura e Dettagli Tecnologici

1. **Installazione Java (JRE 17)**: SongKong richiede Java per l'esecuzione. L'immagine base del normalizzatore (`debian:bookworm-slim`) verrà aggiornata per installare `openjdk-17-jre-headless`.
2. **Download SongKong Headless**: Verrà scaricato ed estratto l'archivio ufficiale di SongKong per Linux Headless (`songkong-linux-headless.tgz`) in `/opt/songkong`, con creazione di un symlink in `/usr/local/bin/songkong`.
3. **Integrazione in `normalize.sh`**:
   - Alla fine dell'elaborazione di splitting delle tracce, verrà invocato `songkong -m "$TARGET_DIR"`.
   - Verrà utilizzato il motore di taggatura di SongKong per compilare i campi chiave per la musica classica (Composer, Conductor, Work, Movement, Opus, ecc.) e per MinimServer (Group, indexTags).
4. **Gestione della Licenza Premium**:
   - La cartella delle preferenze di SongKong si troverà in `/root/.songkong`.
   - Per attivare la versione Premium, l'utente monterà il file di licenza `license.properties` all'interno del pod di Kubernetes in `/root/.songkong/license.properties`.

---

## 🛠️ Modifiche Proposte

### 1. [MODIFY] [Dockerfile](file:///Users/olindo/prj/pindaroli-arr-helm/custom-docker-images/custom-normalizer/Dockerfile)
- Aggiunta di `openjdk-17-jre-headless` tra i pacchetti `apt`.
- Download, estrazione di SongKong Headless e creazione del collegamento simbolico.
- Creazione della cartella `/root/.songkong` per ospitare la licenza.

### 2. [MODIFY] [normalize.sh](file:///Users/olindo/prj/pindaroli-arr-helm/custom-docker-images/custom-normalizer/normalize.sh)
- Aggiunta della fase finale 3 (`Tagging e Ottimizzazione con SongKong Premium`).
- Chiamata a `songkong -m "$TARGET_DIR"` per elaborare i metadati in modalità headless.

---

## 🔍 Piano di Verifica

### 1. Build Locale
- Compilazione dell'immagine Docker per verificare che non vi siano errori di installazione o dipendenze mancanti.

### 2. Test Esecuzione
- Verifica che `songkong` sia disponibile nel container ed esegua la scansione senza errori di avvio Java.

---

## 💾 Stato di Ripristino (AI Save-State)
- **Fase Attiva**: Pianificazione e stesura del piano.
- **Ultima Azione Completata**: Creazione del piano wiki locale.
- **Prossimo Passo Operativo**: Presentare il piano all'utente ed attendere approvazione prima di modificare i sorgenti del Dockerfile e di normalize.sh.
- **Blocchi/Decisioni Pendenti**: In attesa di approvazione per procedere all'esecuzione delle modifiche.

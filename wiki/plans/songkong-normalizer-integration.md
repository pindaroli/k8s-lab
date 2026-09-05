---
title: "Integrazione SongKong Premium nel Normalizzatore Audio"
type: plan
status: archived
certified_for_ai: false
created_at: 2026-07-18
archived_at: 2026-07-18
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
- **Fase Attiva**: **COMPLETATA - NOTIFICHE APPRISE & IMMAGINE 1.2.0 IN PRODUZIONE**
- **Ultima Azione Completata**:
  - **Integrazione Licenza Premium**: Secret Kubernetes `songkong-license` applicato nel namespace `arr` e montato in `/root/.songkong/license.properties`. Testato ed operativo.
  - **Fix Locale Cyrillic Crash**: Aggiunto `LANG=C.UTF-8` e `LC_ALL=C.UTF-8` in tutti i Job per prevenire il crash JVM `InvalidPathException` con caratteri cirillici CP1251.
  - **Transizione a Notifiche Apprise**: Sostituito `notify` e lo script custom Python `send_email.py` con **`apprise`** (installato via `pip3` nel container).
  - **Notifiche Telegram & Email**: `normalize.sh` invia notifiche HTML su Telegram via Apprise (`tgram://`) per avvisi ed esito job, ed invia l'email di riepilogo a `o.pindaro@gmail.com` via Apprise (`mailtos://`) con allegato il report HTML nativo di SongKong.
  - **Rilasci Codebase**: Immagine `custom-normalizer:1.2.0` e Helm Chart `servarr:1.8.0` committati e pushati su GitHub. Secret `smtp-creds` cifrato con SOPS ed applicato nel cluster.
- **Prossimo Passo Operativo per il Ripristino**:
  - Attendere la build automatica della CI/CD di GitHub per l'immagine `ghcr.io/pindaroli/custom-normalizer:1.2.0`.
  - Alla prossima esecuzione di un Job da qBittorrent o `batch-normalization.sh`, verificare la ricezione delle notifiche Telegram e dell'email con il report allegato.
- **Blocchi/Decisioni Pendenti**: Nessuno. Lavori conclusi con successo.


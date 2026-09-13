---
title: "Disaccoppiamento Radarr / FileBot e Risoluzione Job Video Normalizer"
type: plan
status: archived
certified_for_ai: false
created_at: 2026-09-13
archived_at: 2026-09-13
tags:
  - "#servarr"
  - "#radarr"
  - "#filebot"
  - "#normalizer"
  - "#kubernetes"
---

# Disaccoppiamento Radarr / FileBot e Risoluzione Job Video Normalizer

L'obiettivo di questo piano era disaccoppiare la gestione dei download dei film di **Radarr** dal trigger automatico post-download di qBittorrent, ripristinando il flusso nativo del Servarr stack ed eliminando notifiche di errore ridondanti.
Parallelamente, è stata introdotta la categoria dedicata `video-filebot` e sono stati sanati i difetti tecnici di permessi e runtime Java (`UID 1000`) del Job **FileBot** (`normalize-video.sh`), pubblicando la release ufficiale `custom-normalizer:1.3.0`.

---

## 🏗️ Architettura e Analisi dei Problemi

1. **Conflitto Radarr vs FileBot**:
   - In `arr-values.yaml`, il filtro `radarr: "movies video"` innescava un Job Kubernetes con FileBot ad ogni completamento torrent in categoria `radarr`.
   - Radarr gestisce nativamente il parsing, la rinomina secondo TheMovieDB, l'hardlink in `/media/movies`, l'aggiornamento dello stato del database e la notifica a Jellyfin.
   - La contemporanea esecuzione di FileBot generava collisioni su filesystem e una notifica di errore ad ogni download completato.
2. **Crash di Runtime FileBot (UID 1000 & AccessDeniedException)**:
   - I Job Kubernetes del normalizzatore girano con `securityContext` non privilegiato (`runAsUser: 1000, runAsGroup: 1000`).
   - Nel container Debian, la variabile `HOME` non impostata per Java portava la JVM a tentare la scrittura in `/app/?` (cartella `/app` appartenente a `root:root` con permessi 755), provocando `java.nio.file.AccessDeniedException: /app/?`.
   - La soluzione validata consiste nell'esportare `HOME=/tmp` e impostare la proprietà JVM `JAVA_OPTS="-Duser.home=/tmp"`.
3. **Inaccessibilità della Licenza FileBot**:
   - Il secret `filebot-license` veniva montato in `/root/.filebot/license.psm`.
   - La directory `/root` possiede permessi `0700` (`drwx------ root root`), rendendo il percorso inaccessibile a qualsiasi processo non-root.
   - È stata creata la cartella `/etc/filebot` (e `/etc/songkong`) con permessi `777` nel Dockerfile e aggiornato lo script per montare e leggere la licenza da `/etc/filebot/license.psm`.

---

## 🛠️ Interventi Eseguiti

1. **Repository `pindaroli-arr-helm`**:
   - Aggiornato `Dockerfile`: create directory `/etc/songkong` e `/etc/filebot` con permessi `777`.
   - Aggiornato `normalize-video.sh`: esportato `JAVA_OPTS` e aggiunta lettura licenza da `/etc/filebot/license.psm`.
   - Aggiornato `normalize.sh`: copia automatica licenza SongKong per UID 1000.
   - Aggiornato `trigger-job.sh`: mount point licenze in `/etc/`, variabili `HOME` e `JAVA_OPTS`, immagine `custom-normalizer:1.3.0`.
   - Bump versione chart `servarr` a `1.9.7`.
   - Push su GitHub e build completata con successo su GHCR (`ghcr.io/pindaroli/custom-normalizer:1.3.0`).
2. **Repository `k8s-lab`**:
   - In `servarr/arr-values.yaml`: rimossa `radarr: "movies video"`, aggiunta categoria `video-filebot: "movies video"`.
   - Aggiornato `job-normalizzation-template.yaml` per batch execution allineato a `1.3.0`.
   - Deploy Helm `servarr:1.9.7` applicato con successo (Revisione 172).
   - Rollout restart di `servarr-qbittorrent` per aggiornare ConfigMap montata.
3. **Validazione Test-Driven End-to-End**:
   - Test su *I Diavoli (1971)*: hardlink, artwork (poster, fanart, logo) ed NFO creati in `/media/movies/I diavoli (1971) [tmdbid-31767]/`.
   - Test su *Incontrerai l'uomo dei tuoi sogni (2010)*: hardlink, artwork (poster, fanart, clearart, logo, disc) ed NFO creati in `/media/movies/Incontrerai l'uomo dei tuoi sogni (2010) [tmdbid-38031]/`.
   - Esito: 100% completato con 0 errori.

---

## 💾 Stato di Ripristino (AI Save-State)
- **Fase Attiva**: **COMPLETATO CON SUCCESSO**
- **Ultima Azione Completata**: Test reale positivo su entrambi i film con nuova immagine 1.3.0 e release chart 1.9.7.
- **Prossimo Passo Operativo**: Nessuno. Lavori conclusi.
- **Blocchi/Decisioni Pendenti**: Nessuno.

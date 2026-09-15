---
name: video-ingestor
type: skill
description: "Procedura rapida e deterministica per l'ingestion immediata di film (categoria video-filebot o percorsi manuali) nella libreria /media/movies tramite Job Kubernetes FileBot AMC. Trigger: 'fai ingestion di <nome film>', 'ingestion di <nome film>'."
when_to_use: "Quando l'utente richiede 'fai ingestion di <nome film>', 'ingestion di <nome film>', 'esegui ingestion di <nome film>' o chiede di normalizzare/importare film scaricati (categoria video-filebot o percorsi manuali) verso la libreria cinematografica /media/movies."
status: active
tags:
  - servarr
  - filebot
  - ingestion
  - kubernetes
  - jellyfin
---

# Video Ingestor Skill (`video-ingestor`)

## 🗣️ Trigger Phrases Riconosciute (Pattern di Attivazione)
Lo skill si attiva automaticamente quando l'utente utilizza espressioni come:
- `fai ingestion di <nome film>`
- `ingestion di <nome film>`
- `esegui ingestion di <nome film>`
- `video-ingestor: <nome film>`
- `ingestion dei film <film 1>, <film 2>...`
- `ingestion categoria video-filebot`

---

## 🎯 Obiettivo
Eseguire l'ingestion immediata, automatica e verificata di filmati nella libreria ufficiale `/media/movies/` (pool ZFS `oliraid`), delegando il parsing del titolo, l'estrazione TMDb, la creazione di hardlink e il download degli artwork a **FileBot AMC** isolato in un Job Kubernetes non privilegiato (`UID 1000`).

La skill applica rigorosamente il pattern architetturale [[movie-metadata-and-artwork-architecture]]:
1. **Hardlink ZFS**: Nessun consumo aggiuntivo di storage e conservazione del seeding in qBittorrent.
2. **Artwork offline**: Persistenza di `poster.jpg`, `folder.jpg`, `fanart.jpg` (e `logo.png`/`disc.png` se disponibili).
3. **Divieto NFO**: Eliminazione automatica di tutti i file `.nfo` per prevenire duplicati e delegare la gestione dei dati a Jellyfin.

---

## ⚡ Workflow Rapido di Esecuzione (Fast-Path)

### 1. Individuazione del Percorso Sorgente
Verificare il nome esatto della cartella del film all'interno del volume:

```bash
kubectl exec -n arr deploy/servarr-radarr -c radarr -- ls -1 "/media/downloads/video-filebot"
```

---

### 2. Innesco Atomico del Job K8s
Eseguire lo script di trigger all'interno del pod `servarr-qbittorrent` passando il path assoluto della sorgente e la categoria `video-filebot`:

```bash
kubectl exec -n arr deploy/servarr-qbittorrent -c servarr -- /scripts/trigger-job.sh "/media/downloads/video-filebot/<NOME_CARTELLA_O_FILE>" "video-filebot"
```

> **Nota di Sicurezza**: Le virgolette doppie racchiudono in modo sicuro percorsi contenenti spazi, parentesi o apici singoli (es. `L'Ordine Del Tempo...`).

---

### 3. Streaming e Monitoraggio dei Log
Identificare il Job generato (prefisso `video-normalizer-`) e seguire l'elaborazione in tempo reale:

```bash
kubectl logs -n arr -l app.kubernetes.io/name=audio-normalizer --tail=50 -f
```

L'elaborazione si conclude positivamente quando il log riporta:
```text
🎉 ELABORAZIONE COMPLETATA!
Elementi elaborati : 1
Errori riscontrati : 0
```

---

### 4. Verifica di Integrità e Conformità (Test-Driven)
Verificare la corretta materializzazione della scheda e dei file in `/media/movies/`:

```bash
kubectl exec -n arr deploy/servarr-radarr -c radarr -- ls -la "/media/movies/<Titolo Identificato>*/"
```

#### Checklist di Validazione:
- [ ] **Hardlink verificato**: Contatore link video `>= 2` (`ls -l`).
- [ ] **Artwork presenti**: Presenti `folder.jpg` / `poster.jpg` e `fanart.jpg`.
- [ ] **Zero NFO**: Nessun file `.nfo` presente nella directory del film.

---

## 🗂️ Elaborazione Batch Multipla (Opzionale)
Se devono essere processati contemporaneamente più film o un'intera directory di download:

```bash
./scripts/kubernetes/batch-normalization.sh "/media/downloads/video-filebot" "/media/movies" --type video
```

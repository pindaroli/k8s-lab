---
name: video-ingestor
type: skill
description: "Procedura rapida e deterministica per l'ingestion immediata di film (categoria video-filebot o percorsi manuali) nella libreria /media/movies tramite TrueNAS webhook-normalizer (FileBot AMC). Trigger: 'fai ingestion di <nome film>', 'ingestion di <nome film>'."
when_to_use: "Quando l'utente richiede 'fai ingestion di <nome film>', 'ingestion di <nome film>', 'esegui ingestion di <nome film>' o chiede di normalizzare/importare film scaricati (categoria video-filebot o percorsi manuali) verso la libreria cinematografica /media/movies."
status: active
tags:
  - servarr
  - filebot
  - ingestion
  - truenas
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
Eseguire l'ingestion immediata, automatica e verificata di filmati nella libreria ufficiale `/media/movies/` (pool ZFS `oliraid` su TrueNAS Bare Metal `10.10.20.50`), delegando il parsing del titolo, l'estrazione TMDb, la creazione di hardlink e il download degli artwork a **FileBot AMC** in esecuzione isolata nel container Docker `webhook-normalizer` (porta 9000).

La skill applica rigorosamente il pattern architetturale [[movie-metadata-and-artwork-architecture]]:
1. **Hardlink ZFS**: Nessun consumo aggiuntivo di storage e conservazione del seeding in qBittorrent.
2. **Artwork offline**: Persistenza di `poster.jpg`, `folder.jpg`, `fanart.jpg`, `logo.png` e `disc.png`.
3. **Divieto NFO**: Eliminazione automatica di tutti i file `.nfo` per prevenire conflitti di schede e delegare la gestione metadati testuali a Jellyfin.

---

## ⚡ Workflow Rapido di Esecuzione (Fast-Path)

### 1. Individuazione del Percorso Sorgente
Verificare il nome esatto della cartella del film all'interno del volume o tramite il client torrent:

```bash
ssh -o BatchMode=yes olindo@10.10.20.50 "ls -1 /mnt/oliraid/arrdata/media/downloads/video-filebot"
```
*(Oppure interrogare qBittorrent tramite tool MCP `qbt_list_torrents` / `qbt_torrent_details`)*.

---

### 2. Innesco Atomico della Normalizzazione
Eseguire lo script CLI dedicato `scripts/servarr/trigger_normalization.sh` passando il nome della cartella o il path assoluto:

```bash
./scripts/servarr/trigger_normalization.sh "<NOME_CARTELLA_O_FILE>" "video-filebot"
```

*In alternativa, tramite chiamata HTTP diretta a TrueNAS:*
```bash
curl -s -X POST http://10.10.20.50:9000/hooks/normalize \
    --data-urlencode "path=/media/downloads/video-filebot/<NOME_CARTELLA_O_FILE>" \
    --data-urlencode "category=video-filebot"
```

> **Nota di Sicurezza**: Le virgolette doppie racchiudono in modo sicuro percorsi contenenti spazi, parentesi o apici singoli (es. `L'Ordine Del Tempo...`).

---

### 3. Streaming e Monitoraggio dei Log
Seguire l'elaborazione di FileBot AMC in tempo reale sui log del container Docker di TrueNAS:

```bash
ssh -o BatchMode=yes olindo@10.10.20.50 "sudo -n docker logs -f --tail=30 webhook-normalizer"
```

L'elaborazione si conclude positivamente quando il log riporta:
```text
==========================================================
🎉 ELABORAZIONE COMPLETATA!
Elementi elaborati : 1
Errori riscontrati : 0
Directory finale   : '/media/movies'
==========================================================
```

---

### 4. Verifica di Integrità e Conformità (Test-Driven)
Verificare la corretta materializzazione della scheda e dei file in `/media/movies/`:

```bash
ssh -o BatchMode=yes olindo@10.10.20.50 "ls -la '/mnt/oliraid/arrdata/media/movies/<Titolo Identificato>*/'"
```

#### Checklist di Validazione:
- [ ] **Hardlink verificato**: Contatore link video `>= 2` (`ls -l`).
- [ ] **Artwork presenti**: Presenti `folder.jpg` / `poster.jpg`, `fanart.jpg` (e `logo.png`/`disc.png`).
- [ ] **Zero NFO**: Nessun file `.nfo` presente nella directory del film.
- [ ] **Zero Consumo Spazio**: Il file punta allo stesso inode del file scaricato in seeding.

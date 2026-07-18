---
confidence: 0.9
last_updated: 2026-07-18
status: active
title: Custom Docker Images Configuration
type: entity
tags:
  - "#docker"
  - "#custom-images"
  - "#qbittorrent"
  - "#helm"
---

# Custom Docker Images Configuration

Questo documento descrive il pattern e la configurazione utilizzata nel repository `pindaroli-arr-helm` per personalizzare immagini Docker pubbliche e adattarle alle esigenze specifiche dell'infrastruttura Homelab.

## Architettura e Posizione nel Repository

Sotto la radice del progetto `pindaroli-arr-helm` è stata creata la cartella **`custom-docker-images/`**.
Ogni sotto-directory all'interno di questa struttura rappresenta un'immagine Docker custom estesa a partire da un'immagine Docker pubblica mantenuta dalla community (es. `lscr.io/linuxserver/qbittorrent`).

### Struttura Directory

```
pindaroli-arr-helm/
├── custom-docker-images/
│   ├── README.md
│   └── custom-qbittorrent/
│       ├── Dockerfile
│       └── README.md
```

## Gestione Parametrizzata delle Versioni (Best Practice)

Per evitare di cablare la versione dell'immagine base o delle dipendenze direttamente nel `Dockerfile`, si utilizzano gli argomenti di build (`ARG`):

```dockerfile
ARG QBITTORRENT_VERSION="5.2.3_v2.0.13-ls468"
FROM lscr.io/linuxserver/qbittorrent:${QBITTORRENT_VERSION}

ARG FMEDIA_VERSION="1.31"
```

### Dove definire/passare la versione:

1. **`ARG` con Default nel `Dockerfile`**: Garantisce che la build funzioni da sola con una versione stabile di default.
2. **File `VERSION` o `.env` locale**: (Opzionale) File di testo `custom-docker-images/custom-qbittorrent/VERSION` per centralizzare la versione e permettere a script/Makefile di leggerla.
3. **Workflow CI/CD (GitHub Actions)**: Durante la build in pipeline (es. GitHub Actions), si passa la versione desiderata via `--build-arg`:
   ```bash
   docker build --build-arg QBITTORRENT_VERSION=5.2.3_v2.0.13-ls468 -t custom-qbittorrent:latest .
   ```
4. **Helm Values (`arr-values.yaml`)**: Una volta pubblicata l'immagine custom registrata nel registry, la versione/tag pubblicata viene referenziata nel file dei valori Helm del cluster:
   ```yaml
   qbittorrent:
     image:
       repository: ghcr.io/pindaroli/custom-qbittorrent
       tag: 5.2.3-v1
   ```

## Relazioni
- Repository: `pindaroli-arr-helm`
- Stack: [[Servarr]]
- Downloader: qBittorrent

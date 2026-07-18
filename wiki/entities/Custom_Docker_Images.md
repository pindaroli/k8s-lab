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

## Immagini Customizzate

### 1. `custom-qbittorrent`
- **Immagine Base**: `lscr.io/linuxserver/qbittorrent` (o equivalente pubblica ufficiale).
- **Scopo**: Aggiunta di script personalizzati, utility di post-processing, temi WebUI personalizzati, o regolazioni specifiche di configurazione non presenti nell'immagine base.
- **Utilizzo**: Viene costruita e pubblicata nel container registry (o usata direttamente nel cluster) per poi essere referenziata nei Helm chart dello stack Servarr (`charts/servarr`).

## Workflow di Manutenzione
1. Modifica del `Dockerfile` o aggiunta di risorse/script all'interno di `custom-docker-images/<nome-app>/`.
2. Build e push dell'immagine Docker personalizzata con opportuno tag/versione.
3. Aggiornamento dei valori nei file di configurazione Helm (es. `arr-values.yaml`) con il repository/tag dell'immagine custom.
4. Applicazione dell'aggiornamento tramite `helm upgrade`.

## Relazioni
- Repository: `pindaroli-arr-helm`
- Stack: [[Servarr]]
- Downloader: qBittorrent

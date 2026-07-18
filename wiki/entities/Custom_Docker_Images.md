---
confidence: 0.95
last_updated: 2026-07-18
status: active
title: Custom Docker Images Configuration
type: entity
tags:
  - "#docker"
  - "#custom-images"
  - "#qbittorrent"
  - "#ghcr"
  - "#github-actions"
  - "#helm"
---

# Custom Docker Images Configuration

Questo documento descrive la configurazione ed il workflow di build/pubblicazione automatizzata su **GHCR** (GitHub Container Registry) per le immagini Docker personalizzate del repository `pindaroli-arr-helm`.

## Nomi Immagini Pubblicate su GHCR

Le immagini pubblicate su GitHub Container Registry sono denominate:

1. **`ghcr.io/pindaroli/custom-qbittorrent`**: Container qBittorrent customizzato con fmedia, cuefix e normalize.sh.
2. **`ghcr.io/pindaroli/custom-normalizer`**: Immagine Debian standalone adibita esclusivamente all'esecuzione dello script `normalize.sh`.

### Tag Generati:
- `ghcr.io/pindaroli/<image-name>:<VERSION>` (es. `:1.0.0`, letto dal rispettivo file `VERSION`)
- `ghcr.io/pindaroli/<image-name>:latest` (aggiornata automaticamente ad ogni push su `main`)
- `ghcr.io/pindaroli/<image-name>:sha-<commit_sha>` (tag immutabile legato al singolo commit)

---

## Gestione della Variabile Tag (`VERSION`)

La versione di ogni immagine personalizzata è definita nel rispettivo file `VERSION`:
- `custom-docker-images/custom-qbittorrent/VERSION`
- `custom-docker-images/custom-normalizer/VERSION`

Durante l'esecuzione delle pipeline CI/CD (`.github/workflows/build-custom-*.yml`), il tag viene letto dinamicamente dal file `VERSION` e applicato all'immagine pushata su GHCR.

```
pindaroli-arr-helm/
├── .github/workflows/
│   ├── build-custom-qbittorrent.yml   # Pipeline qBittorrent custom
│   └── build-custom-normalizer.yml    # Pipeline Normalizer standalone
├── custom-docker-images/
│   ├── README.md
│   ├── custom-qbittorrent/
│   │   ├── Dockerfile
│   │   ├── VERSION
│   │   └── normalize.sh
│   └── custom-normalizer/
│       ├── Dockerfile
│       ├── VERSION
│       └── normalize.sh
```

---

## Configurazione nei Valori Helm (`arr-values.yaml`)

Nei file di configurazione Helm del cluster (es. `arr-values.yaml`), l'immagine può essere referenziata con il tag di versione specifico:

```yaml
qbittorrent:
  image:
    repository: ghcr.io/pindaroli/custom-qbittorrent
    tag: 1.0.0 # oppure latest, sha-<commit_sha>
```

---

## Relazioni
- Repository: `pindaroli-arr-helm`
- Registry: GHCR (`ghcr.io`)
- Stack: [[Servarr]]
- Downloader: qBittorrent
- Script di Normalizzazione: `normalize.sh`

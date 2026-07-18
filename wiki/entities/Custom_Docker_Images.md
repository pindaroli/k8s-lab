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

## Nome Immagine Pubblicata su GHCR

L'immagine pubblicata su GitHub Container Registry è denominata:

**`ghcr.io/pindaroli/custom-qbittorrent`**

### Tag Generati:
- `ghcr.io/pindaroli/custom-qbittorrent:<VERSION>` (es. `:1.0.0`, letto dal file `VERSION`)
- `ghcr.io/pindaroli/custom-qbittorrent:latest` (aggiornata automaticamente ad ogni push su `main`)
- `ghcr.io/pindaroli/custom-qbittorrent:sha-<commit_sha>` (tag immutabile legato al singolo commit)

---

## Gestione della Variabile Tag (`VERSION`)

La versione dell'immagine personalizzata è definita nel file:
`custom-docker-images/custom-qbittorrent/VERSION`

Durante l'esecuzione della pipeline CI/CD (`.github/workflows/build-custom-qbittorrent.yml`), il tag viene letto dinamicamente dal file `VERSION` e applicato all'immagine pushata su GHCR.

```
pindaroli-arr-helm/
├── .github/workflows/
│   └── build-custom-qbittorrent.yml   # Pipeline automatizzata GitHub Actions
├── custom-docker-images/
│   ├── README.md
│   └── custom-qbittorrent/
│       ├── Dockerfile
│       ├── VERSION                    # File contenente il tag esplicito (es. 1.0.0)
│       └── README.md
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

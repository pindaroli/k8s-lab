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

### Tag Disponibili:
- `ghcr.io/pindaroli/custom-qbittorrent:latest` (aggiornata automaticamente ad ogni push su `main`)
- `ghcr.io/pindaroli/custom-qbittorrent:sha-<commit_sha>` (tag immutabile legato al singolo commit)

---

## Architettura e Posizione nel Repository

Sotto la radice del progetto `pindaroli-arr-helm` è presente la cartella **`custom-docker-images/`**:

```
pindaroli-arr-helm/
├── .github/workflows/
│   └── build-custom-qbittorrent.yml   # Pipeline automatizzata GitHub Actions
├── custom-docker-images/
│   ├── README.md
│   └── custom-qbittorrent/
│       ├── Dockerfile
│       └── README.md
```

---

## Automazione CI/CD con GitHub Actions

La pubblicazione dell'immagine è gestita dal workflow `.github/workflows/build-custom-qbittorrent.yml`.

### Caratteristiche del Workflow:
1. **Trigger (Opzione A - Path Based)**: Scatta in automatico al push sul ramo `main` se vengono modificati i file sotto `custom-docker-images/custom-qbittorrent/**`.
2. **Autenticazione GHCR**: Utilizza il token nativo di GitHub (`secrets.GITHUB_TOKEN`) con permessi `packages: write`.
3. **Buildx & Caching**: Utilizza Docker Buildx e `cache-from/cache-to: type=gha` per velocizzare le successive build.

---

## Configurazione nei Valori Helm (`arr-values.yaml`)

Nei file di configurazione Helm del cluster (es. `arr-values.yaml`), l'immagine va referenziata nel seguente modo:

```yaml
qbittorrent:
  image:
    repository: ghcr.io/pindaroli/custom-qbittorrent
    tag: latest # oppure sha-<commit_sha>
```

---

## Relazioni
- Repository: `pindaroli-arr-helm`
- Registry: GHCR (`ghcr.io`)
- Stack: [[Servarr]]
- Downloader: qBittorrent

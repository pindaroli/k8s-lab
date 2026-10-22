---
title: "Piano: Estensione GraphQL Bitmagnet per arrstack-mcp (v1.2.0)"
type: plan
status: active
certified_for_ai: true
created_at: 2026-10-22
tags:
  - "#plan"
  - "#mcp"
  - "#bitmagnet"
  - "#graphql"
  - "#servarr"
  - "#truenas"
  - "#docker"
---

# Piano: Estensione GraphQL Bitmagnet per arrstack-mcp (v1.2.0)

## 🎯 Obiettivo
Estendere il server MCP in-house **`arrstack-mcp`** (`docker/mcp/in-house/arrstack-mcp/src/server.py`, esposto tramite Traefik Umbrella Gateway su `http://10.10.20.50:8100/arrstack/mcp`) integrando il motore di ricerca **GraphQL di Bitmagnet** (`http://10.10.20.50:3333/graphql`) tramite due nuovi tool asincroni validati con **Pydantic**:
1. **`bitmagnet_simple_search`**: Ricerca full-text rapida con filtro opzionale per `contentType`, ordinata per `seeders` decrescenti.
2. **`bitmagnet_complex_search`**: Ricerca avanzata multi-filtro tramite faccette GraphQL (`contentType`, `videoResolution`, `videoSource`, `language`, `releaseYear`, `torrentTag`), filtri di post-processing Python (`minSeeders`, `videoCodecs`, limite file `maxFilesPerTorrent=25`), ordinamento personalizzabile, paginazione e conteggio aggregazioni.

---

## 🗺️ Mappe Concettuali e Relazioni
- [[MCP_Platform]] (Flotta MCP su TrueNAS SCALE bare-metal `10.10.20.50:8100`)
- [[Servarr]] (Stack multimediale su TrueNAS Docker e client qBittorrent)
- [[TrueNAS]] (Host bare-metal `10.10.20.50` dove risiedono `bitmagnet` e `mcp-arrstack`)
- [[bitmagnet-truenas-docker-integration]] (Deployment di Bitmagnet `v0.10.1` su porta `3333`)
- [[arrstack-mcp-prowlarr-qbittorrent-rest-extension]] (Estensione precedente `v1.1.0` di `arrstack-mcp`)
- [[truenas-mcp-fleet-gitops-and-image-tag-sanitization]] (Pipeline GitOps CI/CD GHCR e Traefik Umbrella Gateway)

---

## 1. Analisi Tecnica e Allineamento Schema GraphQL Bitmagnet `v0.10.1`

Dall'introspezione diretta dello schema GraphQL sull'istanza live di Bitmagnet `v0.10.1` (`http://10.10.20.50:3333/graphql`), sono state recepite le seguenti rettifiche strutturali rispetto alla specifica preliminare:

| Elemento | Specifica Preliminare | Schema Reale Bitmagnet `v0.10.1` & Soluzione Adottata |
| :--- | :--- | :--- |
| **Campo `TorrentContent.releaseYear`** | `releaseYear` richiesto su `TorrentContent` | Non esiste su `TorrentContent` (`GRAPHQL_VALIDATION_FAILED`). Sostituito con `releaseGroup` su `TorrentContent`, mentre `releaseYear` viene già restituito in `content { releaseYear }`. |
| **Faccetta e Aggregazione `videoCodec`** | `facets.videoCodec` e `aggregations.videoCodec` | `TorrentContentFacetsInput` e `TorrentContentAggregations` non espongono `videoCodec`. Il campo `videoCodec` è letto su `TorrentContent` e filtrato lato Python in `enrich_items(video_codecs=...)`. Nelle aggregazioni viene esposto `releaseYear { value count }`. |
| **Enum `VideoSource`** | `"WEB"`, `"HDTV"` | Lo schema `v0.10.1` definisce `WEBDL`, `WEBRip`, `TV`, `BluRay`, `DVD`, `CAM`, `TELESYNC`, `TELECINE`, `WORKPRINT`. Il Literal accetta sia i valori nativi sia `"WEB"` / `"HDTV"`, mappandoli automaticamente a `["WEBDL", "WEBRip"]` e `["TV"]`. |
| **Enum `VideoResolution` & `VideoCodec`** | Subset risoluzioni/codec | Allineati a tutti i valori validi di `v0.10.1` (`V360p`..`V4320p`; `H264`, `x264`, `x265`, `XviD`, `DivX`, `MPEG2`, `MPEG4`, più alias tollerati in filtro Python come `AV1`, `H265`, `VP9`, `VC1`). |
| **Attivazione `aggregations`** | `facets[k] = {"filter": ...}` | In Bitmagnet GraphQL le aggregazioni ritornano `null` se non viene richiesto `aggregate: true` nella faccetta corrispondente. Il builder delle faccette inietta `"aggregate": True` sulle faccette di aggregazione (`contentType`, `videoResolution`, `videoSource`, `releaseYear`, `language`). |
| **Protezione Context Window (`torrent.files`)** | Array `files` illimitato | Su torrent multi-file (`DHT_CRAWLER_SAVE_FILES_THRESHOLD=500`), 20 risultati possono generare fino a 10.000 record. Introdotto `maxFilesPerTorrent: int = 25` in `enrich_items` (con campo `filesTruncated: true` quando troncato). |

---

## 2. Architettura di Integrazione in `arrstack-mcp`

### 2.1 Configurazione e Service Discovery (`SERVICE_CONFIG` & `ard.py`)
- **Variabili d'ambiente supportate**:
  - `BITMAGNET_GRAPHQL_URL` (prioritaria, es. `http://10.10.20.50:3333/graphql`) e fallback su `BITMAGNET_URL` (se configurata come base URL `http://10.10.20.50:3333`, aggiunge automaticamente `/graphql`).
  - `BITMAGNET_TIMEOUT` (default `30.0` secondi).
- **Registrazione in `SERVICE_CONFIG` (`src/server.py`)**:
  - `"bitmagnet": ("Bitmagnet", BITMAGNET_GRAPHQL_URL, "bitmagnet_")`
  - Garantisce la piena compatibilità con `ENABLED_SERVICES`, `--list-services`, `--setup` e la rimozione dinamica dei tool non abilitati (`_configure_service_tools()`).
- **Registrazione in `src/ard.py`**:
  - Aggiunta di `"bitmagnet": "search the Bitmagnet DHT index for 4K BluRay or FLAC torrents"` in `_SERVICE_QUERIES` e inserimento in `_QUERY_PRIORITY` per la generazione conforme del manifesto `ai-catalog.json`.

### 2.2 Modelli Pydantic, Query SDL e Tool Asincroni (`src/server.py`)

```python
ContentTypeLiteral = Literal[
    "movie", "tv_show", "music", "ebook", "comic",
    "audiobook", "game", "software", "xxx", "null"
]

VideoResolutionLiteral = Literal[
    "V360p", "V480p", "V540p", "V576p", "V720p", "V1080p", "V1440p", "V2160p", "V4320p"
]

VideoSourceLiteral = Literal[
    "BluRay", "WEBDL", "WEBRip", "WEB", "TV", "HDTV",
    "DVD", "CAM", "TELESYNC", "TELECINE", "WORKPRINT"
]

VideoCodecLiteral = Literal[
    "x264", "x265", "H264", "H265", "AV1", "XviD", "DivX", "MPEG2", "MPEG4", "VC1", "VP9"
]

OrderFieldLiteral = Literal[
    "relevance", "published_at", "updated_at", "size",
    "files_count", "seeders", "leechers", "name", "info_hash"
]


class OrderByInput(BaseModel):
    field: OrderFieldLiteral = Field(
        default="seeders",
        description="Campo su cui ordinare i risultati."
    )
    descending: bool = Field(
        default=True,
        description="Se True, ordina in modo decrescente."
    )
```

- **Funzione `_bitmagnet_enrich_items`**:
  - Filtra per `min_seeders` (se specificato).
  - Filtra per `video_codecs` (case-insensitive, con equivalenza `H265`/`x265` se applicabile).
  - Calcola `torrent["sizeFormatted"]` e per ogni file `f["sizeFormatted"]`.
  - Tronca `torrent["files"]` a `max_files_per_torrent` (default `25`), aggiungendo `torrent["filesTruncated"] = True` se il numero originale di file eccede la soglia.

### 2.3 Bonifica Struttura Directory e Suite di Test (`pytest`)
- **Rimozione duplicati obsoleti nella root di `docker/mcp/in-house/arrstack-mcp/`**:
  - Eliminazione di `docker/mcp/in-house/arrstack-mcp/server.py` e `docker/mcp/in-house/arrstack-mcp/ard.py` (residui del 6 ottobre pre-v1.1.0; il `Dockerfile` copia esclusivamente `src/`).
- **Allineamento `requirements.txt` e `tests/`**:
  - Aggiunta esplicita di `pydantic>=2.0.0` in `requirements.txt`.
  - Aggiornamento di `tests/conftest.py` affinché inserisca `../src` nel `sys.path`.
  - Creazione di `tests/test_bitmagnet.py` per testare unitariamente `bitmagnet_simple_search`, `bitmagnet_complex_search`, il mapping `WEB`/`HDTV`, il filtro `minSeeders`/`videoCodecs`, il troncamento `maxFilesPerTorrent` e la gestione errori GraphQL.

### 2.4 Configurazione Runtime TrueNAS (`docker/mcp/docker-compose.yaml`)
Aggiornamento del servizio `arrstack-mcp` alla versione **`1.2.0`**:
```yaml
  arrstack-mcp:
    container_name: mcp-arrstack
    image: ghcr.io/pindaroli/arrstack-mcp:1.2.0
    restart: unless-stopped
    env_file: .env
    environment:
      - ENABLED_SERVICES=radarr,lidarr,prowlarr,qbittorrent,bitmagnet
      - RADARR_URL=https://radarr-internal.pindaroli.org
      - RADARR_API_KEY=${ARRSTACK_RADARR_API_KEY}
      - LIDARR_URL=https://lidarr-internal.pindaroli.org
      - LIDARR_API_KEY=${ARRSTACK_LIDARR_API_KEY}
      - PROWLARR_URL=http://10.10.20.50:9696
      - PROWLARR_API_KEY=${ARRSTACK_PROWLARR_API_KEY}
      - QBT_URL=http://10.10.20.50:8080
      - QBT_USER=admin
      - QBT_PASS=${ARRSTACK_QBT_PASS}
      - BITMAGNET_GRAPHQL_URL=http://10.10.20.50:3333/graphql
      - BITMAGNET_TIMEOUT=30.0
      - MCP_ALLOWED_HOSTS=*
      - MCP_DNS_REBINDING_PROTECTION=false
```

---

## 3. Fasi Operative Dettagliate (Protocollo Test-Driven)

### FASE 1: Bonifica Duplicati, Estensione Codice & Unit Test Locali
- [ ] **Passo 1.1**: Rimozione dei file obsoleti duplicati nella root (`docker/mcp/in-house/arrstack-mcp/server.py` e `docker/mcp/in-house/arrstack-mcp/ard.py`) e aggiornamento di `requirements.txt` (`pydantic>=2.0.0`).
  - *Verifica*: Controllo `ls -la docker/mcp/in-house/arrstack-mcp/` e `git status`.
- [ ] **Passo 1.2**: Integrazione di Bitmagnet in `docker/mcp/in-house/arrstack-mcp/src/ard.py` e `docker/mcp/in-house/arrstack-mcp/src/server.py` (`SERVICE_CONFIG`, modelli Pydantic, query GraphQL `v0.10.1`, helper `execute_graphql`, `bitmagnet_simple_search` e `bitmagnet_complex_search`).
  - *Verifica*: Compilazione sintattica `python3 -m py_compile docker/mcp/in-house/arrstack-mcp/src/server.py docker/mcp/in-house/arrstack-mcp/src/ard.py` e verifica `--list-services` con `BITMAGNET_GRAPHQL_URL=http://10.10.20.50:3333/graphql`.
- [ ] **Passo 1.3**: Riallineamento `tests/conftest.py` su `../src`, creazione di `tests/test_bitmagnet.py` ed esecuzione dell'intera suite `pytest`.
  - *Verifica*: Esecuzione di `pytest` su `docker/mcp/in-house/arrstack-mcp/tests/` con 100% dei test passati + test live delle funzioni Python contro `http://10.10.20.50:3333/graphql`.

### FASE 2: Versioning `1.2.0`, Configurazione Dichiarativa & CI/CD GHCR
- [ ] **Passo 2.1**: Aggiornamento di `docker/mcp/in-house/arrstack-mcp/VERSION` a `1.2.0` e aggiornamento di `docker/mcp/docker-compose.yaml` (`ghcr.io/pindaroli/arrstack-mcp:1.2.0`, `ENABLED_SERVICES` con `bitmagnet`, `BITMAGNET_GRAPHQL_URL=http://10.10.20.50:3333/graphql`).
  - *Verifica*: Ispezione `git diff` su `VERSION` e `docker/mcp/docker-compose.yaml`.
- [ ] **Passo 2.2**: Commit e push su `main` per innescare il workflow GitHub Actions `.github/workflows/docker-arrstack-mcp.yml`.
  - *Verifica*: Monitoraggio del workflow CI fino a completamento (`gh run list` / `gh run watch`) e verifica della pubblicazione del tag `ghcr.io/pindaroli/arrstack-mcp:1.2.0`.

### FASE 3: Rollout GitOps su TrueNAS SCALE (`10.10.20.50`) & Validazione E2E
- [ ] **Passo 3.1**: Sincronizzazione di `docker/mcp/docker-compose.yaml` su TrueNAS (`/mnt/stripe/truenas-docker/mcp/docker-compose.yaml`), pull dell'immagine `ghcr.io/pindaroli/arrstack-mcp:1.2.0` e ricreazione del container `mcp-arrstack`.
  - *Verifica*: Controllo stato container (`healthy`), log di avvio (`🎬 arrstack-mcp starting (Radarr, Lidarr, Prowlarr, qBittorrent, Bitmagnet)`) e healthcheck HTTP.
- [ ] **Passo 3.2**: Smoke test JSON-RPC End-to-End attraverso Traefik (`http://10.10.20.50:8100/arrstack/mcp`) verificando l'esposizione e il funzionamento reale di `bitmagnet_simple_search` e `bitmagnet_complex_search`.
  - *Verifica*: Risposta `200 OK` JSON-RPC con risultati reali estratti dal DB PostgreSQL di Bitmagnet e conteggi `aggregations` valorizzati.

### FASE 4: Consolidamento Documentale & Chiusura Piano
- [ ] **Passo 4.1**: Aggiornamento delle entità wiki [[MCP_Platform]] e [[Servarr]] con i nuovi tool Bitmagnet e la versione `1.2.0` di `arrstack-mcp`.
- [ ] **Passo 4.2**: Sincronizzazione `todo.md`, archiviazione del piano e rigenerazione del contesto wiki (`python3 scripts/network/validate_network.py && python3 scripts/wiki/build_wiki_context.py`).

---

## 💾 Stato di Ripristino (AI Save-State)
- **Fase Attiva**: Pianificazione Completata — In attesa di autorizzazione per Fase 1 (Passo 1.1)
- **Ultima Azione Completata**: Verifica live dello schema GraphQL di Bitmagnet `v0.10.1` su `10.10.20.50:3333`, completamento dell'intervista `/grill-me` e stesura del piano `wiki/plans/arrstack-mcp-bitmagnet-graphql-extension.md`.
- **Prossimo Passo Operativo**: Eseguire il Passo 1.1 (rimozione duplicati obsoleti `server.py`/`ard.py` nella root di `arrstack-mcp` e aggiornamento `requirements.txt`) previa approvazione esplicita dell'utente.
- **Blocchi/Decisioni Pendenti**: Attesa autorizzazione dell'utente per avviare la Fase 1.

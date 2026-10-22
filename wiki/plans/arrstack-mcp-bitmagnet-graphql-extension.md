---
title: "Piano: Estensione GraphQL Bitmagnet per arrstack-mcp (v1.2.0)"
type: plan
status: completed
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

> [!IMPORTANT]
> **Scopo di questo piano**: Fornire una specifica operativa esaustiva, priva di ambiguità e con snippet di codice, diff e comandi esatti pronti per essere eseguiti in autonomia anche da un modello con capacità di ragionamento ridotta (es. Gemini Flash / Flash Lite).

---

## 🎯 Obiettivo
Estendere il microservizio MCP in-house **`arrstack-mcp`** (ospitato in `docker/mcp/in-house/arrstack-mcp/` ed eseguito su TrueNAS SCALE bare-metal `10.10.20.50:8100/arrstack/mcp` dietro Traefik Umbrella Gateway) aggiungendo due nuovi tool asincroni basati su **FastMCP**, **Pydantic** e **httpx** per interrogare l'endpoint GraphQL nativo di **Bitmagnet** (`http://10.10.20.50:3333/graphql`):
1. **`bitmagnet_simple_search`**: Ricerca full-text rapida per keyword con filtro opzionale per `contentType`, ordinata per seeders decrescenti.
2. **`bitmagnet_complex_search`**: Ricerca avanzata multi-filtro con faccette GraphQL native (`contentType`, `videoResolution`, `videoSource`, `releaseYear`, `language`, `torrentTag`), filtri di post-processing Python (`minSeeders`, `videoCodecs`, limite file `maxFilesPerTorrent=25`), paginazione, ordinamento personalizzato e aggregazioni conteggiate.

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

## 2. Dettaglio Operativo e Codice Pronto per Modelli Leggeri

### FASE 1: Bonifica Directory e Dipendenze

#### Passo 1.1: Eliminazione dei file obsoleti duplicati
Comando:
```bash
rm -f /Users/olindo/prj/k8s-lab/docker/mcp/in-house/arrstack-mcp/server.py /Users/olindo/prj/k8s-lab/docker/mcp/in-house/arrstack-mcp/ard.py
```
Verifica:
```bash
ls -la /Users/olindo/prj/k8s-lab/docker/mcp/in-house/arrstack-mcp/
```

#### Passo 1.2: Aggiornamento di `requirements.txt`
File: `/Users/olindo/prj/k8s-lab/docker/mcp/in-house/arrstack-mcp/requirements.txt`
```diff
--- requirements.txt
+++ requirements.txt
@@ -2,3 +2,4 @@
 httpx>=0.27.0
 starlette>=0.38.0
 uvicorn>=0.30.0
+pydantic>=2.0.0
```

#### Passo 1.3: Aggiornamento di `VERSION`
File: `/Users/olindo/prj/k8s-lab/docker/mcp/in-house/arrstack-mcp/VERSION`
Contenuto: `1.2.0`

#### Passo 1.4: Correzione del path di import in `tests/conftest.py`
File: `/Users/olindo/prj/k8s-lab/docker/mcp/in-house/arrstack-mcp/tests/conftest.py`
```diff
--- conftest.py
+++ conftest.py
@@ -3,4 +3,4 @@
 import pytest
 
-# Add parent directory (docker/mcp/in-house/arrstack-mcp) to sys.path so server.py can be imported
-sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
+# Add src directory (docker/mcp/in-house/arrstack-mcp/src) to sys.path so server.py can be imported
+sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../src")))
```

---

### FASE 2: Integrazione Codice in `src/ard.py` e `src/server.py`

#### Passo 2.1: Aggiornamento di `src/ard.py`
File: `/Users/olindo/prj/k8s-lab/docker/mcp/in-house/arrstack-mcp/src/ard.py`
In `_SERVICE_QUERIES`:
```python
    "qbittorrent": "what torrents are downloading right now",
    "bitmagnet": "search the Bitmagnet DHT index for 4K BluRay or FLAC torrents",
    "sabnzbd": "pause my usenet download queue",
```
In `_QUERY_PRIORITY`:
```python
_QUERY_PRIORITY = [
    "radarr", "sonarr", "qbittorrent", "bitmagnet", "romm", "lidarr",
    "jellyfin", "gamevault", "prowlarr", "sabnzbd", "rdtclient", "bookshelf",
]
```

#### Passo 2.2: Aggiornamento di `src/server.py`
File: `/Users/olindo/prj/k8s-lab/docker/mcp/in-house/arrstack-mcp/src/server.py`

1. **Imports** (aggiungere in testa a `src/server.py` subito dopo gli import standard esistenti):
```python
from typing import Optional, List, Literal, Dict, Any
from pydantic import BaseModel, Field
```

2. **Configurazione variabili d'ambiente** (aggiungere subito dopo il blocco di configurazione `QBT_PASS` / `QBT_URL`):
```python
BITMAGNET_GRAPHQL_URL = os.environ.get("BITMAGNET_GRAPHQL_URL", "").rstrip("/")
if not BITMAGNET_GRAPHQL_URL:
    bitmagnet_base = os.environ.get("BITMAGNET_URL", "").rstrip("/")
    if bitmagnet_base:
        BITMAGNET_GRAPHQL_URL = f"{bitmagnet_base}/graphql" if not bitmagnet_base.endswith("/graphql") else bitmagnet_base
BITMAGNET_TIMEOUT = float(os.environ.get("BITMAGNET_TIMEOUT", "30.0"))
```

3. **Mappa `SERVICE_CONFIG`** (aggiungere la chiave `"bitmagnet"` all'interno del dizionario `SERVICE_CONFIG` esistente):
```python
    "bitmagnet": ("Bitmagnet", BITMAGNET_GRAPHQL_URL, "bitmagnet_"),
```

4. **Nuova sezione Tool Bitmagnet** (prima di `# ── MCP Prompts ──`):
```python
# ════════════════════════════════════════════════════════════════
#  Bitmagnet Tools (GraphQL DHT & Torrent Search Engine)
# ════════════════════════════════════════════════════════════════

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


_BITMAGNET_SIMPLE_SEARCH_QUERY = """
query SimpleTorrentSearch($input: TorrentContentSearchQueryInput!) {
  torrentContent {
    search(input: $input) {
      items {
        id
        infoHash
        title
        contentType
        seeders
        leechers
        publishedAt
        torrent {
          name
          size
          magnetUri
          filesCount
        }
      }
    }
  }
}
"""

_BITMAGNET_COMPLEX_SEARCH_QUERY = """
query ComplexTorrentSearch($input: TorrentContentSearchQueryInput!) {
  torrentContent {
    search(input: $input) {
      totalCount
      hasNextPage
      items {
        id
        infoHash
        title
        releaseGroup
        contentType
        languages {
          id
          name
        }
        videoResolution
        videoSource
        videoCodec
        video3d
        videoModifier
        seeders
        leechers
        publishedAt
        torrent {
          name
          size
          magnetUri
          filesCount
          tagNames
          files {
            index
            path
            size
          }
        }
        content {
          title
          releaseYear
          overview
          collections {
            name
            type
          }
        }
      }
      aggregations {
        contentType { value count }
        videoResolution { value count }
        videoSource { value count }
        releaseYear { value count }
        language { value label count }
      }
    }
  }
}
"""


def _bitmagnet_enrich_items(
    items: List[Dict[str, Any]],
    min_seeders: Optional[int] = None,
    video_codecs: Optional[List[str]] = None,
    max_files_per_torrent: int = 25,
) -> List[Dict[str, Any]]:
    """Filtra per min_seeders e video_codecs, calcola sizeFormatted e limita i file restituiti."""
    processed = []
    allowed_codecs = {c.lower() for c in video_codecs} if video_codecs else None

    if allowed_codecs:
        if "x265" in allowed_codecs:
            allowed_codecs.add("h265")
        if "h265" in allowed_codecs:
            allowed_codecs.add("x265")
        if "x264" in allowed_codecs:
            allowed_codecs.add("h264")
        if "h264" in allowed_codecs:
            allowed_codecs.add("x264")

    for item in items:
        seeders = item.get("seeders") or 0
        if min_seeders is not None and seeders < min_seeders:
            continue

        if allowed_codecs:
            codec = (item.get("videoCodec") or "").strip().lower()
            if not codec or codec not in allowed_codecs:
                continue

        torrent = item.get("torrent")
        if isinstance(torrent, dict):
            if torrent.get("size") is not None:
                torrent["sizeFormatted"] = _format_size(torrent["size"])

            files = torrent.get("files")
            if isinstance(files, list) and len(files) > 0:
                total_files = len(files)
                for f in files[:max_files_per_torrent]:
                    if isinstance(f, dict) and f.get("size") is not None:
                        f["sizeFormatted"] = _format_size(f["size"])
                if total_files > max_files_per_torrent:
                    torrent["files"] = files[:max_files_per_torrent]
                    torrent["filesTruncated"] = True
                    torrent["filesTotalCount"] = total_files

        processed.append(item)
    return processed


async def _bitmagnet_execute_graphql(query: str, variables: Dict[str, Any]) -> Dict[str, Any]:
    """Esegue la chiamata POST all'endpoint GraphQL di Bitmagnet con gestione errori sanitizzata."""
    if not BITMAGNET_GRAPHQL_URL:
        raise ValueError("Bitmagnet non è configurato. Impostare BITMAGNET_GRAPHQL_URL o BITMAGNET_URL.")

    headers = {"Content-Type": "application/json", "Accept": "application/json"}
    async with httpx.AsyncClient(timeout=BITMAGNET_TIMEOUT, verify=False) as client:
        response = await client.post(
            BITMAGNET_GRAPHQL_URL,
            json={"query": query, "variables": variables},
            headers=headers,
        )
        response.raise_for_status()
        payload = response.json()

        if "errors" in payload and payload["errors"]:
            error_messages = "; ".join(err.get("message", str(err)) for err in payload["errors"])
            raise RuntimeError(f"Errore GraphQL da Bitmagnet: {error_messages}")

        return payload.get("data", {})


@mcp.tool()
async def bitmagnet_simple_search(
    query: str = Field(..., description="Stringa di ricerca full-text (titolo, autore, album, software o infoHash)."),
    contentType: Optional[ContentTypeLiteral] = Field(None, description="Filtra opzionalmente per tipo principale di contenuto."),
    limit: int = Field(10, ge=1, le=50, description="Numero massimo di risultati da restituire (default: 10, max: 50).")
) -> str:
    """Esegue una ricerca testuale rapida su Bitmagnet per trovare torrent e contenuti multimediali tramite parole chiave. Ideale per query veloci con filtro opzionale sulla categoria."""
    if not BITMAGNET_GRAPHQL_URL:
        return "Bitmagnet non è configurato. Impostare BITMAGNET_GRAPHQL_URL o BITMAGNET_URL."

    input_vars: Dict[str, Any] = {
        "queryString": query,
        "limit": limit,
        "orderBy": [{"field": "seeders", "descending": True}]
    }

    if contentType:
        input_vars["facets"] = {"contentType": {"filter": [contentType]}}

    try:
        data = await _bitmagnet_execute_graphql(_BITMAGNET_SIMPLE_SEARCH_QUERY, {"input": input_vars})
        search_res = data.get("torrentContent", {}).get("search", {})
        items = _bitmagnet_enrich_items(search_res.get("items", []))
        return json.dumps({"count": len(items), "items": items}, indent=2, ensure_ascii=False)
    except Exception as error:
        logger.error("bitmagnet_simple_search failed: %s", error)
        return json.dumps({"error": str(error)}, indent=2, ensure_ascii=False)


@mcp.tool()
async def bitmagnet_complex_search(
    queryString: Optional[str] = Field(None, description="Query di ricerca testuale full-text."),
    contentTypes: Optional[List[ContentTypeLiteral]] = Field(None, description="Elenco dei tipi di contenuto da includere (es. ['movie', 'music'])."),
    videoResolutions: Optional[List[VideoResolutionLiteral]] = Field(None, description="Filtra per risoluzioni video (es. ['V1080p', 'V2160p'])."),
    videoSources: Optional[List[VideoSourceLiteral]] = Field(None, description="Filtra per sorgente video (es. ['BluRay', 'WEBDL', 'WEB', 'HDTV'])."),
    videoCodecs: Optional[List[VideoCodecLiteral]] = Field(None, description="Filtra per codec video (es. ['x265', 'AV1', 'H264'])."),
    languages: Optional[List[str]] = Field(None, description="Codici lingua ISO 639-1 (es. ['it', 'en'])."),
    releaseYear: Optional[int] = Field(None, description="Anno di rilascio del contenuto."),
    minSeeders: Optional[int] = Field(None, ge=0, description="Numero minimo di seeders attivi richiesti."),
    tags: Optional[List[str]] = Field(None, description="Filtra per tag associati ai torrent."),
    orderBy: Optional[OrderByInput] = Field(None, description="Criterio di ordinamento dei risultati (default: seeders desc)."),
    limit: int = Field(20, ge=1, le=100, description="Numero di elementi per pagina (default: 20, max: 100)."),
    page: int = Field(1, ge=1, description="Numero di pagina (a partire da 1)."),
    includeTotalCount: bool = Field(True, description="Se True, restituisce il conteggio totale dei risultati."),
    maxFilesPerTorrent: int = Field(25, ge=0, le=100, description="Limite massimo di file dettagliati da includere per singolo torrent per contenere i token (default: 25).")
) -> str:
    """Esegue una ricerca avanzata su Bitmagnet combinando full-text, faccette video (risoluzione, sorgente), lingue, anno, seeders minimi, codec, tag, paginazione e aggregazioni."""
    if not BITMAGNET_GRAPHQL_URL:
        return "Bitmagnet non è configurato. Impostare BITMAGNET_GRAPHQL_URL o BITMAGNET_URL."

    facets: Dict[str, Any] = {
        "contentType": {"aggregate": True},
        "videoResolution": {"aggregate": True},
        "videoSource": {"aggregate": True},
        "releaseYear": {"aggregate": True},
        "language": {"aggregate": True},
    }

    if contentTypes:
        facets["contentType"]["filter"] = contentTypes
    if videoResolutions:
        facets["videoResolution"]["filter"] = videoResolutions
    if videoSources:
        mapped_sources = set()
        for src in videoSources:
            if src == "WEB":
                mapped_sources.update(["WEBDL", "WEBRip"])
            elif src == "HDTV":
                mapped_sources.add("TV")
            else:
                mapped_sources.add(src)
        facets["videoSource"]["filter"] = list(mapped_sources)
    if languages:
        facets["language"]["filter"] = languages
    if releaseYear is not None:
        facets["releaseYear"]["filter"] = [releaseYear]
    if tags:
        facets["torrentTag"] = {"filter": tags}

    order_clause = (
        [{"field": orderBy.field, "descending": orderBy.descending}]
        if orderBy
        else [{"field": "seeders", "descending": True}]
    )

    input_vars: Dict[str, Any] = {
        "limit": limit,
        "page": page,
        "totalCount": includeTotalCount,
        "hasNextPage": True,
        "orderBy": order_clause,
        "facets": facets,
    }

    if queryString:
        input_vars["queryString"] = queryString

    try:
        data = await _bitmagnet_execute_graphql(_BITMAGNET_COMPLEX_SEARCH_QUERY, {"input": input_vars})
        search_res = data.get("torrentContent", {}).get("search", {})

        items = _bitmagnet_enrich_items(
            search_res.get("items", []),
            min_seeders=minSeeders,
            video_codecs=videoCodecs,
            max_files_per_torrent=maxFilesPerTorrent,
        )

        result = {
            "totalCount": search_res.get("totalCount"),
            "hasNextPage": search_res.get("hasNextPage"),
            "returnedCount": len(items),
            "items": items,
            "aggregations": search_res.get("aggregations", {})
        }

        return json.dumps(result, indent=2, ensure_ascii=False)
    except Exception as error:
        logger.error("bitmagnet_complex_search failed: %s", error)
        return json.dumps({"error": str(error)}, indent=2, ensure_ascii=False)
```

---

### FASE 3: Test Unitari & Validazione

#### Passo 3.1: Creazione file `tests/test_bitmagnet.py`
Creare il file `/Users/olindo/prj/k8s-lab/docker/mcp/in-house/arrstack-mcp/tests/test_bitmagnet.py` con i tre test unitari (`test_bitmagnet_simple_search`, `test_bitmagnet_complex_search_filtering`, `test_bitmagnet_not_configured`):
```python
import json
from unittest.mock import AsyncMock, patch
import pytest
import server


@pytest.mark.asyncio
async def test_bitmagnet_not_configured(monkeypatch):
    """Verifica che i tool restituiscano un messaggio chiaro se Bitmagnet non è configurato."""
    monkeypatch.setattr(server, "BITMAGNET_GRAPHQL_URL", "")

    res_simple = await server.bitmagnet_simple_search(query="Ubuntu", contentType=None, limit=5)
    assert "Bitmagnet non è configurato" in res_simple

    res_complex = await server.bitmagnet_complex_search(
        queryString="Ubuntu",
        contentTypes=None,
        videoResolutions=None,
        videoSources=None,
        videoCodecs=None,
        languages=None,
        releaseYear=None,
        minSeeders=None,
        tags=None,
        orderBy=None,
        limit=10,
        page=1,
        includeTotalCount=True,
        maxFilesPerTorrent=25,
    )
    assert "Bitmagnet non è configurato" in res_complex


@pytest.mark.asyncio
async def test_bitmagnet_simple_search(monkeypatch):
    """Verifica bitmagnet_simple_search e la formattazione di sizeFormatted."""
    monkeypatch.setattr(server, "BITMAGNET_GRAPHQL_URL", "[http://10.10.20.50:3333/graphql](http://10.10.20.50:3333/graphql)")

    mock_graphql_data = {
        "torrentContent": {
            "search": {
                "items": [
                    {
                        "id": "tc-1",
                        "infoHash": "abcdef1234567890",
                        "title": "Beethoven Complete Symphonies FLAC",
                        "contentType": "music",
                        "seeders": 42,
                        "leechers": 3,
                        "publishedAt": "2026-01-15T10:00:00Z",
                        "torrent": {
                            "name": "Beethoven.Complete.Symphonies.FLAC",
                            "size": 1073741824,
                            "magnetUri": "magnet:?xt=urn:btih:abcdef1234567890",
                            "filesCount": 9,
                        },
                    }
                ]
            }
        }
    }

    with patch.object(server, "_bitmagnet_execute_graphql", new=AsyncMock(return_value=mock_graphql_data)) as mock_exec:
        raw_out = await server.bitmagnet_simple_search(query="Beethoven", contentType="music", limit=5)
        payload = json.loads(raw_out)

        assert payload["count"] == 1
        assert payload["items"][0]["seeders"] == 42
        assert "sizeFormatted" in payload["items"][0]["torrent"]

        called_query, called_vars = mock_exec.call_args[0]
        assert called_vars["input"]["queryString"] == "Beethoven"
        assert called_vars["input"]["limit"] == 5
        assert called_vars["input"]["facets"] == {"contentType": {"filter": ["music"]}}


@pytest.mark.asyncio
async def test_bitmagnet_complex_search_filtering(monkeypatch):
    """Verifica mappatura WEB->WEBDL/WEBRip, filtro post-query minSeeders/videoCodecs e troncamento file."""
    monkeypatch.setattr(server, "BITMAGNET_GRAPHQL_URL", "[http://10.10.20.50:3333/graphql](http://10.10.20.50:3333/graphql)")

    mock_graphql_data = {
        "torrentContent": {
            "search": {
                "totalCount": 3,
                "hasNextPage": False,
                "items": [
                    {
                        "id": "1",
                        "title": "Movie 4K HEVC Valid",
                        "seeders": 25,
                        "videoCodec": "H265",
                        "torrent": {
                            "size": 5000000000,
                            "files": [
                                {"index": 0, "path": "movie.mkv", "size": 4990000000},
                                {"index": 1, "path": "subs.srt", "size": 50000},
                                {"index": 2, "path": "info.nfo", "size": 1000},
                            ],
                        },
                    },
                    {
                        "id": "2",
                        "title": "Movie Low Seeders (Filtered Out)",
                        "seeders": 2,
                        "videoCodec": "x265",
                        "torrent": {"size": 4000000000, "files": []},
                    },
                    {
                        "id": "3",
                        "title": "Movie Wrong Codec (Filtered Out)",
                        "seeders": 50,
                        "videoCodec": "x264",
                        "torrent": {"size": 3000000000, "files": []},
                    },
                ],
                "aggregations": {"contentType": [{"value": "movie", "count": 3}]},
            }
        }
    }

    with patch.object(server, "_bitmagnet_execute_graphql", new=AsyncMock(return_value=mock_graphql_data)) as mock_exec:
        raw_out = await server.bitmagnet_complex_search(
            queryString="Movie",
            contentTypes=["movie"],
            videoResolutions=["V2160p"],
            videoSources=["WEB"],
            videoCodecs=["x265"],
            languages=["it", "en"],
            releaseYear=2025,
            minSeeders=10,
            tags=["uhd"],
            orderBy=None,
            limit=20,
            page=1,
            includeTotalCount=True,
            maxFilesPerTorrent=2,
        )
        payload = json.loads(raw_out)

        assert payload["totalCount"] == 3
        assert payload["returnedCount"] == 1
        item = payload["items"][0]
        assert item["id"] == "1"
        assert item["torrent"]["filesTruncated"] is True
        assert item["torrent"]["filesTotalCount"] == 3
        assert len(item["torrent"]["files"]) == 2

        _, called_vars = mock_exec.call_args[0]
        facets = called_vars["input"]["facets"]
        assert set(facets["videoSource"]["filter"]) == {"WEBDL", "WEBRip"}
        assert facets["releaseYear"]["filter"] == [2025]
        assert facets["torrentTag"] == {"filter": ["uhd"]}
```

#### Passo 3.2: Esecuzione verifica sintassi e test
```bash
python3 -m py_compile /Users/olindo/prj/k8s-lab/docker/mcp/in-house/arrstack-mcp/src/server.py /Users/olindo/prj/k8s-lab/docker/mcp/in-house/arrstack-mcp/src/ard.py
uv run --with pytest --with pytest-mock --with pytest-asyncio --with httpx --with "mcp>=1.0.0,<2.0.0" --with pydantic pytest /Users/olindo/prj/k8s-lab/docker/mcp/in-house/arrstack-mcp/tests
```

---

### FASE 4: Aggiornamento Dichiarativo `docker-compose.yaml` e Build GHCR

#### Passo 4.1: Modifica di `docker/mcp/docker-compose.yaml`
```yaml
  arrstack-mcp:
    container_name: mcp-arrstack
    image: ghcr.io/pindaroli/arrstack-mcp:1.2.0
    restart: unless-stopped
    env_file: .env
    environment:
      - ENABLED_SERVICES=radarr,lidarr,prowlarr,qbittorrent,bitmagnet
      - RADARR_URL=[https://radarr-internal.pindaroli.org](https://radarr-internal.pindaroli.org)
      - RADARR_API_KEY=${ARRSTACK_RADARR_API_KEY}
      - LIDARR_URL=[https://lidarr-internal.pindaroli.org](https://lidarr-internal.pindaroli.org)
      - LIDARR_API_KEY=${ARRSTACK_LIDARR_API_KEY}
      - PROWLARR_URL=[http://10.10.20.50:9696](http://10.10.20.50:9696)
      - PROWLARR_API_KEY=${ARRSTACK_PROWLARR_API_KEY}
      - QBT_URL=[http://10.10.20.50:8080](http://10.10.20.50:8080)
      - QBT_USER=admin
      - QBT_PASS=${ARRSTACK_QBT_PASS}
      - BITMAGNET_GRAPHQL_URL=[http://10.10.20.50:3333/graphql](http://10.10.20.50:3333/graphql)
      - BITMAGNET_TIMEOUT=30.0
      - MCP_ALLOWED_HOSTS=*
      - MCP_DNS_REBINDING_PROTECTION=false
```

#### Passo 4.2: Git commit e push
```bash
git add docker/mcp/in-house/arrstack-mcp/ docker/mcp/docker-compose.yaml
git commit -m "feat(arrstack-mcp): v1.2.0 estensione Bitmagnet GraphQL (simple & complex search)"
git push origin main
```
Verifica completamento build GHCR (attesa sincrona fino al termine della pipeline):
```bash
sleep 5
RUN_ID=$(gh run list --workflow=docker-arrstack-mcp.yml --limit=1 --json databaseId -q '.[0].databaseId')
gh run watch "$RUN_ID" --exit-status
```

---

### FASE 5: Rollout TrueNAS e Test Live E2E

#### Passo 5.1: Sincronizzazione e restart container
```bash
scp -o BatchMode=yes docker/mcp/docker-compose.yaml olindo@10.10.20.50:/mnt/stripe/truenas-docker/mcp/docker-compose.yaml
ssh -o BatchMode=yes olindo@10.10.20.50 "cd /mnt/stripe/truenas-docker/mcp && sudo docker compose pull arrstack-mcp && sudo docker compose up -d arrstack-mcp"
```

#### Passo 5.2: Test E2E JSON-RPC via Traefik (:8100)
```bash
SESSION_ID=$(curl -si -X POST [http://10.10.20.50:8100/arrstack/mcp](http://10.10.20.50:8100/arrstack/mcp) \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -d '{"jsonrpc":"2.0","id":0,"method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"e2e-test","version":"1.0.0"}}}' \
  | awk 'tolower($1)=="mcp-session-id:" {print $2}' | tr -d '\r')

curl -s -X POST [http://10.10.20.50:8100/arrstack/mcp](http://10.10.20.50:8100/arrstack/mcp) \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  ${SESSION_ID:+-H "Mcp-Session-Id: $SESSION_ID"} \
  -d '{"jsonrpc": "2.0", "id": 1, "method": "tools/call", "params": {"name": "bitmagnet_simple_search", "arguments": {"query": "Beethoven", "limit": 2}}}'
```

---

### FASE 6: Chiusura Documentale

#### Passo 6.1: Aggiornamento Wiki
- `wiki/entities/MCP_Platform.md`
- `wiki/entities/Servarr.md`
- `wiki/plans/arrstack-mcp-bitmagnet-graphql-extension.md` (`status: completed`)
- `todo.md` (spunta task)

#### Passo 6.2: Sincronizzazione finale
```bash
python3 scripts/network/validate_network.py && python3 scripts/wiki/build_wiki_context.py
```

---

## 💾 Stato di Ripristino (AI Save-State)
- **Fase Attiva**: Piano Completato con Successo ✅
- **Ultima Azione Completata**: Rollout su TrueNAS SCALE, test E2E JSON-RPC via Traefik Gateway (`:8100`) con esito positivo (55 tool attivi, inclusi `bitmagnet_simple_search` e `bitmagnet_complex_search`), aggiornamento entità Wiki (`MCP_Platform.md`, `Servarr.md`) e `todo.md`.
- **Prossimo Passo Operativo**: Nessuno. Funzionalità integrata in produzione.
- **Blocchi/Decisioni Pendenti**: Nessuno.

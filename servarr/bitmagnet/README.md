# BitMagnet GraphQL Schema & Operations

Questo repository contiene la definizione completa dello schema GraphQL (SDL - Schema Definition Language) di **BitMagnet**, estratto direttamente dall'istanza live in esecuzione nell'homelab, unitamente alla scomposizione modulare dei sorgenti e alle definizioni delle operazioni (query, mutazioni, frammenti).

---

## 📌 Informazioni Generali

- **Servizio**: BitMagnet (BitTorrent DHT Crawler, Search Engine, Content Classifier & Torznab Indexer)
- **Versione**: `v0.10.1` (`ghcr.io/bitmagnet-io/bitmagnet:v0.10.1`)
- **Collocazione Homelab**: TrueNAS SCALE Bare Metal (`10.10.20.50`), Docker Compose su storage NVMe (`/mnt/stripe/truenas-docker/bitmagnet/`)
- **GraphQL Endpoint**: `http://10.10.20.50:3333/graphql` (e risoluzione interna Docker `http://bitmagnet:3333/graphql`)
- **Web UI**: `http://10.10.20.50:3333/webui/torrents`
- **Torznab API**: `http://10.10.20.50:3333/torznab/` (indicizzatore Prowlarr ID 15)

---

## 🗂️ Struttura Directory

```text
servarr/bitmagnet/
├── schema.graphql              # Schema Definition Language (SDL) unificato ed esaustivo estratto via introspezione
├── README.md                   # Documentazione di riferimento API ed esempi operativi
├── schema/                     # Definizioni modulari dello schema (gqlgen)
│   ├── enums.graphqls          # Enumeratori (ContentType, VideoQuality, AudioCodec, ecc.)
│   ├── metrics.graphqls        # Metriche aggregate e serie temporali
│   ├── models.graphqls         # Modelli entità (Content, Metadata, Torrent, File, ecc.)
│   ├── mutation.graphqls       # Mutazioni root (TorrentMutation, QueueMutation)
│   ├── query.graphqls          # Query root (TorrentQuery, TorrentContentQuery, Health, Workers)
│   ├── queue.graphqls          # Gestione code di lavoro e reprocessing
│   ├── scalars.graphqls        # Tipi scalari personalizzati (DateTime, Date, Year, Map, Void)
│   ├── torrent_content.graphqls # Ricerca e facet di torrent associati a contenuti
│   └── torrent_files.graphqls  # Ispezione file e directory interni ai torrent
└── operations/                 # Operazioni GraphQL client
    ├── queries/                # Query precostruite (HealthCheck, TorrentContentSearch, QueueJobs, ecc.)
    ├── mutations/              # Mutazioni precostruite (TorrentDelete, Reprocess, Tags, Purge)
    └── fragments/              # Frammenti riutilizzabili (Torrent, Content, TorrentContent, ecc.)
```

---

## 🔍 Schema Summary (Top-Level Types)

### Query Root (`Query`)
| Campo | Tipo Ritorno | Descrizione |
| :--- | :--- | :--- |
| `version` | `String!` | Restituisce la versione applicativa attiva (es. `v0.10.1`) |
| `health` | `HealthQuery!` | Stato di salute e check dei sottosistemi (database, dht, worker) |
| `workers` | `WorkersQuery!` | Lista dei worker attivi (http_server, queue_server, dht_crawler) |
| `queue` | `QueueQuery!` | Ispezione e metriche dei job in coda Redis/PostgreSQL |
| `torrent` | `TorrentQuery!` | Ispezione file dei torrent, elenco sorgenti e suggerimento tag |
| `torrentContent` | `TorrentContentQuery!` | Motore di ricerca avanzato torrent con filtri e aggregazioni (facets) |

### Mutation Root (`Mutation`)
| Campo | Tipo Ritorno | Descrizione |
| :--- | :--- | :--- |
| `torrent` | `TorrentMutation!` | Cancellazione torrent, modifica/aggiunta tag, riprocessamento singolo |
| `queue` | `QueueMutation!` | Enqueue batch di reprocessing (con classificazione TMDb), purge dei job |

---

## 🚀 Esempi di Utilizzo (cURL & GraphQL)

### 1. Verifica Versione e Stato di Salute
```bash
curl -s -X POST http://10.10.20.50:3333/graphql \
  -H "Content-Type: application/json" \
  -d '{
    "query": "query { version health { status checks { key status } } }"
  }' | jq
```

### 2. Ricerca Torrent per Titolo e Tipologia
```bash
curl -s -X POST http://10.10.20.50:3333/graphql \
  -H "Content-Type: application/json" \
  -d '{
    "query": "query Search($input: TorrentContentSearchQueryInput!) { torrentContent { search(input: $input) { totalCount items { id infoHash title contentType torrent { seeders leechers size } } } } }",
    "variables": {
      "input": {
        "queryString": "Matrix",
        "limit": 5
      }
    }
  }' | jq
```

### 3. Ispezione Metriche Code
```bash
curl -s -X POST http://10.10.20.50:3333/graphql \
  -H "Content-Type: application/json" \
  -d '{
    "query": "query { queue { metrics { queue count } } }"
  }' | jq
```

---

## 🔄 Procedura di Rigenerazione dello Schema

Qualora l'immagine BitMagnet venga aggiornata a una nuova release (es. `v0.11.x`), lo schema SDL può essere rieseguito ed estratto con:

```bash
npx -y get-graphql-schema http://10.10.20.50:3333/graphql > servarr/bitmagnet/schema.graphql
```

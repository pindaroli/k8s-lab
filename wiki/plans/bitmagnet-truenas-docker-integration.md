---
title: "Piano: Integrazione Bitmagnet nello Stack Docker su TrueNAS SCALE (Porte 3333/3334)"
type: plan
status: archived
certified_for_ai: false
resolved: true
resolved_at: "2026-10-15"
created_at: 2026-10-14
tags:
  - "#plan"
  - "#bitmagnet"
  - "#docker"
  - "#truenas"
  - "#servarr"
  - "#dht"
  - "#indexer"
---

# Piano: Integrazione Bitmagnet nello Stack Docker su TrueNAS SCALE (Porte 3333/3334)

Questo piano definisce l'integrazione architetturale e operativa di **Bitmagnet** all'interno dello stack Docker primario su TrueNAS SCALE bare-metal (`10.10.20.50`), fornendo un crawler DHT autonomo, motore di classificazione contenuti, arricchimento TMDb per la WebUI, search engine torrent locale ed endpoint **Torznab** integrato direttamente con **Prowlarr** e la suite Servarr.

---

## 🎯 Obiettivi Architetturali

1. **Indicizzazione DHT e Torznab Locale Autonomo**:
   - Operare un crawler BitTorrent DHT locale per scoprire, indicizzare e catalogare infohash e metadati torrent in tempo reale direttamente sul pool NVMe `stripe` di TrueNAS.
   - Fornire un endpoint **Torznab** compatibile per l'integrazione diretta in Prowlarr (e di riflesso Sonarr, Radarr, Lidarr), aumentando la resilienza contro il blocco o l'inaccessibilità di tracker pubblici/esterni.
2. **Architettura a Due Container Segregata (App + DB)**:
   - Deploy del servizio `bitmagnet` affiancato da un'istanza dedicata e ottimizzata di **PostgreSQL 16** (`bitmagnet-postgres`) con estensioni trigram e GIN abilitate e `shm_size: 1g`.
   - Porta 5432 **non esposta sull'host LAN**: il database opera esclusivamente all'interno della rete bridge Docker, isolato e protetto.
3. **Persistenza su Storage NVMe (`stripe`)**:
   - Allocazione delle directory di configurazione e dei dati PostgreSQL sul pool ZFS ad alte prestazioni `/mnt/stripe/truenas-docker/bitmagnet/`, garantendo latenze minime di scrittura WAL, commit transazionali istantanei e zero stress meccanico/rumore sugli hard disk di `oliraid`.
4. **Sicurezza di Rete (Zero Esposizione WAN)**:
   - Funzionamento in **outbound NAT puro**: Bitmagnet effettua query DHT verso l'esterno sfruttando la state-table di OPNsense senza richiedere alcuna regola di port forwarding sulla WAN.
5. **Gestione Sicura dei Segreti (SOPS)**:
   - Cifratura dell'API Key TMDb in `secrets-sops/tmdb-credentials.enc.yaml` e iniezione nel file `.env` di TrueNAS.
6. **Osservabilità e Visibilità Immediata**:
   - Rilevamento automatico e live log inspection tramite **Dozzle** (`10.10.20.50:8888`).
   - Aggiunta della card di servizio su **Homepage** (K8s, Local e TrueNAS) conforme alle regole di `homepage-manager`.

---

## 🗺️ Mappe Concettuali e Relazioni
- [[TrueNAS]] (TrueNAS SCALE bare-metal `10.10.20.50` su VLAN 20)
- [[Servarr]] (Stack multimediale e integrazione Prowlarr)
- [[Homepage]] (Dashboard unificata di monitoraggio e indicatori di salute)
- [[dozzle-truenas-docker-integration]] (Osservabilità e streaming log live)
- [[servarr-truenas-permanent-migration]] (Stack container principale su TrueNAS)

---

## 1. Parametri di Configurazione Concordati

### 1.1 Immagini e Version Pinning
- **Bitmagnet**: `ghcr.io/bitmagnet-io/bitmagnet:v0.10.1` (ultima release stabile, no `:latest`).
- **PostgreSQL**: `postgres:16-alpine` (versione ufficialmente supportata e raccomandata, footprint ~100MB, estensioni `pg_trgm` e `btree_gin` native).

### 1.2 Mappatura Porte e Rete
- **Host IP**: TrueNAS `10.10.20.50` (VLAN 20 Client).
- **Porte Bitmagnet**:
  - `3333:3333` (TCP): Web UI, GraphQL API ed endpoint Torznab (`http://10.10.20.50:3333` e `http://bitmagnet:3333`).
  - `3334:3334/tcp` & `3334:3334/udp`: BitTorrent DHT crawler listening port interna per sessioni outbound NAT.
- **Porte PostgreSQL (`bitmagnet-postgres`)**:
  - Porta `5432`: **ESCLUSIVAMENTE INTERNA** alla rete bridge Docker. Non esposta sull'host TrueNAS per evitare conflitti e garantire la massima sicurezza.
- **Firewall OPNsense**: **Nessun Port Forwarding WAN**. Il crawler opera al 100% in outbound NAT. qBittorrent continua a usare la sua porta `30661` dedicata.

### 1.3 Storage e Volumi ZFS
Collocazione su pool NVMe `stripe` (`/mnt/stripe/truenas-docker/bitmagnet/`):
- `/mnt/stripe/truenas-docker/bitmagnet/postgres` ➔ `/var/lib/postgresql/data` (dati database relazionale, indici GIN/trigram, stima crescita ~10-30 GB a regime).
- `/mnt/stripe/truenas-docker/bitmagnet/config` ➔ `/root/.config/bitmagnet` (configurazione applicativa).
- `/mnt/stripe/truenas-docker/bitmagnet/data` ➔ `/root/.local/share/bitmagnet` (cache e dati runtime).

### 1.4 Variabili d'Ambiente e Tuning
- **PostgreSQL**:
  - `POSTGRES_DB=bitmagnet`
  - `POSTGRES_USER=postgres`
  - `POSTGRES_PASSWORD=${BITMAGNET_DB_PASSWORD:-postgres}` (configurabile in `.env`)
  - `PGUSER=postgres`
  - `shm_size: 1g` (allocazione memoria condivisa per parallel query execution e GIN indexing).
- **Bitmagnet**:
  - `POSTGRES_HOST=bitmagnet-postgres`
  - `POSTGRES_PORT=5432`
  - `POSTGRES_DB=bitmagnet`
  - `POSTGRES_USER=postgres`
  - `POSTGRES_PASSWORD=${BITMAGNET_DB_PASSWORD:-postgres}`
  - `TMDB_API_KEY=${TMDB_API_KEY}` (gestito via SOPS `secrets-sops/tmdb-credentials.enc.yaml` e proiettato in `.env`).
  - `DHT_CRAWLER_SCALING_FACTOR=10` (confermato: concurrency elevata per massima velocità di indicizzazione su rete 10G).
  - `DHT_CRAWLER_SAVE_FILES_THRESHOLD=500` (limite massimo di singoli file indicizzati per torrent per supportare cofanetti musicali e serie).
  - `DHT_CRAWLER_SAVE_PIECES=false` (disabilitato per risparmiare decine di GB non necessari per la ricerca).
  - `LOG_LEVEL=info`
  - `TZ=Europe/Rome`

### 1.5 Sottosistemi Worker (`command`)
Esecuzione contestuale dei 3 componenti core all'interno del container applicativo:
- `--keys=http_server`: Web UI, GraphQL e Torznab su porta 3333.
- `--keys=queue_server`: Gestione della coda asincrona di classificazione metadati e TMDb.
- `--keys=dht_crawler`: Motore di crawling e discovery sulla rete DHT.

---

## 2. Definizione Dichiarativa Docker Compose

Il blocco da integrare in `servarr/truenas-docker/docker-compose.yaml`:

```yaml
  bitmagnet-postgres:
    image: postgres:16-alpine
    container_name: bitmagnet-postgres
    restart: unless-stopped
    shm_size: 1g
    environment:
      - POSTGRES_DB=bitmagnet
      - POSTGRES_USER=postgres
      - POSTGRES_PASSWORD=${BITMAGNET_DB_PASSWORD:-postgres}
      - PGUSER=postgres
    volumes:
      - /mnt/stripe/truenas-docker/bitmagnet/postgres:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U postgres -d bitmagnet"]
      interval: 10s
      timeout: 5s
      retries: 5
      start_period: 20s

  bitmagnet:
    image: ghcr.io/bitmagnet-io/bitmagnet:v0.10.1
    container_name: bitmagnet
    restart: unless-stopped
    ports:
      - "3333:3333"
      - "3334:3334/tcp"
      - "3334:3334/udp"
    environment:
      - POSTGRES_HOST=bitmagnet-postgres
      - POSTGRES_PORT=5432
      - POSTGRES_DB=bitmagnet
      - POSTGRES_USER=postgres
      - POSTGRES_PASSWORD=${BITMAGNET_DB_PASSWORD:-postgres}
      - TMDB_API_KEY=${TMDB_API_KEY}
      - DHT_CRAWLER_SCALING_FACTOR=10
      - DHT_CRAWLER_SAVE_FILES_THRESHOLD=500
      - DHT_CRAWLER_SAVE_PIECES=false
      - LOG_LEVEL=info
      - TZ=Europe/Rome
    volumes:
      - /mnt/stripe/truenas-docker/bitmagnet/config:/root/.config/bitmagnet
      - /mnt/stripe/truenas-docker/bitmagnet/data:/root/.local/share/bitmagnet
    command:
      - worker
      - run
      - --keys=http_server
      - --keys=queue_server
      - --keys=dht_crawler
    depends_on:
      bitmagnet-postgres:
        condition: service_healthy
```

---

## 3. Integrazione con l'Ecosistema Homelab

### 3.1 Integrazione Torznab in Prowlarr
Prowlarr risiede nello stesso stack Docker compose (`servarr/truenas-docker/docker-compose.yaml`).
- **Tipo Indexer**: Torznab generico ("Torznab")
- **URL Base**: `http://bitmagnet:3333/torznab/` (risoluzione DNS interna Docker) oppure `http://10.10.20.50:3333/torznab/` (LAN).
- **API Key**: Qualsiasi valore (es. `bitmagnet`) se l'autenticazione è disabilitata di default in Bitmagnet.
- **Categorie**: 2000 (Movies), 5000 (TV), 3000 (Audio/Music), 4000 (PC), 7000 (Books).

### 3.2 Integrazione Dashboard Homepage
Aggiunta conforme a `homepage-manager` nella sezione Media / Indexers:
```yaml
    - Bitmagnet:
        icon: bitmagnet.png
        href: "http://10.10.20.50:3333"
        description: "DHT Crawler & Torrent Indexer"
        ping: "http://10.10.20.50:3333"
```

---

## 4. Fasi Operative Dettagliate

### FASE 1: Salvataggio Segreto SOPS & Approvazione Piano (COMPLETATA ✅)
- [x] Ricezione API Key TMDb.
- [x] Creazione del segreto SOPS cifrato `secrets-sops/tmdb-credentials.enc.yaml`.
- [x] Validazione decifratura `sops -d`.

### FASE 2: Aggiornamento Dichiarativo Repository (COMPLETATA ✅)
- [x] Aggiunta dei servizi `bitmagnet-postgres` e `bitmagnet` in `servarr/truenas-docker/docker-compose.yaml` (soglia 500).
- [x] Aggiornamento di `servarr/truenas-docker/.env.example` con `TMDB_API_KEY` e `BITMAGNET_DB_PASSWORD`.
- [x] Validazione sintattica YAML.

### FASE 3: Preparazione Storage & Rollout su TrueNAS (`10.10.20.50`) (COMPLETATA ✅)
- [x] Creazione directory ZFS `/mnt/stripe/truenas-docker/bitmagnet/{postgres,config,data}` con owner e permessi `777` (`olindo:k8s`).
- [x] Iniezione sicura di `TMDB_API_KEY` decifrata da SOPS nel file `.env` su TrueNAS (`/mnt/stripe/truenas-docker/.env`).
- [x] Sincronizzazione del file `docker-compose.yaml` aggiornato in `/mnt/stripe/truenas-docker/`.
- [x] Pull delle immagini OCI `postgres:16-alpine` e `ghcr.io/bitmagnet-io/bitmagnet:v0.10.1`.
- [x] Avvio dei container con `docker compose up -d bitmagnet-postgres bitmagnet`.

### FASE 4: Validazione Test-Driven (COMPLETATA ✅)
- [x] Verifica stato healthcheck PostgreSQL: `docker compose ps bitmagnet-postgres` (healthy).
- [x] Verifica log di avvio, migrazioni DB, avvio worker `http_server` e `dht_crawler`, e connessione TMDb.
- [x] Verifica risposta HTTP Web UI e Torznab:
  - `curl -I http://10.10.20.50:3333/webui` (200 OK)
  - `curl -s "http://10.10.20.50:3333/torznab/api?t=caps"` (XML Torznab valido con supporto `tmdbid`)
  - Test reale ricerca musica classica (`Beethoven`): risultati FLAC/CUE e magnetlink già indicizzati.
- [x] Verifica visibilità automatica log su Dozzle (`http://10.10.20.50:8888`).

### FASE 5: Integrazioni Finali & Consolidamento (COMPLETATA ✅)
- [x] Aggiunta dell'indexer Torznab in Prowlarr (`http://bitmagnet:3333/torznab/`, Indexer ID 15 con test superato `{}`).
- [x] Aggiornamento simmetrico delle dashboard Homepage (`homepage.yaml`, `homepage-local.yaml` e TrueNAS `services.yaml`) con icona verificata `bitmagnet.png`.
- [x] Rollout Kubernetes `homepage` e `homepage-local` completato con stato `1/1 Running`.
- [x] Sincronizzazione `todo.md`, rigenerazione context wiki (`build_wiki_context.py`) e chiusura piano.

---

## 💾 Stato di Ripristino (AI Save-State)
- **Fase Attiva**: Piano Completato con Successo (Fasi 1-5 concluse)
- **Ultima Azione Completata**: Bitmagnet e bitmagnet-postgres attivi su TrueNAS NVMe `stripe`, Torznab agganciato a Prowlarr (ID 15), card presente su tutte le dashboard Homepage, piano archiviato e documentato
- **Prossimo Passo Operativo**: Nessuno
- **Blocchi/Decisioni Pendenti**: Nessuno


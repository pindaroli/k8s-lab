---
title: "Servarr Stack & qBittorrent"
last_updated: "2026-10-22"
confidence: "High"
tags:
  - "#app"
  - "#media"
  - "#torrent"
provenance:
  - "servarr/opnsense-port-forward-config.md"
---

# Servarr Stack

La stack Servarr (Radarr, Sonarr, Lidarr, Prowlarr) è ospitata nel namespace `arr` e utilizza PostgreSQL per i database.

## 1. Sicurezza e Accesso
Tutti i servizi esposti esternamente (es. `radarr.pindaroli.org`) sono protetti da [[OAuth2_Proxy]]. Il traffico interno è diretto o passa via Traefik `-internal`.

## 2. qBittorrent (UPnP & Port Forwarding)
qBittorrent è isolato via MetalLB su un IP dedicato (`10.10.20.60`).
Non utilizza più i sidecar Xray/VPN, il traffico è diretto.

### Configurazione UPnP su OPNsense
Per garantire la raggiungibilità dei peer, qBittorrent utilizza UPnP.
1. **LoadBalancer**: Il servizio `qbittorrent-bittorrent-lb` espone la porta `30661`.
2. **OPNsense**: UPnP & NAT-PMP abilitato sulla WAN.
3. **Access Control**: OPNsense ha una regola UPnP restrittiva per permettere solo all'IP del LoadBalancer di aprire porte:
   `allow 30661-30661 10.10.20.60/32 30661-30661`
4. **Local Traffic Policy**: Il servizio Kubernetes DEVE avere `externalTrafficPolicy: Local` per preservare l'IP sorgente necessario a UPnP.

### Categorie e Percorsi di Salvataggio
Le categorie di download sono gestite in modo dichiarativo e create automaticamente al post-deploy tramite un Job Helm. Esse risiedono nella share NFS `media` sotto la cartella `/media/downloads/`:
* **`radarr`** (Film) -> `/media/downloads/radarr` (fisico: `/mnt/oliraid/arrdata/media/downloads/radarr`)
* **`lidarr`** (Musica Pop/Rock) -> `/media/downloads/lidarr` (fisico: `/mnt/oliraid/arrdata/media/downloads/lidarr`)
* **`readarr`** (Libri/Audiolibri) -> `/media/downloads/readarr` (fisico: `/mnt/oliraid/arrdata/media/downloads/readarr`)
* **`classical`** (Musica Classica) -> `/media/downloads/classical` (fisico: `/mnt/oliraid/arrdata/media/downloads/classical`)

Tutte le categorie utilizzano l'Auto Torrent Management (TMM) per gestire lo spostamento automatico dei file una volta pronti.

## 3. Lidarr & Music Ingestion
La gestione musicale è affidata a una singola istanza Lidarr.
- **Scopo**: Gestione automatica musica (Pop, Rock, Elettronica, ecc.).
- **Ingestione**: Automatico tramite Completed Download Handling abilitato.
- **Volume Ingestione (RW)**: `/Volumes/arrdata/media/music/pop_rock`.
- **Categoria qBittorrent**: `lidarr` (mappato a `/media/downloads/lidarr`).

*(Nota: L'architettura multi-istanza con `lidarr-classic` e `jellyfin-classic` è stata dismessa per semplificare la gestione).*

## 4. MCP Server & Automazione (arrstack-mcp)
Lo stack Servarr è governato tramite il server MCP `arrstack-mcp` (versione `1.2.0`), ospitato su TrueNAS SCALE bare-metal (`10.10.20.50:8100/arrstack/mcp` dietro Traefik Umbrella Gateway) e configurato centralmente in `~/.gemini/antigravity/mcp_config.json`.
- **Servizi Abilitati**: Radarr, Lidarr, Prowlarr, qBittorrent, Bitmagnet (55 tool esposti: gestione librerie multimediali, indexer, client download e ricerca full-text/multi-filtro sul crawler DHT decentralizzato tramite l'endpoint GraphQL di Bitmagnet con `bitmagnet_simple_search` e `bitmagnet_complex_search`).
- **Prompt MCP 2.0 (Template Operativi)**:
  - `audit_downloads`: Ispezione stato download, rilevamento torrent in stallo o con errori, calcolo spazio disco libero e riassunto code.
  - `search_and_grab`: Workflow guidato di ricerca multimediale (film/musica) tramite Prowlarr/Radarr/Lidarr e accodamento automatico su qBittorrent.
  - `media_health_check`: Diagnosi globale di connettività, risposte API e stato di salute per tutti i componenti della stack (Radarr, Lidarr, Prowlarr, qBittorrent).
- **qBittorrent Security & Cookie Patch**: A seguito del breaking change introdotto da qBittorrent v5.2.x (rinomina cookie da `SID` a `QBT_SID_<PORT>`), qBittorrent adotta un `initContainer` dichiarativo in Helm (`qbt-config-security` in `servarr/arr-values.yaml`) e `arrstack-mcp` implementa il matching dinamico del cookie di sessione.
- **Incidente Correlato**: [[2026-09-02-qbittorrent-5.2-auth-cookie-breaking-change]].


## 5. Radarr, Video Ingestion & Normalizer (Pattern Metadati e Multi-Versione)
L'ingestion dei film, la sanificazione delle versioni multiple e la gestione dei file multimediali su `/media/movies/` segue rigorosamente il pattern [[movie-metadata-and-artwork-architecture]] e il workflow [[media-normalization-pipeline]]:
- **Radarr**: opera con il profilo metadati `Kodi (XBMC) / Emby` configurato con `movieMetadata: false` (nessun NFO generato) e `movieImages: true` (locandine `poster.jpg` e `fanart.jpg` salvate localmente).
- **FileBot Normalizer (`webhook-normalizer`)**: container immutabile Docker su TrueNAS bare-metal (`ghcr.io/pindaroli/custom-normalizer:1.7.1`), auto-contenuto (senza bind-mount di codice da host) e governato dal workflow [[media-normalization-pipeline]]. Esegue FileBot AMC, auto-sanitizzazione multi-versione via `sanitize_movie_folder.py`, purge totale dei file `.nfo` e refresh automatico su Jellyfin.
- **Incidenti Correlati**: [[2026-09-13-jellyfin-duplicate-posters-and-nfo-metadata-conflict]].

## 6. FlareSolverr & External Services Decoupling (Pattern Occam's Razor)
Per superare i meccanismi di protezione anti-bot (Cloudflare Turnstile Challenge) su indexer come FileMood, e mantenere una netta separazione delle risorse computazionali tra Kubernetes e TrueNAS:
- **FlareSolverr su TrueNAS Docker**: container `ghcr.io/flaresolverr/flaresolverr:v3.4.6` attivo nello stack Docker bare-metal su porta `8191` (`10.10.20.50:8191`), risolvibile internamente allo stack come `http://flaresolverr:8191`.
- **Integrazione Prowlarr**: configurato proxy `FlareSolverr` associato al tag `flaresolverr` e agganciato all'indexer `FileMood` (ID: 4), consentendo scraping e ricerca torrent senza blocchi o errori HTTP 403.
- **Decoupling Generico Kubernetes (Helm Project Chart)**: in `charts/servarr/templates/external-services.yaml` (`pindaroli-arr-helm` v1.10.2), i carichi disabilitati su cluster (`flaresolverr`, `prowlarr`, `qbittorrent`) vengono materializzati come `Service` ed `Endpoints` standard via oggetto generico:
  ```yaml
  <component>:
    enabled: false
    external:
      ip: "10.10.20.50"
      port: <port>
  ```
  Questo consente a tutti i pod K8s di raggiungere i servizi esterni attraverso i canonici FQDN del cluster DNS (`http://servarr-flaresolverr:8191`, `http://servarr-prowlarr:9696`, `http://servarr-qbittorrent-web:8080`) senza cablaggi hardcoded nei template né consumo di risorse computazionali sui nodi Talos.
## 7. Bitmagnet DHT Crawler & Torznab Indexer (Sovranità Locale e Anti-Censura)
Per superare la dipendenza dai tracker pubblici soggetti a blocchi DNS, sequestri di dominio, rate limiting e protezioni Cloudflare, lo stack multimediale integra un crawler DHT autonomo e indicizzatore Torznab locale:
- **Bitmagnet su TrueNAS Docker**: container `ghcr.io/bitmagnet-io/bitmagnet:v0.10.1` affiancato da un'istanza dedicata e isolata di **PostgreSQL 16** (`postgres:16-alpine`), attestati sullo storage NVMe ad alte prestazioni `/mnt/stripe/truenas-docker/bitmagnet/` di TrueNAS SCALE bare-metal (`10.10.20.50`).
- **Porte ed Endpoint**:
  - `3333`: WebUI e Torznab API (`http://10.10.20.50:3333/webui/torrents`, `http://bitmagnet:3333/torznab`).
  - `3334`: Porta TCP/UDP per il crawling e l'interrogazione della rete BitTorrent DHT globale (outbound stateful).
- **GraphQL API & SDL Schema**: endpoint `http://10.10.20.50:3333/graphql`. Lo Schema Definition Language (SDL) completo di BitMagnet è estratto e persistito dichiarativamente nel repository in `servarr/bitmagnet/schema.graphql`, unitamente ai sorgenti modulari `servarr/bitmagnet/schema/` e alle operazioni client (queries, mutazioni, frammenti) in `servarr/bitmagnet/operations/`.
- **Integrazione Prowlarr**: indicizzatore Torznab custom integrato via API REST (`baseUrl: http://bitmagnet:3333/torznab`, ID 15) con mappatura nativa per Film (2000), Serie TV (5000), Musica (3000), PC/Software (4000) ed eBook (7000).
- **Arricchimento Metadati**: integrazione API TMDb con chiave cifrata via SOPS (`secrets-sops/tmdb-credentials.enc.yaml`), che permette la classificazione automatica e l'arricchimento con metadati e codici `tmdbid` per il matching trasparente su Radarr.
- **Piano di Riferimento**: [[bitmagnet-truenas-docker-integration]].

## Relazioni
- Namespace: `arr`
- Dipendenze Database: `postgres-main` ([[Talos_Cluster]]).
- Storage: [[TrueNAS]] (`oliraid/arrdata/media/music`).
- Media Server: [[Jellyfin]] (LXC 2200 su PVE3 via `jellyfin-external-svc`).
- Pattern Metadati: [[movie-metadata-and-artwork-architecture]].
- Transcodifica: Inviata a [[Tdarr]].
- Strategia Classica: [[classical-music-strategy]].
- Orchestrazione Classica (Prefect): [[prefect-beets-adaptation]].
- Bonifica Modern: [[beets-music-rescue-pipeline]].
- Piani Correlati: [[bitmagnet-truenas-docker-integration]], [[flaresolverr-truenas-migration-and-declarative-sync]], [[arrstack-mcp-truenas-docker-migration]], [[servarr-truenas-permanent-migration]].
- Incidenti: [[2026-09-02-qbittorrent-5.2-auth-cookie-breaking-change]], [[2026-09-13-jellyfin-duplicate-posters-and-nfo-metadata-conflict]].



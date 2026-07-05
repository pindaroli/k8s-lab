---
title: "Servarr Stack & qBittorrent"
last_updated: "2026-06-07"
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

## 3. Multi-Instance Lidarr & Decoupled Ingestion Pattern
Per gestire l'incompatibilità intrinseca tra la tassonomia standard di Lidarr e l'ontologia della musica classica, la suite media adotta un layout multi-istanza:

### A. `lidarr-pop` (Modern Music)
- **Scopo**: Gestione automatica classica (Pop, Rock, Elettronica).
- **Ingestione**: Automatico tramite Completed Download Handling abilitato.
- **Volume Ingestione (RW)**: `/Volumes/arrdata/media/music/pop_rock`.
- **Categoria qBittorrent**: `lidarr` (mappato a `/media/downloads/lidarr`).

### B. `lidarr-classic` (Classical Music Search-and-Dispatch)
- **Scopo**: Scoperta e invio download per materiale classico, senza diritti di scrittura sulla libreria finale.
- **Ingestione**: Decoppiata. Completed Download Handling **disabilitato** (Genera warning in UI, ignorabile).
- **Volume Staging (RW)**: `/media` (punta a `staging` della share NFS).
- **Categoria qBittorrent**: `classical` (mappato a `/media/downloads/classical`).
- **Sincronizzazione API**: Lo stato dei download viene chiuso spegnendo la proprietà `monitored` **esclusivamente sul singolo album appena elaborato** (`PUT /api/v1/album/{id}` con `monitored=false`) via chiamata REST dal **Task 3 (`sync_media_servers`) del flow Prefect**, non da uno script standalone. Questo evita loop di download infiniti (Lidarr è cieco sulla libreria finale).

### C. Prowlarr Indexer Tags
Per evitare conflitti di scaricamento tra le due istanze:
- Tag `classical-indexers` creato in Prowlarr e assegnato a tracker ad alta fedeltà di classica (es. RED, Usenet dedicati).
- Il profilo di sincronizzazione in Prowlarr mappa i tracker taggati `classical-indexers` **esclusivamente** a `lidarr-classic`. Tracker generici e moderni sono mappati a `lidarr-pop`.

## Relazioni
- Namespace: `arr`
- Dipendenze Database: `postgres-main` ([[Talos_Cluster]]).
- Storage: [[TrueNAS]] (`oliraid/arrdata/media/music`).
- Transcodifica: Inviata a [[Tdarr]].
- Strategia Classica: [[classical-music-strategy]].
- Orchestrazione Classica (Prefect): [[prefect-beets-adaptation]].
- Bonifica Modern: [[beets-music-rescue-pipeline]].

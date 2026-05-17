---
title: "Servarr Stack & qBittorrent"
last_updated: "2026-05-03"
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

## 3. Multi-Instance Lidarr & Decoupled Ingestion Pattern
Per gestire l'incompatibilità intrinseca tra la tassonomia standard di Lidarr e l'ontologia della musica classica, la suite media adotta un layout multi-istanza:

### A. `lidarr-pop` (Modern Music)
- **Scopo**: Gestione automatica classica (Pop, Rock, Elettronica).
- **Ingestione**: Automatico tramite Completed Download Handling abilitato.
- **Volume Ingestione (RW)**: `/Volumes/arrdata/media/music/pop_rock`.
- **Categoria qBittorrent**: `music-pop` (mappato a `/staging/pop_rock`).

### B. `lidarr-classical` (Classical Music Search-and-Dispatch)
- **Scopo**: Scoperta e invio download per materiale classico, senza diritti di scrittura sulla libreria finale.
- **Ingestione**: Decoppiata. Completed Download Handling **disabilitato** (Genera warning in UI, ignorabile).
- **Volume Staging (RO)**: `/staging/classical` (Nessun mount su `/media/music/classical`).
- **Categoria qBittorrent**: `music-classical` (mappato a `/staging/classical`).
- **Sincronizzazione API**: Lo stato dei download viene chiuso spegnendo la proprietà `monitored` dell'album via API POST/PUT dopo l'importazione operata esternamente da Beets.

### C. Prowlarr Indexer Tags
Per evitare conflitti di scaricamento tra le due istanze:
- Tag `classical-indexers` creato in Prowlarr e assegnato a tracker ad alta fedeltà di classica (es. RED, Usenet dedicati).
- Il profilo di sincronizzazione in Prowlarr mappa i tracker taggati `classical-indexers` **esclusivamente** a `lidarr-classical`. Tracker generici e moderni sono mappati a `lidarr-pop`.

## Relazioni
- Namespace: `arr`
- Dipendenze Database: `postgres-main` ([[Talos_Cluster]]).
- Storage: [[TrueNAS]] (`oliraid/arrdata/media/music`).
- Transcodifica: Inviata a [[Tdarr]].
- Strategia Classica: [[classical-music-strategy]].
- Bonifica Modern: [[beets-music-rescue-pipeline]].

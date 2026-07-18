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

## 3. Lidarr & Music Ingestion
La gestione musicale è affidata a una singola istanza Lidarr.
- **Scopo**: Gestione automatica musica (Pop, Rock, Elettronica, ecc.).
- **Ingestione**: Automatico tramite Completed Download Handling abilitato.
- **Volume Ingestione (RW)**: `/Volumes/arrdata/media/music/pop_rock`.
- **Categoria qBittorrent**: `lidarr` (mappato a `/media/downloads/lidarr`).

*(Nota: L'architettura multi-istanza con `lidarr-classic` e `jellyfin-classic` è stata dismessa per semplificare la gestione).*

## Relazioni
- Namespace: `arr`
- Dipendenze Database: `postgres-main` ([[Talos_Cluster]]).
- Storage: [[TrueNAS]] (`oliraid/arrdata/media/music`).
- Transcodifica: Inviata a [[Tdarr]].
- Strategia Classica: [[classical-music-strategy]].
- Orchestrazione Classica (Prefect): [[prefect-beets-adaptation]].
- Bonifica Modern: [[beets-music-rescue-pipeline]].

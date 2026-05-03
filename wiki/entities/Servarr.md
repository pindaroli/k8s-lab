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

La stack Servarr (Radarr, Lidarr, Prowlarr) è ospitata nel namespace `arr` e utilizza PostgreSQL per i database.

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

## Relazioni
- Namespace: `arr`
- Dipendenze Database: `postgres-main` ([[Talos_Cluster]]).
- Storage: [[TrueNAS]] (`oliraid/arrdata/media`).
- Transcodifica: Inviata a [[Tdarr]].

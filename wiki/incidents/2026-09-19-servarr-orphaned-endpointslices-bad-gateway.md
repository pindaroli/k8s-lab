---
title: "INC-2026-09-19: Servarr Migration Orphaned EndpointSlices & qBittorrent/Prowlarr 502 Bad Gateway"
type: incident
status: archived
certified_for_ai: false
date: 2026-09-19
severity: P2
resolved: true
resolved_at: 2026-09-19T00:12:50+02:00
tags:
  - "#incident"
  - "#kubernetes"
  - "#traefik"
  - "#qbittorrent"
  - "#prowlarr"
  - "#servarr"
---

# INC-2026-09-19: Servarr Migration Orphaned EndpointSlices & qBittorrent/Prowlarr 502 Bad Gateway

## Descrizione dell'Incidente
In seguito al completamento della Fase 3 del piano [[servarr-truenas-permanent-migration]] (spegnimento dei carichi di lavoro qBittorrent e Prowlarr su Kubernetes e re-routing del traffico verso le istanze Docker su TrueNAS bare-metal `10.10.10.50`), la WebUI di qBittorrent (`https://qbittorrent-internal.pindaroli.org`) presentava una schermata nera anomala: la toolbar superiore e la barra di stato inferiore venivano caricate, ma l'area centrale dei torrent e la sidebar dei filtri/categorie risultavano completamente vuote.

Contemporaneamente, le chiamate programmatiche verso qBittorrent e Prowlarr tramite il server MCP `arrstack-mcp` (`qbt_transfer_info`, `qbt_list_torrents`) fallivano a intermittenza con:
`qBittorrent request failed: HTTP 502 — Bad Gateway`

## Analisi della Root Cause
L'analisi approfondita dei log di Traefik (`traefik-24dgm`) e delle risorse di rete in namespace `arr` ha isolato la causa:

1. **Transizione da Service con Selector a Service con Endpoints Manuali:**
   Nel chart Helm `pindaroli-arr-helm`, disabilitando `qbittorrent.enabled` e `prowlarr.enabled`, i Service `servarr-qbittorrent-web` e `servarr-prowlarr` sono stati convertiti in Service headless/esterni privi di `spec.selector`, agganciati a manifest `Endpoints` manuali con IP `10.10.10.50`.

2. **Mancata Garbage Collection dell'EndpointSlice Originario:**
   - In Kubernetes, quando un Service ha `spec.selector`, gli `EndpointSlice` sono governati da `endpointslice-controller.k8s.io`.
   - Quando il selettore viene rimosso a favore di un `Endpoints` manuale, `endpointslicemirroring-controller.k8s.io` crea correttamente un nuovo EndpointSlice per TrueNAS (`servarr-qbittorrent-web-5vh6s` $\rightarrow$ `10.10.10.50:8080`).
   - Tuttavia, Kubernetes **non distrugge automaticamente** il vecchio EndpointSlice generato in precedenza (`servarr-qbittorrent-web-nfjht` $\rightarrow$ `10.244.2.250:8080`, e `servarr-prowlarr-2rk47` $\rightarrow$ `10.244.0.117:9696`).

3. **Round-Robin di Traefik verso Pod Inesistenti:**
   Traefik monitora le risorse `EndpointSlice` del cluster. Vedendo due fette attive per lo stesso service, ha distribuito il traffico in round-robin:
   - 50% verso `10.10.10.50:8080` (TrueNAS, esito immediato 200/204 in 1-5ms).
   - 50% verso `10.244.2.250:8080` (vecchio IP Pod su `talos-cp-01` terminato), con conseguente timeout di 3 secondi e risposta `HTTP 502 Bad Gateway`.
   
   A causa di questi 502 intermittenti, il caricamento asincrono di `scripts/client.js`, `views/filters.html` e della chiamata `/api/v2/sync/maindata` andava in crash lato browser, bloccando l'infrastruttura MochaUI di qBittorrent e lasciando la pagina nera.

## Azioni Correttive Adottate
1. **Eliminazione Risorse Orfane:**
   Sono stati eliminati manualmente i due EndpointSlice obsoleti tramite API Kubernetes:
   ```bash
   kubectl delete endpointslice servarr-qbittorrent-web-nfjht -n arr
   kubectl delete endpointslice servarr-prowlarr-2rk47 -n arr
   ```

2. **Validazione e Collaudo:**
   - Eseguito test di 5 chiamate sequenziali di autenticazione a `https://qbittorrent-internal.pindaroli.org/api/v2/auth/login`: 5/5 con esito `HTTP 204` in media 5ms (0% drop).
   - Verificato lo strumento `qbt_transfer_info` e `prowlarr_health` tramite `arrstack-mcp`: esito 200 OK immediato con telemetria torrent e DHT attiva.
   - Verificati i log in tempo reale di Traefik: la sessione del browser (`10.10.20.241`) ha scaricato con successo tutti i template (`filters.html`, `transferlist.html`, `properties.html`) e gli script, ripristinando integralmente la visualizzazione grafica della WebUI.

## Stato
**RISOLTO**.

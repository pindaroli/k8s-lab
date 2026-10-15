---
title: "Piano: Estensione REST API arrstack-mcp per Prowlarr e qBittorrent"
type: plan
status: active
certified_for_ai: true
created_at: 2026-10-15
tags:
  - "#plan"
  - "#mcp"
  - "#servarr"
  - "#prowlarr"
  - "#qbittorrent"
---

# Piano: Estensione REST API arrstack-mcp per Prowlarr e qBittorrent

## 🎯 Obiettivo
Estendere il server MCP `arrstack-mcp` (in esecuzione su TrueNAS SCALE bare-metal sulla porta `8110`) aggiungendo le chiamate REST native di **Prowlarr** e **qBittorrent** attualmente mancanti, eliminando la necessità di ricorrere a chiamate `curl` o workaround via terminale.

---

## 📊 Analisi dello Stato Attuale (`server.py`)

### Prowlarr (Attualmente Presenti: 6 tool)
- `prowlarr_list_indexers`: lista indexer configurati (`GET /api/v1/indexer`)
- `prowlarr_test_indexer`: test singolo indexer (`POST /api/v1/indexer/{id}/test`)
- `prowlarr_test_all_indexers`: test di tutti gli indexer abilitati
- `prowlarr_search`: ricerca release su indexer (`GET /api/v1/search`)
- `prowlarr_grab`: download release e invio a qBittorrent
- `prowlarr_health`: verifica warning e allarmi (`GET /api/v1/health`)

### qBittorrent (Attualmente Presenti: 10 tool)
- `qbt_list_torrents`: lista torrent con filtri (`GET /api/v2/torrents/info`)
- `qbt_torrent_details`: proprietà del torrent (`GET /api/v2/torrents/properties`)
- `qbt_add`: aggiunta universale (magnet, URL, file locale, base64)
- `qbt_add_magnet`: aggiunta magnet (`POST /api/v2/torrents/add`)
- `qbt_add_torrent_file`: upload file .torrent (`POST /api/v2/torrents/add`)
- `qbt_pause`: pausa torrent (`POST /api/v2/torrents/stop`)
- `qbt_resume`: ripresa torrent (`POST /api/v2/torrents/start`)
- `qbt_delete`: eliminazione torrent con/senza dati (`POST /api/v2/torrents/delete`)
- `qbt_set_category`: assegnazione categoria a torrent esistente (`POST /api/v2/torrents/setCategory`)
- `qbt_transfer_info`: statistiche globali di download/upload (`GET /api/v2/transfer/info`)

---

## 🚀 Funzionalità REST Mancanti e Proposta Tool MCP

### 1. Prowlarr — Nuovi Tool Proposti

| Priorità | Nome Tool MCP | Endpoint REST Prowlarr | Descrizione & Utilità |
| :--- | :--- | :--- | :--- |
| **Tier 1 (Core)** | `prowlarr_list_applications` | `GET /api/v1/applications` | Elenca le app collegate (Radarr, Sonarr, Lidarr, ecc.), ID, URL, syncLevel e stato. Risolve direttamente la causa del prompt `curl`. |
| **Tier 1 (Core)** | `prowlarr_sync_applications` | `POST /api/v1/command` (`{"name": "ApplicationSync", "applicationId": id}`) | Forza la sincronizzazione automatica degli indexer verso una o tutte le app collegate. |
| **Tier 1 (Core)** | `prowlarr_test_applications` | `POST /api/v1/applications/{id}/test` o `testall` | Esegue il test di connettività verso le applicazioni Servarr collegate. |
| **Tier 2 (Stats)** | `prowlarr_indexer_stats` | `GET /api/v1/indexerstats` | Statistiche aggregate per indexer: query effettuate, grab eseguiti, fallimenti e latenza media. |
| **Tier 2 (History)** | `prowlarr_history` | `GET /api/v1/history` | Storico dei grab recenti effettuati dagli indexer e dalle applicazioni. |
| **Tier 3 (System)** | `prowlarr_system_status` | `GET /api/v1/system/status` | Info di sistema: versione Prowlarr, tempo di avvio, percorso DB e stato runtime. |

---

### 2. qBittorrent — Nuovi Tool Proposti

| Priorità | Nome Tool MCP | Endpoint REST qBittorrent | Descrizione & Utilità |
| :--- | :--- | :--- | :--- |
| **Tier 1 (Core)** | `qbt_list_categories` | `GET /api/v2/torrents/categories` | Elenca tutte le categorie definite (es. `video-filebot`, `lidarr-classical`, `radarr`) e i relativi percorsi di salvataggio (`savePath`). |
| **Tier 1 (Core)** | `qbt_create_category` | `POST /api/v2/torrents/createCategory` | Crea una nuova categoria impostando il relativo percorso fisico di destinazione (`savePath`). |
| **Tier 1 (Core)** | `qbt_torrent_files` | `GET /api/v2/torrents/files?hash={hash}` | Elenca i singoli file contenuti in un torrent (nome, dimensione, progresso, priorità). |
| **Tier 1 (Core)** | `qbt_torrent_trackers` | `GET /api/v2/torrents/trackers?hash={hash}` | Ispeziona i tracker associati al torrent, stato di salute (working/not working), peer, seed e messaggi di errore (indispensabile per debug download bloccati). |
| **Tier 2 (Ops)** | `qbt_recheck_torrent` | `POST /api/v2/torrents/recheck` | Forza il ricontrollo dell'integrità dei file scaricati di un torrent. |
| **Tier 2 (Ops)** | `qbt_reannounce_torrent` | `POST /api/v2/torrents/reannounce` | Forza il reannounce sui tracker per riagganciare peer/seed. |
| **Tier 2 (Tags)** | `qbt_tags` (`list`/`add`/`remove`) | `GET/POST /api/v2/torrents/...Tags` | Gestione tag per categorizzazione secondaria e automazioni granulari. |
| **Tier 3 (Speed)** | `qbt_speed_limits` | `GET/POST /api/v2/transfer/speedLimitsMode` | Lettura e attivazione/disattivazione della modalità limiti alternativi ("turtle mode"). |

---

## 🛠️ Procedura Operativa di Implementazione (Post-Approvazione)

1. **FASE 1: Aggiornamento del Codice (`server.py`)**
   - Modifica di `docker/arrstack-mcp/src/server.py` aggiungendo i tool approvati decorati con `@mcp.tool()`.
   - Formattazione output pulita e concisa per AI.
2. **FASE 2: Deploy e Ricompilazione su TrueNAS SCALE**
   - Sincronizzazione di `server.py` su TrueNAS: `/mnt/stripe/truenas-docker/mcp/arrstack-mcp/src/server.py`.
   - Ricompilazione dell'immagine Docker: `sudo docker build -t local/arrstack-mcp:latest .`
   - Riavvio del container: `sudo docker compose up -d arrstack-mcp`.
3. **FASE 3: Validazione & Test E2E**
   - Esecuzione chiamate di test tramite i nuovi tool MCP (es. `prowlarr_list_applications`, `qbt_list_categories`).
   - Verifica assenza di errori nei log del container `mcp-arrstack`.
4. **FASE 4: Documentazione Wiki & Chiusura**
   - Allineamento delle entità [[MCP_Platform]] e [[Servarr]].
   - Rigenerazione contesto wiki (`build_wiki_context.py`).

---

## 💾 Stato di Ripristino (AI Save-State)
- **Fase Attiva**: Fase 0 (Presentazione Piano e Lista Funzionalità Mancanti)
- **Ultima Azione Completata**: Redazione del piano e censimento delle API REST mancanti per Prowlarr e qBittorrent.
- **Prossimo Passo Operativo**: Attendere l'approvazione e la selezione dei tool desiderati da parte dell'utente.
- **Blocchi/Decisioni Pendenti**: Selezione dell'utente sui tool proposti da implementare (es. solo Tier 1, oppure Tier 1 + Tier 2).

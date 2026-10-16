---
title: "Piano: Estensione REST API arrstack-mcp per Prowlarr e qBittorrent"
type: plan
status: completed
certified_for_ai: true
completed_at: 2026-10-16
resolved: true
resolved_at: "2026-10-16"
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

## 🛠️ Procedura Operativa di Implementazione (Completata)

1. **FASE 1: Aggiornamento del Codice (`server.py`)** [COMPLETATA ✅]
   - Modifica di `docker/arrstack-mcp/src/server.py` aggiungendo i tool approvati decorati con `@mcp.tool()`.
   - Compilazione sintattica Python completata con esito positivo (`py_compile`).
2. **FASE 2: Versionamento SemVer `1.1.0` e Sincronizzazione su TrueNAS** [COMPLETATA ✅]
   - Aggiornato `docker/mcp/docker-compose.yaml`, `docker/mcp/build-images.sh` e `.github/workflows/docker-arrstack-mcp.yml` con la versione deterministica `1.1.0`.
   - Sincronizzazione di `server.py` e `docker-compose.yaml` su TrueNAS (`/mnt/stripe/truenas-docker/mcp/`).
3. **FASE 3: Build Docker & Rollout su TrueNAS SCALE** [COMPLETATA ✅]
   - Compilata immagine Docker locale `local/arrstack-mcp:1.1.0` su TrueNAS (`sudo docker build -t local/arrstack-mcp:1.1.0 .`).
   - Riavviato container `mcp-arrstack` con `sudo docker compose up -d arrstack-mcp`.
   - Container attivo e healthy sulla porta `8110`.
4. **FASE 4: Validazione & Test E2E** [COMPLETATA ✅]
   - Eseguite chiamate di test reali su Prowlarr (`prowlarr_list_applications`, `prowlarr_indexer_stats`) con esito 200 OK.
   - Eseguite chiamate di test reali su qBittorrent (`qbt_list_categories`) con esito 200 OK e 10 categorie rilevate.
5. **FASE 5: Documentazione Wiki & Chiusura** [COMPLETATA ✅]
   - Allineamento delle entità [[MCP_Platform]], [[Servarr]], `todo.md` e rigenerazione `wiki_context.md`.

---

## 💾 Stato di Ripristino (AI Save-State)
- **Fase Attiva**: Piano Completato con Successo ✅
- **Ultima Azione Completata**: Rollout di `local/arrstack-mcp:1.1.0` su TrueNAS bare-metal completato, test live eseguiti e verificati al 100% su Prowlarr e qBittorrent, documentazione wiki sincronizzata.
- **Prossimo Passo Operativo**: Nessuno.
- **Blocchi/Decisioni Pendenti**: Nessuno.

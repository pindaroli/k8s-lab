---
title: "Piano: Migrazione Flotta TrueNAS Docker MCP su Standard Streamable HTTP"
type: plan
status: archived
certified_for_ai: false
superseded_by: [[truenas-mcp-fleet-gitops-and-image-tag-sanitization]]
created_at: 2026-10-15
tags:
  - "#plan"
  - "#mcp"
  - "#docker"
  - "#truenas"
  - "#supergateway"
  - "#streamable-http"
---

# Piano: Migrazione Flotta TrueNAS Docker MCP su Standard Streamable HTTP

Questo documento definisce il piano operativo per la transizione dell'intera flotta di server Model Context Protocol (MCP) in esecuzione nello stack Docker di TrueNAS SCALE bare-metal (`10.10.20.50`, porte `8101`–`8111`) dal legacy SSE multi-endpoint (`--ssePath`/`--messagePath`) al nuovo standard unificato **Streamable HTTP** (`--streamableHttpPath /mcp` e configurazione client `serverUrl`).

---

## 🗺️ Mappe Concettuali e Relazioni
- [[MCP_Platform]] (Architettura e registro della flotta MCP centrale su TrueNAS)
- [[mcp-servers-truenas-docker-migration]] (Piano originario di migrazione bare-metal da K8s a TrueNAS Docker)
- [[zero-install-executable-package-pattern]] (Standard architetturale pacchetti zero-install on-demand)
- [[SCHEMA]] (Regole di governance e save-state del Wiki)

---

## 1. Motivazione Tecnica e Causa Radice

In seguito agli aggiornamenti del runtime Antigravity e all'adozione dello standard ufficiale MCP 2025 (Streamable HTTP RFC):
1. **Divergenza di Protocollo**: Il client invia le richieste di handshake JSON-RPC (`initialize`) tramite chiamate **HTTP POST** direttamente all'endpoint `/mcp`.
2. **Server Funzionanti**: `kubernetes-mcp` (porta `8105`) e `arrstack-mcp` (porta `8110`) espongono nativamente Streamable HTTP su `/mcp` e usano la sintassi `"serverUrl"`. Risultano stabili e operativi al 100%.
3. **Server Falliti con 404 Not Found**: I server wrappati con `supergateway` (`truenas-master-mcp`, `opnsense`, `talos`, `ollama`, `nowaikit`, `github-mcp-server`, `ragflow-local`) sono stati configurati con `--ssePath /mcp --messagePath /message`. Supergateway gestisce GET su `/mcp`, ma accetta POST esclusivamente su `/message`: l'invio di `POST /mcp` causa l'errore `sending "initialize": Not Found`.
4. **Server Fallito con 405 Method Not Allowed**: `gemini-deepsearch` è esposto con FastMCP su `/sse`, dove accetta solo GET e rifiuta la richiesta POST con HTTP 405.

### Soluzione Architetturale
Unificare l'intera flotta su **Streamable HTTP**:
- Per i server `stdio`, configurare `supergateway` con il flag unificato `--streamableHttpPath /mcp`.
- Per `gemini-deepsearch`, abilitare il transport Streamable HTTP nativo su porta 8080.
- Per il client locale, aggiornare `~/.gemini/antigravity/mcp_config.json` impostando `"serverUrl": "http://10.10.20.50:810X/mcp"` per tutti i server.

---

## 2. Matrice Servizi e Mappatura Porte

| Server MCP | Porta Host TrueNAS | Runtime / Wrapper | Parametro Network Container | Endpoint Client Unificato (`serverUrl`) |
| :--- | :--- | :--- | :--- | :--- |
| **`truenas-master-mcp`** | `8101` | Rust / Supergateway | `--streamableHttpPath /mcp` | `http://10.10.20.50:8101/mcp` |
| **`opnsense`** | `8102` | Node.js / Supergateway | `--streamableHttpPath /mcp` | `http://10.10.20.50:8102/mcp` |
| **`talos`** | `8103` | Go / Supergateway | `--streamableHttpPath /mcp` | `http://10.10.20.50:8103/mcp` |
| **`gemini-deepsearch`** | `8104` | Python FastMCP | `streamable-http` / Supergateway | `http://10.10.20.50:8104/mcp` |
| **`kubernetes`** | `8105` | Go nativo | Nativo Streamable HTTP | `http://10.10.20.50:8105/mcp` |
| **`ollama`** | `8106` | Node.js / Supergateway | `--streamableHttpPath /mcp` | `http://10.10.20.50:8106/mcp` |
| **`kef`** | `8107` | Python Uvicorn | Nativo Streamable HTTP | `http://10.10.20.50:8107/mcp` |
| **`nowaikit`** | `8108` | Node.js / Supergateway | `--streamableHttpPath /mcp` | `http://10.10.20.50:8108/mcp` |
| **`github-mcp-server`**| `8109` | Go / Supergateway | `--streamableHttpPath /mcp` | `http://10.10.20.50:8109/mcp` |
| **`arrstack-mcp`** | `8110` | Python nativo | `--transport streamable-http` | `http://10.10.20.50:8110/mcp` |
| **`ragflow-local`** | `8111` | Python / Supergateway | `--streamableHttpPath /mcp` | `http://10.10.20.50:8111/mcp` |

---

## 3. Fasi Operative

### Fase 1: Aggiornamento Dichiarativo Immagini Docker (`docker/mcp/`)
- [x] Modifica di `docker/mcp/build-images.sh` per aggiornare l'entrypoint di Supergateway con `--streamableHttpPath /mcp` per:
  - `local/talos-mcp:latest`
  - `local/truenas-master-mcp:latest`
  - `local/github-mcp-server:latest`
  - `local/opnsense-mcp:latest`
  - `local/ollama-mcp:latest`
  - `local/nowaikit-mcp:latest`
- [x] Aggiornamento di `docker/ragflow-mcp/` con `--streamableHttpPath /mcp`.
- [x] Riconfigurazione di `gemini-deepsearch-mcp` in `docker/mcp/docker-compose.yaml` su Streamable HTTP `/mcp`.

### Fase 2: Rebuild Immagini & Sincronizzazione su TrueNAS
- [x] Trasferimento dello script aggiornato su TrueNAS SCALE bare-metal (`10.10.20.50`).
- [x] Esecuzione della build delle nuove immagini OCI AMD64 su TrueNAS.

### Fase 3: Rollout e Restart Stack Docker
- [x] Esecuzione del riavvio atomico dello stack:
  ```bash
  cd /mnt/stripe/truenas-docker/mcp && docker compose up -d --force-recreate
  ```
- [x] Verifica dello stato di salute (`healthy` 12/12) e assenza di riavvii anomali.

### Fase 4: Allineamento Client Antigravity (`mcp_config.json`)
- [x] Aggiornamento delle definizioni in `~/.gemini/antigravity/mcp_config.json`:
  - Sostituzione della sintassi legacy `{"transport": "sse", "url": "..."}` con la sintassi `{"serverUrl": "http://10.10.20.50:810X/mcp"}` per tutta la flotta (`8101`, `8102`, `8103`, `8104`, `8106`, `8107`, `8108`, `8109`, `8111`).

### Fase 5: Validazione Test-Driven End-to-End
- [x] Esecuzione smoke test via curl su ciascun endpoint con metodo POST e payload `{"jsonrpc": "2.0", "method": "initialize", ...}` per verificare codice 200 OK (11/11 PASSED).
- [x] Riavvio/ricaricamento del runtime Antigravity e verifica del caricamento privo di errori di tutti gli 11 server MCP.
- [x] Collaudo funzionale live dei tool via `call_mcp_tool` (`truenas_master_mcp/get_system_info`, `ragflow_list_datasets`, `qbt_transfer_info`, `talos_version`, `kef_status`).

### Fase 6: Consolidamento Documentale & Knowledge Base
- [x] Aggiornamento di [[MCP_Platform]] con la nuova architettura Streamable HTTP.
- [x] Rigenerazione del contesto wiki tramite `scripts/wiki/build_wiki_context.py`.

---

## 💾 Stato di Ripristino (AI Save-State)
- **Fase Attiva**: Piano Completato con Successo (Fasi 1-6 completate).
- **Ultima Azione Completata**: Migrazione dell'intera flotta TrueNAS Docker MCP (11 server) sullo standard unificato Streamable HTTP RFC 2025 (`--outputTransport streamableHttp`, FastMCP nativo), allineamento di `mcp_config.json`, test live dei tool e consolidamento nel Wiki.
- **Prossimo Passo Operativo**: Nessuno (Infrastruttura MCP completamente migrata e convergente).
- **Blocchi/Decisioni Pendenti**: Nessuno.

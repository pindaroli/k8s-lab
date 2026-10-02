---
title: "Piano: Containerizzazione e Migrazione arrstack-mcp su Docker TrueNAS (Porta 8110)"
type: plan
status: active
certified_for_ai: true
created_at: 2026-10-03
tags:
  - "#plan"
  - "#mcp"
  - "#truenas"
  - "#docker"
  - "#servarr"
---

# Piano: Containerizzazione e Migrazione arrstack-mcp su Docker TrueNAS (Porta 8110)

Questo piano definisce la containerizzazione e il deployment permanente di **`arrstack-mcp`** all'interno dello stack Docker Compose su TrueNAS SCALE bare-metal (`10.10.20.50`), allineandolo all'architettura a 9 server descritta in [[MCP_Platform]] e sulla scia del piano [[mcp-servers-truenas-docker-migration]].

---

## 🎯 Obiettivo Architetturale

1. **Decoupling Completo dal Mac**: Trasferire il processo `arrstack-mcp` (finora eseguito in locale su macOS via `uv run`) su container Docker nativo 24/7 su TrueNAS.
2. **Accesso Diretto LAN (Porta 8110)**: Esporre l'endpoint MCP Streamable HTTP su `http://10.10.20.50:8110/mcp`, senza dipendenza da Traefik K8s né da certificati TLS esterni.
3. **Integrazione con la Flotta MCP Esistente**: Aggiungere il servizio `arrstack-mcp` a `/mnt/stripe/truenas-docker/mcp/docker-compose.yaml` completando la suite a 10 server (8101–8110).

---

## 🗺️ Mappa Porte MCP su TrueNAS (10.10.20.50)

| Porta Host | Servizio MCP | Backend / Ruolo |
| :--- | :--- | :--- |
| `8101` | `truenas-master-mcp` | TrueNAS REST/WebSocket API |
| `8102` | `opnsense-mcp` | OPNsense Firewall REST API |
| `8103` | `talos-mcp` | Talos K8s Nodes gRPC API |
| `8104` | `gemini-deepsearch-mcp` | Google Gemini Cloud API |
| `8105` | `kubernetes-mcp` | Talos Kubernetes API Server VIP |
| `8106` | `ollama-mcp` | Ollama LLM su Mac Studio / PVE3 |
| `8107` | `kef-mcp` | Casse KEF LSX II LT REST API |
| `8108` | `nowaikit-mcp` | ServiceNow Cloud REST API |
| `8109` | `github-mcp-server` | GitHub Cloud API |
| **`8110`** | **`arrstack-mcp`** | **Radarr, Lidarr, Prowlarr, qBittorrent** |

---

## 🏗️ Fasi Operative

### FASE 1: Packaging Dockerfile e Asset (Completata)
- [x] Creazione di `docker/arrstack-mcp/Dockerfile` con Python 3.12-slim, utente non-root (UID 1000) e entrypoint FastMCP `sse`.
- [x] Creazione di `docker/arrstack-mcp/requirements.txt` (`mcp>=1.0.0,<2.0.0`, `httpx`, `starlette`, `uvicorn`).
- [x] Copia dei sorgenti `server.py` e `ard.py` in `docker/arrstack-mcp/src/`.
- [x] Creazione workflow GitHub Actions `.github/workflows/docker-arrstack-mcp.yml`.

### FASE 2: Secret Projection SOPS & Estensione `.env` su TrueNAS
- [x] Iniezione sicura delle variabili `ARRSTACK_*` in `/mnt/stripe/truenas-docker/mcp/.env` su TrueNAS (`10.10.20.50`).

### FASE 3: Aggiornamento Stack Docker Compose Locale
- [x] Aggiornamento del servizio `arrstack-mcp` in `docker/mcp/docker-compose.yaml` (porta `8110:8080`, comando FastMCP SSE, healthcheck `/health`, riferimenti `.env`).
- [x] Aggiornamento script di build `docker/mcp/build-images.sh`.

### FASE 4: Sincronizzazione, Build & Deployment su TrueNAS SCALE
- [x] Sincronizzazione di `docker/arrstack-mcp/` verso `/mnt/stripe/truenas-docker/mcp/arrstack-mcp/`.
- [x] Sincronizzazione di `docker/mcp/docker-compose.yaml` verso `/mnt/stripe/truenas-docker/mcp/docker-compose.yaml`.
- [x] Build dell'immagine `local/arrstack-mcp:latest` su TrueNAS con `sudo docker build`.
- [x] Avvio del container con `sudo docker compose up -d arrstack-mcp`.
- [x] Ispezione log e verifica stato healthy del container `mcp-arrstack` (HTTP 200 OK su `/health`).

### FASE 5: Verifica Endpoint e Allineamento Client Antigravity
- [x] Collaudo HTTP SSE dell'endpoint: `curl -i -N -H "Accept: text/event-stream" http://10.10.20.50:8110/sse` (confermato evento session_id).
- [x] Aggiornamento di `~/.gemini/antigravity/mcp_config.json` per puntare `arrstack-mcp` a `"serverUrl": "http://10.10.20.50:8110/sse"`.
- [x] Container attivo e accessibile 24/7 su TrueNAS.

### FASE 6: Consolidamento Documentale & Chiusura
- [x] Aggiornamento di `wiki/entities/MCP_Platform.md` con l'entry `arrstack-mcp` sulla porta 8110.
- [x] Allineamento `todo.md` e rigenerazione `wiki_context.md`.

---

## 💾 Stato di Ripristino (AI Save-State)
- **Fase Attiva**: Piano Completato con Successo (Fasi 1-6 completate).
- **Ultima Azione Completata**: Container `mcp-arrstack` compilato, avviato e verificato healthy su porta 8110 su TrueNAS SCALE bare-metal. Client `mcp_config.json` aggiornato a `"serverUrl": "http://10.10.20.50:8110/sse"`.
- **Prossimo Passo Operativo**: Nessuno (Infrastruttura MCP completata a 10 server remoti).
- **Blocchi/Decisioni Pendenti**: Nessuno.

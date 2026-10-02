---
title: "Piano: Containerizzazione e Migrazione ragflow-mcp su Docker TrueNAS (Porta 8111)"
type: plan
status: active
certified_for_ai: true
created_at: 2026-10-03
tags:
  - "#plan"
  - "#mcp"
  - "#truenas"
  - "#docker"
  - "#ragflow"
---

# Piano: Containerizzazione e Migrazione ragflow-mcp su Docker TrueNAS (Porta 8111)

Questo piano definisce la containerizzazione e il deployment permanente di **`ragflow-mcp`** all'interno dello stack Docker Compose su TrueNAS SCALE bare-metal (`10.10.20.50`), allineandolo all'architettura descritta in [[MCP_Platform]] e sui piani [[mcp-servers-truenas-docker-migration]] e [[arrstack-mcp-truenas-docker-migration]].

---

## 🎯 Obiettivo Architetturale

1. **Decoupling Completo dal Mac**: Trasferire il server MCP `ragflow-claude-mcp` (finora eseguito localmente su macOS via `uv run`) su container Docker nativo 24/7 su TrueNAS.
2. **Accesso Diretto LAN (Porta 8111)**: Esporre l'endpoint MCP SSE su `http://10.10.20.50:8111/mcp` tramite wrapper `supergateway`, senza dipendenza da Traefik né certificati esterni.
3. **Integrazione con la Flotta MCP Esistente**: Aggiungere il servizio `ragflow-mcp` a `/mnt/stripe/truenas-docker/mcp/docker-compose.yaml` completando la suite a 11 server (8101–8111).

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
| `8110` | `arrstack-mcp` | Radarr, Lidarr, Prowlarr, qBittorrent |
| **`8111`** | **`ragflow-mcp`** | **RAGFlow Server (`https://ragflow-internal.pindaroli.org`)** |

---

## 🏗️ Fasi Operative

### FASE 1: Packaging Dockerfile e Asset
- [x] Creazione di `Dockerfile` multi-stage (Python 3.12-slim, Node.js, `supergateway`, `uv`, utente `appuser` UID 1000).
- [x] Push nel fork GitHub `pindaroli/ragflow-claude-desktop-local-mcp`.
- [x] Creazione workflow GitHub Actions `.github/workflows/docker-ragflow-mcp.yml` in `k8s-lab`.

### FASE 2: Secret Projection & Estensione `.env` su TrueNAS
- [x] Iniezione sicura di `RAGFLOW_API_KEY` in `/mnt/stripe/truenas-docker/mcp/.env` su TrueNAS (`10.10.20.50`).

### FASE 3: Aggiornamento Stack Docker Compose
- [x] Aggiunta del servizio `ragflow-mcp` in `docker/mcp/docker-compose.yaml` (porta `8111:8080`, supergateway SSE `/mcp`, healthcheck `/mcp`).
- [x] Aggiornamento script di build `docker/mcp/build-images.sh`.

### FASE 4: Deployment su TrueNAS SCALE
- [ ] Build immagine `local/ragflow-mcp:latest` su TrueNAS.
- [ ] Avvio container `mcp-ragflow` con `docker compose up -d ragflow-mcp`.
- [ ] Verifica status healthy.

### FASE 5: Allineamento Client Antigravity
- [ ] Collaudo endpoint `http://10.10.20.50:8111/mcp`.
- [ ] Aggiornamento `~/.gemini/antigravity/mcp_config.json`.
- [ ] Test esecuzione tool.

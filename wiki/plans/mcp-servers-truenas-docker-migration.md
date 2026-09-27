---
title: "Piano: Migrazione Server MCP su Docker TrueNAS SCALE (Opzione A - LAN HTTP)"
type: plan
status: archived
certified_for_ai: false
resolved: true
resolved_at: "2026-09-27"
created_at: 2026-09-27
tags:
  - "#plan"
  - "#mcp"
  - "#truenas"
  - "#docker"
  - "#migration"
  - "#energy-saving"
---

# Piano: Migrazione Server MCP su Docker TrueNAS SCALE (Opzione A - LAN HTTP)

Questo piano definisce la transizione dell'intera suite di **Model Context Protocol (MCP) server** dal namespace Kubernetes `mcp-system` a uno stack **Docker Compose nativo su TrueNAS SCALE bare-metal (`10.10.20.50`)**, garantendo l'operatività ininterrotta dell'assistente AI (Antigravity) anche quando il cluster Kubernetes e gli hypervisor Proxmox VE vengono spenti per risparmio energetico.

---

## 🗺️ Mappe Concettuali e Relazioni
- [[MCP_Platform]] (Infrastruttura MCP e catalogo strumenti)
- [[TrueNAS]] (TrueNAS SCALE bare-metal `10.10.20.50`)
- [[servarr-truenas-permanent-migration]] (Precedente migrazione carichi multimediali su TrueNAS)
- [[truenas-mcp-drop-legacy-tools]] (Piano rimozione zavorra pre-25 e passaggio a WebSocket JSON-RPC 2.0)
- [[Secret_Registry]] (Gestione credenziali cifrate con SOPS)
- [[mcp-registry-package-pattern]] (Standard di packaging OCI a versione fissa)
- [[mcp-secret-projection-pattern]] (Pattern di iniezione sicura dei segreti)

---

## 1. Decisioni Architetturali (Opzione A & Disabilitazione K8s Conservativa)

1. **Adozione Esclusiva Opzione A (Direct LAN HTTP)**:
   - Ogni server MCP è mappato su una porta host dedicata (`8101`–`8109`) sull'IP fisico di TrueNAS (`10.10.20.50`).
   - Zero dipendenza da reverse proxy (Traefik), certificati TLS o record DNS Unbound.
   - Nessun rischio di collisione con la porta `8080` (utilizzata da qBittorrent).
2. **Disabilitazione Conservativa e Non Distruttiva su Kubernetes**:
   - **Nessuna cancellazione**: Manifest, chart Helm (`helm-charts/mcp-gateway/`) e secret SOPS (`secrets-sops/`) vengono preservati al 100% nel repository Git.
   - **Disattivazione dichiarativa**: In `mcp-gateway/mcp-gateway-values.yaml`, i server vengono impostati su `enabled: false` e il gateway su `replicas: 0`. I carichi K8s vengono spenti liberando risorse ma restano reversibili in qualsiasi momento.
3. **Architettura Uniforme di Transport (Stdio -> SSE /mcp)**:
   - Tutta la flotta adotta un pattern coerente: i binari MCP girano nella loro modalità nativa e collaudata `stdio`, mentre il wrapper di rete standard **`supergateway`** espone l'endpoint `/mcp` su porta HTTP `8080` (mappata su host `8101`–`8109`).
   - Verso il backend TrueNAS, `truenas-master-mcp` comunica **esclusivamente via WebSocket JSON-RPC 2.0 (`wss://10.10.20.50/api/current`)**, come formalizzato nel piano [[truenas-mcp-drop-legacy-tools]].

---

## 2. Architettura & Mappatura Porte LAN

| Server MCP | Runtime | Transport MCP verso Client (Frontend) | Host Port TrueNAS | URL Configurazione Antigravity | Protocollo e Target Backend |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **`truenas-master-mcp`** | Rust (`1.0.0-alpha.1`) | **Stdio -> SSE `/mcp`** (Supergateway) | **`8101`** | `http://10.10.20.50:8101/mcp` | **WebSocket JSON-RPC 2.0** (`wss://10.10.20.50/api/current`) |
| **`opnsense-mcp`** | Node.js (v0.5.3) | **Stdio -> SSE `/mcp`** (Supergateway) | **`8102`** | `http://10.10.20.50:8102/mcp` | OPNsense REST API (`https://192.168.100.1:443`) |
| **`talos-mcp`** | Go (v2.5.1) | **Stdio -> SSE `/mcp`** (Supergateway) | **`8103`** | `http://10.10.20.50:8103/mcp` | Talos gRPC API (`10.10.20.141/55:50000`) |
| **`gemini-deepsearch-mcp`** | Python (FastMCP) | Nativo SSE `/sse` | **`8104`** | `http://10.10.20.50:8104/sse` | Google Gemini Cloud API |
| **`kubernetes-mcp`** | Go (Containers K8s) | Nativo Streamable HTTP `/mcp` | **`8105`** | `http://10.10.20.50:8105/mcp` | K8s API Server VIP (`10.10.20.55:6443`) |
| **`ollama-mcp`** | Node.js (v2.1.0) | **Stdio -> SSE `/mcp`** (Supergateway) | **`8106`** | `http://10.10.20.50:8106/mcp` | Mac Studio Ollama (`10.10.20.100:11434`) |
| **`kef-mcp`** | Python (Uvicorn) | Nativo Streamable HTTP `/mcp` | **`8107`** | `http://10.10.20.50:8107/mcp` | KEF LSX II LT REST API (`10.10.20.210`) |
| **`nowaikit-mcp`** | Node.js (v4.15.1) | **Stdio -> SSE `/mcp`** (Supergateway) | **`8108`** | `http://10.10.20.50:8108/mcp` | ServiceNow Cloud REST API (`dev395227.service-now.com`) |
| **`github-mcp-server`** | Go (Official) | **Stdio -> SSE `/mcp`** (Supergateway) | **`8109`** | `http://10.10.20.50:8109/mcp` | GitHub Cloud REST/GraphQL API (`api.github.com`) |

---

## 3. Fasi Operative

### FASE 1: Preparazione Directory & Secret Projection su TrueNAS
- [x] Creazione directory `/mnt/stripe/truenas-docker/mcp/{talos,kubernetes}` su TrueNAS.
- [x] Generazione sicura del file `/mnt/stripe/truenas-docker/mcp/.env` con estrazione SOPS dei segreti da `secrets-sops/`.
- [x] Copia read-only di `talosconfig` e `kubeconfig` nei percorsi montati (`chmod 644`).

### FASE 2: Build Immagini OCI AMD64
- [x] Integrazione di `supergateway` nei Dockerfile stdio (`truenas`, `opnsense`, `talos`, `nowaikit`, `ollama`, `github`).
- [x] Abilitazione flag SSE per `gemini-deepsearch-mcp` e Uvicorn per `kef-mcp`.
- [x] Build e caricamento delle immagini nel runtime Docker di TrueNAS.

### FASE 3: Deployment Docker Compose su TrueNAS
- [x] Sincronizzazione di `docker-compose.yaml` in `/mnt/stripe/truenas-docker/mcp/`.
- [x] Avvio dei container con `docker compose up -d`.
- [x] Verifica status healthy dei container con `docker compose ps`.

### FASE 4: Validazione Porte & Aggiornamento `mcp_config.json`
- [x] Collaudo delle singole porte `8101`–`8109` tramite curl HTTP.
- [x] Aggiornamento delle 9 voci in `~/.gemini/antigravity/mcp_config.json`.
- [x] Test effettivo di esecuzione tool da Antigravity.

### FASE 5: Disabilitazione Non Distruttiva K8s & Chiusura
- [x] Aggiornamento di `mcp-gateway-values.yaml` (`replicas: 0`, `enabled: false`).
- [x] Consolidamento documentazione in `wiki/entities/MCP_Platform.md`.

---

## 💾 Stato di Ripristino (AI Save-State)
- **Fase Attiva**: Piano Completato con Successo (Fasi 1-5 completate).
- **Ultima Azione Completata**: Migrazione a TrueNAS Docker completata con successo: 9 server MCP attivi 24/7 su host ports 8101-8109, collaudo HTTP/SSE superato al 100%, client `mcp_config.json` allineato e K8s disabilitato dichiarativamente.
- **Prossimo Passo Operativo**: Nessuno (Infrastruttura MCP pronta e operativa).
- **Blocchi/Decisioni Pendenti**: Nessuno.

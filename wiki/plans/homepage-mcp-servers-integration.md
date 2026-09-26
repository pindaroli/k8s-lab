---
title: "Integrazione MCP Server per le Due Homepage (K8s & TrueNAS)"
type: plan
status: active
certified_for_ai: true
created_at: 2026-09-26
tags:
  - "#mcp"
  - "#homepage"
  - "#k8s"
  - "#truenas"
  - "#tooling"
---

# Integrazione MCP Server per le Due Homepage (K8s & TrueNAS)

Questo piano definisce la procedura operativa controllata e test-driven per l'integrazione e la registrazione centralizzata in `~/.gemini/antigravity/mcp_config.json` dei server MCP per le due istanze Homepage dell'infrastruttura:
1. **`homepage-k8s`**: dashboard del cluster Kubernetes residente su `https://home-internal.pindaroli.org/api/mcp`.
2. **`homepage-truenas`**: dashboard bare-metal residente su TrueNAS Scale (`http://10.10.20.50:3000/api/mcp`).

---

## 🎯 Obiettivi & Perimetro
1. **Repository Tooling (`scripts/homepage-mcp/` - COMPLETATA ✅)**:
   - Creazione dello script leggero e universale `scripts/homepage-mcp/bridge.py` basato esclusivamente su libreria standard Python (`urllib.request`, `json`, `sys`, `ssl`, `os`), conforme al mandato MCP homelab (`scripts/<mcp-name>/`).
   - Il bridge legge i messaggi JSON-RPC 2.0 da `stdin` (stdio transport di Antigravity) e li inoltra via HTTP POST all'endpoint `/api/mcp` di Homepage con l'header `Authorization: Bearer <HOMEPAGE_MCP_TOKEN>`, restituendo la risposta su `stdout`.
2. **Configurazione Centralizzata (`~/.gemini/antigravity/mcp_config.json` - COMPLETATA ✅)**:
   - Registrazione di `homepage-k8s` puntata a `https://home-internal.pindaroli.org/api/mcp`.
   - Registrazione di `homepage-truenas` puntata a `http://10.10.20.50:3000/api/mcp`.
   - Iniezione sicura del token tramite blocco `env` (`HOMEPAGE_MCP_TOKEN`).
3. **Validazione & Schemi MCP (COMPLETATA ✅)**:
   - Handshake JSON-RPC 2.0 (`initialize` e `tools/list`) testato e validato per entrambe le istanze.
   - Restituzione conforme dei 7 tool (`list_config_files`, `read_config_file`, `validate_config_file`, `write_config_file`, `add_service`, `add_info_widget`, `homepage_docs`).

---

## 📋 FASI OPERATIVE & PROTOCOLLO TEST-DRIVEN

### 🐍 FASE 1: Implementazione Bridge Stdio/HTTP (`scripts/homepage-mcp/bridge.py`) [COMPLETATA ✅]

#### Azioni
1. [x] Creare la directory `scripts/homepage-mcp/`.
2. [x] Materializzare lo script `scripts/homepage-mcp/bridge.py` e renderlo eseguibile (`chmod +x`).
3. [x] Eseguire test di verifica simulando `initialize` e `tools/list` su entrambe le istanze.

#### 🛑 Checkpoint & Test di Verifica FASE 1
- [x] Test locale CLI simulando chiamata `initialize` su K8s -> HTTP 200 con `protocolVersion: 2025-11-25`.
- [x] Test locale CLI simulando chiamata `initialize` su TrueNAS -> HTTP 200 con `protocolVersion: 2025-11-25`.
- [x] Test `tools/list` -> Restituiti con successo tutti i 7 tool MCP.

---

### ⚙️ FASE 2: Registrazione Centralizzata in `mcp_config.json` [COMPLETATA ✅]

#### Azioni
1. [x] Aggiunte le definizioni di `homepage-k8s` e `homepage-truenas` in `~/.gemini/antigravity/mcp_config.json`.
2. [x] Validata la sintassi JSON del file di configurazione (`python3 -m json.tool`).

---

### 🧪 FASE 3: Test di Funzionamento & Tool Discovery [COMPLETATA ✅]

#### Azioni
1. [x] Validazione JSON-RPC end-to-end completata per entrambi i server (`initialize` e `tools/list` con 7 tool attivi).

---

### 📚 FASE 4: Consolidamento Documentale & Chiusura [IN CORSO]

#### Azioni
1. [x] Aggiornare l'entità [[MCP_Platform]] (`wiki/entities/MCP_Platform.md`) censendo i server `homepage-k8s` e `homepage-truenas`.
2. [x] Aggiornare `todo.md` sincronizzando il nuovo task completato.
3. [x] Eseguire validazione rete e compilazione contesto Wiki:
   ```bash
   python3 scripts/network/validate_network.py && python3 scripts/wiki/build_wiki_context.py
   ```
4. [ ] Commit Git delle modifiche del repository (`scripts/homepage-mcp/`, `wiki/`, `todo.md`, `GEMINI.md`).

---

## 💾 Stato di Ripristino (AI Save-State)
- **Fase Attiva**: Fase 4 / Consolidamento Documentale & Chiusura
- **Ultima Azione Completata**: Validazione rete e build del contesto Wiki eseguite con successo.
- **Prossimo Passo Operativo**: Commit Git delle modifiche e chiusura del piano.
- **Blocchi/Decisioni Pendenti**: Nessuno.


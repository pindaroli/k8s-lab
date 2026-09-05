---
title: "Piano: Integrazione Suite Server MCP Standard"
type: plan
status: active
certified_for_ai: true
created_at: 2026-09-05
tags:
  - "#plan"
  - "#mcp"
  - "#infrastructure"
  - "#security"
  - "#antigravity"
---

# Piano: Integrazione Suite Server MCP Standard

**Target**: Antigravity Client & Piattaforma MCP GEMINI · **Data**: 2026-09-05  
**Autore**: Antigravity AI Engineering

> [!IMPORTANT]
> Questo piano definisce l'integrazione, la configurazione e il collaudo della suite di 8 server standard Model Context Protocol (MCP) per estendere le capacità operative dell'agente locale e delle automazioni homelab, in conformità con la [[MCP_Platform]] e il pattern [[mcp-secret-projection-pattern]].

---

## 1. Tabella di Catalogazione Server MCP

| Categoria | Pacchetto / Repo | Runtime / Gestore | Note & Requisiti |
| :--- | :--- | :--- | :--- |
| **File** | `@modelcontextprotocol/server-filesystem` | Node.js (>= 18) / `npx` | Richiede la specifica esplicita dei percorsi assoluti autorizzati (`/Users/olindo/prj/k8s-lab`, `/Users/olindo/prj/pindaroli-arr-helm`). |
| **Git** | `mcp-server-git` | Python (>= 3.10) / `uvx` | Richiede il binario `git` nel PATH di sistema e repository paths locali. |
| **Web** | `@modelcontextprotocol/server-fetch` | Node.js (>= 18) / `npx` | Scraping HTTP statico con conversione HTML in Markdown. Nessuna API key richiesta. |
| **Web Dinamico** | `@modelcontextprotocol/server-puppeteer` | Node.js (>= 18) / `npx` | Browser automation headless con Chromium per interazione JS e screenshot. |
| **Search** | `@modelcontextprotocol/server-brave-search` | Node.js (>= 18) / `npx` | Ricerca web tramite Brave Search API (richiede token cifrato in SOPS). |
| **Database** | `@modelcontextprotocol/server-sqlite` | Node.js (>= 18) / `npx` | Introspezione e query SQL su database locali (es. SQLite n8n, Beets DB). |
| **Database** | `@modelcontextprotocol/server-postgres` | Node.js (>= 18) / `npx` | Connessione via connection string URI verso `postgres-main` (cluster CNPG). |
| **Cloud/VCS** | `@modelcontextprotocol/server-github` | Node.js (>= 18) / `npx` | Gestione repository GitHub, issue e PR (allineato con il server Kubernetes `github-mcp-internal.pindaroli.org`). |

---

## 2. Decisioni Architetturali & Governance

Ai sensi delle policy di sicurezza e delle regole auree homelab:
1. **Configurazione Centralizzata**: In conformità al mandato MCP, tutte le istanze locali sono censite centralmente in `~/.gemini/antigravity/mcp_config.json`.
2. **Gestione dei Segreti**: Nessun segreto in chiaro nel file di configurazione. Le chiavi (Brave API Key, GitHub PAT, credenziali DB PostgreSQL) devono essere archiviate cifrate con SOPS in `secrets-sops/`.
3. **Integrazione con MCP Kubernetes**: Per i componenti già migrati o candidati alla migrazione in cluster (es. GitHub MCP e PostgreSQL), si valuterà l'esposizione sia in locale sia remota via Kuadrant MCP Gateway / ToolHive Operator in `mcp-system`.

---

## 3. Fasi Operative

### Fase 1: MCP Server Filesystem
- Configurazione blocco `filesystem` in `mcp_config.json` con argomenti contenenti le root autorizzate.
- Test-Driven: verifica del listing directory e lettura file tramite tool MCP.

### Fase 2: MCP Server Git
- Configurazione blocco `git` via `uvx mcp-server-git` in `mcp_config.json`.
- Test-Driven: verifica di `git_status`, `git_diff` e `git_log`.

### Fase 3: MCP Server Fetch
- Configurazione blocco `fetch` in `mcp_config.json`.
- Test-Driven: test recupero URL pubblico e sanitizzazione Markdown.

### Fase 4: MCP Server Puppeteer
- Configurazione blocco `puppeteer` in `mcp_config.json`.
- Validazione download Chromium ed esecuzione test navigazione pagina complessa (SPA).

### Fase 5: MCP Server Brave Search
- Acquisizione API Key Brave, cifratura SOPS in `secrets-sops/brave-search-mcp.enc.yaml`.
- Configurazione variabile d'ambiente `BRAVE_API_KEY` e validazione ricerca web.

### Fase 6: MCP Server SQLite
- Identificazione file DB target nel lab (`.sqlite` / `.db`).
- Configurazione in `mcp_config.json` e test query SELECT con verifica schema.

### Fase 7: MCP Server PostgreSQL
- Configurazione stringa di connessione verso `postgres-main` (`postgres-main-rw.cnpg-system.svc.cluster.local` o IP L2 10.10.20.56).
- Creazione credenziali dedicate a minor privilegio e cifratura in SOPS.
- Test connettività e query introspection.

### Fase 8: MCP Server GitHub
- Verifica Personal Access Token GitHub (`GITHUB_PERSONAL_ACCESS_TOKEN`) con scope necessari (`repo`, `read:org`).
- Riconciliazione tra istanza locale Node.js e servizio ToolHive Kubernetes `github-mcp-internal.pindaroli.org`.
- Test di lettura issue e pull request.

---

## 💾 Stato di Ripristino (AI Save-State)
- **Fase Attiva**: Fase 1 / Configurazione Server MCP Filesystem
- **Ultima Azione Completata**: Formalizzazione del piano e inserimento task in `todo.md`
- **Prossimo Passo Operativo**: Configurazione iniziale di `@modelcontextprotocol/server-filesystem` in `mcp_config.json`
- **Blocchi/Decisioni Pendenti**: Reperimento chiavi API esterne (Brave Search) e definizione scope GitHub PAT

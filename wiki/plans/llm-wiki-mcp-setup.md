---
title: "Piano: Setup Server MCP llm-wiki"
type: plan
status: active
certified_for_ai: true
created_at: 2026-07-07
completed_at: null
tags:
  - "#plan"
  - "#mcp"
  - "#llm-wiki"
---

# Piano di Setup e Configurazione Dichiarativa del Server MCP llm-wiki

Questo piano definisce i passaggi operativi per clonare, compilare e registrare il server MCP `llm-wiki` nel file di configurazione globale `mcp_config.json` di Antigravity.

## Fasi Operative

### Fase 1: Clonazione e Compilazione
1. Creare la directory `/Users/olindo/prj` se non esiste.
2. Clonare il repository:
   ```bash
   git clone https://github.com/geronimo-iia/llm-wiki.git
   ```
3. Accedere a `/Users/olindo/prj/llm-wiki` ed eseguire la build di rilascio tramite Cargo:
   ```bash
   cargo build --release
   ```

### Fase 2: Configurazione Dichiarativa
1. Generare/Aggiornare il file `/Users/olindo/.gemini/antigravity/mcp_config.json` inserendo la definizione del server:
   ```json
   {
     "mcpServers": {
       "llm-wiki": {
         "command": "/Users/olindo/prj/llm-wiki/target/release/llm-wiki",
         "args": [],
         "env": {
           "WIKI_PATH": "/Users/olindo/prj/llm-wiki-data"
         }
       }
     }
   }
   ```

### Fase 3: Validazione
1. Verificare che la build sia andata a buon fine e che il file JSON sia valido.

---

## 💾 Stato di Ripristino (AI Save-State)
- **Fase Attiva**: Fase 2 (Configurazione Dichiarativa)
- **Ultima Azione Completata**: Compilazione di llm-wiki v0.4.1 completata con successo.
- **Prossimo Passo Operativo**: Configurare il server mcp in mcp_config.json.
- **Blocchi/Decisioni Pendenti**: Nessuno.

---
title: "Piano: Installazione TrueNAS Master MCP"
type: plan
status: archived
certified_for_ai: false
created_at: 2026-06-28
completed_at: 2026-06-28
tags:
  - "#plan"
  - "#truenas"
  - "#mcp"
---

# Piano di Integrazione Automatizzata di TrueNAS Master MCP su Google Antigravity

Questo piano definisce i passaggi operativi per installare e configurare il plugin `truenas-master-mcp` per il monitoraggio e la gestione di [[TrueNAS]] SCALE (`10.10.10.50`) dall'istanza desktop di Google Antigravity.

## Stato dell'Infrastruttura e Requisiti
- **Destinazione**: macOS 14+ Apple Silicon (`arm64`).
- **Endpoint TrueNAS**: `10.10.10.50` (VLAN 10, vedi [[Network_Registry]]).
- **Autenticazione**: Token API ad alta sicurezza generato dalla WebUI di TrueNAS in *System Settings -> API Keys*.
- **Toolchain Rust**: Versione 1.85+ (compilazione nativa arm64).

---

## Fasi Operative

### Fase 1: Installazione Prerequisiti (Rust toolchain)
1. Installare la toolchain Rust tramite Homebrew:
   ```bash
   brew install rust
   ```
2. Verificare l'installazione:
   ```bash
   cargo --version
   ```

### Fase 2: Compilazione del server MCP
1. Scaricare e compilare il binario `truenas-master-mcp` tramite Cargo:
   ```bash
   cargo install truenas-master-mcp
   ```
2. Verificare l'avvenuta compilazione e la presenza del binario eseguibile in `~/.cargo/bin/`:
   ```bash
   ~/.cargo/bin/truenas-master-mcp --help
   ```

### Fase 3: Patch di Efficienza Energetica (Electron CPU spikes)
1. Modificare il file `main.js` dell'applicazione desktop Antigravity per disattivare l'elaborazione software delle ombre (mitigazione del surriscaldamento CPU in Dark Mode):
   ```bash
   sudo sed -i '' 's/experimentalDarkMode:!0}/experimentalDarkMode:!0,hasShadow:false}/g' /Applications/Antigravity.app/Contents/Resources/app/out/main.js
   ```

### Fase 4: Configurazione Globale MCP in Antigravity
1. Creare la cartella globale per i plugin di Antigravity:
   ```bash
   mkdir -p ~/.gemini/config/plugins/truenas-master
   ```
2. Creare il manifest del plugin in `~/.gemini/config/plugins/truenas-master/plugin.json`:
   ```json
   {
     "name": "truenas-master",
     "version": "1.0.0",
     "description": "Estensione globale per il controllo centralizzato di server TrueNAS via MCP",
     "entrypoint": "mcp_config.json"
   }
   ```
3. Aggiungere la definition del server a `~/.gemini/config/mcp_config.json`:
   ```json
   "truenas-master-mcp": {
     "command": "/Users/olindo/.cargo/bin/truenas-master-mcp",
     "args": [],
     "env": {
       "TRUENAS_SERVER_URL": "https://10.10.10.50",
       "TRUENAS_API_KEY": "<INSERIRE_API_KEY_DI_TRUENAS>",
       "TRUENAS_VERIFY_SSL": "false",
       "TRUENAS_TIMEOUT": "30",
       "TRUENAS_VERSION": "scale"
     }
   }
   ```

### Fase 5: Avvio e Validazione Funzionale (Test-Driven)
1. Riavviare l'applicazione Google Antigravity.
2. Eseguire un comando di test per verificare che l'agente riesca ad interfacciarsi con TrueNAS (es. elencare i pool o controllare lo stato dello storage).

---

## 💾 Stato di Ripristino (AI Save-State)
- **Fase Attiva**: Fase Preliminare (Draft/Planning)
- **Ultima Azione Completata**: Creazione del piano wiki.
- **Prossimo Passo Operativo**: Ottenere il via libera dell'utente e la chiave API per procedere con l'installazione.
- **Blocchi/Decisioni Pendenti**: In attesa di chiarire le risposte alle domande aperte (installazione Rust e URI TrueNAS).

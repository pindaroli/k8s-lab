---
title: "Piano: Ripristino Inizializzazione Server MCP"
type: plan
status: archived
certified_for_ai: false
created_at: 2026-06-28
completed_at: 2026-06-28
tags:
  - "#plan"
  - "#mcp"
  - "#node"
  - "#truenas"
---

# Piano di Ripristino e Inizializzazione dei Server MCP

Questo piano definisce i passaggi per risolvere due anomalie bloccanti riscontrate nell'avvio dei server MCP del Lab:
1. **Errore di Dynamic Linking in Node.js**: Il binario di Node.js (`25.8.2`) è rotto a causa della rimozione di `libllhttp.9.3.dylib` (aggiornata da Homebrew a `9.4.2`). Questo blocca tutti i server MCP scritti in Node (GitHub, Kubernetes, Notebooks, ecc.).
2. **Errore di Protocollo in TrueNAS MCP**: Il client IDE riscontra `unsupported protocol version: ""` all'inizializzazione perché la risposta del server `truenas-master-mcp` non restituisce il campo `protocolVersion` (richiesto dallo spec MCP).

---

## 🗺️ Mappe Concettuali e Relazioni
- [[Talos_Cluster]] (Kubernetes MCP)
- [[TrueNAS]] (TrueNAS Master MCP)
- [[Network_Registry]] (Endpoint di rete)

---

## Fasi Operative

### Fase 1: Ripristino Node.js e Server MCP Node-based
1. Aggiornare o reinstallare Node.js tramite Homebrew per compilarlo/collegarlo contro la nuova versione di `llhttp`:
   ```bash
   brew upgrade node
   ```
2. Verificare che il comando `node -v` e `npm -v` funzionino regolarmente senza errori di dynamic linking.
3. Testare l'avvio di uno dei server MCP Node-based (es. `github-mcp-server`) per confermare il corretto funzionamento.

### Fase 2: Fix del Protocollo su TrueNAS MCP
1. Modificare [main.rs](file:///Users/olindo/prj/truenas-master-mcp/src/main.rs#L2162-L2178) per aggiungere la chiave `"protocolVersion": "2024-11-05"` nella risposta del metodo `initialize`.
2. Compilare ed eseguire i test su `truenas-master-mcp` con `cargo test`.
3. Reinstallare il binario tramite `cargo install --path .`.
4. Effettuare un test di handshake per verificare che `protocolVersion` sia presente nella risposta di inizializzazione.

---

## Verification Plan

### Test Automatizzati
- `cargo test` per verificare il compilato Rust di TrueNAS MCP.
- `node -v` per verificare l'integrità del runtime JavaScript.

### Test Manuali
- Handshake di inizializzazione di `truenas-master-mcp` via stdio:
  ```bash
  echo '{"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {"capabilities": {}, "protocolVersion": "2024-11-05", "clientInfo": {"name": "test", "version": "1.0"}}}' | ~/.cargo/bin/truenas-master-mcp
  ```
  Verificare la presenza di `"protocolVersion": "2024-11-05"` nel JSON di output.

---

## 💾 Stato di Ripristino (AI Save-State)
- **Fase Attiva**: Completato (Archiviato)
- **Ultima Azione Completata**: Ripristinato Node.js via Homebrew e integrato il fix `protocolVersion` nel server `truenas-master-mcp`. Handshake di inizializzazione validato con successo.
- **Prossimo Passo Operativo**: Nessuno, tutti i passaggi sono stati completati con successo.
- **Blocchi/Decisioni Pendenti**: Nessuno.

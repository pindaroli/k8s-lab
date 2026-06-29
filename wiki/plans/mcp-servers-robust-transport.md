---
title: "Piano: Consolidamento Trasporto Stdio MCP"
type: plan
status: draft
certified_for_ai: false
created_at: 2026-06-28
tags:
  - "#plan"
  - "#mcp"
  - "#rust"
---

# Piano di Consolidamento e Robustezza del Trasporto Stdio MCP

Questo piano definisce i passaggi per rendere il trasporto `stdio` del server `truenas-master-mcp` conforme alle specifiche JSON-RPC e MCP, prevenendo arresti anomali.

## Analisi del Problema
Il server crasha restituendo `EOF` al client per due motivi:
1. **Mancata gestione delle notifiche**: Il client invia la notifica `notifications/initialized` che non ha un campo `id`. Il server, non trovando la notifica tra i metodi validi, restituisce un errore generico e crasha.
2. **Crash su errori di protocollo**: Qualsiasi metodo non riconosciuto o errore di parsing ritorna un `anyhow::Result::Err` propagato fino a `main()`, causando la terminazione del processo.

---

## Fasi Operative

### Fase 1: Aggiornamento del Protocollo e Gestione Notifiche
1. Riscrivere la funzione `run_stdio` in `src/main.rs` per:
   - Controllare se il messaggio in ingresso è una notifica (privo di campo `id`).
   - Gestire o ignorare silenziosamente le notifiche (es. `notifications/initialized`) senza inviare risposte (come richiesto dallo standard JSON-RPC).
2. Riscrivere la funzione `handle_request` in `src/main.rs` per:
   - Ritornare sempre una stringa contenente un pacchetto di risposta JSON-RPC valido (successo o errore).
   - In caso di metodi sconosciuti, ritornare un errore standard JSON-RPC `Method not found (-32601)` invece di mandare in crash l'applicazione.
3. Adeguare i trasporti `run_http` e `run_sse` alla nuova firma di `handle_request`.

### Fase 2: Compilazione e Test
1. Verificare la compilazione ed eseguire `cargo test`.
2. Reinstallare il binario tramite `cargo install --path .`.
3. Validare la stabilità inviando in sequenza la richiesta `initialize`, la notifica `notifications/initialized` e la richiesta `tools/list`.

---

## Verification Plan

### Test Manuali
- Inviare in sequenza sulla console di test:
  ```bash
  (
    echo '{"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {"capabilities": {}, "protocolVersion": "2024-11-05", "clientInfo": {"name": "test", "version": "1.0"}}}'
    sleep 0.5
    echo '{"jsonrpc": "2.0", "method": "notifications/initialized", "params": {}}'
    sleep 0.5
    echo '{"jsonrpc": "2.0", "id": 2, "method": "tools/list"}'
  ) | ~/.cargo/bin/truenas-master-mcp
  ```
  Verificare che il server risponda a `initialize` e `tools/list`, ignori silenziosamente `notifications/initialized` e rimanga attivo senza crashare.

---

## 💾 Stato di Ripristino (AI Save-State)
- **Fase Attiva**: Fase Preliminare (Draft/Planning)
- **Ultima Azione Completata**: Analisi della causa radice e scrittura del piano wiki.
- **Prossimo Passo Operativo**: Ottenere l'approvazione del piano per procedere alle modifiche.
- **Blocchi/Decisioni Pendenti**: In attesa di approvazione.

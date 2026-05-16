---
title: "DNSBL Automation Payload Mismatch & Reload Failure"
date: "2026-05-16"
status: "Resolved"
severity: "Medium"
tags:
  - "#dns"
  - "#opnsense"
  - "#automation"
  - "#ansible"
entities:
  - "[[OPNsense]]"
---

# Incident Report: DNSBL Automation Payload Mismatch

## Descrizione
L'automazione per il blocco dei domini pubblicitari (DNSBL) tramite lo script Python `opnsense_dnsbl_config.py` ha fallito silenziosamente l'applicazione delle nuove wildcard definite in `rete.json`. Nonostante lo script riportasse `[SUCCESS]`, i domini continuavano a risolvere verso gli IP reali, esponendo i client (in particolare su `subito.it`) a banner pubblicitari non filtrati.

## Diagnosi
L'indagine tecnica ha rivelato un problema a due livelli:
1.  **Payload API Invalido (Data Format)**: Lo script Python inviava le wildcard nel formato "Object" (es. `{"dominio": {"value": "dominio", "selected": 1}}`), replicando la struttura restituita dal comando `GET`. Tuttavia, l'endpoint `SET` di OPNsense per i campi Multi-Select si aspetta una **stringa separata da virgole**. L'API rispondeva con un errore di validazione (`"Array" is invalid`), che lo script non intercettava correttamente.
2.  **Incomplete Service Reload**: Il comando di `reconfigure` inviato via API non era sufficiente per forzare Unbound a rigenerare i file di zona fisici (`dnsbl.conf`) partendo dalla configurazione aggiornata nel database. Questo causava la persistenza della vecchia configurazione in memoria.

## Azioni Correttive
1.  **Refactoring Script Python**: Modificato `ansible/playbooks/scripts/opnsense_dnsbl_config.py` per:
    -   Convertire la lista dei domini in una stringa piatta separata da virgole prima dell'invio.
    -   Sostituire la chiamata finale di `reconfigure` con un **`service/restart`** completo di Unbound.
2.  **SSoT Update**: Aggiunti i domini `adnxs.com`, `rubiconproject.com`, `taboola.com`, `criteo.com` e `outbrain.com` al file `rete.json`.
3.  **Manual Verification**: Eseguito test di risoluzione DNS post-restart, confermando il blocco (`0.0.0.0`) per tutti i domini target.

## Verifica Finale
```bash
dig @10.10.20.254 adnxs.com +short
# Risultato: 0.0.0.0
```

## Lezioni Apprese
*   **API Divergence**: Non assumere mai che il formato dati restituito da un `GET` sia quello accettato da un `SET` per la stessa entità in OPNsense.
*   **Deep Service Reload**: Per modifiche strutturali alle zone DNS (come le wildcard), il `restart` del servizio è l'unico metodo garantito per forzare la rigenerazione dei file di configurazione da parte di OPNsense.
*   **Error Handling**: Lo script di automazione deve validare il campo `result` nel JSON di risposta dell'API, non solo il codice di stato HTTP 200.

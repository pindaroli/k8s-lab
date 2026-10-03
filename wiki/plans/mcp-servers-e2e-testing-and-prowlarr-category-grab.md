---
title: "Piano: Integration Test Suite per MCP Servers e Gestione Categoria Prowlarr Grab"
type: plan
status: completed
certified_for_ai: true
created_at: 2026-10-03
completed_at: 2026-10-03
tags:
  - "#mcp"
  - "#testing"
  - "#arrstack"
  - "#prowlarr"
  - "#ragflow"
  - "#gemini-deepsearch"
  - "#pytest"
---

# Piano: Integration Test Suite per MCP Servers e Gestione Categoria Prowlarr Grab

## Sintesi dell'Intervento e Architettura

Il presente piano documenta l'estensione del protocollo MCP per la gestione delle categorie di download in `prowlarr_grab`, l'analisi della causa radice dell'errore FileBot AMC sui file audio musicali e la creazione delle suite di test unitarie ed End-to-End (E2E) per tutti i server MCP custom Python dell'infrastruttura.

---

## 1. Risoluzione della Categoria in `prowlarr_grab`

### Problema
Quando un rilascio veniva inviato a qBittorrent tramite il tool MCP `prowlarr_grab`, Prowlarr non assegnava alcuna categoria. Di conseguenza, qBittorrent eseguiva l'hook post-download di default (`video-filebot`), avviando FileBot AMC su file audio `.flac` con conseguente errore `0 elaborati, 1 errori`.

### Soluzione Applicata
- Modificata la funzione `prowlarr_grab(index: int, category: str = "") -> str` in `docker/arrstack-mcp/server.py`, `src/server.py` e `scripts/arrstack-mcp/server.py`.
- Passato il parametro `category` alle funzioni `_qbt_add_url` e `_qbt_add_file`, inoltrandolo nel payload form `category` invocato nell'endpoint HTTP `POST /torrents/add` di qBittorrent.
- Aggiornato lo schema JSON locale in `.gemini/antigravity-cli/mcp/arrstack-mcp/prowlarr_grab.json`.

---

## 2. Test Suite ed Isolamento Immagini Docker

Per garantire che le immagini Docker di produzione rimanessero snelle e prive di codice di test:
1. La suite di test è stata posizionata nella cartella `tests/` alla radice di ciascun server MCP (all'esterno del context `src/` copiato da `Dockerfile`).
2. Configurato il file `.dockerignore` in ciascun server MCP per escludere `tests/`, `.pytest_cache/` e `__pycache__/`.

### Risultati delle Suite di Test Implementate

| Server MCP | Percorso Test Suite | Esito Test |
| :--- | :--- | :--- |
| **`arrstack-mcp`** | [`docker/arrstack-mcp/tests/`](file:///Users/olindo/prj/k8s-lab/docker/arrstack-mcp/tests/) | **10/10 PASSED** (prowlarr_search, prowlarr_grab, category forwarding, qbittorrent, radarr, lidarr) |
| **`gemini-deepsearch-mcp`** | [`docker/gemini-deepsearch-mcp/tests/`](file:///Users/olindo/prj/k8s-lab/docker/gemini-deepsearch-mcp/tests/) | **2/2 PASSED** (agente di ricerca in modalità low e high effort) |
| **`ragflow-mcp`** | [`docker/ragflow-mcp/tests/`](file:///Users/olindo/prj/k8s-lab/docker/ragflow-mcp/tests/) | **6/6 PASSED** (redact data sensibili, validate dataset ID, list_datasets, retrieval_query) |

**Totale Generale: 18/18 PASSED (100% Success Rate)**

---

## Stato del Piano
- [x] Diagnosi ed esecuzione dell'innesco di normalizzazione in `lidarr-classical` per *Le nozze di Figaro*.
- [x] Estensione del parametro `category` in `prowlarr_grab` per `arrstack-mcp`.
- [x] Creazione delle suite di test `pytest` isolati e con mock HTTP per tutti i server MCP Python.
- [x] Verifica dell'esclusione della cartella `tests/` dalle build Docker via `.dockerignore`.
- [x] Esecuzione e superamento del 100% dei test (18/18 passed).
- [x] Commit & push su repository Git (`main`).

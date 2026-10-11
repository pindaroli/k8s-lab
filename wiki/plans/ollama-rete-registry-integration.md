---
title: "Piano: Registrazione Canonica dei Servizi Ollama in rete.json e Discovery Dinamica nei Benchmark"
type: plan
status: active
certified_for_ai: true
created_at: 2026-10-11
tags:
  - "#rete"
  - "#ollama"
  - "#registry"
  - "#guidellm"
  - "#benchmarking"
  - "#automation"
---

# Piano: Registrazione Canonica dei Servizi Ollama in rete.json e Discovery Dinamica nei Benchmark

Il presente piano operativo definisce l'architettura per eleggere formalmente **`rete.json`** a Source of Truth dei servizi di inferenza **Ollama** distribuiti nell'homelab e adattare gli script di benchmark ([[guidellm-benchmark-script]]) per interrogare dinamicamente il registro di rete senza parametri o mapping hardcoded.

---

## 🗺️ Mappe Concettuali e Relazioni
- [[SCHEMA]] (Regole di governance e conformità del Wiki)
- [[Network_Registry]] (Inventario di rete e contratti `rete.json`)
- [[guidellm-benchmark-script]] (Launcher interattivo e batch per benchmark GuideLLM)
- [[guidellm-report-naming-pattern]] (Convenzione di denominazione dei report generati)
- [[pve3-lxc-ollama-nfs-stripe-storage]] (Hosting Ollama su CT 300 PVE3 con storage NFS TrueNAS)

---

## 1. Analisi dello Stato Attuale e Motivazione

1. **Disallineamento Architetturale**:
   - Attualmente l'istanza `lxc-ollama` è censita in `rete.json` come container LXC (CT 300, `10.10.20.33`), ma la porta del servizio (`11434`), il protocollo (`HTTP`), la base API (`/v1`) e la dotazione di memoria (`38gb`) sono descritti solo in forma testuale nel campo `notes`.
   - Sull'host `mac studio` (`10.10.20.100`), è attiva un'ulteriore istanza Ollama accelerata Metal con oltre 7 modelli (tra cui `qwen2.5:72b` e `deepseek-r1:32b`), ma non è formalizzata tra i `services` del nodo.
2. **Accoppiamento Hardcoded nello Script**:
   - Lo script `scripts/benchmarks/run_guidellm_benchmark.sh` contiene attualmente uno switch statico (`case "$NODE"`) per dedurre memoria e URL endpoint (`http://10.10.20.33:11434/v1`).
   - L'aggiunta o la modifica di istanze Ollama nell'infrastruttura richiede di modificare manualmente il codice dello script anziché aggiornare il registro canonico di rete.

---

## 2. Architettura della Proposta in `rete.json`

### 2.1 Censimento Servizi nei Nodi (`nodi[].services`)
In linea con la struttura già adottata in `rete.json` per `mac studio` (servizio `tdarr-node`) e `tdarr-api`, aggiungiamo la definizione formale del servizio `ollama` nei rispettivi nodi:

#### Su `lxc-ollama` (`10.10.20.33`):
```json
"services": [
  {
    "id": "ollama",
    "label": "Ollama LLM Engine (AMD Radeon 890M APU)",
    "port": 11434,
    "protocol": "HTTP",
    "api_base": "/v1",
    "memory": "38gb",
    "hardware": "AMD Radeon 890M (Vulkan RADV)",
    "status": "active",
    "notes": "Ollama 0.34.2 con OLLAMA_IGPU_ENABLE=1 e mount NFS stripe/ollama."
  }
]
```

#### Su `mac studio` (`10.10.20.100`):
```json
{
  "id": "ollama",
  "label": "Ollama LLM Engine (Apple Silicon Metal)",
  "port": 11434,
  "protocol": "HTTP",
  "api_base": "/v1",
  "memory": "64gb-unified",
  "hardware": "Apple Silicon M2 Ultra",
  "status": "active",
  "notes": "Inferenza locale su macOS via Metal framework."
}
```

### 2.2 Censimento Applicativo Globale (`applicazioni[]`)
Aggiunta dell'entità `ollama` nella sezione top-level `applicazioni`:
```json
{
  "id": "ollama",
  "label": "Ollama Distributed LLM Inference",
  "role": "Local LLM Inference Engine (Homelab)",
  "service_id": "ollama",
  "port": 11434,
  "nodes": [
    "lxc-ollama",
    "mac studio"
  ],
  "storage": "NFS stripe/ollama (TrueNAS SCALE 10.10.20.50)",
  "status": "Active"
}
```

---

## 3. Integrazione Dinamica nello Script (`run_guidellm_benchmark.sh`)

Lo script utilizzerà `jq` per leggere a runtime `rete.json`:
1. **Discovery Automatica dei Nodi Fornitori**:
   - Query: `jq -r '.nodi[] | select(.services[]?.id == "ollama") | "\(.id)|\(.ip)|\(.services[] | select(.id == "ollama") | .port)|\(.services[] | select(.id == "ollama") | .memory)|\(.label)"' rete.json`
2. **Generazione Dinamica del Menu Interattivo**:
   - Se l'utente non passa il nodo da CLI, il menu numerato elencherà automaticamente tutti i nodi censiti in `rete.json` con relativo IP, porta, memoria e hardware, più l'opzione "Custom".
3. **Risoluzione Automatica per Argomenti CLI**:
   - Se l'utente esegue `./run_guidellm_benchmark.sh lxc-ollama` o `-n "mac studio"`, lo script estrae direttamente da `rete.json` l'IP, la porta `11434` e la dotazione di memoria, senza alcun valore hardcoded nel codice shell.
4. **Resilienza**:
   - Se `rete.json` è assente o non contiene il nodo richiesto, lo script mantiene un fallback sicuro con valori di default minimi.

---

## 4. Fasi Operative Dettagliate (Test-Driven Protocol)

### Fase 1: Aggiornamento Dichiarativo di `rete.json` ✅
- **Esito**: Completata. Aggiunto blocco `services` su `lxc-ollama` (10.10.20.33, porta 11434, memoria 38gb) e su `mac studio` (10.10.20.100, porta 11434, memoria 64gb-unified); aggiunta entità applicativa globale `ollama` in `applicazioni[]`.
- **Verifica**: `python3 scripts/network/validate_network.py` ha riportato congruenza al 100% (0 errori).

### Fase 2: Validazione Parsing Dinamico da CLI (`jq` / python) ✅
- **Esito**: Completata. Testato parsing di estrazione nodi, IP, porte, memorie ed hardware sia in formato tab/pipe delimitato sia via helper JSON per garantire portabilità assoluta.

### Fase 3: Refactoring di `scripts/benchmarks/run_guidellm_benchmark.sh` ✅
- **Esito**: Completata. Sostituito lo switch case statico con la query dinamica da `rete.json` (Source of Truth). Linting eseguito con successo (`bash -n`) e verifica `--help`.

### Fase 4: Validazione Test-Driven End-to-End ✅
- **Esito**: Completata con successo:
  - Risoluzione batch CLI `lxc-ollama`: risolto `10.10.20.33:11434`, memoria `38gb`, discovery automatica di 3 modelli dal target (`qwen3-vl:32b`, `bge-m3:latest`, `gemma4:31b`), pattern corretto `report-lxc-ollama-qwen3-vl-32b-38gb-<timestamp>`.
  - Risoluzione batch CLI `mac studio`: risolto `10.10.20.100:11434`, memoria `64gb-unified`, discovery automatica di 7 modelli dal target (`qwen2.5:72b`, `deepseek-r1:32b`, ecc.), pattern corretto `report-macstudio-qwen3-vl-32b-64gb-unified-<timestamp>`.
  - Wizard interattivo (nessun parametro): menu generato dinamicamente da `rete.json` con selezione numerica del nodo e successivo menu numerico dei modelli del target.

### Fase 5: Consolidamento Documentale e Sync Wiki Context ✅
- **Esito**: Completata. Aggiornato `todo.md`, sincronizzato `wiki/wiki_context.md` e convalidata la rete.

---

## 💾 Stato di Ripristino (AI Save-State)
- **Fase Attiva**: Piano Completato con Successo ✅
- **Ultima Azione Completata**: Validazione end-to-end con esecuzione test su nodi fisici del lab, risoluzione dinamica da `rete.json` e sincronizzazione documentale.
- **Prossimo Passo Operativo**: Nessuno. Lo script `scripts/benchmarks/run_guidellm_benchmark.sh` e il registro `rete.json` sono operativi e convergenti.
- **Blocchi/Decisioni Pendenti**: Nessuno.

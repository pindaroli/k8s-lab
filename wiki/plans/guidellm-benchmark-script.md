---
title: "Piano: Script Shell Interattivo per Benchmark GuideLLM con Naming Pattern Standard"
type: plan
status: active
certified_for_ai: true
created_at: 2026-10-11
tags:
  - "#benchmarking"
  - "#guidellm"
  - "#llm"
  - "#ollama"
  - "#pve3"
  - "#automation"
---

# Piano: Script Shell Interattivo per Benchmark GuideLLM con Naming Pattern Standard

Il presente piano operativo definisce l'architettura, la progettazione e la realizzazione di uno script shell (`scripts/benchmarks/run_guidellm_benchmark.sh`) per automatizzare l'esecuzione di benchmark di modelli linguistici tramite **GuideLLM** nell'infrastruttura homelab. Lo script gestisce sia l'invocazione batch con parametri da linea di comando sia una modalità interattiva con prompt guidati, applicando rigorosamente la convenzione definita in [[guidellm-report-naming-pattern]].

---

## 🗺️ Mappe Concettuali e Relazioni
- [[SCHEMA]] (Regole di governance e salvataggio del Wiki)
- [[guidellm-report-naming-pattern]] (Standard di denominazione dei report: `report-<nodo>-<modello>-<memoria>-<dataora>.<ext>`)
- [[zero-install-executable-package-pattern]] (Esecuzione effimera on-demand via `uvx` in assenza di binario locale)
- [[pve3-lxc-ollama-nfs-stripe-storage]] (Endpoint di inferenza Ollama su `lxc-ollama` `10.10.20.33:11434`)
- [[Network_Registry]] (Censimento IP e nodi homelab da `rete.json`)

---

## 1. Analisi dei Requisiti e Architettura dello Script

### 1.1 Risoluzione Semantica dei Parametri
Lo script deve accettare i parametri sia posizionali/tramite flag da CLI, sia via prompt interattivi qualora omessi:

1. **Nodo / Macchina Host (`--node` / `$1`)**:
   - Identificativo dell'host censito in `rete.json` o macchina fisica che ospita il motore LLM.
   - Nodi preconfigurati nel lab:
     - `lxc-ollama`: Container LXC 300 su PVE3 (`10.10.20.33`), GPU Radeon 890M / Vulkan RADV, memoria default `38gb`.
     - `pve3`: Host Proxmox VE 9.2 (`10.10.10.31`), APU AMD Strix, memoria default `64gb`.
     - `olilab-worker`: VM Ubuntu 24.04 (`10.10.20.70`), memoria default `2gb`.
     - `macbook-pro` / `localhost`: Macchina locale client, memoria rilevabile tramite `sysctl hw.memsize`.
     - Input libero (qualsiasi altro host o identificativo custom).

2. **Modello LLM (`--model` / `$2`)**:
   - Nome del modello da sottoporre a benchmark (es. `llama-3.2-3b-instruct`, `qwen2.5-coder-7b`, `gemma4:31b`).
   - Se in modalità interattiva e l'endpoint Ollama è raggiungibile, lo script effettua una query a `http://<target>:11434/api/tags` e visualizza l'elenco dei modelli installati per selezione immediata tramite numero, oltre a consentire l'inserimento manuale.
   - Normalizzazione automatica del nome per il filesystem (sostituzione di `:` o `/` con trattini o underscore, per conformità al pattern).

3. **Dotazione di Memoria (`--mem` / `$3`)**:
   - Dimensione RAM/VRAM della macchina per il pattern di naming (es. `64gb`, `38gb`, `64gb-unified`).
   - Se non specificata da CLI, viene automaticamente preimpostata sul valore di default associato al nodo selezionato, con possibilità di modifica manuale.

4. **Backend URL (`--backend` / `$4`)**:
   - Endpoint OpenAI-compatibile per GuideLLM (`kind=openai_http,target=...`).
   - Default per `lxc-ollama` / `pve3`: `http://10.10.20.33:11434/v1`.
   - Default per `localhost`: `http://localhost:11434/v1`.

5. **Opzioni Aggiuntive e Runner**:
   - `--dry-run`: Mostra i parametri risolti, i nomi dei file generati e il comando GuideLLM senza eseguire il benchmark.
   - Supporto runner flessibile: verifica della presenza di `guidellm` nel PATH di sistema; se assente, invocazione automatica di `uvx guidellm` in conformità con [[zero-install-executable-package-pattern]].
   - Generazione multi-formato simultanea: JSON (dati grezzi), CSV (tabelle comparative) e HTML (dashboard visiva) nella directory configurabile `--output-dir` (default: `./reports`).

---

## 2. Specifiche del Pattern di Naming ([[guidellm-report-naming-pattern]])

La convenzione applicata dallo script per gli artefatti prodotti è:
```text
report-<nome macchina>-<nome llm>-<memoria macchina>-<dataora>.<estensione>
```

- Regex di conformità:
  `^report-([a-z0-9-]+)-([a-z0-9._-]+)-([0-9]+[a-z]+(?:-[a-z0-9]+)*)-([0-9]{8}-[0-9]{4,6})\.(json|csv|html|log)$`
- Timestamp: `date +"%Y%m%d-%H%M%S"`

Esempio generato:
- `reports/report-lxc-ollama-llama-3.2-3b-instruct-38gb-20261011-203500.json`
- `reports/report-lxc-ollama-llama-3.2-3b-instruct-38gb-20261011-203500.csv`
- `reports/report-lxc-ollama-llama-3.2-3b-instruct-38gb-20261011-203500.html`

---

## 3. Fasi Operative Dettagliate (Test-Driven Protocol)

### Fase 1: Creazione Struttura Directory e Script Shell ✅
- **Esito**: Completata. Creato `scripts/benchmarks/run_guidellm_benchmark.sh` con permessi `+x`, linting `bash -n` e help completi.

### Fase 2: Validazione della Modalità Dry-Run e Risoluzione Naming ✅
- **Esito**: Completata. Verificato `--dry-run` sia con flag che posizionale, normalizzazione nomi modelli (`gemma4:31b` -> `gemma4-31b`) e regex POSIX conforme al 100%.

### Fase 3: Validazione Connettività e Test Interattivo ✅
- **Esito**: Completata. Discovery automatica modelli via API Ollama (`/api/tags`) su `10.10.20.33:11434` testata e funzionante con successo.

### Fase 4: Esecuzione di Benchmark Reale di Prova ✅
- **Esito**: Completata. Eseguito benchmark reale di smoke test con `gemma4:31b` e generazione con successo di:
  - `reports/report-lxc-ollama-gemma4-31b-38gb-20261011-210320.json` (48 KB)
  - `reports/report-lxc-ollama-gemma4-31b-38gb-20261011-210320.csv` (14 KB)
  I nomi file generati soddisfano al 100% la regex di [[guidellm-report-naming-pattern]].

### Fase 5: Consolidamento Documentale e Allineamento Pattern ✅
- **Esito**: Completata. Aggiornato `in_use_by` in `wiki/patterns/guidellm-report-naming-pattern.md`, aggiornato `todo.md` e contesti wiki.

---

## 💾 Stato di Ripristino (AI Save-State)
- **Fase Attiva**: Piano Completato con Successo ✅
- **Ultima Azione Completata**: Test-driven smoke test reale con generazione file JSON e CSV conformi al pattern e consolidamento wiki.
- **Prossimo Passo Operativo**: Nessuno, script operativo e pronto all'uso interattivo o batch.
- **Blocchi/Decisioni Pendenti**: Nessuno.

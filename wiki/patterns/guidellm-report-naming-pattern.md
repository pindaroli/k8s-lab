---
id: guidellm-report-naming-pattern
title: "Pattern: Convenzione di Naming dei Report Benchmark GuideLLM"
type: pattern
status: active
certified_for_ai: true
created_at: 2026-10-11
last_updated: 2026-10-11
in_use_by:
  - project: "k8s-lab"
    paths:
      - "wiki/patterns/guidellm-report-naming-pattern.md"
tags:
  - "#pattern"
  - "#guidellm"
  - "#benchmarking"
  - "#llm"
  - "#naming-convention"
  - "#ollama"
  - "#vllm"
---

# Pattern: Convenzione di Naming dei Report Benchmark GuideLLM

Questo pattern definisce lo standard architetturale e la convenzione canonica di denominazione dei file generati dalle sessioni di benchmark e profilazione prestazionale di modelli linguistici (LLM) eseguite tramite lo strumento **GuideLLM** (Neural Magic / vLLM ecosystem) all'interno dell'infrastruttura homelab.

---

## 🗺️ Mappe Concettuali e Relazioni
- [[SCHEMA]] (Regole di governance e catalogazione del Wiki)
- [[Talos_Cluster]] (Cluster Kubernetes del lab)
- [[pve3-hybrid-controlplane-lxc-convergence]] (Nodo PVE3 e workload AI / GPU)
- [[pve3-lxc-ollama-nfs-stripe-storage]] (Hosting modelli LLM e inferenza su Ollama)

---

## 1. Problema e Motivazione

Durante l'esecuzione di benchmark prestazionali (throughput tokens/sec, Time To First Token TTFT, Inter-Token Latency ITL, rate sweeps) su motori di inferenza come Ollama, vLLM o TGI ospitati su diversi host dell'homelab:
1. **Dispersione dei Risultati**: Se i report generati da GuideLLM (JSON, CSV, HTML) mantengono nomi generici (es. `report.json`, `output.html`, `benchmark.csv`), diventa impossibile correlare a posteriori i file con la specifica macchina ospitante, il modello testato e le condizioni hardware.
2. **Confronto Multi-Hardware**: I benchmark vengono condotti su macchine eterogenee (es. nodo Proxmox `pve3` con APU AMD Radeon 890M, workstation Apple Silicon con memoria unificata, container LXC o VM dedicate come `lxc-ollama` o `olilab-worker`). Conoscere immediatamente la dotazione di memoria disponibile/allocata è essenziale per comprendere il comportamento del KV cache, dell'offloading su GPU/RAM e il throughput complessivo.
3. **Ordinamento Cronologico e Tracciabilità**: È fondamentale che i file siano ordinabili cronologicamente (`sort` / `ls`) per tracciare regressioni o miglioramenti prestazionali a seguito di aggiornamenti di engine, modelli o driver.

---

## 2. Definizione del Pattern di Naming

La struttura canonica per i file di output prodotti dall'esecuzione di GuideLLM è:

```text
report-<nome macchina che hosta llm>-<nome llm>-<dotazione di memoria della macchina che hosta>-<dataora-esecuzione>.<estensione>
```

### Espressione Regolare (Regex di Validazione)

```regex
^report-([a-z0-9-]+)-([a-z0-9._-]+)-([0-9]+[a-z]+(?:-[a-z0-9]+)*)-([0-9]{8}-[0-9]{4,6})\.(json|csv|html|txt|log)$
```

---

## 3. Specifiche dei Componenti

| Segmento | Formato / Vincoli | Descrizione e Regole | Esempi Canonici |
| :--- | :--- | :--- | :--- |
| **`report-`** | Costante | Prefisso fisso minuscolo che identifica immediatamente la tipologia di artefatto come report di benchmark. | `report-` |
| **`<nome macchina>`** | Kebab-case minuscolo `[a-z0-9-]+` | Hostname o identificativo canonico dell'host/nodo/LXC/VM censito in `rete.json` o macchina fisica che esegue l'engine LLM. | `pve3`, `lxc-ollama`, `olilab-worker`, `macbook-pro` |
| **`<nome llm>`** | Minuscolo `[a-z0-9._-]+` | Nome univoco del modello LLM testato, normalizzato eliminando due punti (`:`) o slash (`/`) e includendo quantizzazione o variante se rilevante. | `llama-3.2-3b-instruct`, `qwen2.5-coder-7b`, `mistral-nemo-12b-q8_0` |
| **`<memoria macchina>`** | Minuscolo `[a-z0-9-]+` | Quantità di RAM/VRAM disponibile sulla macchina o allocata per il container/VM. Per APU/Unified specificare la natura della memoria. | `64gb`, `32gb`, `64gb-unified`, `32gb-ram-16gb-vram` |
| **`<dataora>`** | `YYYYMMDD-HHMMSS` o `YYYYMMDD-HHMM` | Timestamp numerico compatto di avvio del benchmark per garantire univocità e ordinamento cronologico. | `20261011-193000`, `20261011-1930` |
| **`<estensione>`** | `json`, `csv`, `html`, `log`, `txt` | Formato del report o log generato da GuideLLM o dal wrapper di esecuzione. | `.json`, `.csv`, `.html`, `.log` |

---

## 4. Esempi Concreti nel Homelab

### Caso 1: Test su nodo Proxmox PVE3 con APU Radeon 890M (64 GB)
- **JSON Metriche**: `report-pve3-llama-3.2-3b-instruct-64gb-20261011-193000.json`
- **Dashboard HTML**: `report-pve3-llama-3.2-3b-instruct-64gb-20261011-193000.html`
- **Tabella CSV**: `report-pve3-llama-3.2-3b-instruct-64gb-20261011-193000.csv`

### Caso 2: Test su LXC Ollama con 32 GB RAM allocata
- **JSON Metriche**: `report-lxc-ollama-qwen2.5-coder-7b-32gb-20261011-201500.json`
- **Dashboard HTML**: `report-lxc-ollama-qwen2.5-coder-7b-32gb-20261011-201500.html`

### Caso 3: Test su Workstation macOS Apple Silicon con 64 GB Memoria Unificata
- **JSON Metriche**: `report-macbook-pro-mistral-nemo-12b-64gb-unified-20261011-141522.json`
- **Dashboard HTML**: `report-macbook-pro-mistral-nemo-12b-64gb-unified-20261011-141522.html`

---

## 5. Implementazione Pratica con CLI GuideLLM

GuideLLM supporta il parametro `--output-path <path>` per impostare la destinazione e il nome del report generato.

### Template Script Bash di Esecuzione Conforme

```bash
#!/usr/bin/env bash
set -euo pipefail

# Parametri di configurazione del benchmark
HOST_NAME="pve3"
MODEL_NAME="llama-3.2-3b-instruct"
HOST_MEM="64gb"
BACKEND_URL="http://10.10.20.33:11434/v1"

# Generazione dataora conforme YYYYMMDD-HHMMSS
DATAORA=$(date +"%Y%m%d-%H%M%S")

# Costruzione del prefisso base secondo il pattern
BASE_NAME="report-${HOST_NAME}-${MODEL_NAME}-${HOST_MEM}-${DATAORA}"
OUTPUT_DIR="./reports"
mkdir -p "${OUTPUT_DIR}"

REPORT_JSON="${OUTPUT_DIR}/${BASE_NAME}.json"
REPORT_CSV="${OUTPUT_DIR}/${BASE_NAME}.csv"
REPORT_HTML="${OUTPUT_DIR}/${BASE_NAME}.html"

echo "Avvio GuideLLM per ${MODEL_NAME} su ${HOST_NAME}..."
echo "Destinazione report: ${REPORT_JSON}"

# Esecuzione GuideLLM con output strutturato JSON
guidellm run \
  --backend kind=openai_http,target="${BACKEND_URL}" \
  --model "${MODEL_NAME}" \
  --profile kind=sweep \
  --output-path "${REPORT_JSON}"

echo "Benchmark completato con successo: ${REPORT_JSON}"
```

---

## 6. Regole di Conformità e Governance

1. **Mai Omettere l'Host**: Il campo `<nome macchina>` non deve mai essere generico (vietato usare solo `server` o `host`). Usare sempre l'identificativo esatto della macchina o del container (`pve3`, `lxc-ollama`, ecc.).
2. **Caratteri Speciali Proibiti**: Gli unici separatori ammessi all'interno del nome file sono il trattino `-` e il punto per l'estensione `.` (e facoltativamente underscore `_` solo all'interno del nome specifico del modello o quantizzazione). Vietati spazi, slash, due punti e parentesi.
3. **Dataora ISO-Compatta**: Usare sempre `YYYYMMDD-HHMMSS` o `YYYYMMDD-HHMM`. Mai usare formati data all'italiana (es. `11-10-2026`) né separatori come `/` o `:` che alterano la leggibilità e l'ordinamento naturale nei filesystem Unix.

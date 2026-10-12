---
title: "Piano: Script Shell Interattivo per Benchmark OCR con Promptfoo"
type: plan
status: completed
certified_for_ai: true
created_at: 2026-10-12
tags:
  - "#benchmarking"
  - "#ocr"
  - "#promptfoo"
  - "#llama-server"
  - "#ollama"
  - "#pve3"
  - "#automation"
---

# Piano: Script Shell Interattivo per Benchmark OCR con Promptfoo

Il presente piano operativo definisce l'architettura, la progettazione e la realizzazione di uno script shell interattivo e da linea di comando (`scripts/benchmarks/run_promptfoo_ocr.sh` o collegato da `benchmarks/promptfoo-ocr/run_promptfoo.sh`) per automatizzare l'esecuzione di benchmark di modelli Vision/OCR (Document Understanding, Estrazione Tabelle e JSON) tramite **Promptfoo** nell'infrastruttura homelab.
Lo script gestisce sia l'invocazione batch tramite flag CLI sia un menu interattivo con selezione guidata dei modelli, fixture e target backend, applicando rigorosamente la convenzione di denominazione dei report definita in [[guidellm-report-naming-pattern]].

---

## 🗺️ Mappe Concettuali e Relazioni
- [[SCHEMA]] (Regole del Wiki, Governance e Protocollo Test-Driven)
- [[promptfoo-ocr-benchmark-evaluation]] (Installazione e Configurazione Promptfoo per Benchmark OCR, Layout e JSON su Mac)
- [[lxc-ollama-llama-ocr-qwen25-sidecar]] (Sidecar `llama-server` Vulkan con Qwen2.5-VL-7B OCR su CT 300)
- [[guidellm-report-naming-pattern]] (Standard di denominazione dei report: `report-<nodo>-<modello>-<memoria>-<dataora>.<ext>`)
- [[guidellm-benchmark-script]] (Architettura di riferimento per script shell interattivi homelab)
- [[ollama-rete-registry-integration]] (Registrazione canonica dei servizi AI in `rete.json` e discovery dinamica)
- [[Network_Registry]] (Censimento IP `lxc-ollama` su VLAN 20: `10.10.20.33`)

---

## 1. Analisi dei Requisiti e Architettura dello Script

### 1.1 Risoluzione Dinamica dei Backend da `rete.json`
In conformità con [[ollama-rete-registry-integration]], lo script interroga `rete.json` per risolvere automaticamente gli indirizzi e le porte dei target:
1. **Target Primario (Vision-Language OCR)**: `llama-server` Vulkan su `10.10.20.33:8081` (modello `Qwen2.5-VL-7B-Instruct`).
2. **Target Comparativo (Ollama Baseline)**: `ollama` su `10.10.20.33:11434` (modelli multimodali come `llama3.2-vision:11b` o LLM testuali come `qwen2.5:32b`).
3. **Endpoint Locale**: Mac locale su `127.0.0.1:11434` o `127.0.0.1:8081`.

### 1.2 Parametri e Modalità di Esecuzione
Lo script supporta sia parametri CLI sia un prompt guidato interattivo:
1. **Nodo / Host (`--node` / `-n`)**: default `lxc-ollama` (con risoluzione automatica memoria `54gb`).
2. **Modello OCR (`--model` / `-m`)**: default `qwen2.5-vl-7b-instruct` (o selezione da API `/api/tags` o `/v1/models`).
3. **Memoria (`--mem`)**: default `54gb` (o rilevamento per nodi locali/remoti).
4. **Backend URL (`--backend` / `-b`)**: default `http://10.10.20.33:8081/v1`.
5. **Fixture Documento (`--fixture` / `-f`)**: selezione tra `fattura_test.png`, `ricevuta_test.jpg` o file custom.
6. **Task OCR (`--task` / `-t`)**:
   - `all`: suite completa (Markdown + JSON)
   - `markdown`: trascrizione layout tabellare
   - `json`: estrazione entità strutturata
7. **Azioni (`eval`, `view`, `dry-run`)**:
   - `eval`: esecuzione della valutazione Promptfoo con export simultaneo JSON e HTML.
   - `view`: avvio dashboard web su porta configurabile (default 15500).
   - `--dry-run`: ispezione dei parametri risolti e validazione configurazione senza chiamare gli endpoint.

---

## 2. Naming Standard dei Report ([[guidellm-report-naming-pattern]])

La convenzione applicata per gli artefatti prodotti in `reports/` è:
```text
report-<nome macchina>-<nome modello>-<memoria macchina>-<dataora>.<estensione>
```

- Regex di conformità:
  `^report-([a-z0-9-]+)-([a-z0-9._-]+)-([0-9]+[a-z]+(?:-[a-z0-9]+)*)-([0-9]{8}-[0-9]{4,6})\.(json|html)$`
- Timestamp: `date +"%Y%m%d-%H%M%S"`

Esempio generato:
- `reports/report-lxc-ollama-qwen2.5-vl-7b-instruct-54gb-20261012-004000.json`
- `reports/report-lxc-ollama-qwen2.5-vl-7b-instruct-54gb-20261012-004000.html`

---

## 3. Fasi Operative Dettagliate (Test-Driven Protocol)

### Fase 1: Progettazione Architettura e Scaffolding dello Script
- **Azione**: Creazione di `scripts/benchmarks/run_promptfoo_ocr.sh` con gestione colori, parsing argomenti CLI, funzioni di help e permessi `+x`.
- **Test di Verifica Reale**: `bash -n scripts/benchmarks/run_promptfoo_ocr.sh && scripts/benchmarks/run_promptfoo_ocr.sh --help`
  *Criterio di successo*: Nessun errore di sintassi e corretta visualizzazione della guida.

### Fase 2: Discovery Dinamica Modelli OCR ed Endpoint da `rete.json`
- **Azione**: Implementazione della lettura automatica di `rete.json` (tramite `jq` / Python fallback) per estrarre host e porte di `lxc-ollama` (`llama-ocr` :8081 e `ollama` :11434).
- **Test di Verifica Reale**: Esecuzione dello script con flag di test connettività verso gli endpoint censiti.
  *Criterio di successo*: Risoluzione corretta di URL e stato online/offline dei servizi.

### Fase 3: Supporto Modalità Interattiva, CLI Flags, Fixture Picker e Dry-Run
- **Azione**: Sviluppo del menu interattivo con selezione guidata di nodo, backend, modello, fixture e task, con supporto per il flag `--dry-run`.
- **Test di Verifica Reale**: Esecuzione in modalità `--dry-run` e verifica che il comando generato e i percorsi dei report siano conformi alle specifiche.
  *Criterio di successo*: Risoluzione corretta del report name e assenza di esecuzioni accidentali in dry-run.

### Fase 4: Validazione Test-Driven End-to-End ed Esportazione Report Multi-Formato
- **Azione**: Esecuzione di una sessione di benchmark reale con salvataggio automatico in `reports/`.
- **Test di Verifica Reale**: Ispezione dei file generati (`ls -lh reports/report-lxc-ollama-*.json reports/report-lxc-ollama-*.html`) e validazione conformità regex [[guidellm-report-naming-pattern]].
  *Criterio di successo*: Report generati con esito positivo e matching regex al 100%.

### Fase 5: Consolidamento Documentale, Allineamento Wiki e Sincronizzazione Contesto
- **Azione**: Allineamento di `todo.md`, aggiornamento frontmatter del piano e sincronizzazione del contesto wiki.
- **Comandi**: `python3 scripts/network/validate_network.py && python3 scripts/wiki/build_wiki_context.py`
  *Criterio di successo*: Contesto wiki sincronizzato senza errori.

---

## 💾 Stato di Ripristino (AI Save-State)
- **Fase Attiva**: Completato (Fasi 1-5 completate con successo)
- **Ultima Azione Completata**: Validazione test-driven end-to-end con esito 2/2 PASS (100%) in 6s su task Markdown e JSON con `qwen2.5vl:7b-q4_K_M` ed esportazione report conformi a `[[guidellm-report-naming-pattern]]`.
- **Prossimo Passo Operativo**: Nessuno (piano completato con successo).
- **Blocchi/Decisioni Pendenti**: Nessuno.

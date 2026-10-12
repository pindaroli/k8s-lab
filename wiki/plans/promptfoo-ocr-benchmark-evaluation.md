---
title: "Piano: Installazione e Configurazione Promptfoo per Benchmark OCR, Layout e JSON su Mac"
type: plan
status: archived
certified_for_ai: false
created_at: 2026-10-11
archived_at: 2026-10-12
superseded_by: [[promptfoo-ocr-benchmark-script]]
tags:
  - "#ocr"
  - "#benchmarking"
  - "#promptfoo"
  - "#macos"
  - "#ollama"
  - "#llama-server"
  - "#pve3"
---

# Piano: Installazione e Configurazione Promptfoo per Benchmark OCR, Layout e JSON su Mac

Il presente piano operativo definisce l'architettura, la progettazione e la procedura test-driven per l'installazione e la configurazione sul client **macOS** del framework di valutazione automatizzata **Promptfoo**.
Il framework consente di misurare in modo oggettivo e ripetibile le performance di **Document Understanding**, **Accuratezza OCR**, **Preservazione del Layout Tabellare** ed **Estrazione JSON Strutturato**, testando i modelli visivi e linguistici ospitati sull'infrastruttura homelab (in primis **`llama-server` Vulkan** con `Qwen2.5-VL-7B-Instruct` su `10.10.20.33:8081` e in confronto **Ollama** su `10.10.20.33:11434`).

---

## 🗺️ Mappe Concettuali e Relazioni
- [[SCHEMA]] (Regole del Wiki, Governance e Protocollo Test-Driven)
- [[lxc-ollama-llama-ocr-qwen25-sidecar]] (Sidecar `llama-server` Vulkan con Qwen2.5-VL-7B OCR su CT 300)
- [[guidellm-report-naming-pattern]] (Standard di denominazione dei report: `report-<nodo>-<modello>-<memoria>-<dataora>.<ext>`)
- [[zero-install-executable-package-pattern]] (Valutazione esecuzione effimera via `npx` vs installazione Homebrew)
- [[Network_Registry]] (Censimento IP `lxc-ollama` su VLAN 20: `10.10.20.33`)

---

## 1. Analisi dei Requisiti e Confronto Tecnico

### 1.1 Risoluzione dell'Architettura Homelab & Endpoint
I test vengono eseguiti localmente dal Mac, mentre i modelli AI sono ospitati sul container LXC 300 (`lxc-ollama`) su PVE3:
- **Target Primario (Vision-Language OCR)**: `http://10.10.20.33:8081/v1`
  - Istanza dedicata: `llama-server` Vulkan (da [[lxc-ollama-llama-ocr-qwen25-sidecar]])
  - Modello: `Qwen2.5-VL-7B-Instruct` accelerato con RADV su GPU AMD Radeon 890M.
  - Formato OpenAI: Vision Chat API (`image_url` con data URI o file locale gestito da Promptfoo).
- **Target Comparativo (Ollama Baseline)**: `http://10.10.20.33:11434/v1`
  - Istanza: Ollama su CT 300 (porta 11434).
  - Modelli: `qwen2.5:32b` (per confronto testo/formattazione) o modelli Vision aggiuntivi (es. `llama3.2-vision:11b`).

### 1.2 Strategia di Installazione su macOS (Confronto Opzioni)

In conformità con le policy del repository e la regola **Priorità Homebrew (brew)**:
- **Stato Attuale del Sistema**:
  - Node.js è già installato via Homebrew: `/opt/homebrew/bin/node` (v26.4.0)
  - npm e npx sono presenti: `/opt/homebrew/bin/npm`, `/opt/homebrew/bin/npx`
  - Homebrew dispone della formula ufficiale dedicata: `brew desc promptfoo` -> `promptfoo: Test your LLM app locally`.

| Metodo | Comando | Vantaggi | Svantaggi | Raccomandazione |
| :--- | :--- | :--- | :--- | :--- |
| **Opzione A: Homebrew Nativo** | `brew install promptfoo` | Conforme alla regola di progetto Homelab; gestione pacchetti isolata e pulita; aggiornamenti centralizzati via `brew upgrade`. | Formula gestita dai maintainer Homebrew. | ⭐ **Consigliato (Priorità di Progetto)** |
| **Opzione B: NPM Globale** | `npm install -g promptfoo` | Versione sempre aggiornatissima da registry npm. | Rischio di permessi `/opt/homebrew/lib/node_modules` o inquinamento path globale. | Alternativa proposta dall'utente |
| **Opzione C: Zero-Install (npx)** | `npx promptfoo eval` | Conforme a [[zero-install-executable-package-pattern]]; nessuna installazione permanente sul disco. | Scaricamento/latenza ad ogni esecuzione o dipendenza da cache locale temporanea. | Valido per prove rapide on-demand |

---

## 2. Architettura della Test Suite e Scaffolding

Per garantire riproducibilità GitOps e coerenza con gli altri benchmark del lab (es. GuideLLM):
- **Directory del Progetto**: `benchmarks/promptfoo-ocr/`
- **Struttura dei File**:
  ```text
  benchmarks/promptfoo-ocr/
  ├── promptfooconfig.yaml          # Configurazione dichiarativa della suite
  ├── fixtures/                     # Documenti e immagini campione per i test
  │   ├── fattura_test.png          # Documento fattura con tabella prezzi e totali
  │   ├── ricevuta_test.jpg         # Scontrino / ricevuta con layout complesso
  │   └── synthetic_invoice.py      # Script Python per rigenerare fixture sintetiche
  ├── prompts/                      # Template di prompt separati
  │   ├── transcribe_markdown.txt   # Prompt per trascrizione Markdown & tabelle
  │   └── extract_json.txt          # Prompt per estrazione strutturata JSON
  └── run_promptfoo.sh              # Wrapper script di esecuzione con salvataggio report in reports/
  ```

### 2.1 Specifiche delle Asserzioni e Metriche
La configurazione implementa tre tipologie essenziali di validazione:
1. **Accuratezza Testuale e Presenza Entità (`icontains`)**:
   - Rilevazione parole chiave ("FATTURA", "Totale Euro", P.IVA, importi).
   - Assenza di disclaimer di rifiuto ("not-icontains": "non posso elaborare immagini").
2. **Preservazione del Layout Tabellare (`javascript`)**:
   - Asserzione JS per verificare che l'output contenga la struttura Markdown standard di una tabella (`|` delimitatori e `---` separatori di header).
   - Conteggio o conformità delle colonne estratte.
3. **Validazione JSON Strutturato (`is-json` / Schema)**:
   - Asserzione che l'output sia un JSON valido e contenga i campi richiesti (`totale`, `data`, `voci`).

---

## 3. Fasi Operative Dettagliate (Test-Driven Protocol)

### Fase 1: Verifica Prerequisiti e Installazione Promptfoo su Mac
- **Azione**: Installazione di `promptfoo` tramite il gestore di pacchetti Homebrew (`brew install promptfoo`), oppure in subordine tramite `npm install -g promptfoo`.
- **Comandi**:
  ```bash
  brew install promptfoo
  ```
- **Test di Verifica Reale**:
  ```bash
  promptfoo --version
  ```
  *Criterio di successo*: Il comando restituisce la versione installata di Promptfoo senza errori.

---

### Fase 2: Creazione Scaffolding e Predisposizione Fixture di Test
- **Azione**: Creazione della directory `benchmarks/promptfoo-ocr/` e delle sottocartelle `fixtures/` e `prompts/`. Predisposizione dei documenti immagine di test (`fattura_test.png`, `ricevuta_test.jpg`) con uno script Python opzionale per generare fixture sintetiche ad alta risoluzione.
- **Comandi**:
  ```bash
  mkdir -p benchmarks/promptfoo-ocr/fixtures benchmarks/promptfoo-ocr/prompts
  ```
- **Test di Verifica Reale**:
  ```bash
  ls -la benchmarks/promptfoo-ocr/fixtures/
  ```
  *Criterio di successo*: Le directory sono create e le immagini campione sono presenti e leggibili.

---

### Fase 3: Stesura della Configurazione Dichiarativa (`promptfooconfig.yaml`)
- **Azione**: Creazione del file `benchmarks/promptfoo-ocr/promptfooconfig.yaml` con:
  - Definizione provider per `llama-server` (`http://10.10.20.33:8081/v1`) e per Ollama (`http://10.10.20.33:11434/v1`).
  - Template dei prompt per trascrizione Markdown e per estrazione JSON.
  - Test suite con asserzioni semantiche (`icontains`), layout (`javascript`) e JSON schema.
- **Test di Verifica Reale**:
  ```bash
  # Validazione sintassi YAML e dry-run Promptfoo
  npx promptfoo eval --config benchmarks/promptfoo-ocr/promptfooconfig.yaml --dry-run
  ```
  *Criterio di successo*: Promptfoo valida la configurazione caricando correttamente i provider e i test case definiti.

---

### Fase 4: Validazione Connettività verso gli Endpoint Remoti
- **Azione**: Test di raggiungibilità HTTP dal Mac verso gli endpoint AI su `lxc-ollama` (`10.10.20.33`).
- **Comandi di Test**:
  ```bash
  # Verifica endpoint Ollama
  curl -s http://10.10.20.33:11434/api/tags | jq .

  # Verifica endpoint llama-server (una volta attivo CT 300 porta 8081)
  curl -s http://10.10.20.33:8081/v1/models | jq .
  ```
  *Criterio di successo*: Risposta HTTP 200 con payload JSON valido per ciascun servizio.

---

### Fase 5: Esecuzione Benchmark di Prova ed Esportazione Report
- **Azione**: Esecuzione del test di valutazione `promptfoo eval` ed esportazione del report nel percorso canonico `reports/` in conformità con [[guidellm-report-naming-pattern]].
- **Comandi**:
  ```bash
  promptfoo eval -c benchmarks/promptfoo-ocr/promptfooconfig.yaml -o reports/report-lxc-ollama-ocr-promptfoo-$(date +%Y%m%d-%H%M%S).json
  ```
- **Test di Verifica Reale**:
  ```bash
  ls -lh reports/report-lxc-ollama-ocr-promptfoo-*.json
  ```
  *Criterio di successo*: Generazione del file report con esito PASS/FAIL per ciascuna asserzione (accuratezza, layout tabella, JSON).

---

### Fase 6: Avvio Dashboard Web Interattiva e Allineamento Wiki
- **Azione**: Avvio dell'interfaccia web locale di Promptfoo per l'esplorazione visiva comparativa dei risultati su Safari/Chrome.
- **Comandi**:
  ```bash
  promptfoo view -p 15500
  ```
- **Test di Verifica Reale**:
  ```bash
  curl -I http://localhost:15500
  ```
  *Criterio di successo*: Risposta HTTP 200 e apertura della dashboard UI nel browser.
- **Allineamento Documentale**:
  - Aggiornamento `todo.md`
  - Validazione e rigenerazione `wiki_context.md`

---

## 💾 Stato di Ripristino (AI Save-State)
- **Fase Attiva**: Sessione interrotta su richiesta dell'utente (Stato congelato per ripresa sessione)
- **Ultima Azione Completata**: 
  - Installazione nativa Promptfoo v0.123.1 via Homebrew e creazione scaffolding `benchmarks/promptfoo-ocr/`.
  - Risoluzione bottleneck di tokenizzazione: conversione template in OpenAI Vision chat nativo con Data URI base64 inline (`PROMPTFOO_INLINE_MEDIA=true`), tempi di inferenza scesi da 5 minuti a 8-12 secondi.
  - Test-driven validation completata con successo al 100% PASS su fattura e scontrino commerciale (riconosciute tutte le voci: `CAFFE ESPRESSO`, `BRIOCHE ARTIGIANALI`, `SPREMUTA D ARANCIA`, totali e tabelle Markdown).
  - Processi di background fermati e memoria VRAM di Ollama liberata al 100% (`ollama ps` vuoto).
- **Prossimo Passo Operativo**:
  - Ripresa sessione domani tramite `/resume [[promptfoo-ocr-benchmark-evaluation]]`.
  - Riavvio facoltativo della Web Dashboard: `./benchmarks/promptfoo-ocr/run_promptfoo.sh view 15500`.
  - Connessione e benchmark comparativo con l'endpoint remoto `llama-server` Vulkan su `lxc-ollama` (`http://10.10.20.33:8081/v1`).
- **Blocchi/Decisioni Pendenti**: Nessun blocco. Tutti gli artefatti, script e report persistiti nel repository.

---
title: "Piano: Integrazione Livelli di Benchmark Guidati (1, 2, 3) in GuideLLM Launcher"
type: plan
status: active
certified_for_ai: true
created_at: 2026-10-21
tags:
  - "#benchmarking"
  - "#guidellm"
  - "#llm"
  - "#ollama"
  - "#pve3"
  - "#automation"
---

# Piano: Integrazione Livelli di Benchmark Guidati (1, 2, 3) in GuideLLM Launcher

Il presente piano operativo definisce l'evoluzione dello script shell `scripts/benchmarks/run_guidellm_benchmark.sh` per integrare una selezione esplicita e guidata della profondità del benchmark LLM suddivisa in **3 Livelli**, con spiegazione interattiva a video e impostazione predefinita sul **Livello 2 (Standard Attendibile)**, prevenendo esecuzioni incontrollate da migliaia di richieste.

---

## 🗺️ Mappe Concettuali e Relazioni
- [[SCHEMA]] (Regole di governance e salvataggio del Wiki)
- [[guidellm-report-naming-pattern]] (Standard di denominazione report `report-<nodo>-<modello>-<memoria>-<dataora>.<ext>`)
- [[guidellm-benchmark-script]] (Piano originario dello script launcher)
- [[Network_Registry]] (Censimento endpoint Ollama e nodi homelab)

---

## 1. Definizione dei 3 Livelli di Benchmark

| Livello | Nome | Descrizione & Obiettivo | Parametri GuideLLM | Durata Stimata |
| :--- | :--- | :--- | :--- | :---: |
| **1** | **Smoke Test / Rapido** | Verifica connettività, funzionamento dell'endpoint e stima grezza di throughput. Ideale per test veloci post-boot o post-aggiornamento. | `--max-seconds 15`<br>`--max-requests 10`<br>`--rate 3` | **~1 – 2 min** |
| **2** | **Standard Attendibile**<br>*(Default / Raccomandato)* | **Sweet spot statistico**. Campione sufficiente per stabilizzare media, p50 e p90 con varianza <3%, senza innescare throttling termico o bloccare la macchina per ore. | `--max-seconds 30`<br>`--max-requests 30`<br>`--rate 4` | **~3 – 5 min** |
| **3** | **Approfondito / Stress Test** | Benchmark esaustivo per analisi delle code di latenza (p95, p99), saturazione massima e tenuta termica prolungata. | `--max-seconds 90`<br>`--max-requests 100`<br>`--rate 10` | **~15 – 20 min** |

---

## 2. Architettura delle Modifiche a `run_guidellm_benchmark.sh`

1. **Supporto CLI (`-l, --level <1|2|3>`)**:
   - Flag CLI per invocazioni batch e script automatizzati.
   - Override gerarchico: se l'utente fornisce manualmente `--max-seconds`, `--max-requests` o `--rate`, questi mantengono la priorità sul preset del livello.
2. **Wizard Interattivo con Menu Spiegato**:
   - Se né `--level` né parametri di limite sono passati, lo script mostra un pannello chiaro che spiega i tre livelli, i tempi stimati e l'attendibilità statistica.
   - Prompt con default: `Seleziona livello di benchmark [1-3] (default: 2): `
   - Premendo Invio senza input, viene automaticamente selezionato il **Livello 2**.
3. **Pannello di Riepilogo Pre-Lancio**:
   - Visualizzazione esplicita del livello scelto, del tempo massimo per step e del tetto massimo di richieste prima dell'avvio.

---

## 3. Fasi Operative Dettagliate (Test-Driven Protocol)

### Fase 1: Aggiornamento Argparsing e Logica Livelli in `run_guidellm_benchmark.sh` ✅
- **Esito**: Completata. Aggiunta variabile `LEVEL` con opzioni CLI `-l, --level <1|2|3>`.
- Aggiornata la guida in linea `--help` ed esempi di invocazione con i 3 livelli.

### Fase 2: Integrazione Sezione Interattiva Guidata ✅
- **Esito**: Completata. Integrato box esplicativo a colori con dettagli di funzionamento, stime temporali e trade-off statistici per ciascun livello.
- Aggiunto prompt interattivo con selezione predefinita a invio sul **Livello 2**.
- Mappatura preset con fallback automatico e preservazione degli override CLI (`--max-seconds`, `--max-requests`, `--rate`).

### Fase 3: Validazione Test-Driven (Dry-Run e Test Parametri) ✅
- **Test 3.1**: Sintassi bash verificata con `bash -n scripts/benchmarks/run_guidellm_benchmark.sh` (esito: OK, exit 0).
- **Test 3.2**: Output `--help` verificato con opzione `-l, --level` e spiegazione chiara (esito: OK).
- **Test 3.3**: Dry-run Livello 1 (`-l 1`): parametri verificati `--max-requests 10 --max-seconds 15 --rate 3` (esito: OK).
- **Test 3.4**: Dry-run Livello 2 esplicito (`-l 2`): parametri verificati `--max-requests 30 --max-seconds 30 --rate 4` (esito: OK).
- **Test 3.5**: Dry-run interattivo: premendo Invio seleziona automaticamente il Livello 2 (esito: OK).
- **Test 3.6**: Dry-run Livello 3 (`-l 3`): parametri verificati `--max-requests 100 --max-seconds 90 --rate 10` (esito: OK).
- **Test 3.7**: Dry-run override esplicito (`-l 2 --max-seconds 10`): preserva il tetto manuale di 10s (esito: OK).

### Fase 4: Smoke Test Reale Rapido (Livello 1)
- In attesa di autorizzazione per eseguire un test reale rapido (~1-2 minuti) su un modello installato su `lxc-ollama` (o localhost).

### Fase 5: Consolidamento Documentale Wiki
- Aggiornamento di `todo.md` e script canonici:
  `python3 scripts/network/validate_network.py && python3 scripts/wiki/build_wiki_context.py`

---

## 💾 Stato di Ripristino (AI Save-State)
- **Fase Attiva**: Fase 4 (Smoke Test Reale Rapido)
- **Ultima Azione Completata**: Fasi 1, 2 e 3 completate e validate al 100% con test-driven protocol su sintassi, help, preset livelli 1-2-3, fallback a invio e override manuali.
- **Prossimo Passo Operativo**: Esecuzione reale di uno smoke test rapido Livello 1 per verificare la chiusura deterministica del benchmark entro ~1-2 minuti.
- **Blocchi/Decisioni Pendenti**: Autorizzazione dell'utente per eseguire il benchmark reale di test.

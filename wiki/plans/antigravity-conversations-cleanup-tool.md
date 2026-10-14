---
title: "Piano: Tool CLI Interattivo per Pulizia Selettiva Conversazioni Antigravity"
type: plan
status: completed
certified_for_ai: true
created_at: 2026-10-14
tags:
  - "#antigravity"
  - "#automation"
  - "#maintenance"
  - "#scripting"
  - "#storage"
---

# Piano: Tool CLI Interattivo per Pulizia Selettiva Conversazioni Antigravity

Il presente piano operativo definisce l'architettura, la progettazione e l'implementazione di uno strumento CLI interattivo e modulare (`scripts/antigravity/clean_conversations.sh` e motore `clean_conversations.py`) per consentire la ricerca, la selezione temporale, il filtraggio con eccezioni e la pulizia atomica delle conversazioni storiche di Antigravity, integrando la compattazione `VACUUM` di SQLite e la reportistica di recupero storage.

Lo script è conforme agli standard del repository homelab e al pattern architetturale [[go-launcher-script-pattern]], rendendolo invocabile sia direttamente da riga di comando sia dal menu unificato `go.py`.

---

## 🗺️ Mappe Concettuali e Relazioni
- [[SCHEMA]] (Regole del Wiki, Governance e Protocollo Test-Driven)
- [[go-launcher-script-pattern]] (Standard per script auto-documentanti, CWD-independent ed eseguibili da `scripts/go.py`)
- [[Network_Registry]] / [[Storage_Registry]] (Verità infrastrutturale dell'Homelab)

---

## 1. Analisi dei Requisiti e Architettura Funzionale

### 1.1 Requisiti Funzionali
1. **Selezione Progetto / Workspace**:
   - Rilevamento automatico dei workspace presenti in `~/.gemini/antigravity/conversation_summaries.db`.
   - Prompt interattivo con autocompletamento o menu numerato dei progetti disponibili (es. `k8s-lab`, `pindaroli-arr-helm`, o tutti), con default impostato su `k8s-lab`.
2. **Finestra Temporale Dinamica (Inizio e Fine)**:
   - Richiesta in input di `Data Inizio` (es. data più recente o inizio finestra, formato `YYYY-MM-DD`, `YYYY-MM-DD HH:MM` o alias come `now`, `today`, `1m`).
   - Richiesta in input di `Data Fine` (data limite nel passato, più vecchia dell'inizio, es. `2026-01-01` o `start`).
   - Algoritmo di normalizzazione automatica: lo script ordina cronologicamente le due date per definire l'intervallo chiuso `[data_min, data_max]`, proteggendo l'utente da inversioni involontarie di input.
3. **Elenco Numerato con Metadati Completi**:
   - Presentazione a schermo di una lista tabellare numerata `[1]`, `[2]`, ... `[N]`.
   - Per ogni elemento: Data/Ora ultima attività, Titolo/Preview, ID sessione troncato, Step count, Dimensione stimata su disco (MB).
   - Riepilogo sintetico del totale sessioni candidate e volume storage occupato.
4. **Gestione Flessibile delle Eccezioni**:
   - Domanda interattiva: `Ci sono eccezioni da NON cancellare? (yes/no) [default: no]`.
   - In caso affermativo (`yes` / `y` / `s` / `si`):
     - Accetta una lista di indici separati da virgola o intervalli (es. `2, 5, 8-12`).
     - Esclude le conversazioni corrispondenti dal set di cancellazione.
     - Mostra a video l'elenco finale ricalcolato delle sole conversazioni che verranno effettivamente eliminate.
   - In caso negativo (`no` / `n`): tutti gli elementi dell'elenco iniziale procedono verso la fase successiva.
5. **Conferma Finale e Protezione Anti-Disastro**:
   - Protezione rigida: la sessione corrente di Antigravity (estratta da variabile d'ambiente o blacklist) non può MAI essere cancellata.
   - Richiesta di conferma esplicita prima di qualsiasi azione distruttiva (`Digitare 'yes' per confermare: `).
6. **Procedura di Pulizia Atomica Collaudata**:
   - Creazione di backup preventivo `conversation_summaries.db.bak_<timestamp>`.
   - Rimozione selettiva su disco di:
     - `~/.gemini/antigravity/conversations/<id>.db` e `.pb`
     - `~/.gemini/antigravity/brain/<id>/`
     - `~/.gemini/antigravity/annotations/<id>.pbtxt`
   - Rimozione transazionale dei record da `conversation_summaries` e `conversations_fts`.
   - Esecuzione `VACUUM` di SQLite per rilasciare i blocchi fisici al file system.
   - Esecuzione `PRAGMA integrity_check` per validare l'assenza di corruzione.
7. **Reportistica Finale e Statistiche**:
   - Numero esatto di conversazioni eliminate.
   - Spazio fisico liberato (MB e GB).
   - Dimensione iniziale e finale di `conversation_summaries.db`.
   - Esito del test di integrità.

---

## 2. Struttura dei Componenti e File

```text
scripts/antigravity/
├── clean_conversations.sh    # Wrapper eseguibile Bash conforme a go-launcher-script-pattern
└── clean_conversations.py    # Motore logico Python (SQLite, I/O interattivo, calcolo storage)
```

### 2.1 Standard Go-Launcher Script (`clean_conversations.sh`)
```bash
#!/usr/bin/env bash
# Pulizia selettiva e compattazione conversazioni storiche Antigravity

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"
cd "$ROOT_DIR"

python3 "$SCRIPT_DIR/clean_conversations.py" "$@"
```

---

## 3. Fasi Operative di Implementazione

### Fase 1: Creazione della Directory e del Motore Python
- Creazione di `scripts/antigravity/clean_conversations.py`.
- Implementazione del parser date flessibile (supporto `YYYY-MM-DD`, `YYYY-MM-DD HH:MM:SS`, alias `now`, `today`, `Xm`, `Xd`).
- Implementazione della query parametrizzata a `conversation_summaries.db` con join logico verso le cartelle disco.
- Implementazione del parsing della lista di indici/eccezioni (inclusi range come `3-7`).

### Fase 2: Creazione del Wrapper Shell e Integrazione Launcher
- Creazione di `scripts/antigravity/clean_conversations.sh` con permessi di esecuzione (`chmod +x`).
- Aggiunta della riga di descrizione standard per la compatibilità con `scripts/go.py`.
- Aggiornamento della lista `in_use_by` in `wiki/patterns/go-launcher-script-pattern.md`.

### Fase 3: Test e Validazione Funzionale (Dry-Run & Test Mode)
- Aggiunta dell'opzione `--dry-run` al motore Python per consentire la simulazione completa senza cancellazione effettiva.
- Test interattivo con selezione di un intervallo fittizio ed esclusione tramite eccezioni.
- Verifica del corretto filtraggio e calcolo delle metriche di spazio.

---

## 4. Matrice di Sicurezza e Protezioni Anti-Errore

| Rischio | Meccanismo di Protezione Implementato |
| :--- | :--- |
| **Cancellazione sessione attiva** | Rilevamento della sessione corrente ed esclusione tassativa hardcoded. |
| **Inversione date inizio/fine** | Ordinamento automatico `min(d1, d2)` e `max(d1, d2)` con log esplicito. |
| **Corruzione del database durante delete** | Backup preventivo obbligatorio `.bak_<timestamp>` prima di ogni transazione. |
| **Input errato nelle eccezioni** | Validazione sintattica degli indici con feedback visivo e riesame lista prima del proceed. |
| **Cancellazione accidentale senza conferma** | Richiesta digitazione stringa esatta `yes`; abort immediato su qualsiasi altro input. |

---

## 💾 Stato di Ripristino (AI Save-State)
- **Fase Attiva**: Piano Completato con Successo ✅
- **Ultima Azione Completata**: Realizzazione e validazione di `scripts/antigravity/clean_conversations.sh` e `clean_conversations.py` con test dry-run, filtro eccezioni e integrazione `go.py`.
- **Prossimo Passo Operativo**: Nessuno. Lo strumento è pienamente operativo e integrato.
- **Blocchi/Decisioni Pendenti**: Nessuno. Tool pronto all'uso.

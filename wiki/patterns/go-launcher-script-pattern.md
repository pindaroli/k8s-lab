---
title: "Pattern: Go Launcher Script Integration"
type: pattern
status: active
certified_for_ai: true
date: 2026-09-11
tags:
  - "#pattern"
  - "#automation"
  - "#scripting"
in_use_by:
  - "scripts/infrastructure/shutdown_k8s.sh"
  - "scripts/infrastructure/startup_k8s.sh"
---

# Pattern: Go Launcher Script Integration

Questo pattern definisce lo standard architetturale per scrivere script (`.sh` o `.py`) all'interno del repository in modo che siano automaticamente scoperti, correttamente etichettati e perfettamente eseguibili tramite il launcher interattivo globale `scripts/go.py`.

## 📌 Contesto e Motivazione
Il progetto utilizza uno script Python (`scripts/go.py`) che funge da orchestratore e menu interattivo. Lo script:
1. Naviga la cartella `scripts/` e sottocartelle.
2. Trova i file eseguibili (`+x`).
3. Legge il file testualmente per estrarrne una descrizione.
4. Esegue il file selezionato **mantenendo la working directory originaria da cui l'utente ha lanciato il launcher**.

Per evitare errori di path (specialmente con strumenti come Ansible che dipendono strettamente dalla root directory del progetto), ogni script deve essere "Self-Aware" (consapevole della propria posizione) e auto-documentante.

## 🛠️ Implementazione (Regole del Pattern)

Ogni nuovo script inserito in `scripts/` DEVE rispettare la seguente struttura:

### 1. Intestazione e Descrizione (Per il Menu)
Il launcher legge la riga immediatamente successiva allo shebang per ricavare la descrizione da mostrare a menu.
- **Regola**: La seconda riga deve essere un commento (`#`) che descrive l'azione in modo sintetico.

```bash
#!/usr/bin/env bash
# Script per avviare il cluster Kubernetes in sicurezza.
```

### 2. Risoluzione Dinamica del Contesto (CWD Independence)
Lo script deve calcolare il percorso assoluto della root del progetto e forzare il context (`cd`) prima di eseguire qualsiasi comando operativo.

- **Snippet Standard (Bash)**:
```bash
# Risoluzione dinamica della directory di root del repository
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"  # Adatta i '../' in base alla profondità
cd "$ROOT_DIR" || exit 1
```

- **Snippet Standard (Python)**:
```python
import os

# Risoluzione dinamica della root
SCRIPT_DIR = os.path.dirname(os.path.realpath(__file__))
ROOT_DIR = os.path.abspath(os.path.join(SCRIPT_DIR, "..", "..")) # Adatta la profondità
os.chdir(ROOT_DIR)
```

### 3. Permessi di Esecuzione
Lo script `go.py` filtra i file utilizzando `os.X_OK`.
- **Regola**: Dopo la creazione, è obbligatorio eseguire `chmod +x` sullo script, altrimenti non sarà visibile nel menu.

## ✅ Esempio Pratico

```bash
#!/usr/bin/env bash
# Esegue il backup di emergenza del database principale.

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"
cd "$ROOT_DIR" || exit 1

ansible-playbook -i ansible/inventory.ini ansible/playbooks/backup.yml
```

---
title: "Riorganizzazione Script Principali e Aggiornamento go.py"
status: archived
certified_for_ai: false
resolved: true
resolved_at: 2026-07-05
date: 2026-07-01
tags:
  - "#scripts"
  - "#refactoring"
  - "#plan"
---

# Piano: Riorganizzazione Script Principali e Aggiornamento go.py

Questo piano descrive la ristrutturazione della cartella `scripts/` principale, raggruppando i file per ambito d'azione e aggiornando il launcher interattivo `go.py` affinché scansioni ricorsivamente le nuove cartelle.

## 🗺️ Nuova Struttura Proposta per `scripts/`

Il launcher interattivo `scripts/go.py` rimarrà nella posizione originale per preservare l'operatività del comando `./scripts/go.py`. Gli altri script verranno divisi in queste sottocartelle:

```text
scripts/
├── go.py                       # Launcher principale (aggiornato per scansione ricorsiva)
├── network/                    # Script e test relativi alla rete e a rete.json
├── opnsense/                   # Diagnostica ed utility specifiche di OPNsense
├── kubernetes/                 # Script relativi al cluster K8s/Talos
├── storage/                    # Sincronizzazione ed analisi ZFS/oliraid
├── infrastructure/             # Gestione lab, backup, spegnimento e snapshot
├── wiki/                       # Manutenzione della documentazione
└── security/                   # Controlli di sicurezza e SOPS
```

## 🌐 Configurazione Variabili d'Ambiente Centralizzate

Elimineremo tutti i calcoli di percorso relativi (`../` o `../../`) all'interno degli script, sostituendoli con riferimenti diretti alle seguenti variabili d'ambiente:
*   `RETE_JSON_PATH`: Percorso assoluto del file `rete.json`.
*   `STORAGE_JSON_PATH`: Percorso assoluto del file `storage.json`.

Le variabili verranno configurate in due posti per massima sicurezza:
1.  **In `~/.zshrc`**: Inserimento tramite export globale per consentire l'esecuzione diretta degli script in qualsiasi terminale utente.
2.  **In `scripts/go.py`**: Iniezione automatica nel dizionario `env` di esecuzione per garantire il funzionamento anche nei terminali non interattivi o script automatizzati che non caricano `~/.zshrc`.

## 🛠️ Modifiche ai Singoli Script

### 1. File del Profilo Shell
*   **`~/.zshrc`**: Aggiunta delle righe:
    ```bash
    export RETE_JSON_PATH="/Users/olindo/prj/k8s-lab/rete.json"
    export STORAGE_JSON_PATH="/Users/olindo/prj/k8s-lab/storage.json"
    ```

### 2. Modifiche a `go.py`
*   **`scripts/go.py`**: Iniezione automatica delle variabili nell'ambiente di esecuzione:
    ```python
    if "RETE_JSON_PATH" not in env:
        env["RETE_JSON_PATH"] = os.path.abspath(os.path.join(SCRIPT_DIR, '..', 'rete.json'))
    if "STORAGE_JSON_PATH" not in env:
        env["STORAGE_JSON_PATH"] = os.path.abspath(os.path.join(SCRIPT_DIR, '..', 'storage.json'))
    ```

### 3. Script Shell `.sh`
Tutti gli script shell elencati leggeranno le variabili d'ambiente sollevando un errore bloccante se non sono impostate:
*   **`scripts/network/test_dhcp.sh`**
*   **`scripts/network/test_dns.sh`**
*   **`scripts/infrastructure/test_internet.sh`**
*   **`scripts/infrastructure/test-pve-cluster-con.sh`**
*   **`scripts/infrastructure/setup_postgres_dbs.sh`**

Esempio di codice sostitutivo:
```bash
if [ -z "${RETE_JSON_PATH:-}" ]; then
  echo "❌ Errore: RETE_JSON_PATH non impostata nell'ambiente!" >&2
  exit 1
fi
RETE_JSON="$RETE_JSON_PATH"
```

### 4. Script Python `.py`
Tutti gli script Python leggeranno le variabili d'ambiente tramite `os.environ`:
*   **`scripts/opnsense/check_opnsense_plugins.py`**
*   **`scripts/kubernetes/update_talos_storage.py`**
*   **`scripts/wiki/standardize_wiki_metadata.py`**
*   **`scripts/wiki/build_wiki_context.py`**
*   **`scripts/utils/common.py`** (percorso base globale)

Esempio di codice sostitutivo:
```python
rete_path = os.environ.get("RETE_JSON_PATH")
if not rete_path:
    print("Error: RETE_JSON_PATH environment variable not set.")
    sys.exit(1)
```

---

## 💾 Stato di Ripristino (AI Save-State)
- **Fase Attiva**: Archiviato
- **Ultima Azione Completata**: Riorganizzazione degli script principali conclusa con successo. Archiviazione eseguita in data 2026-07-05.
- **Prossimo Passo Operativo**: Nessuno.
- **Blocchi/Decisioni Pendenti**: Nessuno.

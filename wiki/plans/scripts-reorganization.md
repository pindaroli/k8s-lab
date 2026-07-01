---
title: "Riorganizzazione Script Principali e Aggiornamento go.py"
status: active
certified_for_ai: true
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
│   ├── validate_network.py
│   ├── analyze_ips.py
│   ├── update_disks_rete.py
│   ├── test_dns.sh
│   ├── test_dhcp.sh
│   └── verify_network_fix.sh
├── opnsense/                   # Diagnostica ed utility specifiche di OPNsense
│   ├── check_opnsense_plugins.py
│   ├── update_qbittorrent_plugins.py
│   └── check_qbittorrent_net.sh
├── kubernetes/                 # Script relativi al cluster K8s/Talos
│   ├── check_k8s.py
│   └── update_talos_storage.py
├── storage/                    # Sincronizzazione ed analisi ZFS/oliraid
│   ├── sync_storage.py
│   └── analyze_special_frag.py
├── infrastructure/             # Gestione lab, backup, spegnimento e snapshot
│   ├── check_lab.py
│   ├── test-pve-cluster-con.sh
│   ├── test_internet.sh
│   ├── setup_postgres_dbs.sh
│   ├── restore_classical_snapshot.sh
│   ├── find_richest_snapshot.sh
│   ├── find_max_staging_snapshot.sh
│   ├── find_max_library_snapshot.sh
│   └── safe_sync.sh
├── wiki/                       # Manutenzione della documentazione
│   ├── build_wiki_context.py
│   └── standardize_wiki_metadata.py
├── security/                   # Controlli di sicurezza e SOPS
│   └── check-sops-encrypted.sh
└── unit-test/                  # (Rimane cartella esistente)
```

## 🛠️ Fasi del Piano

### Fase 1: Aggiornamento di `go.py`
Modificheremo `scripts/go.py` per:
1. Usare `os.walk(SCRIPT_DIR)` al posto di `os.listdir(SCRIPT_DIR)`.
2. Trovare tutti i file `.py` e `.sh` eseguibili ricorsivamente nelle sottocartelle.
3. Rappresentare il nome del file con il prefisso della cartella (es. `opnsense/check_opnsense_plugins.py`) per mantenere la leggibilità e l'ordine nel menu di selezione.
4. Escludere la cartella `unit-test/` ed eventuali directory nascoste.

### Fase 2: Creazione Cartelle e Spostamento degli Script
1. Creare le cartelle `network`, `opnsense`, `kubernetes`, `storage`, `infrastructure`, `wiki`, `security` sotto `scripts/`.
2. Spostare i rispettivi file tramite `git mv` per preservare la cronologia.
3. Archiviare o eliminare script di test temporanei orfani se presenti.

### Fase 3: Aggiornamento Riferimenti nel Progetto
1. Aggiornare le regole in `.agents/AGENTS.md` se fanno riferimento a percorsi assoluti (es. `scripts/validate_network.py` diventerà `scripts/network/validate_network.py`).
2. Aggiornare eventuali cronjob o script esterni che invocano questi strumenti.

---

## 💾 Stato di Ripristino (AI Save-State)
- **Fase Attiva**: Pianificazione completata.
- **Ultima Azione Completata**: Stesura del piano di riorganizzazione degli script.
- **Prossimo Passo Operativo**: Ottenere l'approvazione del piano da parte dell'utente per avviare la Fase 1 (aggiornamento `go.py`) e poi la Fase 2.
- **Blocchi/Decisioni Pendenti**: Approvazione dell'utente.

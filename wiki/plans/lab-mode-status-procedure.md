---
title: "Piano: Procedura Diagnostica di Stato Homelab (lab_mode_status.sh)"
type: plan
status: completed
certified_for_ai: false
created_at: 2026-10-25
completed_at: 2026-10-25
tags:
  - "#plan"
  - "#automation"
  - "#diagnostics"
  - "#homelab-status"
  - "#bash"
---

# Piano: Procedura Diagnostica di Stato Homelab (`lab_mode_status.sh`)

Il presente piano definisce la progettazione e implementazione della procedura shell [`scripts/infrastructure/lab_mode_status.sh`](file:///Users/olindo/prj/k8s-lab/scripts/infrastructure/lab_mode_status.sh) per rilevare ed esporre in modo rapido, non distruttivo e deterministico lo stato operativo dell'intero Homelab (`FULL`, `ECO`, `OFF` o `INCONGRUENTE`). In caso di stato incongruente, lo script dettaglia in testo semplice le contraddizioni che portano alla diagnosi.

---

## 🏛️ Pattern Architetturali Adottati

1. **[[go-launcher-script-pattern]]**:
   - Intestazione descrittiva alla riga 2, risoluzione autonoma di `ROOT_DIR` (CWD independence), permessi `chmod +x` e inclusione nel menu interattivo [`scripts/go.py`](file:///Users/olindo/prj/k8s-lab/scripts/go.py).
2. **KISS & Read-Only Probe Execution**:
   - Esecuzione non invasiva: timeout TCP brevi (1s) eseguiti in parallelo, query DNS reale su Unbound OPNsense e ispezione dei container Docker locali su Mac Studio (OrbStack).
   - Zero notifiche esterne (nessun invio Telegram/Email non necessario) per massima reattività (<2 secondi di esecuzione complessiva).
   - Exit code sempre `0` per garantire compositività con altri script e automazioni.

---

## 🏗️ Matrice degli Stati e Condizioni di Coerenza

| Componente | Modalità `FULL` | Modalità `ECO` | Modalità `OFF` |
| :--- | :--- | :--- | :--- |
| **Storage (TrueNAS)** `10.10.20.50` | **ONLINE** (Porte 22, 443/80) | **ONLINE** (Porte 22, 443/80) | **OFFLINE** (Porte non raggiungibili) |
| **Hypervisor (PVE)** `pve1, pve2, pve3` | **ONLINE** (3/3 Porte 8006/22) | **OFFLINE** (3/3 Porte chiuse) | **OFFLINE** (3/3 Porte chiuse) |
| **Kubernetes (Talos)** VIP `10.10.20.55` / `10.10.20.56` | **ONLINE** (Porta 6443 / Ingress 443) | **OFFLINE** (Porte chiuse) | **OFFLINE** (Porte chiuse) |
| **Failover OrbStack (Mac Studio)** | **STANDBY** (Container fermi) | **STANDBY** (Container fermi) | **ONLINE** (Container attivi su Mac) |
| **DNS Unbound** (`home-internal`) | `10.10.20.56` (K8s Ingress) | `10.10.20.50` (TrueNAS) | `10.10.20.100` (Mac Studio) |
| **DNS Unbound** (`mcp`, AI/log) | `10.10.20.50` (TrueNAS) | `10.10.20.50` (TrueNAS) | `10.10.20.100` (Mac Studio) |

### ⚠️ Regole di Incongruenza (Contraddizioni)
Qualsiasi deviazione dalla tabella sopra viene diagnosticata come **`INCONGRUENTE`**. Tra le contraddizioni identificate e spiegate in testo semplice:
- **Asimmetria Compute**: Nodi PVE parzialmente accesi (es. solo 1 o 2 nodi online su 3).
- **Compute senza Storage**: PVE o K8s accesi mentre TrueNAS è spento (incoerenza storage/NFS).
- **K8s Incompleto**: PVE accesi ma K8s VIP `10.10.20.55:6443` o Ingress `10.10.20.56:443` non rispondono.
- **Split-Brain OrbStack/TrueNAS**: Container di failover OrbStack attivi su Mac Studio mentre TrueNAS è online.
- **Failover Mancante**: TrueNAS è offline ma i container di failover OrbStack su Mac Studio sono spenti.
- **Disallineamento DNS vs Hardware**:
  - DNS punta a K8s VIP ma K8s è offline.
  - DNS punta a TrueNAS ma TrueNAS è offline.
  - DNS punta a OrbStack ma TrueNAS o PVE sono accesi.
  - DNS asimmetrico (`home-internal` punta a un backend e `mcp` a un backend non compatibile).

---

## 🖥️ Specifiche di Output

1. **Stato Coerente**:
   - Una sola riga essenziale:
     - `🟢 STATO: FULL`
     - `🟡 STATO: ECO`
     - `⚫ STATO: OFF`
2. **Stato Incongruente**:
   - Banner iniziale seguito da righe di contraddizione in testo semplice, nessun suggerimento di fix:
     ```text
     ⚠️ STATO: INCONGRUENTE
     - TrueNAS è acceso ma il DNS home-internal punta a Mac Studio OrbStack (10.10.20.100)
     - I nodi PVE sono parzialmente accesi (pve1: UP, pve2: DOWN, pve3: DOWN)
     ```
3. **Flag Opzionali**:
   - `--raw`: stampa solo la parola `FULL`, `ECO`, `OFF` o `INCONGRUENTE`.
   - `-v` / `--verbose`: stampa l'esito di ciascun singolo probe TCP/DNS/Docker per ispezione approfondita.

---

## 📋 Fasi Operative di Implementazione

### FASE 1: Redazione del Piano e Allineamento Task
- [x] Raccolta requisiti e intervista architetturale completata via `/grill-me`.
- [x] Creazione del documento di piano `wiki/plans/lab-mode-status-procedure.md`.
- [x] Sincronizzazione task in `todo.md`.

### FASE 2: Sviluppo di `scripts/infrastructure/lab_mode_status.sh`
- [x] Implementazione dei probe paralleli con `nc` (timeout 1s) per TrueNAS, PVE, K8s VIP.
- [x] Implementazione del controllo DNS Unbound con `dig` (o `nslookup` fallback).
- [x] Implementazione del controllo Docker locale per container OrbStack.
- [x] Implementazione del motore di valutazione regole di congruenza e formattazione contraddizioni.
- [x] Supporto argomenti `--raw` e `-v`/`--verbose`.
- [x] Assegnazione permessi di esecuzione `chmod +x`.

### FASE 3: Integrazione in `scripts/go.py` e Collaudo Test-Driven
- [x] Aggiunta voce dedicata nel menu di `scripts/go.py` (rilevamento automatico script eseguibile `[9] lab_mode_status.sh`).
- [x] Test di esecuzione reale dello script nello stato corrente dell'infrastruttura (`🟡 STATO: ECO`).
- [x] Verifica del flag `--raw` (`ECO`) e `-v` (dettaglio completo probe).
- [x] Verifica che l'exit code sia `0`.

### FASE 4: Validazione e Chiusura
- [x] Esecuzione validazione e rigenerazione contesto:
  `python3 scripts/network/validate_network.py && python3 scripts/wiki/build_wiki_context.py`
- [x] Aggiornamento `todo.md` e save-state.

---

## 💾 Stato di Ripristino (AI Save-State)
- **Fase Attiva**: [x] COMPLETATO (100% Task Eseguiti e Convalidati)
- **Ultima Azione Completata**: Implementato `scripts/infrastructure/lab_mode_status.sh`, integrato in `go.py`, collaudato con successo e compilato il contesto Wiki.
- **Prossimo Passo Operativo**: Nessuno.
- **Blocchi/Decisioni Pendenti**: Nessuno.

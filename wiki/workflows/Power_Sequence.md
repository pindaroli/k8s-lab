---
title: "Workflow: Safe Shutdown & Startup Sequence"
last_updated: "2026-10-19"
confidence: "High"
tags:
  - "#workflow"
  - "#maintenance"
  - "#automation"
  - "#power"
  - "#wol"
---

# Safe Shutdown & Startup (Rack Power Orchestration)

Questa procedura garantisce la coerenza dei dati e l'idempotenza assoluta durante lo spegnimento o l'accensione dell'intero rack Homelab, consentendo la transizione deterministica verso la modalità desiderata **partendo da qualsiasi configurazione iniziale** (Rack Spento, Modalità Eco o Full Mode).

---

## 🧭 Matrice delle Modalità Dichiarative Idempotenti (State-Driven)

L'infrastruttura è governata da tre entrypoint principali che eseguono la convergenza dichiarativa:

| Modalità Target | Script Eseguibile | Mattoni Atomici Eseguiti | Storage TrueNAS | Compute (PVE + K8s) | Notifiche Start & Stop |
| :--- | :--- | :--- | :---: | :---: | :--- |
| **Full Lab (Tutto Attivo)** | [`lab_mode_full.sh`](file:///Users/olindo/prj/k8s-lab/scripts/infrastructure/lab_mode_full.sh) | 1. `ensure_storage_on`<br>2. `ensure_compute_on` | **ONLINE** (ZFS sani) | **ONLINE** (3 nodi Ready, uncordoned) | Start: Telegram<br>Stop: TG + Email HTML |
| **Eco Lab (Solo TrueNAS)** | [`lab_mode_eco.sh`](file:///Users/olindo/prj/k8s-lab/scripts/infrastructure/lab_mode_eco.sh) | 1. `ensure_storage_on`<br>2. `ensure_compute_off` | **ONLINE** (Servarr 24/7) | **OFFLINE** (PVE e K8s spenti) | Start: Telegram<br>Stop: TG + Email HTML |
| **Rack Dark (Tutto Spento)** | [`lab_mode_off.sh`](file:///Users/olindo/prj/k8s-lab/scripts/infrastructure/lab_mode_off.sh) | 1. `ensure_compute_off`<br>2. `ensure_storage_off` | **OFFLINE** (Bare metal spento) | **OFFLINE** (PVE e K8s spenti) | Start: Telegram<br>Stop: TG + Email HTML |

---

## 1. Descrizione Dettagliata dei Comandi

### 1.1 Full Homelab (`lab_mode_full.sh`)
Porta l'intero rack a regime operativo completo.
```bash
./scripts/infrastructure/lab_mode_full.sh
```
**Regola di Sequenza & Checkpoint**:
1. **Hard Gate Storage (`ensure_storage_on.yml`)**:
   - Probe porta 22 su TrueNAS (`10.10.20.50`): invio WoL solo se spento (altrimenti `SKIP WoL`).
   - Attesa SSH (22) e WebUI (443).
   - Validazione ZFS (`zpool status -x`: `all pools are healthy`).
   - Verifica servizi (3000 Homepage, 8080 qBittorrent, 8096 Jellyfin) ed export NFS.
   - *Se TrueNAS fallisce o non è sano, la procedura scatta in errore immediato e NON sveglia Proxmox*.
2. **Gate Compute (`ensure_compute_on.yml`)**:
   - WoL mirato solo ai nodi Proxmox spenti (`pve1`, `pve2`, `pve3`).
   - Verifica via SSH dello stato delle VM Talos (`1300`, `2300`, `3200`): se `stopped`, avvio automatico (`qm start`).
   - Attesa porte API Talos (50000) e API Server K8s (VIP `10.10.20.55:6443`).
   - **Sync Barrier**: attesa contemporanea `Ready=True` su tutti e 3 i nodi Talos + 10s stabilizzazione CNI Flannel.
   - **Uncordon Atomico Parallelo**: apertura bilanciata dello scheduling (preservando taint protettivo su `cp-03`).
   - Health-Check Ingress Traefik (VIP `10.10.20.56:443`) e cluster PostgreSQL CNPG.

---

### 1.2 Modalità Eco (`lab_mode_eco.sh`)
Mantiene attivo solo lo storage server TrueNAS SCALE per i carichi leggeri (Servarr, download qBittorrent, streaming Jellyfin), spegnendo gli hypervisor di calcolo Proxmox VE e Kubernetes per ridurre consumi e usura.
```bash
./scripts/infrastructure/lab_mode_eco.sh
```
**Regola di Sequenza**:
1. Esegue `ensure_storage_on.yml` per garantire che TrueNAS sia operativo e sano (WoL solo se era spento).
2. Esegue `ensure_compute_off.yml` per disattivare K8s Talos e gli hypervisor PVE (se già spenti, skip immediato in pochi secondi).

---

### 1.3 Spegnimento Totale del Rack (`lab_mode_off.sh`)
Arresta l'intero rack in sicurezza per portare l'assorbimento a standby / zero watt (safe per manutenzione PDU o spegnimento prolungato).
```bash
./scripts/infrastructure/lab_mode_off.sh
```
**Regola di Sequenza**:
1. Esegue prima `ensure_compute_off.yml`:
   - Cordon K8s e checkpoint database PostgreSQL CNPG (`CHECKPOINT;`).
   - `talosctl shutdown` e verifica porte chiuse.
   - Shutdown ACPI satelliti Proxmox (`pve3`, `pve2`) e successivamente del master (`pve1`).
   - Attesa porte 22 e 8006 PVE STOPPED (tutti i client NFS rilasciano i lock in modo pulito).
2. Solo a Compute spento, esegue `ensure_storage_off.yml`:
   - Flush preventivo I/O ZFS (`sync`).
   - Shutdown controllato TrueNAS (`shutdown -h now`).
   - Verifica chiusura porta SSH 22 STOPPED.

---

## 🛡️ Gestione Errori e Notifiche
- **Pattern Architetturale**: [[hierarchical-automation-alerting-pattern]] (Zero start emails, single summary success report per procedure root, fail-fast incondizionato su tutti gli errori).
- **Gestore Scope Gerarchico**: [`scripts/infrastructure/procedure_scope.sh`](file:///Users/olindo/prj/k8s-lab/scripts/infrastructure/procedure_scope.sh) (Governa il ciclo di vita e la variabile d'ambiente `HOMELAB_PARENT_PROCEDURE`).
- **Libreria Notifiche & I/O**: [`scripts/infrastructure/utils.sh`](file:///Users/olindo/prj/k8s-lab/scripts/infrastructure/utils.sh) (Invio Telegram bot e Email HTML via Gmail SMTP con caricamento credenziali protette da SOPS).
- **Zero Plaintext Secrets**: tutte le credenziali (Telegram bot/chat ID e credenziali SMTP Gmail) vengono caricate dinamicamente in memoria tramite `sops` dai file cifrati in `secrets-sops/`.
- **Trap di Errore**: in caso di fallimento di qualsiasi comando o checkpoint, lo script bash intercetta l'uscita anomala (`trap ERR`), invia un alert immediato su Telegram e inoltra un'email HTML con **allegato il file di log completo della sessione** salvato in `logs/automation/`.

---

## 🔗 Relazioni & Riferimenti
- Piano Operativo: [[homelab-idempotent-mode-scripts]]
- Pattern Notifiche: [[hierarchical-automation-alerting-pattern]]
- Pattern Launcher CLI: [[go-launcher-script-pattern]]
- Launcher Interattivo: [`scripts/go.py`](file:///Users/olindo/prj/k8s-lab/scripts/go.py)
- Utilità WoL: [`wake_node.py`](file:///Users/olindo/prj/k8s-lab/scripts/network/wake_node.py)
- Componenti: [[TrueNAS]], [[Talos_Cluster]], [[OPNsense]], [[sops-secret-sovereignty]]

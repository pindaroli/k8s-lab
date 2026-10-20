---
title: "Piano: Bonifica Script Obsoleti e Riallineamento Diagnostica all'Architettura Homelab Corrente"
type: plan
status: active
certified_for_ai: true
created_at: 2026-10-19
last_updated: 2026-10-19
tags:
  - "#plan"
  - "#scripts"
  - "#maintenance"
  - "#diagnostics"
  - "#truenas"
  - "#kubernetes"
---

# Piano: Bonifica Script Obsoleti e Riallineamento Diagnostica all'Architettura Homelab Corrente

Questo piano governa la pulizia degli script obsoleti/one-off in `scripts/` e il riallineamento degli script di diagnostica e automazione (`check_lab.py`, `check_k8s.py`, `test_internet.sh`, `sync_storage.py`, `go.py`, `README.md`) all'architettura corrente del laboratorio:
- **TrueNAS SCALE Bare-Metal** (`10.10.20.50`) con pool ZFS `oliraid` e `stripe`.
- **Proxmox Backup Server (PBS)** su VM KVM TrueNAS (`10.10.10.100:8007`).
- **Stack Servarr, Normalizer e Flotta MCP** migrati definitivamente su Docker TrueNAS (`10.10.20.50`).
- **PVE1** rinominato da `pve` a `pve1` (`10.10.10.11`) e **PVE3** (`10.10.10.31`) con LXC `lxc-ollama` (CT 300) e `lxc-steam` (CT 301).

---

## 🗺️ Mappe Concettuali e Relazioni
- [[TrueNAS]] (Storage bare-metal `10.10.20.50`, Docker host per Servarr e MCP, host KVM per PBS)
- [[Talos_Cluster]] (Cluster Kubernetes 3 CP senza namespace `arr`)
- [[Servarr]] (Stack media su TrueNAS Docker e `webhook-normalizer`)
- [[MCP_Platform]] (Flotta MCP su TrueNAS Docker)
- [[go-launcher-script-pattern]] (Standard per entry-point `.sh` e CWD independence in `scripts/go.py`)
- [[truenas-docker-image-updates-checker]] (Piano correlato per il wrapper `check_truenas_docker_updates.sh`)

---

## 📋 FASI OPERATIVE & PROTOCOLLO TEST-DRIVEN

### 🧹 FASE 1: Rimozione Script Obsoleti e One-Off (Sezioni 1 & 2) [COMPLETATA ✅]

#### Obiettivo
Eliminare dal repository gli script resi obsoleti dai cambi architetturali (migrazione MCP e Servarr su TrueNAS, dismissione Beets/staging, dismissione VM 1100 TrueNAS su PVE1) e gli script di test/debug one-off.

#### Azioni Completate
1. [x] Rimossi wrapper/duplicati MCP obsoleti: `scripts/talos_mcp_wrapper.py`, `scripts/arrstack-mcp/`.
2. [x] Rimossi artefatti Servarr K8s obsoleti: `scripts/kubernetes/yaml/job-normalizzation-template.yaml`, `scripts/servarr/webhook_server.py`, `scripts/opnsense/check_qbittorrent_net.sh`, `scripts/infrastructure/setup_postgres_dbs.sh`.
3. [x] Rimossi script di emergenza snapshot Beets/staging dismessi: `find_max_library_snapshot.sh`, `find_max_staging_snapshot.sh`, `find_richest_snapshot.sh`, `restore_classical_snapshot.sh`.
4. [x] Rimossi script hardware/storage one-off legacy: `scripts/network/update_disks_rete.py`, `scripts/kubernetes/update_talos_storage.py`.
5. [x] Rimossi file e cartelle temporanee/one-off: `scripts/test_common.py`, `scripts/test_import.py`, `scripts/mac-network-fix/`, `scripts/infrastructure/safe_sync.sh`, `scripts/servarr/check_raw_folders.py`, `scripts/servarr/check_videots.py`, `scripts/opnsense/update_qbittorrent_plugins.py`, `scripts/network/verify_network_fix.sh`, `scripts/security/sync_hermes_talosconfig.sh`.

#### 🛑 Checkpoint & Test di Verifica FASE 1
- [x] Verifica tramite `git status -s scripts/` (21 file obsoleti rimossi).
- [x] Verifica esecuzione menu `python3 scripts/go.py` senza errori di scansione.

---

### 🖥️ FASE 2: Riallineamento `scripts/infrastructure/check_lab.py`

#### Obiettivo
Aggiornare lo script di diagnostica globale del Data Center (`check_lab.py`) affinché rifletta l'architettura fisica e virtuale attuale.

#### Azioni
1. **Nodi Proxmox**: Aggiornare il dizionario `PVE_NODES` sostituendo la chiave legacy `"pve1/pve"` con `"pve1": "10.10.10.11"`.
2. **Core Storage & Services**:
   - Rimuovere la ricerca su Proxmox di `vmid == 1100` (TrueNAS non è più una VM su PVE1) e `vmid == 1400` (PBS non è più un LXC su PVE1).
   - Verificare **TrueNAS Bare Metal (`10.10.20.50`)** tramite Ping + controllo stato pool ZFS (`oliraid`, `stripe`) via SSH passwordless (`ssh -o BatchMode=yes olindo@10.10.20.50 "/sbin/zpool status -x"`).
   - Verificare **Proxmox Backup Server (`10.10.10.100`)** tramite Ping + verifica raggiungibilità porta TCP `8007` (Web UI/API PBS).
   - Aggiungere verifica stato dei workload LXC su `pve3` dalle risorse cluster Proxmox: `CT 300 (lxc-ollama)` e `CT 301 (lxc-steam)` (considerando regolare che uno dei due sia `running` e l'altro `stopped` per mutua esclusione GPU Radeon 890M).

#### 🛑 Checkpoint & Test di Verifica FASE 2
- [ ] Esecuzione `./scripts/infrastructure/check_lab.sh` con segnalazione `ONLINE` per TrueNAS Bare Metal (`10.10.20.50`) e PBS (`10.10.10.100`), senza falsi errori su `VM 1100` o `LXC 1400`.

---

### ☸️ FASE 3: Riallineamento `scripts/kubernetes/check_k8s.py`

#### Obiettivo
Aggiornare la diagnostica Kubernetes (`check_k8s.py`) ai namespace realmente attivi nel cluster Talos.

#### Azioni
1. Rimuovere `"arr"` da `CRITICAL_NAMESPACES` (in quanto lo stack Servarr risiede stabilmente su TrueNAS Docker).
2. Aggiornare `CRITICAL_NAMESPACES` includendo i namespace core effettivamente in produzione:
   `["kube-system", "traefik", "metallb-system", "cert-manager", "cnpg-system", "monitoring", "homepage"]`.

#### 🛑 Checkpoint & Test di Verifica FASE 3
- [ ] Esecuzione `./scripts/kubernetes/check_k8s.sh` senza falsi warning `Namespace arr: NON TROVATO o vuoto`.

---

### 🌐 FASE 4: Correzione `test_internet.sh` e Pulizia `sync_storage.py`

#### Obiettivo
Rendere `test_internet.sh` autonomo (CWD-independent) e rimuovere residui di password legacy da `sync_storage.py`.

#### Azioni
1. **`scripts/infrastructure/test_internet.sh`**:
   - Alla riga 11, sostituire `RETE_JSON="${RETE_JSON_PATH}"` con `RETE_JSON="${RETE_JSON_PATH:-${SCRIPT_DIR}/../../rete.json}"` per evitare l'errore `RETE_JSON_PATH: unbound variable` (`set -u`) quando lanciato direttamente o da `go.py`.
2. **`scripts/storage/sync_storage.py`**:
   - Rimuovere la variabile inutilizzata `TRUENAS_PASS = "REDACTED_SECRET"` e passare a `fetch_exports.sh` solo `[script_path, TRUENAS_IP, TRUENAS_USER]` in aderenza al **Passwordless SSH Mandate**.

#### 🛑 Checkpoint & Test di Verifica FASE 4
- [ ] Esecuzione `./scripts/infrastructure/test_internet.sh` senza variabili d'ambiente preimpostate (esito 0).
- [ ] Verifica sintattica e funzionale di `python3 scripts/storage/sync_storage.py`.

---

### 🚀 FASE 5: Rifinitura `scripts/go.py`, Descrizioni Script PVE3 e `scripts/README.md`

#### Obiettivo
Pulire il launcher interattivo `go.py` e aggiornare la documentazione della directory `scripts/`.

#### Azioni
1. **`scripts/go.py`**:
   - Rimuovere `"mac-network-fix"` da `exclude_dirs`.
   - Evitare la duplicazione nel menu dei symlink alias nella stessa cartella (es. `lab_mode_echo.sh` che punta a `lab_mode_eco.sh`), saltando i file `os.path.islink(full_path)` quando il target risiede già negli script scansionati, mantenendo `lab_mode_echo.sh` funzionante da CLI diretta.
2. **Descrizioni Script PVE3 (`pve3-gpu-*.sh`, `pve3-host-backup-pbs.sh`)**:
   - Aggiungere l'header descrittivo standard alla riga 2 di `pve3-gpu-eco.sh`, `pve3-gpu-mode.sh`, `pve3-gpu-turbo.sh` e `pve3-host-backup-pbs.sh` (specificando `[Host PVE3] ...`).
3. **`scripts/README.md`**:
   - Aggiornare la tabella e la panoramica delle sottocartelle (`antigravity`, `benchmarks`, `homepage-mcp`, `infrastructure`, `kubernetes`, `llmwiki`, `network`, `opnsense`, `ragflow`, `security`, `servarr`, `sn`, `storage`, `truenas`, `unit-test`, `utils`, `wiki`), rimuovendo i riferimenti obsoleti a `expect` e `_OLD_ARCHIVE/`.
4. **Validazione e Rigenerazione Wiki**:
   - Eseguire `python3 scripts/network/validate_network.py && python3 scripts/wiki/build_wiki_context.py`.

#### 🛑 Checkpoint & Test di Verifica FASE 5
- [ ] Verifica output `python3 scripts/go.py` (nessun duplicato `lab_mode_echo.sh` / `lab_mode_eco.sh`, tutte le voci dotate di descrizione chiara).
- [ ] Esecuzione `python3 scripts/network/validate_network.py && python3 scripts/wiki/build_wiki_context.py` con esito 0.

---

## 💾 Stato di Ripristino (AI Save-State)
- **Fase Attiva**: Fase 2 (Riallineamento `scripts/infrastructure/check_lab.py`)
- **Ultima Azione Completata**: Fase 1 completata con successo (rimossi 21 script/file obsoleti e one-off delle sezioni 1 e 2; verificato `go.py`).
- **Prossimo Passo Operativo**: Aggiornamento di `scripts/infrastructure/check_lab.py` per riflettere TrueNAS Bare Metal (`10.10.20.50`), PBS KVM (`10.10.10.100`) e LXC su PVE3 (`CT 300`, `CT 301`), seguito dal test `./scripts/infrastructure/check_lab.sh`.
- **Blocchi/Decisioni Pendenti**: In attesa di approvazione dell'utente sul piano per procedere con la Fase 2.

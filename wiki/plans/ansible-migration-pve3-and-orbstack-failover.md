---
title: "Piano: Migrazione Ansible Integrale per GPU PVE3, Failover OrbStack e Portabilità Docker per go.py"
type: plan
status: active
certified_for_ai: true
created_at: 2026-10-27
tags:
  - "#ansible"
  - "#pve3"
  - "#orbstack"
  - "#failover"
  - "#docker"
  - "#gopy"
---

# Piano: Migrazione Ansible Integrale per GPU PVE3, Failover OrbStack e Portabilità Docker per `go.py`

> **Percorso Canonico Wiki**: `wiki/plans/ansible-migration-pve3-and-orbstack-failover.md`
> **Comando di Ripresa**: `/resume [[ansible-migration-pve3-and-orbstack-failover]]`
> **Pattern Adottati**: [[go-launcher-script-pattern]], [[hierarchical-automation-alerting-pattern]], [[SCHEMA]] (§6 IaC, §11 Save-State, §12 Test-Driven Verification, §13 Wiki Context Refresh).

---

## 1. Obiettivo e Decisioni Architetturali Approvate (`/grill-me` & Sessioni successive)

L'obiettivo del piano è rendere **l'intero parco comandi del launcher `scripts/go.py` 100% Location-Independent ed eseguibile sia da un container Docker di produzione (snapshot immutabile ad ogni commit di `k8s-lab`) sia direttamente dal Mac Studio (`10.10.20.100`) come ambiente di sviluppo e test locale**, eliminando ogni dipendenza implicita dall'esecuzione fisica rigida e rimuovendo i flag esclusivi BSD/macOS (`nc -G`, `base64 -i`).

### Matrice delle Scelte Architetturali Consolidate

| # | Ambito | Decisione Approvata | Specifiche di Implementazione |
| --- | --- | --- | --- |
| **1** | **Ambiente Dual-Mode (Dev/Test su Mac & Prod in Container)** | **Working Tree Dinamico via `ROOT_DIR` e `controller_repo_root**` | Sviluppo e test eseguibili direttamente su `/Users/olindo/prj/k8s-lab` (Mac Studio) o dentro il container di produzione (snapshot del repo). I path si adattano dinamicamente in base a dove viene invocato `go.py`. |
| **2** | **Target Ansible per Mac Studio (`10.10.20.100`)** | **SSH Standard con Interpete Python Dedicato** | Censimento del gruppo `[mac_studio]` (`10.10.20.100 ansible_user=olindo ansible_python_interpreter=/usr/bin/python3`) in `ansible/inventory.ini`. Connessione SSH passwordless (`BatchMode=yes`). |
| **3** | **Gestione Energetica GPU Radeon 890M su `pve3**` | **Playbook Parametrico Unico + 3 Wrapper nel Menu `go**` | Playbook idempotente `ansible/playbooks/infrastructure/pve3_gpu_power.yml` (`gpu_mode: eco | turbo | status`) su host `10.10.10.31`. Wrapper conformi a [[go-launcher-script-pattern]]. |
| **4** | **Pulizia Script Obsoleti (`pve3-host-backup-pbs.sh`)** | **Principio KISS (Opzione B0)** | Rimozione definitiva di `scripts/infrastructure/pve3-host-backup-pbs.sh` dal menu di `go.py` e dal repository (`git rm`), in quanto ridondante rispetto alla gestione IaC e non utilizzato dalle automazioni. |
| **5** | **Migrazione Failover OrbStack e `lab_mode_{full,eco,off}.sh**` | **Playbook `orbstack_failover.yml` + Split Control/Data Plane (A1)** | Tutta la logica di failover è gestita da `ansible.builtin` e `delegate_to: truenas` (`10.10.20.50`) per i comandi di controllo, mentre i dati (`rsync`) viaggiano diretti sulla VLAN 20 tra Mac Studio e TrueNAS. Eliminato `orbstack_failover.sh`. |
| **6** | **Transizione `OFF -> FULL` senza Downtime (`lab_mode_full.sh`)** | **Due Step (C1)**: `deactivate` in `eco` (Fase 2) $\rightarrow$ `set_backend` in `full` (Fine Fase 3) | Evita errori `502 Bad Gateway` su `home-internal.pindaroli.org` durante il boot del cluster Kubernetes Talos e del VIP Traefik (`10.10.20.56`). |
| **7** | **Guardrail di Sicurezza SQLite e Health (D1)** | **Marker `.failover_active` + Check Container Running + Probe `/api/health` & `/health**` | Protezione matematica contro la sovrascrittura accidentale dei 7 database SQLite di TrueNAS durante `deactivate`. |

---

## 1.5 Mappa dei File da Creare, Modificare o Rimuovere

| Percorso File | Operazione | Scopo |
| --- | --- | --- |
| `ansible/inventory.ini` | **Modifica** | Aggiunta del gruppo `[mac_studio]` con utente e interprete Python dedicato. |
| `ansible/playbooks/infrastructure/pve3_gpu_power.yml` | **Creazione** | Playbook idempotente per gestione DPM (`auto`/`high`) e query stato iGPU Radeon 890M su `pve3` (`10.10.10.31`). |
| `ansible/playbooks/infrastructure/orbstack_failover.yml` | **Creazione** | Playbook completo per le transizioni `sync_from_truenas`, `activate`, `deactivate` e `set_backend` tra TrueNAS, Mac Studio e OPNsense. |
| `scripts/infrastructure/pve3-gpu-eco.sh` | **Modifica** | Wrapper CWD-independent per `go.py` $\rightarrow$ `pve3_gpu_power.yml -e gpu_mode=eco`. |
| `scripts/infrastructure/pve3-gpu-mode.sh` | **Modifica** | Wrapper CWD-independent per `go.py` $\rightarrow$ `pve3_gpu_power.yml -e gpu_mode=status`. |
| `scripts/infrastructure/pve3-gpu-turbo.sh` | **Modifica** | Wrapper CWD-independent per `go.py` $\rightarrow$ `pve3_gpu_power.yml -e gpu_mode=turbo`. |
| `scripts/infrastructure/pve3-host-backup-pbs.sh` | **Rimozione** | Eliminazione dello script PBS host obsoleto (Opzione B0). |
| `scripts/infrastructure/lab_mode_full.sh` | **Modifica** | Integrazione transizione in due step (ECO in Fase 2, FULL a fine Fase 3). |
| `scripts/infrastructure/lab_mode_eco.sh` | **Modifica** | Sostituzione chiamate `orbstack_failover.sh` con `ansible-playbook ... orbstack_failover.yml`. |
| `scripts/infrastructure/lab_mode_off.sh` | **Modifica** | Sostituzione chiamate `orbstack_failover.sh` con `ansible-playbook ... orbstack_failover.yml`. |
| `scripts/infrastructure/orbstack_failover.sh` | **Rimozione** | Libreria Bash sostituita integralmente dal playbook `orbstack_failover.yml`. |
| `scripts/infrastructure/lab_mode_status.sh` | **Modifica** | Fix POSIX (`nc -z -w 1`, normalizzazione `$TMPDIR`, probe TCP remoto `10.10.20.100:9119`). |
| `scripts/network/test_dns.sh` | **Modifica** | Fallback automatico `RETE_JSON="${RETE_JSON_PATH:-$ROOT_DIR/rete.json}"`. |
| `scripts/network/test_dhcp.sh` | **Modifica** | Fallback automatico `RETE_JSON="${RETE_JSON_PATH:-$ROOT_DIR/rete.json}"`. |
| `scripts/benchmarks/run_promptfoo_ocr.sh` | **Modifica** | Fix POSIX (`base64 < "$FIXTURE_PATH" |

---

## 2. Piano Operativo Dettagliato (Step-by-Step Test-Driven)

### Fase 1: Aggiornamento `ansible/inventory.ini` e Bootstrap SSH

1. **Modifica a `ansible/inventory.ini**`:
Aggiunta del gruppo `[mac_studio]` con interprete Python esplicito:
```ini
[mac_studio]
10.10.20.100 ansible_user=olindo ansible_python_interpreter=/usr/bin/python3

```


2. **Bootstrap SSH & Verifica**:
* Verifica che il servizio *Remote Login (sshd)* sia attivo su Mac Studio (`10.10.20.100`) e che la chiave pubblica sia in `~/.ssh/authorized_keys`.
* Test di connettività Ansible: `ansible -i ansible/inventory.ini all -m ping` (verificando il secondo hop SSH e il funzionamento sia da ambiente Mac locale che da container).



---

### Fase 2: Migrazione Ansible GPU Power Management su `pve3` (`pve3-gpu-{eco,mode,turbo}.sh`)

1. **Creazione di `ansible/playbooks/infrastructure/pve3_gpu_power.yml**`:
Playbook idempotente con validazione input `assert` per i parametri `gpu_mode` (`eco`, `turbo`, `status`) su `10.10.10.31`.
2. **Rifattorizzazione dei 3 Script Wrapper in `scripts/infrastructure/**`:
Aggiornamento di `pve3-gpu-eco.sh`, `pve3-gpu-mode.sh` e `pve3-gpu-turbo.sh` per risolvere dinamicamente `ROOT_DIR` e invocare `ansible-playbook`.
3. **Test di Verifica**: Syntax check e test di esecuzione con verifica `changed=0/1`.

---

### Fase 3: Migrazione Ansible del Failover OrbStack (`orbstack_failover.yml`)

Creazione del playbook unificato `ansible/playbooks/infrastructure/orbstack_failover.yml` strutturato sulle 4 azioni (`failover_action`):

1. **`failover_action=sync_from_truenas`** (Fase 2 di `lab_mode_off.sh`):
* Verifica la raggiungibilità di TrueNAS (`10.10.20.50:22`) con `wait_for`.
* Se online: ferma `hermes-main` su TrueNAS (`delegate_to: truenas`), normalizza i permessi UID/GID `1000:1000` (`olindo:k8s`) ed esegue il data plane `rsync` diretto da `10.10.20.50` a `10.10.20.100` (`HermesMain/` con `-az`, `common/` con `-auz`, più file `.env*` e `acme.json`).


2. **`failover_action=activate`** (Fase 4 di `lab_mode_off.sh`):
* Copia `docker-compose.yaml` dal controller (container o Mac working tree) in `~/.homelab-failover/docker-compose.yaml` su `mac_studio`.
* Avvia OrbStack (`orbctl start`), lancia il compose failover, attende i gate HTTP/TCP (`4000`, `9119`, `8100`, `8180`, `8888`, `3000`), crea il file marker `~/.homelab-failover/.failover_active` ed esegue `switch_failover_dns.py --target off`.


3. **`failover_action=deactivate`** (Fase 2 di `lab_mode_eco.sh` e `lab_mode_full.sh`):
* Esegue il push `rsync` inverso da `mac_studio` a `truenas` **solo se** il marker `.failover_active` esiste o se il container `hermes` è attivo su OrbStack (D1). Rimuove `.failover_active` a fine sync.
* Ferma/avvia `hermes-main` su TrueNAS (`delegate_to: truenas`), applica il self-healing sulle porte TrueNAS (`8100, 9119, 4000, 8888`) e sincronizza la homepage ECO.
* Arresta e rimuove lo stack OrbStack e spegne OrbStack se era inattivo in origine.


4. **`failover_action=set_backend`** (Fine Fase 3 di `lab_mode_full.sh` - C1):
* Aggiorna `dynamic.yaml` su TrueNAS puntando al VIP K8s `[https://10.10.20.56](https://10.10.20.56)` ed esegue `switch_failover_dns.py --target full`.



---

### Fase 4: Micro-Fix POSIX (Compatibilità 100% Container Docker & macOS)

* **`scripts/infrastructure/lab_mode_status.sh`**: Fix `nc -z -w 1`, normalizzazione `TMPDIR="${TMPDIR%/}"`, e probe TCP remoto `10.10.20.100:9119`.
* **`scripts/network/test_dns.sh`** & **`scripts/network/test_dhcp.sh`**: Fallback automatico `RETE_JSON="${RETE_JSON_PATH:-$ROOT_DIR/rete.json}"`.
* **`scripts/benchmarks/run_promptfoo_ocr.sh`**: Fix `base64 < "$FIXTURE_PATH" | tr -d '\n\r'` (compatibile GNU/BSD) e `$TMPDIR` normalizzato.

---

### Fase 5: Validazione Finale e Consolidamento Wiki (§13)

* Rimozione definitiva di `scripts/infrastructure/pve3-host-backup-pbs.sh` (`git rm`).
* Esecuzione di `python3 scripts/network/validate_network.py && python3 scripts/wiki/build_wiki_context.py`.
* Aggiornamento stato in `todo.md` e `GEMINI.md`.

---

## 3. Piano di Rollback

1. **Rollback Granulare via Git**:
* In caso di anomalia: `git checkout HEAD -- scripts/infrastructure/` e rimozione dei playbook Ansible creati in `ansible/playbooks/infrastructure/`.


2. **Ripristino Stato GPU PVE3**:
* Comando diretto di emergenza: `ssh root@10.10.10.31 "echo auto > /sys/class/drm/card0/device/power_dpm_force_performance_level"`.


3. **Ripristino DNS e Backend Traefik**:
* Esecuzione diretta di `python3 scripts/network/switch_failover_dns.py --target full` (o `eco`/`off`).



---

## 💾 Stato di Ripristino (AI Save-State)

* **Fase Attiva**: Pronto per l'esecuzione della Fase 1.
* **Ultima Azione Completata**: Approvazione delle scelte architetturali (Dual-Mode, A1, B0, C1, D1) e riscrittura del piano.
* **Prossimo Passo Operativo**: Iniziare l'applicazione della Fase 1 (`ansible/inventory.ini` e bootstrap SSH).
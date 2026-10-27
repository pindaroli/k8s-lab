# Quadro Contestuale per Consulto Piano: `ansible-migration-pve3-and-orbstack-failover`

> **Generato il**: 2026-10-27
> **Piano di Riferimento**: [`wiki/plans/ansible-migration-pve3-and-orbstack-failover.md`](file:///Users/olindo/prj/k8s-lab/wiki/plans/ansible-migration-pve3-and-orbstack-failover.md)
> **Contesto Globale**: [`wiki/wiki_context.md`](file:///Users/olindo/prj/k8s-lab/wiki/wiki_context.md)

---

## 1. Scheda del Piano

- **Titolo**: Piano: Migrazione Ansible Integrale per GPU/Backup PVE3, Failover OrbStack e Portabilità Docker per `go.py`
- **Percorso**: `wiki/plans/ansible-migration-pve3-and-orbstack-failover.md`
- **Stato**: `active` (`certified_for_ai: true`)
- **Tecnologie Coinvolte**: Ansible (`ansible-playbook`, `wait_for`, `uri`), Bash, Python 3, Docker / OrbStack (`docker compose`, `orbctl`), Proxmox VE 9.2 (`sysfs` AMD Radeon 890M DPM, `proxmox-backup-client`), TrueNAS SCALE 25.10 (`rsync`, ZFS `stripe`), OPNsense Unbound DNS REST API (`switch_failover_dns.py`).
- **Indice Sezioni del Piano**:
  1. Obiettivo e Decisioni Architetturali Approvate (`/grill-me`)
  1.5. Mappa dei File da Creare, Modificare o Rimuovere
  2. Piano Operativo Dettagliato (Fasi 1–6: Inventory, GPU PVE3, Backup PBS PVE3, Failover OrbStack, Micro-Fix POSIX, Validazione Wiki)
  3. Piano di Rollback
  4. Stato di Ripristino (AI Save-State)

---

## 2. Nodi, IP, Porte e VLAN Pertinenti (da `rete.json`)

| ID Nodo / Entità | Indirizzo IP | VLAN | Ruolo nel Piano e Servizi Toccati |
| :--- | :---: | :---: | :--- |
| **`pve3`** (GMKtec NucBox EVO-X1) | `10.10.10.31` (Mgmt)<br>`192.168.100.31` (OOB) | VLAN 10 (Server)<br>VLAN 99 (OOB) | Hypervisor Proxmox VE 9.2 con iGPU **AMD Radeon 890M (RDNA 3.5)**. Ospita `/sys/class/drm/card0/device/power_dpm_force_performance_level` (`auto`/`high`), `/etc/pve/priv/storage/pbs.pw`, `/usr/local/bin` e `/var/lib/vz/snippets`. Utente SSH: `root`. |
| **`pbs`** (Proxmox Backup Server) | `10.10.10.100` | VLAN 10 (Server) | VM KVM su TrueNAS SCALE. Espone il datastore `pbs-store` (`root@pam@10.10.10.100:pbs-store`, porta `8007`) ricevente il backup host di `pve3`. |
| **`truenas`** (TrueNAS SCALE Bare Metal) | `10.10.20.50` | VLAN 20 (Client) | Server primario in `FULL` ed `ECO`. Ospita lo stack Docker (`/mnt/stripe/truenas-docker/` e `/mnt/stripe/truenas-docker/mcp/`) e lo stato di Hermes Agent (`/mnt/stripe/hermesAgent/{HermesMain,common}`). Porte monitorate: `22` (SSH, utente `olindo` con `sudo -n`), `8443` (WebUI), `8100` (MCP Traefik), `9119` (Hermes), `4000` (LiteLLM), `8888` (Dozzle), `3000` (Homepage ECO). |
| **`mac-studio`** (Mac Studio M2 Ultra) | `10.10.20.100` | VLAN 20 (Client) | Workstation macOS e nodo di failover attivo in modalità `OFF` tramite **OrbStack** (`docker/orbstack/docker-compose.yaml`). Ospita `~/.homelab-failover/{.env,.env.ai,.env.mcp,acme}` e `/Users/olindo/hermesAgent/{HermesMain,common}`. Porte stack failover: `8100`, `8180`, `9119`, `4000`, `8888`, `3000`. Utente SSH: `olindo`. |
| **`opnsense`** (Firewall / Router) | `192.168.2.254` (Transit/DNS)<br>`192.168.100.1` (OOB) | Transit / VLAN 99 | Server Unbound DNS (commutazione record A `home-internal`, `mcp`, `hermes`, `litellm`, `dozzle` tramite `scripts/network/switch_failover_dns.py`) e Kea DHCP (`test_dhcp.sh`). |
| **`pve1` / `pve2`** | `10.10.10.11` / `10.10.10.21` | VLAN 10 (Server) | Nodi Proxmox VE coinvolti nei controlli di stato (`lab_mode_status.sh`) e nelle sequenze `ensure_compute_on.yml` / `ensure_compute_off.yml`. |
| **VIP Kubernetes & Traefik** | `10.10.20.55` (`:6443`)<br>`10.10.20.56` (`:443`) | VLAN 20 (Client) | VIP API Server Talos K8s e VIP MetalLB Traefik Ingress (destinazione di `home-internal.pindaroli.org` e del proxy `dynamic.yaml` di TrueNAS in `FULL`). |

---

## 3. Storage ZFS, Dataset e Percorsi Pertinenti (da `storage.json`)

| Host | Percorso / Dataset | Owner / Permessi | Utilizzo nel Piano |
| :--- | :--- | :---: | :--- |
| **TrueNAS (`10.10.20.50`)** | `/mnt/stripe/hermesAgent/HermesMain` | `1000:1000` (`olindo:k8s`), SQLite `journal_mode=DELETE` | Stato istanza di Hermes Agent sincronizzato bidirezionalmente con `rsync -az` (senza `-u` e senza `--delete`, escludendo `.sock`, `.lock`, `gateway-locks/`). |
| **TrueNAS (`10.10.20.50`)** | `/mnt/stripe/hermesAgent/common` | `1000:1000` (`olindo:k8s`), SGID `g+s` | Workspace condiviso `common/prj` sincronizzato additivamente con `rsync -auz`. |
| **TrueNAS (`10.10.20.50`)** | `/mnt/stripe/truenas-docker/{.env,mcp/.env,mcp/dynamic.yaml,homepage/}` | `olindo:k8s` / `root` | File `.env` sorgenti per il failover, configurazione dinamica Traefik (`homepage-truenas-svc`) e dashboard Homepage `ECO`. |
| **Mac Studio (`10.10.20.100`)** | `/Users/olindo/hermesAgent/{HermesMain,common}` | `olindo:staff` (`UID 501` su macOS, mappato trasparentemente da OrbStack a `1000` nel container) | Copia locale di failover dello stato e del workspace di Hermes Agent. |
| **Mac Studio (`10.10.20.100`)** | `/Users/olindo/.homelab-failover/` | `0700` (`0600` per `.env*` e `acme.json`) | Directory runtime locale per i segreti `.env` unificati dello stack `docker/orbstack/docker-compose.yaml`. |
| **PVE3 (`10.10.10.31`)** | `/usr/local/bin` e `/var/lib/vz/snippets` | `root:root` | Directory sottoposte a backup host PXAR verso PBS (`pbs-store`, backup-id `pve3-host`). |

---

## 4. Vincoli Architetturali & Golden Rules Applicabili (`GEMINI.md`)

1. **Passwordless SSH Mandate**: Tutte le connessioni Ansible e `rsync` tra container/runner, `mac_studio` (`10.10.20.100`), `truenas` (`10.10.20.50`) e `pve3` (`10.10.10.31`) devono operare esclusivamente tramite chiavi SSH (`BatchMode=yes`), senza password in chiaro o prompt interattivi.
2. **Go Launcher Script Pattern (`[[go-launcher-script-pattern]]`)**: Ogni script `.sh` esposto nel menu di `scripts/go.py` deve avere la descrizione sulla riga 2, risolvere dinamicamente `ROOT_DIR` (CWD independence) ed essere eseguibile (`chmod +x`), mentre le librerie non eseguibili direttamente non devono avere `+x`.
3. **Hierarchical Automation Alerting Pattern (`[[hierarchical-automation-alerting-pattern]]`)**: `lab_mode_full.sh`, `lab_mode_eco.sh` e `lab_mode_off.sh` devono preservare `procedure_scope.sh`, `trap 'on_error $LINENO' ERR`, zero email di avvio e una singola notifica riassuntiva finale Telegram + Email HTML.
4. **KISS Failover Invariants (`[[homelab-hermes-convergence-and-compose-cross-hardening]]` & `[[hermes-sqlite-journal-mode-and-homepage-health-hardening]]`)**:
   - Arresto preventivo di `hermes-main` su TrueNAS (`docker stop -t 25`) e `hermes-agent` su OrbStack prima di ogni `rsync` di `HermesMain/` per garantire la quiescenza dei 7 database SQLite (`journal_mode=DELETE`).
   - Separazione rigorosa tra `rsync -az` su `HermesMain/` (con `--exclude='/common/**'`, `--exclude='*.sock*'`, `--exclude='/*.lock'`, `--exclude='*gateway-locks/'`) e `rsync -auz` additivo su `common/`.
   - Normalizzazione dei permessi su TrueNAS (`UID:GID 1000:1000` `olindo:k8s` con `-path '.../common' -prune` per non rallentare su `common/prj`, più `chmod -R u+rwX,g+rwX,o+rX` e SGID `g+s`).
5. **Protocollo di Verifica Test-Driven (`[[SCHEMA]]` §12)**: Ogni singola fase deve essere validata con syntax-check e test reale prima di passare alla successiva.

---

## 5. Aree di Attenzione & Quesiti Specifici per il Revisore

1. **Topologia dell'`rsync` tra `mac_studio` (`10.10.20.100`) e `truenas` (`10.10.20.50`) quando Ansible gira in un Container Remoto**:
   - Se il playbook `orbstack_failover.yml` ha `hosts: mac_studio`, i task `shell` contenenti `rsync ... olindo@10.10.20.50:... /Users/olindo/hermesAgent/...` vengono eseguiti **direttamente dal Mac Studio verso TrueNAS** (usando le chiavi SSH di `olindo` già presenti su Mac Studio in `/Users/olindo/.ssh/`). Verificare che non vi siano problemi di SSH Agent / HostKeyChecking o `PATH` (`/opt/homebrew/bin/rsync` vs `/usr/bin/rsync` openrsync di macOS) quando Ansible si connette in sessione non-interattiva a `mac_studio`.
2. **Risoluzione del Percorso del Repository su `mac_studio` vs Container**:
   - Quando Ansible gira in un container (es. in `/workspace/k8s-lab`), `playbook_dir` punta al path interno al container (`/workspace/k8s-lab/ansible/playbooks/infrastructure`), mentre sul nodo remoto `mac_studio` il file `docker/orbstack/docker-compose.yaml` si trova in `/Users/olindo/prj/k8s-lab/docker/orbstack/docker-compose.yaml`. È fondamentale distinguere nel playbook `orbstack_failover.yml` tra i path sul controller Ansible (`playbook_dir` per `switch_failover_dns.py` e `secrets-sops/`) e i path sul nodo target `mac_studio` (`mac_repo_root: "/Users/olindo/prj/k8s-lab"`).
3. **Auto-Detection Connessione a `mac_studio` (SSH vs Local)**:
   - Se l'utente lancia `lab_mode_off.sh` direttamente dal terminale macOS del Mac Studio e non ha abilitato "Accesso Remoto" (`sshd` porta 22 su macOS) o non ha la propria chiave pubblica in `~/.ssh/authorized_keys` del Mac stesso, la connessione SSH a `10.10.20.100:22` fallirebbe. Valutare come pre-requisito della Fase 1 la verifica dell'auto-autorizzazione SSH `olindo@10.10.20.100` (aggiunta idempotente di `~/.ssh/id_ed25519.pub` a `~/.ssh/authorized_keys` sul Mac).
4. **Probe `http://127.0.0.1:9119/api/health` vs `/health` per Hermes Agent**:
   - In seguito al piano `[[hermes-sqlite-journal-mode-and-homepage-health-hardening]]`, verificare se l'endpoint canonico di health di Hermes sia `/api/health` (o entrambi `/health` e `/api/health`) per il gate di attivazione in `orbstack_failover.yml` e per il probe in `lab_mode_status.sh`.

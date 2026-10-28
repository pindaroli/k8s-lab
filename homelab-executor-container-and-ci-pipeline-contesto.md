# Contesto Tecnico & Architetturale per Consulto: `homelab-executor-container-and-ci-pipeline`

Documento di supporto contestuale generato per la revisione critica e consulto esperto sul piano:
📄 [**`wiki/plans/homelab-executor-container-and-ci-pipeline.md`**](file:///Users/olindo/prj/k8s-lab/wiki/plans/homelab-executor-container-and-ci-pipeline.md)

---

## 1. Scheda del Piano Operativo

- **Titolo**: Pipeline DevOps CI/CD e Container Immutabile Homelab Executor per `scripts/go.py`
- **ID Piano**: `homelab-executor-container-and-ci-pipeline`
- **Percorso File**: `wiki/plans/homelab-executor-container-and-ci-pipeline.md`
- **Stato**: `active` | **Certified for AI**: `true`
- **Data Creazione**: 2026-10-28
- **Tecnologie Coinvolte**: Docker (Multi-stage, `python:3.12-slim`), FastMCP / MCP SDK 2.0 (SSE/HTTP), FastAPI, OpenSSH Server/Client (`sshd` porta 2222), Ansible Core, SOPS + Age (`secrets-sops/`), GitHub Actions CI/CD (`ghcr.io`), TrueNAS SCALE Bare Metal (`10.10.20.50`), Traefik Reverse Proxy (`dynamic.yaml`), Python 3.12.
- **Obiettivo Fondamentale**: Realizzare un container di esecuzione DevOps immutabile e standardizzato che incapsula tutti gli script operativi (`scripts/`), i playbook Ansible (`ansible/`) e le definizioni di rete/storage (`rete.json`, `storage.json`) per consentire sia l'orchestrazione programmata/agentica (via server MCP e REST API) sia l'esecuzione interattiva o batch via SSH passwordless, con decifratura on-the-fly dei segreti SOPS a runtime.

---

## 2. Nodi, Rete e Punti di Integrazione (`rete.json`)

| Entità | IP / Endpoint | VLAN / Rete | Ruolo nel Piano |
| :--- | :--- | :--- | :--- |
| **TrueNAS SCALE** | `10.10.20.50` | VLAN 20 (Client/Storage) | Host bare-metal di produzione che esegue lo stack Docker dei container (`docker/mcp` o dedicato). Ospiterà il container `homelab-executor`. |
| **MCP Traefik Gateway** | `mcp.pindaroli.org:8100` (`10.10.20.50:8100`) | VLAN 20 | Reverse proxy Traefik esposto localmente per instradare le connessioni MCP HTTP/SSE verso i singoli container backend. |
| **Homelab Executor (Container)** | `10.10.20.50:2222` (SSH) <br> `http://10.10.20.50:8000` (FastAPI/MCP) | `mcp_network` (Docker bridge) | Container target in esecuzione su TrueNAS: espone la porta SSH interna 22 mappata su 2222 dell'host e l'endpoint web su Traefik (`/executor/mcp`). |
| **Mac Studio (Sviluppo & Test)** | `10.10.20.100` | VLAN 20 | Client primario di sviluppo e test: vi risiede la working copy git `k8s-lab`. Esegue lo step 1 (test locale) e lo step 4 (lancio di `update_homelab_executor.sh` da `go.py`). |
| **Proxmox Cluster (`pve1, pve2, pve3`)** | `10.10.10.11`, `10.10.10.21`, `10.10.10.31` | VLAN 10 (Server) | Nodi hypervisor gestiti via SSH/Ansible dai playbook incapsulati nel container (es. audit SMART, controllo stato, switch GPU). |
| **OPNsense Router** | `10.10.20.254` (LAN) / `10.10.10.254` (DMZ) | VLAN 10 / 20 | Gateway e firewall: target per script di switching DNS failover (`switch_failover_dns.py`) e test DHCP. |
| **Extreme Switch EXOS** | `10.10.20.253` | VLAN 20 | Switch di centro stella: target per script e playbook Ansible di gestione porte (es. bounce SFP porta 10). |
| **GitHub Packages (GHCR)** | `ghcr.io/pindaroli/homelab-executor` | Cloud Registry | Registry OCI ufficiale dove la pipeline CI/CD GitHub Actions pubblica le immagini versionate. |

---

## 3. Storage & Volumi Persistenti (`storage.json`)

- **Nessun volume codice montato a runtime**:
  Il container adotta il principio dell'**artefatto immutabile**. Il codice (`scripts/`, `ansible/`, `rete.json`, `storage.json`, `secrets-sops/`) viene incorporato direttamente nell'immagine in fase di build Docker via GitHub Actions.
- **Volumi di Credenziali (Host Mount Read-Only su TrueNAS `10.10.20.50`)**:
  - `/root/.config/sops/age/keys.txt`: file di chiave privata Age (`age1x5pmv4jqhp99mzt089nrm4wn8cd6y4vlt88n8mq0xe30wngasuaqxl4ytl`) montato in sola lettura (`:ro`) per consentire al binario `sops` nel container di decifrare `secrets-sops/*.enc.yaml`.
  - `/root/.ssh/id_rsa`: chiave privata SSH (con permessi restrittivi `600`) per consentire ad Ansible e agli script nel container di connettersi senza password ai nodi Proxmox, TrueNAS, OPNsense e Switch.
  - `/root/.ssh/authorized_keys`: file di chiavi pubbliche autorizzate montato per consentire all'utente da Mac Studio (`10.10.20.100`) di entrare via SSH sulla porta `2222`.

---

## 4. Vincoli Architetturali e Golden Rules Applicabili

1. **Passwordless SSH Mandate (`AGENTS.md` / `GEMINI.md`)**:
   È categoricamente vietato hardcodare o trasmettere password di sistema in script, playbook o configurazioni Docker. Tutte le connessioni SSH in uscita dal container verso l'infrastruttura devono operare con `BatchMode=yes` tramite la chiave SSH montata. L'accesso SSH in ingresso al container deve accettare esclusivamente autenticazione a chiavi (`PasswordAuthentication no`).
2. **Zero Plaintext Secrets & SOPS Sovereignty (`wiki/patterns/mcp-secret-projection-pattern.md`)**:
   Nessun segreto (token Telegram, password SMTP, API key OPNsense, token GitHub) deve essere scritto in chiaro nell'immagine o nei file YAML del repository. Tutti i segreti risiedono cifrati in `secrets-sops/*.enc.yaml` e vengono estratti a runtime tramite il comando nativo `sops -d`.
3. **CWD & Location Independence (`wiki/patterns/go-launcher-script-pattern.md`)**:
   Ogni script in `scripts/` deve risolvere dinamicamente la propria root (`ROOT_DIR`) e funzionare indistintamente sia se invocato da `/Users/olindo/prj/k8s-lab` su macOS, sia se invocato all'interno del container Linux (es. in `/app` o `/workspace`).
4. **Validazione Dichiarativa MCP (`wiki/patterns/script-to-mcp-tool-schema-pattern.md`)**:
   Ogni comando esposto dal server MCP deve aderire rigorosamente alla specifica dichiarativa in `scripts/mcp_tools.yaml` e validare tramite `schemas/mcp-tools.schema.json`.
5. **Divieto Port-Forwarding Permanente**:
   L'esposizione di rete deve avvenire esclusivamente tramite Traefik per i protocolli HTTP/SSE e tramite binding di porta specifico dell'host (`2222:22`) per il demone SSH.

---

## 5. Aree di Attenzione Critica e Quesiti per il Consulto

1. **Supervisione Processi Multipli (Entrypoint Architecture)**:
   - Il container deve eseguire simultaneamente il server OpenSSH (`sshd`) e il server Python (FastAPI/FastMCP con Uvicorn).
   - *Quesito per il revisore*: Qual è la strategia di supervisione o entrypoint più robusta, sicura ed elegante in `python:3.12-slim` (es. script shell `entrypoint.sh` con `trap` e backgrounding controllato vs supervisord leggero / tini / dumb-init)?
2. **Gestione Permessi e Utente Unix (Root vs Non-Root con SSHD)**:
   - OpenSSH Server richiede tipicamente privilegi di root per eseguire il bind, gestire la separazione dei privilegi e caricare le chiavi utente, mentre le best practice dei container prediligono utenti non privilegiati (UID 1000).
   - *Quesito per il revisore*: Conviene eseguire il container come `root` con `dropbear`/`openssh` configurato in modo restrittivo (solo chiavi pubbliche), oppure creare un utente dedicato `executor` (UID 1000) e configurare sshd solo per tale utente?
3. **Path Filtering e Ottimizzazione Build CI/CD**:
   - I trigger di GitHub Actions includono modifiche a `scripts/**`, `ansible/**`, `rete.json`, `storage.json`.
   - *Quesito per il revisore*: Come evitare build superflue quando vengono modificate semplici note o documentazione (es. file markdown `.md` in `scripts/` o commenti), garantendo al contempo che ogni modifica a script `.py`, `.sh` e `.yml` inneschi la build dell'immagine?
4. **Resilienza e Rollout Atomico su TrueNAS (Step 4)**:
   - Lo script `update_homelab_executor.sh` deve aggiornare il container in esecuzione senza causare lock o corruzione se lanciato da un agente o dall'utente via `go.py`.
   - *Quesito per il revisore*: Ci sono raccomandazioni sul drain o timeout per garantire che eventuali task o comandi lunghi in corso (es. backup o sincronizzazioni) non vengano interrotti bruscamente durante `docker compose up -d`?

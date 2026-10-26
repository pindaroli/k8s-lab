# Analisi Idoneità Script per Esecuzione su Nodo Remoto vs Mac Locale

Questo documento censisce tutti gli script operativi (`.py`, `.sh` e playbook Ansible correlati) del repository `k8s-lab`, classificandoli in base alla possibilità di essere eseguiti all'interno di un server MCP ospitato su un **nodo remoto attrezzato** (Linux Debian/Ubuntu con Python 3, bash, Ansible, `kubectl`, `talosctl` e chiavi SSH) oppure esclusivamente su **Mac locale**.

---

## ❌ 1. Script con Dipendenza Esclusiva da macOS (Da Escludere su Nodo Remoto)

I seguenti script non possono essere eseguiti direttamente su un nodo remoto Linux poiché richiedono binari nativi Darwin, framework AppleScript/JXA, database locali o motori container esclusivi di macOS:

| Script / Directory | Motivo Tecnico dell'Incompatibilità (Solo Mac) |
| :--- | :--- |
| **`scripts/office-mac-mcp/`** (`office365_mcp_server.py`, `applescript_bridge.py`, ecc.) | **Architettura macOS nativa (AppleScript/JXA)**: Automatizza direttamente le suite desktop Word, Excel e PowerPoint tramite il comando Darwin `osascript`. Non può girare su Linux privo di GUI Darwin e Microsoft Office per Mac. |
| **`scripts/infrastructure/orbstack_failover.sh`** | **Dipendenza OrbStack locale**: Esegue comandi `docker compose` locali per avviare/fermare i container failover su OrbStack (il motore container nativo di macOS residente su Mac Studio). Se eseguito su un nodo Linux remoto, opererebbe sul demone Docker del nodo invece che su OrbStack del Mac. |
| **`scripts/infrastructure/lab_mode_full.sh`**<br>**`scripts/infrastructure/lab_mode_eco.sh`**<br>**`scripts/infrastructure/lab_mode_off.sh`** | **Invocazione locale di OrbStack Failover**: Questi 3 script orchestrano il cluster ma contengono invocazioni dirette di `orbstack_failover.sh` per switchare localmente i container Docker del Mac. *(Possono girare su Linux solo se il failover OrbStack viene delegato via SSH verso il Mac Studio `10.10.20.100`)*. |
| **`scripts/antigravity/clean_conversations.py`** e **`.sh`** | **Database locale Antigravity IDE**: Opera direttamente sui file SQLite e JSONL locali memorizzati in `~/.gemini/antigravity/` sul Mac dell'utente. Su un nodo remoto questo percorso non esiste. |
| **`scripts/benchmarks/run_promptfoo_ocr.sh`** | **CLI Mac e visualizzatori PDF nativi**: Utilizza comandi e strumenti di rendering PDF/OCR (`pdftoppm`, framework Quartz e runtime locali) configurati specificamente per il client Mac. |
| **`scripts/go.py`** | **Launcher TTY Interattivo per terminale utente**: È un menu interattivo `stdout`/ANSI pensato per la shell umana dello sviluppatore su Mac, non un tool programmatico per un server MCP remoto. |

---

## ✅ 2. Script Perfettamente Idonei per Nodo Remoto Attrezzato

Tutti i seguenti script operano tramite chiamate di rete standard, socket UDP/TCP, API REST HTTP, invocazioni CLI Kubernetes/Talos o connessioni SSH batch-mode senza password.

### A. Rete, DNS e Switching
- **`scripts/network/validate_network.py`**: Parsing e validazione formale pura di `rete.json` (zero dipendenze OS).
- **`scripts/network/switch_failover_dns.py`**: Invocazione API REST OPNsense (`/api/unbound/settings/...`) per cambiare gli Host Overrides.
- **`scripts/network/wake_node.py`**: Invio socket UDP (porta 9) di Magic Packet Wake-on-LAN sulla subnet di broadcast (`10.10.20.255`).
- **`scripts/network/test_dns.sh`**: Query standard `dig` / `nslookup` contro il resolver Unbound a `10.10.20.254`.
- **`scripts/network/exos/bounce_port10.py`**: Connessione SSH standard verso lo switch Extreme EXOS.
- **`scripts/network/analyze_ips.py`**: Analisi semantica e validazione CIDR di rete (Python standard).

### B. Storage & TrueNAS
- **`scripts/storage/analyze_special_frag.py`**: Esecuzione remota via SSH su TrueNAS (`zpool status`, `smartctl`) e parsing JSON.
- **`scripts/truenas/check_truenas_docker_updates.sh`**: Chiamate HTTP verso registry OCI V2 e query via SSH a TrueNAS.
- **`scripts/storage/sync_storage.py`**: Interrogazione SSH verso TrueNAS per export NFS.

### C. Kubernetes & Container
- **`scripts/kubernetes/check_k8s.py`**: Diagnostica cluster via API `kubectl` e `talosctl` (richiede kubeconfig e talosconfig montati).
- **`scripts/kubernetes/check_nova_updates.sh`**: Esecuzione CLI `nova` (aggiornamenti release Helm K8s).
- **`scripts/kubernetes/safe_shutdown_cp.sh`**: Drenaggio e spegnimento controllato control-plane via `talosctl`/`pvesh`.

### D. Proxmox VE & Hardware
- **`ansible/proxmox_smart_audit.yml`** (e wrapper `scripts/infrastructure/check_proxmox_smart.sh`): Playbook Ansible standard su SSH verso `pve1`, `pve2`, `pve3`.
- **`scripts/infrastructure/check_lab.py`**: Diagnostica homelab via SSH e chiamate `pvesh` REST su Proxmox.
- **`scripts/infrastructure/lab_mode_status.sh`**: Verifica di stato non invasiva (ping, porte TCP aperte e query DNS).
- **`scripts/infrastructure/pve3-gpu-mode.sh`**: Query stato GPU Radeon via SSH su `pve3`.

### E. Sicurezza & SOPS
- **`scripts/security/check-sops-encrypted.sh`**: Verifica presenza metadati SOPS su file locali del repo.
- **`scripts/security/check_certificate.sh`**: Query `openssl` e verifica certificati/segreti su Traefik / Kubernetes.

### F. Servarr & Multimediale
- **`scripts/servarr/sync_prowlarr_flaresolverr.py`**: Chiamate REST API HTTP verso Prowlarr e FlareSolverr.
- **`scripts/servarr/cleanup_torrents.py`**: Chiamate REST API HTTP verso qBittorrent.
- **`scripts/servarr/audit_movie_duplicates.py`**: Scansione percorsi NFS/filesystem montati (es. `/media/movies`).
- **`scripts/servarr/trigger-job.sh`**: Invio trigger webhook FileBot AMC verso il normalizer.

### G. Documentazione e RAGFlow
- **`scripts/wiki/build_wiki_context.py`**: Parsing file Markdown del wiki e generazione `wiki_context.md`.
- **`scripts/ragflow/ingestion_stats.py`**: Query API REST verso l'istanza RAGFlow (`ragflow-internal.pindaroli.org`).

---

## 📌 Sintesi per la Configurazione del Server MCP Remoto

Quando si compila o genera il file `mcp_tools.yaml` destinato a un server MCP che gira in remoto (es. su un container Docker o Pod K8s):
1. **Escludere:** I tool appartenenti alla Sezione 1 (`office-mac-mcp`, `orbstack_failover.sh`, `clean_conversations.py`, `run_promptfoo_ocr.sh`, `go.py`).
2. **Abilitare:** Tutti i tool di rete, storage, K8s, Ansible, Servarr e wiki della Sezione 2, fornendo al container/ambiente le credenziali SSH verso i nodi homelab (`BatchMode=yes`) e i file di configurazione (`kubeconfig`, `talosconfig`).

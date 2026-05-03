# Project GEMINI: Kubernetes Homelab Migration

> [!IMPORTANT]
> **Current Status**: **DNS EXPLICIT MAPPING OPERATIONAL**
> 0.0.0.0 "Black Hole" records removed from Cloudflare; All internal services exclusively managed via OPNsense.
> **Active Goal**: Ingress & External Access (Phase 5).

## 1. Quick Reference
### Monitoring (VictoriaMetrics)
- **Namespace**: `monitoring` (Etichettato come `privileged` per node-exporter).
- **Dashboard**: `victoria-monitoring-grafana` (Porta 3000).
- **AlertManager**: Integrato con Telegram (Bot Lab).
- **Scrapes**: Traefik (9100), CNPG (9187), Velero (8085), Servarr (Namespace `arr`).

### Debugging access policies
whenever an agent command fails for security reasons append it to security-issues.log + errore code and string
### Security Policies
> [!CRITICAL]
> **EXTERNAL ACCESS & OAUTH**
> ALL services exposed via Cloudflare (External) MUST have **OAuth2 Authentication** enabled (Google Login).
> **NO EXCEPTIONS**. Even services with native login (like MinIO/TrueNAS) must sit behind the OAuth shield.
> *Implementation:* Traefik Middleware `oauth2-auth`.
>
> **INTERNAL ACCESS (LAN/VPN)**
> Services exposed via `-internal.pindaroli.org` **MUST NOT** use OAuth2 authentication. 
> Access from LAN/VPN is considered trusted. Do not add `oauth2-auth` middleware to internal IngressRoutes.
>
> **DOCUMENTATION MAINTENANCE**
> The file `homelab_notebooklm.md` is a comprehensive compilation of the project for AI context (NotebookLM).
> **RULE**: Whenever you make SUBSTANTIAL changes to the infrastructure (topology, new nodes, major migrations), you **MUST** update `homelab_notebooklm.md` to reflect the new state.
>
> **UNIFIED NAMING CONVENTION (UNC)**
> For every service, three mnemonic endpoints are provided:
> 1. `<service>.pindaroli.org`: **Premium (External)**. Via Traefik + SSL + OAuth2.
> 2. `<service>-internal.pindaroli.org`: **Premium (Internal)**. Via Traefik + SSL + Trusted LAN.
> 3. `<service>-direct.pindaroli.org`: **Infrastructure (Direct)**. Bypasses Traefik, points directly to the Host IP.
>
> **INGRESS & DNS ALIGNMENT RULE**
> Every host defined in a Traefik `IngressRoute` **MUST** have a corresponding alias in `rete.json` under the `traefik-lb` node. This ensures explicit DNS resolution and prevents "Black Hole Routing" issues after wildcard removal.

### Network Summary
| VLAN | ID | Subnet | Gateway | DHCP | Usage |
|---|---|---|---|---|---|
| **Server** | 10 | `10.10.10.0/24` | `10.10.10.254` | Static | TrueNAS, Proxmox Mgmt |
| **Client** | 20 | `10.10.20.0/24` | `10.10.20.1` | OPNsense | Talos Nodes, Personal Devices |
| **IoT** | 30 | `10.10.30.0/24` | `10.10.30.1` | - | *DEPRECATED / UNUSED* |
| **Tunnel** | - | `10.255.0.1/32` | - | Static | **Dummy IP** for Xray Tunnel Binding |
| **Transit** | - | `192.168.2.0/24` | `192.168.2.1` | - | Switch Interconnects |

### Operational Cheatsheet
**Canonical Configuration Philosophy**
> [!IMPORTANT]
> **AI MUST EXPLAIN, VERIFY & WAIT**
> 1. **Explain**: Prima di eseguire QUALSIASI comando, l'AI deve spiegare esplicitamente cosa fa il comando e perché.
> 2. **Execute & Show**: Eseguire il comando e mostrare l'output completo.
> 3. **Verify**: Analizzare il risultato per confermare il successo o identificare errori.
> 4. **Wait**: ATTENDERE l'autorizzazione esplicita dell'utente prima di procedere al passo successivo della catena operativa.
>
> **PRESERVE SYMMETRICAL ROUTING**
> Always prioritize solutions that maintain **Symmetrical Routing via switch10g** (ONT/Xikestor) for inter-VLAN internal traffic (e.g., VLAN 20 to VLAN 10).
> *Warning:* Alternative solutions (e.g., forcing internal traffic through OPNsense) are possible but strongly discouraged as they deviate from the chosen architecture, risking asymmetric routing issues and performance bottlenecks.
>
> **ALWAYS update `talos-config/controlplane.yaml` (or worker.yaml) first.**
> Do not rely on `talosctl patch` for permanent changes. Update the source of truth, then apply via `talosctl apply-config`.
>
> **MACOS LOGGING STRATEGY**
> For services running on macOS (Mac Studio), prioritize the "newsyslog" strategy:
> 1. Use `~/Library/Logs/<app-name>/` for persistent logs (macOS Standard).
> 2. Separate component logs (e.g., `engine.log` vs `exporter.log`).
> 3. MANDATORY: Configure `/etc/newsyslog.d/<app>.conf` for auto-rotation (10MB, gzip, 5 copies) to prevent disk saturation.
>
> **BEFORE MAJOR CHANGES (Upgrades, Refactors)**
> **ALWAYS run a manual backup:** `velero backup create backup-pre-change-$(date +%F) --wait`
> **After a command, ALWAYS check the response/logs and report the status.**

**Talos Cluster Management**
- **Talos Config**: `export TALOSCONFIG=talos-config/talosconfig`
- **Kube Config**: `export KUBECONFIG=talos-config/kubeconfig`
- **Dashboard**: `talosctl dashboard`
- **Node List**: `talosctl get members`
- **Config Info**: `talosctl config info`

**Key IPs**
- **Talos VIP**: `10.10.20.55`
- **Talos CP 01**: `10.10.20.141`
- **Talos CP 02**: `10.10.20.142` (VM ID: 2300)
- **Talos CP 03**: `10.10.20.143` (VM ID: 3200)
- **Postgres DB**: `10.10.20.57` (MetalLB External)
- **TrueNAS**: `10.10.10.50` (Storage/Management)
- **Talos CP 03**: `10.10.20.143` (VM ID: 3200)
- **Postgres DB**: `10.10.20.57` (MetalLB External)
- **TrueNAS**: `10.10.10.50` (Storage/Management)

### Safe Shutdown Procedure (Rack Power Off)
> [!WARNING]
> **NEVER** just pull the plug or use Proxmox "Shutdown All".
> Use the Ansible Playbook to ensure data consistency (Talos -> Database -> Storage -> Hypervisors).

1.  **Run Playbook**:
    ```bash
    ansible-playbook ansible/playbooks/shutdown_lab.yml --vault-password-file ~/.vault_pass.txt
    ```
2.  **Monitor Telegram**: Wait for confirmation messages ("Phase 1", "Phase 2", "TrueNAS Complete").
3.  **Physical Power**: Wait for lights out, then switch off PDU/UPS.

### Safe Startup Procedure (Rack Power On)
**Boot Order Logic is AUTOMATED via Proxmox Hooks.**
1.  **Power On**: Switch on PDU/UPS. Proxmox nodes will boot.
2.  **PVE1 (TrueNAS)**: Starts TrueNAS VM (ID 1100) first.
3.  **PVE2/3 (Compute)**: VMs (Talos, Jellyfin) will attempt start using `wait-for-truenas.sh` hook.
4.  **Monitor Telegram**:
    - You will see: `⏳ VM [ID] is starting... Checking TrueNAS...`
    - It will wait indefinitely until TrueNAS is pingable.
    - Once UP: `✅ TrueNAS is UP. Starting VM [ID].`
5.  **Cluster Quorum**: Wait ~5 minutes for Talos to form quorum. Verify with `k9s`.

---

## 2. Directory Organization

- **`ansible/`**: Active Automation.
  - `playbooks/opnsense_sync_dns.yml`: **Master Sync**. Syncs `rete.json` to both Unbound DNS and Kea DHCP.

- **`talos-config/`**: **Source of Truth** for Cluster Access.
  - Contains `talosconfig`, `controlplane.yaml`, `worker.yaml`.
- **`scripts/`**: Automation & Diagnostic Scripts.
  - Managed via **Interactive Launcher**: Use `./go` from the project root to run scripts.
  - **`utils/`**: Internal helper scripts (hidden from the launcher).
- **`xray/`**: OCI Proxy Configuration.
  - Contains `xray_secrets.yml`.
- **`secrets/`**: Global Environment Secrets.
  - Contains `setEnv.sh` (Traefik/OAuth variables).
  - Contains `google_client_secret.json` (Raw OAuth credentials).
- **`ansible/vars/secrets.yml`**: Encrypted Ansible Secrets (Cloudflare keys, SSH keys).
  - **Decryption**: `ansible-vault view ansible/vars/secrets.yml --vault-password-file ~/.vault_pass.txt`
  - **Vault Password**: Located at `~/.vault_pass.txt` (User Home Directory).
- **`kube-system/`**: Core Kubernetes system configurations (e.g., `metrics-server`).
- **`proxmox/`**: Scripts and hooks intended for local execution on Proxmox hypervisors.
  - `hooks/`: VM automated startup hooks.
  - `scripts/`: Manual maintenance scripts (e.g., disk swapping).
- **`storage/local-path/`**: CSI Local Path Provisioner configurations for node-local storage.
- **`_OLD_ARCHIVE/`**: Legacy/Stale files.
  - `ansible-venv`, old scripts, previous attempts, and deprecated `.yaml`/temp files.

---

## 3. Infrastructure Details

### Hardware & OS
- **Hypervisors**: 3x Proxmox VE (Debian 13/Trixie)
- **NAS**: TrueNAS SCALE (Debian-based) (VM ID: 1100)
- **Backup**: Proxmox Backup Server (PBS) (LXC ID: 1400, IP: 10.10.10.100)
- **Firewall**: OPNsense (FreeBSD)

### Load Balancing & Ingress
- **MetalLB**: `metallb/` (L2Advertisement to be defined)
- **Traefik**: `traefik/` (Ingress Controller + SSL)
- **DNS Strategy**: Split-DNS.
  - **Internal**: OPNsense Unbound (Authoritative for `.pindaroli.org` internal).
  - **External**: Cloudflare.
    - **Tunnel**: Use Cloudflare Tunnel for external access. **DO NOT use wildcard records for internal DNS** to avoid search path hijacking.
    - **Policy**: ALL Tunneled services must use `oauth2-auth`.

### Certs & Auth
- **Cert-Manager**: `cert-manager/` (Cloudflare DNS Challenge).
- **OAuth2 Proxy**: `oauth2-proxy/` (Google Auth for all services).

## 4. Workloads (Postgres Migrated)

### Media Stack (Servarr)
- **Namespace**: `arr`
- **Helm Chart Path**: `pindaroli/servarr` (Official Repo)
- **Deploy Command**: `helm upgrade --install servarr pindaroli/servarr -n arr -f servarr/arr-values.yaml`
- **Config**: `servarr/`
- **Services**: Jellyfin (LXC), Radarr (Nightly), Lidarr (Nightly), Prowlarr (Stable), qBittorrent (5.1.4).
- **External Jellyfin**: LXC ID 2200 on PVE3 (Migration Complete - v10.11.6).
- **Database**: PostgreSQL (CloudNativePG) exposed on `10.10.20.57`.
- **Status**: Radarr/Lidarr/Prowlarr Migrated. qBittorrent v5.1.4 Secured.
- **Transcoding (Tdarr)**: 
  - **Node**: Mac Studio M2 Ultra (10.10.20.100).
  - **Strategy**: **Tdarr Flows** (Standard 2024+). 
  - **Logic**: Clean -> Backup (`movies_backup`) -> HEVC Transcode (Apple VideoToolbox) -> Replace.
  - **Rationale**: I Flows garantiscono un'architettura più pulita e meno soggetta a errori rispetto ai Classic Plugins per operazioni multi-step.
- **Privacy**: Xray sidecars have been DEPRECATED/REMOVED for both qBittorrent and Prowlarr to ensure maximum performance and indexer connectivity. Traffic flows direct. qBittorrent is isolated via a dedicated LoadBalancer IP (10.10.20.60).

### Automation Stack (n8n)
- **Namespace**: `n8n`
- **Version**: `1.40.0`
- **Database**: PostgreSQL (CloudNativePG) consolidated in `postgres-main` (cnpg-system).
- **Status**: Migrated (Fresh Start).
- **Access**: `https://n8n.pindaroli.org`.

### Storage Integration
- **NFS CSI Driver**: `CSI-driver/`
- **Shares**:
  - `/mnt/oliraid/arrdata/media`
  - `/mnt/stripe/k8s-arr`

## 5. Reference Files
- **Network Source of Truth**: [rete.json](file:///Users/olindo/prj/k8s-lab/rete.json)
- **Ansible Inventory**: `ansible/inventory.ini`

## 6. Access Strategy

### External Access (Internet)
*   **URL**: `https://<service>.pindaroli.org`
*   **Method**: Cloudflare Tunnel -> Traefik VIP.
*   **Security**: **Strictly OAuth2 Protected** (Google Login).
*   **Note**: Transitioning from wildcard `*` to explicit host mapping for enhanced security.

### Internal Access (LAN/VPN)
*   **URL**: `https://<service>-internal.pindaroli.org` OR Short Hostnames.
*   **Method**: Split-DNS (OPNsense/Unbound) -> Traefik VIP (`10.10.20.56`).
*   **Security**: **Trusted Network** (No Auth / Optional Basic Auth).
*   **CRITICAL**: Internal DNS MUST use explicit mapping (no wildcards) to prevent routing loops during external DNS resolution (ndots issue).

## 7. Pending Maintenance

### PVE3 Recovery (When Hardware is Online)
**Problem**: PVE3 is currently offline (Hardware Failure).
**Action**: When node is back online (`10.10.10.31`), run these commands to align it with the cluster:

1.  **Deploy Hook Script**:
    ```bash
    scp proxmox/hooks/wait-for-truenas.sh root@10.10.10.31:/var/lib/vz/snippets/
    ```
2.  **Configure VM 3200 (Talos CP 03)**:
    ```bash
    # Remove CD-ROM (Fix Storage Dependency)
    ssh root@10.10.10.31 "qm set 3200 --ide2 none,media=cdrom"
    
    # Attach Hook Script & Boot Store Order
    ssh root@10.10.10.31 "qm set 3200 --onboot 1 --startup order=1 --hookscript local:snippets/wait-for-truenas.sh"
    ```
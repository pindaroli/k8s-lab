# Project GEMINI: Kubernetes Homelab Migration

> [!IMPORTANT]
> **Current Status**: **DATABASE MIGRATION COMPLETE**
> Servarr Stack migrated to PostgreSQL (Radarr, Lidarr, Prowlarr).
> **Active Goal**: Maintenance & Monitoring.

## 1. Quick Reference

### Security Policies
> [!CRITICAL]
> **EXTERNAL ACCESS & OAUTH**
> ALL services exposed via Cloudflare (External) MUST have **OAuth2 Authentication** enabled (Google Login).
> **NO EXCEPTIONS**. Even services with native login (like MinIO/TrueNAS) must sit behind the OAuth shield.
> *Implementation:* Traefik Middleware `oauth2-auth`.

### Network Summary
| VLAN | ID | Subnet | Gateway | DHCP | Usage |
|---|---|---|---|---|---|
| **Server** | 10 | `10.10.10.0/24` | `10.10.10.254` | Static | TrueNAS, Proxmox Mgmt |
| **Client** | 20 | `10.10.20.0/24` | `10.10.20.1` | OPNsense | Talos Nodes, Personal Devices |
| **IoT** | 30 | `10.10.30.0/24` | `10.10.30.1` | OPNsense | Isolated Devices |
| **Tunnel** | - | `10.255.0.1/32` | - | Static | **Dummy IP** for Xray Tunnel Binding |
| **Transit** | - | `192.168.2.0/24` | `192.168.2.1` | - | Switch Interconnects |

### Operational Cheatsheet
**Canonical Configuration Philosophy**
> [!IMPORTANT]
> **ALWAYS update `talos-config/controlplane.yaml` (or worker.yaml) first.**
> Do not rely on `talosctl patch` for permanent changes. Update the source of truth, then apply via `talosctl apply-config`.
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
- **Talos CP 02**: `10.10.20.142`
- **Talos CP 03**: `10.10.20.143`
- **Postgres DB**: `10.10.20.57` (MetalLB External)
- **TrueNAS**: `10.10.10.50` (Storage), `10.10.20.50` (Client)

---

## 2. Directory Organization

- **`ansible/`**: Active Automation.
  - `playbooks/dhcp_reservations.yml`: Sync Talos IPs to OPNsense.
  - `playbooks/opnsense_sync_dns.yml`: Sync `rete.json` hosts to Unbound.
- **`talos-config/`**: **Source of Truth** for Cluster Access.
  - Contains `talosconfig`, `controlplane.yaml`, `worker.yaml`.
- **`xray/`**: OCI Proxy Configuration.
  - Contains `xray_secrets.yml`.
- **`secrets/`**: Global Environment Secrets.
  - Contains `setEnv.sh` (Traefik/OAuth variables).
  - Contains `google_client_secret.json` (Raw OAuth credentials).
- **`ansible/vars/secrets.yml`**: Encrypted Ansible Secrets (Cloudflare keys, SSH keys).
  - **Decryption**: `ansible-vault view ansible/vars/secrets.yml --vault-password-file ~/.vault_pass.txt`
  - **Vault Password**: Located at `~/.vault_pass.txt` (User Home Directory).
- **`_OLD_ARCHIVE/`**: Legacy/Stale files.
  - `ansible-venv`, old scripts, previous attempts.

---

## 3. Infrastructure Details

### Hardware & OS
- **Hypervisors**: 3x Proxmox VE (Debian 13/Trixie)
- **NAS**: TrueNAS SCALE (Debian-based)
- **Firewall**: OPNsense (FreeBSD)

### Load Balancing & Ingress
- **MetalLB**: `metallb/` (L2Advertisement to be defined)
- **Traefik**: `traefik/` (Ingress Controller + SSL)
- **DNS Strategy**: Split-DNS.
  - **Internal**: OPNsense Unbound (Authoritative for `.pindaroli.org` internal).
  - **External**: Cloudflare.
    - **Tunnel**: Use Cloudflare Tunnel (Wildcard `*`) for ALL external access.
    - **Policy**: ALL Tunneled services must use `oauth2-auth`.

### Certs & Auth
- **Cert-Manager**: `cert-manager/` (Cloudflare DNS Challenge).
- **OAuth2 Proxy**: `oauth2-proxy/` (Google Auth for all services).

## 4. Workloads (Postgres Migrated)

### Media Stack (Servarr)
- **Namespace**: `arr`
- **Helm Chart Path**: `/Users/olindo/prj/helm/charts/servarr` (External)
- **Deploy Command**: `helm upgrade --install servarr /Users/olindo/prj/helm/charts/servarr -n arr -f servarr/arr-values.yaml`
- **Config**: `servarr/`
- **Services**: Jellyfin, *arr apps, qBittorrent.
- **Database**: PostgreSQL (CloudNativePG) exposed on `10.10.20.57`.
- **Status**: Radarr/Lidarr/Prowlarr Migrated. Readarr Cancelled (Unstable).
- **Privacy**: Transparent Xray Tunnel (Sidecar) for qBittorrent & Prowlarr.

### Storage Integration
- **NFS CSI Driver**: `CSI-driver/`
- **Shares**:
  - `/mnt/oliraid/arrdata/media`
  - `/mnt/stripe/k8s-arr`

## 5. Reference Files
- **Network Source of Truth**: [rete.json](file:///Users/olindo/prj/k8s-lab/rete.json)
- **Ansible Inventory**: `ansible/inventory.ini`
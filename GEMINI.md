# Project GEMINI: Kubernetes Homelab Migration

> [!IMPORTANT]
> **Current Status**: **MIGRATION PHASE** (Proxmox -> Talos Linux)
> We are currenly bootstrapping the Talos Cluster.
> **Active Goal**: Stabilize networking and storage before deploying workloads.

## 1. Quick Reference

### Network Summary
| VLAN | ID | Subnet | Gateway | DHCP | Usage |
|---|---|---|---|---|---|
| **Server** | 10 | `10.10.10.0/24` | `10.10.10.254` | Static | TrueNAS, Proxmox Mgmt |
| **Client** | 20 | `10.10.20.0/24` | `10.10.20.1` | OPNsense | Talos Nodes, Personal Devices |
| **IoT** | 30 | `10.10.30.0/24` | `10.10.30.1` | OPNsense | Isolated Devices |
| **Transit** | - | `192.168.2.0/24` | `192.168.2.1` | - | Switch Interconnects |

### Operational Cheatsheet
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

### Certs & Auth
- **Cert-Manager**: `cert-manager/` (Cloudflare DNS Challenge).
- **OAuth2 Proxy**: `oauth2-proxy/` (Google Auth for all services).

## 4. Workloads (Migration Pending)

### Media Stack (Servarr)
- **Namespace**: `arr`
- **Helm Chart**: `../helm/charts/servarr` (External Sibling Project - Shared Library)
- **Config**: `servarr/`
- **Services**: Jellyfin, *arr apps, qBittorrent.

### Storage Integration
- **NFS CSI Driver**: `CSI-driver/`
- **Shares**:
  - `/mnt/oliraid/arrdata/media`
  - `/mnt/stripe/k8s-arr`

## 5. Reference Files
- **Network Source of Truth**: [rete.json](file:///Users/olindo/prj/k8s-lab/rete.json)
- **Ansible Inventory**: `ansible/inventory.ini`
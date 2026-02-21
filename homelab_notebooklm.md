# Project GEMINI: Homelab Infrastructure Documentation
> **Document Status**: Active / Source of Truth for LLM Context
> **Last Updated**: 2026-02-16

## 1. Executive Summary
Project GEMINI represents the migration and modernization of a personal homelab environment. The core objective is to move from legacy standalone deployments to a fully declarative, high-availability Kubernetes cluster running on **Talos Linux**, hosted on a 3-node **Proxmox VE** cluster. Major components include **TrueNAS Scale** for storage, **OPNsense** for routing/firewalling, and a **Servarr** media stack backed by **PostgreSQL**.

---

## 2. Network Topology & Security
The network is segmented into VLANs to separate management traffic from client/iot traffic, strictly controlled by OPNsense.

### VLAN Structure
| Name | VLAN ID | Subnet | Role | Access Policy |
|---|---|---|---|---|
| **Server** | `10` | `10.10.10.0/24` | Management, Storage (TrueNAS), Hypervisors | Strictly Restricted. Admin access only. |
| **Client** | `20` | `10.10.20.0/24` | Talos Nodes, Personal Computers, WiFi | Trusted Network. Access to Services. |
| **IoT** | `30` | `10.10.30.0/24` | Smart Devices, Isolated Hardware | Internet Access Only. No LAN access. |
| **Transit**| `-` | `192.168.2.0/24`| Switch Interconnects | L3 Routing backbone. |

### Access Strategy (Split-DNS)
The lab uses a Split-DNS architecture to ensure optimal routing and security.
*   **External Access**: Users accessing `*.pindaroli.org` from the internet are routed through **Cloudflare Tunnel**. All requests MUST pass through **Google OAuth2** authentication (Traefik Middleware).
*   **Internal Access**: Users inside the LAN (VLAN 20) resolve `*.pindaroli.org` or short names (`home`, `nas`) directly to the internal Traefik VIP (`10.10.20.56`). Authentication is optional/bypassed for trusted devices.

---

## 3. Infrastructure Layer (Hypervisors & Storage)
The foundation runs on **Proxmox VE 9.1** (Debian 13 Trixie).

### Compute Nodes
*   **PVE (10.10.10.11)**: Host for TrueNAS (Storage) and PBS (Backup).
*   **PVE2 (10.10.10.21)**: Compute Node. Runs Media Server (LXC) and Talos CP.
*   **PVE3 (10.10.10.31)**: Compute Node. Runs Talos CP.

### Storage (TrueNAS Scale)
*   **Role**: Central NAS providing NFS shares to Kubernetes and VM backups.
*   **IPs**: `10.10.10.50` (Storage traffic), `10.10.20.50` (Direct Client access).
*   **Startup Logic**: Critical dependency. All other VMs wait for TrueNAS to be pingable via a custom hook script (`wait-for-truenas.sh`) before booting.

### Backup Strategy
*   **Proxmox Backup Server (PBS)**: LXC Container (`10.10.10.100`) saving snapshots to NFS.
*   **Velero**: Kubernetes disaster recovery tool, backing up cluster resources and PVCs to MinIO/S3.

---

## 4. Kubernetes Cluster (Talos Linux)
The application layer runs on a **Talos Linux** cluster (Version 1.12.0), treating the OS as immutable infrastructure.

### Cluster Nodes
*   **Control Plane 01**: `10.10.20.141` (VM on PVE)
*   **Control Plane 02**: `10.10.20.142` (VM on PVE2)
*   **Control Plane 03**: `10.10.20.143` (VM on PVE3)
*   **Virtual IP (VIP)**: `10.10.20.55` (High Availability Endpoint for API)

### Management
*   **Source of Truth**: `talos-config/` directory contains `controlplane.yaml` and `worker.yaml`.
*   **Operations**: Managed via `talosctl`. No SSH access to nodes (API only).

---

## 5. Services & Workloads
Major applications deployed via Helm and Flux (planned/in-progress).

### Media Stack (Namespace: `arr`)
*   **Apps**: Radarr, Lidarr, Prowlarr, qBittorrent.
*   **Readarr**: Cancelled due to instability.
*   **Database**: Migrated from SQLite to **CloudNativePG** (PostgreSQL) cluster (`10.10.20.57`).
*   **Privacy**: qBittorrent and Prowlarr traffic is routed through a transparent **Xray Sidecar** container connected to an Oracle Cloud (OCI) proxy for anonymity.

### Ingress & Connectivity
*   **Traefik**: Main Ingress Controller (`10.10.20.56`). Handles SSL termination (LetsEncrypt via Cert-Manager) and Routing.
*   **MetalLB**: Provides Layer 2 LoadBalancer IPs for Traefik (`.56`) and Postgres (`.57`).
*   **Cert-Manager**: Automates wildcard certificate (`*.pindaroli.org`) renewal via Cloudflare DNS challenge.

---

## 6. Automation & Maintenance
*   **Ansible**: `ansible/` contains playbooks for Day-2 operations:
    *   `shutdown_lab.yml`: Orchestrates safe shutdown (Kubernetes -> DB -> Storage -> Hypervisors).
    *   `dhcp_reservations.yml`: Syncs inventory IPs to OPNsense DHCP.
    *   `opnsense_sync_dns.yml`: Updates Unbound DNS config based on `rete.json`.
*   **Source of Truth**: The `rete.json` file is the master record for all IP addresses, MAC addresses, and VLAN assignments.

## 7. Known Issues & Pending Tasks
*   **PVE3 Recovery**: Node was offline for hardware failure. Recovery procedure involves deploying the storage hook script and verifying cluster quorum.
*   **Traffic Traversal**: ongoing monitoring of "Asymmetric Routing" issues between OPNsense and the L3 Switch.

---
*Created for ingestion by NotebookLM to provide full context on the Project GEMINI architecture.*

# Storage Strategy for Kubernetes Lab - NVMe/TCP Edition

## Overview
This document outlines a high-efficiency storage strategy for the `k8s-lab` cluster running on **Talos Linux**.
**Key Decision**: We accept a Single Point of Failure (SPOF) on the TrueNAS storage to prioritize performance and simplicity over High Availability (HA) complexity.

## Architecture
- **Compute**: 3x Talos Linux VMs on Proxmox (Converged Control Plane + Worker).
  - **Node Distribution**: 1 VM per Proxmox Node (`pve`, `pve2`, `pve3`).
- **Storage Backend**: TrueNAS Scale (`truenas`, IP `10.10.10.50`).
- **ETCD Storage**: Local VirtIO Block storage on each Proxmox node (low latency).
- **Protocols**:
  - **NVMe over TCP** (via Proxmox): *Reserved for high-performance single-instance DBs only.*
  - **NFS v4.1**: **Primary Storage** for `arr` stack (Config + Media) to ensure multi-node access (RWX).
  > [!NOTE]
  > **Strategy Update (2026-01-05)**: We attempted to use NVMe-TCP for qBittorrent Config, but reverted to NFS because the "One Disk per Node" rule of Block Storage prevented failover/migration without complex replication (Longhorn). NFS is the chosen standard for this cluster.

## Strategic Evaluation (Reference)
We evaluated three options. **Option B is selected** for implementation.

| Feature | Option A: Direct (Talos Initiator) | Option B: Proxmox-Mediated | Option C: Proxmox HCI |
| :--- | :--- | :--- | :--- |
| **Path** | TrueNAS -> Network -> Talos Kernel | TrueNAS -> Proxmox Kernel -> VirtIO Disk -> Talos | Local SSD -> Proxmox |
| **Verdict** | Too complex. | **SELECTED**. Best balance. | Alt. for Recovery. |

## Implementation Plan
The implementation is broken down into **5 Standalone Phases** for safe execution over multiple sessions:

1.  **[01_talos_setup.md](file:///Users/olindo/prj/k8s-lab/istruzioni/migration/01_talos_setup.md)**: Cluster Bootrap & Kernel Config (Custom ISO, 3 Nodes).
2.  **[02_storage_setup.md](file:///Users/olindo/prj/k8s-lab/istruzioni/migration/02_storage_setup.md)**: Truenas/Proxmox NVMe & Maintenance Script.
3.  **[03_data_recovery.md](file:///Users/olindo/prj/k8s-lab/istruzioni/migration/03_data_recovery.md)**: Data Migration via Recovery VM.
4.  **[04_k8s_manifests.md](file:///Users/olindo/prj/k8s-lab/istruzioni/migration/04_k8s_manifests.md)**: Final Kubernetes Configuration.
5.  **[05_proxmox_backup_setup.md](file:///Users/olindo/prj/k8s-lab/istruzioni/migration/05_proxmox_backup_setup.md)**: Proxmox Backup Server (PBS) & Cluster Backups.

## Storage Tiers

### 1. Hot Tier (Performance) - DEPRECATED / REMOVED
*Originally planned for: SQLite, Databases, Configs.*
*Status: **Abandoned** in favor of NFS (Soft Mounts).*
- **Reason**: Single disk prevented pod failover between nodes. NFS with proper caching/options proved sufficient for SQLite.
- **Action**: The Proxmox NVMe/TCP disk attachment has been removed.

#### Filesystem Choice
N/A - Disk removed.

### 2. Warm Tier (Capacity)
*Implementation: **NFS v4.1** (Direct)*

## Management & Browsing

### Solution 1: "FileBrowser" Pod (Daily Use)
A Web GUI (`https://files.pindaroli.org`) running inside Kubernetes.

### Solution 2: Automated Recovery Mode (Emergency)
To prevent accidental corruption via the Proxmox GUI:

**Safety Mechanism**: "Detached by Default"
1.  **Normal State**: The Hot Disk is ONLY present in the **Talos VM** config.
2.  **Maintenance State**: The Hot Disk is moved to the **Recovery VM**.

**The Automation Script (`maintenance-mode.sh`)**:
This script performs the physical swap of the disk configuration.
1.  `./maintenance-mode.sh on`: Detaches from Talos -> Attaches to Recovery -> Starts Recovery.
2.  `./maintenance-mode.sh off`: Detaches from Recovery -> Attaches to Talos -> Starts Talos.

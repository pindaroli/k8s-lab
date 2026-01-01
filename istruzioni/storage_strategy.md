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
  - **NVMe over TCP** (via Proxmox): For "Hot" block storage (App Data).
  - **NFS v4.1**: For "Warm/Cold" file storage (Media).

## Strategic Evaluation (Reference)
We evaluated three options. **Option B is selected** for implementation.

| Feature | Option A: Direct (Talos Initiator) | Option B: Proxmox-Mediated | Option C: Proxmox HCI |
| :--- | :--- | :--- | :--- |
| **Path** | TrueNAS -> Network -> Talos Kernel | TrueNAS -> Proxmox Kernel -> VirtIO Disk -> Talos | Local SSD -> Proxmox |
| **Verdict** | Too complex. | **SELECTED**. Best balance. | Alt. for Recovery. |

## Implementation Plan
The implementation is broken down into **4 Standalone Phases** for safe execution over multiple sessions:

1.  **[01_talos_setup.md](file:///Users/olindo/prj/k8s-lab/istruzioni/migration/01_talos_setup.md)**: Cluster Bootrap & Kernel Config (Custom ISO, 3 Nodes).
2.  **[02_storage_setup.md](file:///Users/olindo/prj/k8s-lab/istruzioni/migration/02_storage_setup.md)**: Truenas/Proxmox NVMe & Maintenance Script.
3.  **[03_data_recovery.md](file:///Users/olindo/prj/k8s-lab/istruzioni/migration/03_data_recovery.md)**: Data Migration via Recovery VM.
4.  **[04_k8s_manifests.md](file:///Users/olindo/prj/k8s-lab/istruzioni/migration/04_k8s_manifests.md)**: Final Kubernetes Configuration.

## Storage Tiers

### 1. Hot Tier (Performance)
*Used for: SQLite, Databases, Configs.*
*Implementation: **Local Path** (`local-path-provisioner`)*
- **Infrastructure**: One large Zvol on TrueNAS -> Exposed via NVMe/TCP -> Mounted by Proxmox -> Attached as Secondary Disk (`/dev/vdb`) to Talos VM.

#### Filesystem Choice
We explicitly choose **ext4** or **xfs** for the Talos guest filesystem to avoid "CoW on CoW" performance penalties.

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

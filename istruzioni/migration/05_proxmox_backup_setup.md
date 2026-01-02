# Phase 5: Proxmox Backup Server (PBS) Implementation
**Goal**: Implement enterprise-grade incremental backups for all Proxmox VMs (Talos, TrueNAS, etc.).
**Architecture**: PBS running in a lightweight LXC Container, storing data on TrueNAS (NFS).

## 1. Preparation (Storage)
PBS needs a place to store deduplicated chunks. We will use the existing TrueNAS.

- [ ] **TrueNAS Config**:
    - Create Dataset: `oliraid/backups/pbs` (Enable Compression: `lz4` or `zstd`).
    - **NFS Share**: Export `/mnt/oliraid/backups/pbs`.
        - *Mapall User*: `root` (or a specific backup user).
        - *Allowed Hosts*: IP of the Proxmox Host running PBS (e.g., `10.10.10.11`).

## 2. Install PBS (LXC Method)
We will host PBS on `pve` (Node 1) as a privileged LXC for easier NFS mounting, or use a VM.
*Recommendation: Use a small VM (2 vCPU, 2GB RAM) for maximum stability and easy NFS mounting, or a Privileged LXC.*

### Option A: The "Easy" Way (Tteck Script)
- [ ] **Run on PVE Shell**:
    ```bash
    bash -c "$(wget -qLO - https://github.com/tteck/Proxmox/raw/main/ct/proxmox-backup-server.sh)"
    ```
    - Follow prompts.
    - IP: `10.10.10.60/24` (Example).

### Option B: Manual LXC
- [ ] Create Debian 12 LXC.
- [ ] Install packages:
    ```bash
    wget https://enterprise.proxmox.com/debian/proxmox-release-bookworm.gpg -O /etc/apt/trusted.gpg.d/proxmox-release-bookworm.gpg
    echo "deb http://download.proxmox.com/debian/pbs bookworm pbs-no-subscription" > /etc/apt/sources.list.d/pbs.list
    apt update && apt install proxmox-backup-server
    ```

## 3. Storage Configuration
Connecting PBS to the Storage Backend.

- [ ] **Mount NFS (Inside PBS)**:
    - Install client: `apt install nfs-common`.
    - Edit `/etc/fstab`:
        ```text
        10.10.10.50:/mnt/oliraid/backups/pbs /mnt/datastore/pbs-store nfs defaults 0 0
        ```
    - Mount: `mount -a`.
    - *Verify*: `df -h` shows the TrueNAS space.

- [ ] **Create Datastore (Web UI)**:
    - Access `https://10.10.10.60:8007`.
    - **Add Datastore**:
        - Name: `truenas-nfs`.
        - Path: `/mnt/datastore/pbs-store`.
        - Prune Options: Keep Daily: 7, Keep Weekly: 4.

## 4. Connect Proxmox to PBS
Now tell the Proxmox Cluster to use this new backup server.

- [ ] **Get Fingerprint**:
    - PBS Dashboard -> Dashboard -> Show Fingerprint.
- [ ] **Add Storage (Datacenter)**:
    - Proxmox GUI -> Datacenter -> Storage -> Add -> **Proxmox Backup Server**.
    - ID: `pbs`.
    - Server: `10.10.10.60`.
    - Username: `root@pam`.
    - Password: (Your PBS root password).
    - Datastore: `truenas-nfs`.
    - Fingerprint: (Paste it).

## 5. Configure Backup Jobs
- [ ] **Create Job**:
    - Datacenter -> Backup -> Add.
    - Nodes: All.
    - Storage: `pbs`.
    - Schedule: Daily (e.g., `03:00`).
    - Selection: All VMs (Talos CP 1-3, TrueNAS, etc.).
    - Mode: **Snapshot**.

## 6. Verification
- [ ] **Run Manual Backup**: Select a small VM -> Backup Now.
- [ ] **Restore Test**: Try "File Restore" on a backup to see if you can browse contents.

# Phase 3: Data Migration (Recovery Mode)
**Goal**: Move existing data from NFS snapshots to the new Local Hot tier.
**Prerequisites**: Phases 1 & 2 Complete. Old data exists on TrueNAS NFS share.

## 1. Prepare Recovery VM
- [ ] **Create VM**: Standard Debian/Ubuntu VM on Proxmox (ID 900).
- [ ] **Install Tools**: `apt install rsync nfs-common`.

## 2. Enter Maintenance Mode
- [ ] **Run Script**:
    ```bash
    /root/maintenance-mode.sh on
    ```
    - *Verifies*: Talos stops. Disk attaches to Recovery. Recovery starts.

## 3. Perform Migration
- [ ] **SSH into Recovery VM**.
- [ ] **Mount New Hot Disk**:
    ```bash
    mkdir -p /mnt/new_hot
    mount /dev/sdb /mnt/new_hot # Format with ext4 if first time: mkfs.ext4 /dev/sdb
    ```
- [ ] **Mount Old NFS Source**:
    ```bash
    mkdir -p /mnt/old_nfs
    mount 10.10.10.50:/mnt/stripe/k8s-arr /mnt/old_nfs
    ```
- [ ] **Copy Data**:
    - **Apps to Copy**: Radarr, Sonarr, Lidarr, Readarr, Prowlarr, Bazarr, Jellyseerr.
    - **SKIP**: **Jellyfin** (External Service - Config managed on LXC), **Transcoder** (Temp).
    ```bash
    # Example for Radarr
    rsync -avP /mnt/old_nfs/radarr-config/ /mnt/new_hot/radarr-config/
    # Repeat for others. Ensure directory structure matches what PVC expects (usually root of PVC).
    ```
    *Note: Since we are moving from many PVCs to one big disk with potentially subpaths, check your HostPath structure.*
    *Recommendation: Create subfolders for each PV `mkdir /mnt/new_hot/radarr-config` etc.*

- [ ] **Unmount**:
    ```bash
    umount /mnt/new_hot
    umount /mnt/old_nfs
    poweroff
    ```

## 4. Return to Operation
- [ ] **Run Script**:
    ```bash
    /root/maintenance-mode.sh off
    ```
    - *Verifies*: Recovery stops. Disk attaches to Talos. Talos starts.

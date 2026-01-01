# Phase 2: Storage Activation (NVMe/TCP)
**Goal**: Enable high-performance block storage backend on TrueNAS and attach it to Proxmox.
**Prerequisites**: Phase 1 Complete.

## 1. TrueNAS Scale Config
- [ ] **Create Zvol**:
    - Pool: `stripe`
    - Name: `proxmox-hot`
    - Size: 100GB (or as needed)
    - Type: Sparse (Thin Provisioning)
- [ ] **Enable Service**: System Settings > Services > **NVMe-oF**.
- [ ] **Create Target**:
    - Sharing > NVMe-oF Subsystems > Add.
    - Port: `4420`.
    - Transport: `TCP`.
    - Namespace: Linked to `stripe/proxmox-hot`.

## 2. Proxmox Host Config
- [ ] **Add Storage**:
    - Datacenter > Storage > Add > **NVMe/TCP** (or iSCSI).
    - ID: `truenas-nvme`.
    - Portal: `10.10.10.50`.
    - Target: Select the subsystem created above.
- [ ] **Create Safety Script**:
    - Create file `/root/maintenance-mode.sh` on Proxmox.
    - Paste content:
    ```bash
    #!/bin/bash
    # ADJUST IDs TO YOUR ENV
    TALOS_ID=100
    RECOVERY_ID=900
    DISK_ID="scsi1"
    DISK_PATH="/dev/disk/by-id/nvme-TrueNAS_..." # Find exact path via 'ls -l /dev/disk/by-id/'

    case "$1" in
      on)
        echo "Entering Maintenance Mode (Recovery)..."
        qm stop $TALOS_ID && qm set $TALOS_ID --delete $DISK_ID
        qm set $RECOVERY_ID --$DISK_ID $DISK_PATH
        qm start $RECOVERY_ID
        ;;
      off)
        echo "Exiting Maintenance Mode (Talos)..."
        qm stop $RECOVERY_ID && qm set $RECOVERY_ID --delete $DISK_ID
        qm set $TALOS_ID --$DISK_ID $DISK_PATH
        qm start $TALOS_ID
        ;;
      *)
        echo "Usage: $0 {on|off}"
        ;;
    esac
    ```
    - Make executable: `chmod +x /root/maintenance-mode.sh`.

## 3. Attach to Talos (Initial Setup)
- [ ] **Attach**: Run `./maintenance-mode.sh off` to attach the disk to Talos.
- [ ] **Update Talos Config**:
    - Edit `controlplane.yaml` (since all are CPs).
    - Add Mount:
    ```yaml
    machine:
      kubelet:
        extraMounts:
          - destination: /var/mnt/hot
            type: bind
            source: /var/mnt/hot
            options:
              - bind
              - rshared
              - rw
      disks:
        - device: /dev/vdb # Check exact device name inside Talos
          partitions:
            - mountpoint: /var/mnt/hot
    ```
    - **Apply & Reboot**: `talosctl apply-config ...`

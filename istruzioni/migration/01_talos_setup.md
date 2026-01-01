# Phase 1: Talos Cluster Implementation
**Goal**: Replace MicroK8s with an immutable Talos Linux cluster on Proxmox.
**Architecture**: 3 VMs (1 per Proxmox Node). ALL "Control Plane + Worker" (Converged).
**ETCD Storage**: Using Local VM Disk (VirtIO) backed by `local-lvm` (NVMe/SSD).
**Status**: [ ] Not Started

## 1. Prepare Custom Talos ISO
Since we need specific extensions for Proxmox and NVMe/TCP tools, we must generate a custom image.

- [ ] **Go to Image Factory**: Visit [factory.talos.dev](https://factory.talos.dev/).
- [ ] **Select Settings**:
    - **Hardware**: Generic / QEMU
    - **Version**: Latest Stable (v1.9.x)
    - **Extensions**:
        - `siderolabs/qemu-guest-agent` (Critical for Proxmox IP reporting & Shutdown).
        - `siderolabs/util-linux-tools` (For `mkfs`, `lsblk` debugging).
        - `siderolabs/iscsi-tools` (Optional fallback).
- [ ] **Download**: 
    - Download the **ISO** (to upload to Proxmox).
    - Note the **Factory Image ID** (e.g., `factory.talos.dev/image/...`).

## 2. Create VMs (Proxmox)
Create 3 identical VMs, one on `pve`, one on `pve2`, one on `pve3`.

- [ ] **VM Configuration**:
    - **General**: Name: `talos-cp-01` / `02` / `03`. Start at boot: Yes.
    - **OS**: Linux 6.x - 2.6 Kernel. Select the Custom ISO.
    - **System**: QEMU Agent: **Enabled**.
    - **Disks**:
        - **Bus**: VirtIO Block.
        - **Storage**: `local-lvm` (Proxmox Local SSD/NVMe).
        - **Size**: 32GB (OS + PVCs for local storage).
        - *Note*: **Do not** attach the "Hot NVMe" disk yet.
    - **CPU**: 2 (or 4) vCores. Type: `host`.
    - **Memory**: 4GB (Min) - 8GB (Recommended).
    - **Network**: Bridge `vmbr0` (LAN). Model: VirtIO.

## 3. Generate Configuration
- [ ] **Install talosctl**: `brew install siderolabs/tap/talosctl` (on Mac).
- [ ] **Generate Configs**:
    - Pick an unused IP for the VIP (e.g., `10.10.20.55`).
    ```bash
    talosctl gen config k8s-lab https://<VIP_OR_NODE1_IP>:6443 \
      --install-image factory.talos.dev/installer/<YOUR_IMAGE_ID>
    ```
- [ ] **Edit `controlplane.yaml`**:
    **This config applies to ALL 3 nodes.**
    - **Allow Scheduling on CP**:
    ```yaml
    cluster:
      allowSchedulingOnControlPlanes: true
    ```
    - **Enable NVMe/TCP Kernel Modules**:
    ```yaml
    machine:
      kernel:
        modules:
          - nvme-tcp
          - nvme-fabrics
      sysctls:
        net.ipv4.tcp_window_scaling: "1"
        net.core.rmem_max: "16777216"
        net.core.wmem_max: "16777216"
    ```

## 4. Bootstrap Cluster
- [ ] **Apply Config**:
    ```bash
    # Node 1 (pve)
    talosctl apply-config --insecure --nodes <IP_NODE_1> --file controlplane.yaml
    # Node 2 (pve2)
    talosctl apply-config --insecure --nodes <IP_NODE_2> --file controlplane.yaml
    # Node 3 (pve3)
    talosctl apply-config --insecure --nodes <IP_NODE_3> --file controlplane.yaml
    ```
- [ ] **Bootstrap**:
    - Pick ONE node to bootstrap.
    ```bash
    talosctl bootstrap --nodes <IP_NODE_1>
    ```
- [ ] **Setup `talosctl` client**:
    ```bash
    talosctl config endpoint <IP_NODE_1> <IP_NODE_2> <IP_NODE_3>
    talosctl kubeconfig .
    ```

## 5. Verification
- [ ] **Check Nodes**: `kubectl get nodes` -> Should show 3 Ready nodes.
- [ ] **Check QEMU Agent**: Check Proxmox GUI -> Summary -> IPs should be visible.
- [ ] **Check NVMe Module**:
    ```bash
    talosctl ssh -n <IP_NODE_1> "lsmod | grep nvme"
    ```

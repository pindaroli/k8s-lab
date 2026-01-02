# Phase 1: Talos Cluster Implementation
**Goal**: Replace MicroK8s with an immutable Talos Linux cluster on Proxmox.
**Architecture**: 3 VMs (1 per Proxmox Node). ALL "Control Plane + Worker" (Converged).
**ETCD Storage**: Using Local VM Disk (VirtIO) backed by `local-lvm` (NVMe/SSD).
**Status**: [ ] Not Started

## 1. Prepare Custom Talos ISO
Since we need specific extensions for Proxmox and NVMe/TCP tools, we must generate a custom image.

- [x] **Go to Image Factory**: Visit [factory.talos.dev](https://factory.talos.dev/).
- [x] **Select Settings**:
    - **Hardware**: Generic / QEMU
    - **Version**: 1.12.0 (NoCloud)
    - **Extensions**:
        - `siderolabs/qemu-guest-agent` (Critical for Proxmox).
        - `siderolabs/util-linux-tools` (Debug tools).
        - `siderolabs/nfs-utils` (NFSv3 compatibility).
        - `siderolabs/nvme-cli` (Optional but good for debug).
        - **Note**: Ensure `amdgpu` is UNSELECTED.
- [x] **Download**: 
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
    - **CPU**: 4 vCores. Type: `host`.
    - **Memory**: 8GB.
    - **Network**: Bridge `vmbr20` (VLAN 20 - Client/Cluster). Model: VirtIO.

## 3. Generate Configuration
- [x] **Install talosctl**: `brew install siderolabs/tap/talosctl` (on Mac).
- [x] **Generate Configs**:
    - Pick an unused IP for the VIP (e.g., `10.10.20.55`).
    ```bash
    talosctl gen config k8s-lab https://10.10.20.55:6443 \
      --install-image factory.talos.dev/installer/1fa08dac4d39afb03631c18f62f95af7251864bb4e4db68191b12268c840dd09:v1.12.0
    ```
- [x] **Edit `controlplane.yaml`**:
    **This config applies to ALL 3 nodes.**
    - [x] **Allow Scheduling on CP**:
    ```yaml
    cluster:
      allowSchedulingOnControlPlanes: true
    ```
    - [x] **Enable NVMe/TCP Kernel Modules**:
    ```yaml
    machine:
      sysctls:
        net.ipv4.tcp_window_scaling: "1"
        net.core.rmem_max: "16777216"
        net.core.wmem_max: "16777216"
      kernel:
        modules:
          - name: nvme-tcp
          - name: nvme-fabrics
    ```

## 4. Bootstrap Cluster
- [x] **Apply Config**:
    ```bash
    # Node 1 (pve)
    talosctl apply-config --insecure --nodes <IP_NODE_1> --file controlplane.yaml
    # Node 2 (pve2)
    talosctl apply-config --insecure --nodes <IP_NODE_2> --file controlplane.yaml
    # Node 3 (pve3)
    talosctl apply-config --insecure --nodes <IP_NODE_3> --file controlplane.yaml
    ```
- [x] **Bootstrap**:
    - Pick ONE node to bootstrap.
    ```bash
    talosctl bootstrap --nodes <IP_NODE_1>
    ```
- [x] **Setup `talosctl` client**:
    ```bash
    talosctl config endpoint <IP_NODE_1> <IP_NODE_2> <IP_NODE_3>
    talosctl kubeconfig .
    ```

## 5. Verification
- [x] **Check Nodes**: `kubectl get nodes` -> Should show 3 Ready nodes.
- [x] **Check QEMU Agent**: Check Proxmox GUI -> Summary -> IPs should be visible.
- [x] **Check NVMe Module**:
    ```bash
    talosctl ssh -n <IP_NODE_1> "read /proc/modules | grep nvme"
    ```

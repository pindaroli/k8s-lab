# Servarr Stack Installation

## Prerequisites

1. Install NFS CSI driver:
```bash
helm repo add csi-driver-nfs https://raw.githubusercontent.com/kubernetes-csi/csi-driver-nfs/master/charts
helm repo update

helm install csi-driver-nfs csi-driver-nfs/csi-driver-nfs \
    --namespace kube-system \
    --set kubeletDir=/var/snap/microk8s/common/var/lib/kubelet
```

2. Create storage volumes:
```bash
kubectl apply -f arr-volumes-csi.yaml 
```

## Storage Strategy
This deployment uses a **Hybrid Storage Strategy** to balance Performance and Capacity:

| Data Type | Path | Storage Class | Backend | Naming Conv. |
| :--- | :--- | :--- | :--- | :--- |
| **Configs / DBs** | `/config` | `local-path` | **NVMe (Hot)** | `{{ .PVC.Name }}` (e.g. `servarr-radarr-config`) |
| **Media Library** | `/media` | `nfs-csi` | **TrueNAS (Warm)** | `servarr-jellyfin-media` (Static PV) |

### Directory Naming
- **Local Path Provisioner** is configured with `pathPattern: "{{ .PVC.Name }}"`.
- This ensures that configuration directories on the host NVMe disk (`/var/mnt/hot/`) are clean and readable (e.g., `/var/mnt/hot/servarr-sonarr-config`).
- **NO RANDOM SUFFIXES**: The default random UUIDs are disabled.

## Installation

Install servarr stack from local Helm chart:
```bash
helm install servarr /Users/olindo/prj/helm/charts/servarr -n arr --create-namespace -f arr-values.yaml
```

## Management

- **List releases**: `helm list -n arr`
- **Get values**: `helm get values servarr -n arr`
- **Upgrade**: `helm upgrade servarr ../helm/charts/servarr -n arr -f servarr/arr-values.yaml`
- **Uninstall**: `helm uninstall servarr -n arr`

## Node Affinity Configuration

### Jellyfin Pod Placement
- **Primary**: Runs on `k8s-control` node
- **Failover**: Moves to `k8s-runner-1` only if `k8s-control` is down
- **Configuration**: Node affinity rules in `arr-values.yaml`

#### Behavior
- Normal operation: Jellyfin on k8s-control
- Node failure: Automatic failover to k8s-runner-1 (300s grace period)
- Recovery: Manual pod restart needed to return to k8s-control

#### Check Status
```bash
kubectl get pods -n arr -o wide | grep jellyfin
```

## Privacy & Networking (Tunnel)

Traffic for **qBittorrent** (Download) and **Prowlarr** (Search) is transparently routed through an encrypted **VLESS/Reality** tunnel to an external Oracle Cloud VPS.

### Architecture: The "Sidecar" Pattern
Each tunneled pod runs 3 containers:
1.  **Application** (qBittorrent/Prowlarr): Binds to `tun0`.
2.  **Xray Core**: Establishes the connection to the remote VPS (SOCKS5 on `127.0.0.1:10808`).
3.  **Tun2Socks**: Creates the `tun0` network interface and routes traffic into the SOCKS5 proxy.

### Critical Configurations

#### 1. qBittorrent - `tun0` Binding Fix
qBittorrent refuses to bind to a network interface without an IP address. `tun2socks` creates a Layer 3 tunnel but doesn't assign an IP by default.
**Fix**: We inject a dummy static IP (`10.255.0.1/32`) to the `tun0` interface during pod startup.
- **Config**: `Arr-Values.yaml` -> `extraContainers` -> `tun2socks` args.
- **App Setting**: qBittorrent -> Advanced -> Network Interface: `tun0`.
- **Note**: `UPnP` must be **DISABLED**.

#### 2. Prowlarr - Privileged Mode
Prowlarr requires similar tunneling. However, `tun2socks` must run in **Privileged Mode** (`privileged: true`) alongside `NET_ADMIN` capabilities to correctly manipulate the pod's routing table.

#### 3. Verification
To verify the tunnel is active:
```bash
# Check External IP (Should be Oracle Cloud IP, not Home ISP)
kubectl exec -n arr deploy/servarr-prowlarr -c servarr -- curl -s https://ifconfig.me
```
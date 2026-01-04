# MetalLB Configuration for GEMINI (Talos Linux)

This directory contains the Load Balancer configuration for the Talos Kubernetes cluster. It enables Layer 2 (ARP) load balancing on the Client VLAN (20).

## Architecture

- **Cluster**: Talos Linux (3 Control Plane Nodes)
- **Mode**: Layer 2 (ARP-based)
- **Network**: VLAN 20 Client Network (`10.10.20.0/24`)
- **IP Pool**: `10.10.20.56 - 10.10.20.60` (5 IPs)
  - *Note: Starts at .56 to avoid conflict with Talos VIP (.55)*

## Configuration Files

| File | Role | Description |
|---|---|---|
| **`values.yaml`** | **Installation Config** | Helm Chart overrides. Configures Pod tolerations for Control Plane nodes and security contexts for the controller. |
| **`metallb-speaker-security.yaml`** | **Security Patch** | **CRITICAL**. A post-install patch for "Speaker" pods. Grants `NET_ADMIN` and `privileged` access required to broadcast ARP packets on Talos/hardened OS. |
| **`metallb-complete.yaml`** | **Functional Config** | Defines the *Namespace*, *IPAddressPool* (Range), and *L2Advertisement*. Applies the logic of *what* IPs to serve. |

## Installation Procedure

The deployment must follow this specific order to handle permissions and CRDs correctly.

### 1. Prepare Namespace
Manually create the namespace and apply Pod Security Standards to allow privileged containers (required for ARP).
```bash
kubectl create ns metallb-system
kubectl label ns metallb-system \
  pod-security.kubernetes.io/enforce=privileged \
  pod-security.kubernetes.io/audit=privileged \
  pod-security.kubernetes.io/warn=privileged \
  --overwrite
```

### 2. Install MetalLB (Helm)
Installs the binaries, keys, and Custom Resource Definitions (CRDs).
```bash
helm repo add metallb https://metallb.github.io/metallb
helm repo update
helm upgrade --install metallb metallb/metallb -n metallb-system -f metallb/values.yaml
```

### 3. Apply Configuration
Defines the IP pool and advertisement strategy.
```bash
kubectl apply -f metallb/metallb-complete.yaml
```

### 4. Patch Speakers (If Needed)
If Speaker pods show "Permission Denied" in logs, apply the security boost.
```bash
kubectl patch daemonset metallb-speaker -n metallb-system --patch-file metallb/metallb-speaker-security.yaml
```

---

## Verification

**Check Status:**
```bash
kubectl get pods -n metallb-system
kubectl get ipaddresspool -n metallb-system
```

**Test Assignment:**
Deploy a test service or check Traefik (once deployed).
```bash
kubectl get svc -A | grep LoadBalancer
```

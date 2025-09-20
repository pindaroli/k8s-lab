# MetalLB Configuration for k8s-lab

MetalLB provides LoadBalancer services for bare metal Kubernetes clusters. This configuration enables Layer 2 load balancing with IP addresses from the local network range.

## Architecture

- **IP Pool**: `192.168.1.3-192.168.1.13` (11 available IPs)
- **Mode**: Layer 2 (ARP-based)
- **Network**: Local subnet `192.168.1.0/24`
- **Cluster**: microk8s 2-node cluster

## Files

### Core Configuration
- **`metallb-complete.yaml`** - Complete MetalLB configuration including namespace, IP pool, and L2 advertisement
- **`values.yaml`** - Helm values for MetalLB installation
- **`metallb-speaker-security.yaml`** - Security context patch for speaker pods (fixes ARP permission issues)

### Installation Methods

#### Method 1: Direct YAML Application (Recommended)
```bash
# Apply complete configuration
kubectl apply -f metallb-complete.yaml

# Install MetalLB via Helm with custom values
helm repo add metallb https://metallb.github.io/metallb
helm install metallb metallb/metallb -n metallb-system -f values.yaml

# Apply speaker security patch to fix ARP permissions
kubectl patch daemonset metallb-speaker -n metallb-system --patch-file metallb-speaker-security.yaml
```

#### Method 2: Step by Step
```bash
# 1. Create namespace with Pod Security labels
kubectl apply -f metallb-complete.yaml

# 2. Install MetalLB
helm repo add metallb https://metallb.github.io/metallb
helm install metallb metallb/metallb -n metallb-system -f values.yaml

# 3. Configure IP pool and L2 advertisement
kubectl apply -f metallb-complete.yaml

# 4. Fix speaker permissions
kubectl patch daemonset metallb-speaker -n metallb-system --patch-file metallb-speaker-security.yaml
```

## Verification

```bash
# Check MetalLB pods
kubectl get pods -n metallb-system

# Check IP pool and L2 advertisement
kubectl get ipaddresspool,l2advertisement -n metallb-system

# Check speaker logs (should show no "permission denied" errors)
kubectl logs -n metallb-system -l app.kubernetes.io/component=speaker

# Test with a LoadBalancer service
kubectl get svc -o wide | grep LoadBalancer
```

## Troubleshooting

### Common Issues

**1. "bind: permission denied" errors in speaker logs**
- Solution: Apply `metallb-speaker-security.yaml` patch
- Root cause: MetalLB speaker needs privileged access for ARP operations

**2. LoadBalancer services stuck in "Pending" state**
- Check IP pool: `kubectl get ipaddresspool -n metallb-system`
- Check L2 advertisement: `kubectl get l2advertisement -n metallb-system`
- Verify speaker pods are running: `kubectl get pods -n metallb-system`

**3. External IP assigned but not reachable**
- Check ARP table: `arp -a | grep <external-ip>`
- Test Layer 2 connectivity: `arping <external-ip>`
- Verify network interfaces support ARP

### Pod Security Standards

The namespace is configured with `pod-security.kubernetes.io/enforce: privileged` labels to allow MetalLB speaker pods to perform network operations required for ARP responses.

### Security Context

MetalLB speaker pods run with:
- `privileged: true`
- `hostNetwork: true`
- Capabilities: `NET_ADMIN`, `NET_RAW`, `SYS_ADMIN`, `NET_BIND_SERVICE`

This configuration is required for Layer 2 mode ARP operations in Kubernetes environments with Pod Security Standards.

## Network Configuration

Current LoadBalancer services:
- Traefik: `192.168.1.3` (ports 80/443)

IP allocation is automatic from the configured pool (`192.168.1.3-192.168.1.13`).

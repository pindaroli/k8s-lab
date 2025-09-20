# Hybrid Traffic Flow Architecture

## Overview

This document describes the hybrid traffic flow architecture implemented to resolve the Cloudflare tunnel bypass issue while maintaining MetalLB's role in the infrastructure.

## Problem Statement

The original issue was that Cloudflare tunnel was bypassing MetalLB entirely by routing traffic directly to Kubernetes services via service discovery, which prevented proper external load balancing functionality.

## Solution: Hybrid Architecture

### Traffic Flow Design

```
Internet → Cloudflare Edge → Cloudflare Tunnel → Traefik Service (Cluster IP) → Application Pods
                                                          ↓
External LAN ← MetalLB (Layer 2) ← Traefik LoadBalancer Service ← Same Application Pods
```

### Components

#### 1. External Traffic (Internet → Applications)
- **Route**: Internet → Cloudflare → Cloudflare Tunnel → Traefik Service (Cluster IP)
- **Service**: `traefik.traefik.svc.cluster.local:9443`
- **Advantages**:
  - Zero Trust security through Cloudflare
  - Automatic SSL/TLS termination
  - Global CDN and DDoS protection
  - No port forwarding required

#### 2. Internal/LAN Traffic (Local Network → Applications)
- **Route**: LAN → MetalLB External IP → Traefik LoadBalancer Service → Applications
- **Service**: `192.168.1.3:443` (MetalLB-assigned IP)
- **Advantages**:
  - Direct local access without internet dependency
  - Full MetalLB load balancing capabilities
  - Lower latency for local connections
  - Preserves existing MetalLB infrastructure

### Implementation Details

#### Cloudflare Tunnel Configuration
```yaml
ingress:
  - hostname: "*.pindaroli.org"
    service: https://traefik.traefik.svc.cluster.local:9443
    originRequest:
      noTLSVerify: true
```

#### MetalLB Configuration
```yaml
apiVersion: metallb.io/v1beta1
kind: IPAddressPool
metadata:
  name: my-ip-pool
  namespace: metallb-system
spec:
  addresses:
    - 192.168.1.3-192.168.1.13
```

#### Traefik Service Configuration
- **Type**: LoadBalancer (for MetalLB)
- **External IP**: 192.168.1.3 (assigned by MetalLB)
- **Cluster IP**: 10.152.183.193 (for internal routing)
- **Ports**:
  - 9080 (HTTP) → 80 (external)
  - 9443 (HTTPS) → 443 (external)

## Benefits

### 1. No MetalLB Bypass
- Cloudflare tunnel uses cluster-internal routing to Traefik service
- MetalLB maintains its role for external LAN connectivity
- Both traffic paths converge at the same Traefik instance

### 2. Redundant Connectivity
- Applications accessible via both internet (Cloudflare) and LAN (MetalLB)
- Failover capabilities between routes
- Independent scaling of external vs internal traffic

### 3. Security
- Internet traffic protected by Cloudflare Zero Trust
- Local traffic secured by Kubernetes RBAC and network policies
- No exposed ports on firewall for internet access

### 4. Performance
- Internet traffic benefits from Cloudflare's global network
- Local traffic has direct, low-latency access
- Both paths optimized for their use case

## Configuration Files

| File | Purpose |
|------|---------|
| `cloudflare/cloudflared-deployment.yaml` | Cloudflare tunnel configuration with cluster IP routing |
| `metallb/metallb-complete.yaml` | MetalLB IP pool and L2 advertisement |
| `traefik/traefik-values.yaml` | Traefik Helm values with LoadBalancer service |

## Monitoring and Troubleshooting

### Health Checks

#### Cloudflare Tunnel
```bash
kubectl logs -l app=cloudflared -n default --tail=20
```

#### MetalLB External Access
```bash
curl -k -I https://192.168.1.3
```

#### Service Discovery
```bash
kubectl get svc traefik -n traefik
kubectl get endpoints traefik -n traefik
```

### Common Issues

1. **502 Bad Gateway**: Usually indicates connectivity issues between tunnel and service
2. **Timeout Errors**: Check service ports and cluster DNS resolution
3. **MetalLB Not Responding**: Verify L2 advertisement and speaker pods

## Future Enhancements

1. **Load Balancing**: Consider multiple Cloudflare tunnel replicas
2. **Monitoring**: Implement metrics collection for both traffic paths
3. **Automation**: Add health checks and automatic failover logic
4. **Documentation**: Service-specific routing documentation

---

*Architecture implemented: September 2025*
*Status: Phase 1 completed, Phase 4 debugging in progress*
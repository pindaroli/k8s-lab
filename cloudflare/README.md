# Cloudflare Tunnel Configuration for k8s-lab

This directory contains the Cloudflare tunnel configuration for secure external access to the k8s-lab cluster using Zero Trust networking.

## Overview

The Cloudflare tunnel provides secure external access to the k8s-lab cluster without exposing ports on the firewall. All internet traffic flows through Cloudflare's edge network to the internal Traefik ingress controller.

## Architecture

### Hybrid Traffic Flow
```
Internet Traffic:
Internet → Cloudflare Edge → Cloudflare Tunnel → Traefik Service (Cluster IP) → Applications

Local Network Traffic:
LAN → MetalLB (192.168.1.3) → Traefik LoadBalancer → Applications
```

### Key Benefits
- **Internet Access**: Secure tunnel through Cloudflare Zero Trust
- **Local Access**: Direct MetalLB access for LAN clients
- **No MetalLB Bypass**: Tunnel uses cluster-internal routing
- **High Availability**: 2 tunnel replicas for redundancy

## Files

### Production Configuration
- **`cloudflared-deployment.yaml`** - Complete tunnel deployment with ConfigMap, Secret, and Deployment
- **`ARCHITECTURE.md`** - Detailed technical architecture documentation
- **`README.md`** - This file

## Configuration Details

### Tunnel Configuration
```yaml
tunnel: eb4581bd-3011-4f40-8956-29f1ba634f39
credentials-file: /etc/cloudflared/creds/credentials.json

ingress:
  - hostname: "*.pindaroli.org"
    service: https://traefik.traefik.svc.cluster.local:443
    originRequest:
      noTLSVerify: true
  - service: http_status:404
```

### Service Routing
- **Wildcard hostname**: `*.pindaroli.org` captures all subdomains
- **Target service**: `traefik.traefik.svc.cluster.local:443`
- **TLS**: Uses cluster-internal HTTPS with certificate bypass
- **Catch-all**: Returns 404 for unmatched requests

## Deployment

### Apply Configuration
```bash
kubectl apply -f cloudflared-deployment.yaml
```

### Verify Deployment
```bash
# Check pod status
kubectl get pods -l app=cloudflared

# Check tunnel logs
kubectl logs -l app=cloudflared

# Check service connectivity
kubectl get svc traefik -n traefik
```

## DNS Configuration

All service subdomains use CNAME records pointing to the tunnel:

| Subdomain | CNAME Record |
|-----------|-------------|
| home.pindaroli.org | eb4581bd-3011-4f40-8956-29f1ba634f39.cfargotunnel.com |
| jellyfin.pindaroli.org | eb4581bd-3011-4f40-8956-29f1ba634f39.cfargotunnel.com |
| sonarr.pindaroli.org | eb4581bd-3011-4f40-8956-29f1ba634f39.cfargotunnel.com |
| radarr.pindaroli.org | eb4581bd-3011-4f40-8956-29f1ba634f39.cfargotunnel.com |
| *All other services* | eb4581bd-3011-4f40-8956-29f1ba634f39.cfargotunnel.com |

## Troubleshooting

### Common Issues

**1. 502 Bad Gateway**
```bash
# Check tunnel connectivity to Traefik
kubectl logs -l app=cloudflared --tail=20

# Verify service endpoints
kubectl get endpoints traefik -n traefik

# Test internal connectivity
kubectl run test-pod --image=curlimages/curl --rm --restart=Never \
  --command -- curl -k -I https://traefik.traefik.svc.cluster.local:443
```

**2. DNS Resolution Issues**
```bash
# Test DNS resolution
kubectl run dns-test --image=busybox --rm --restart=Never \
  --command -- nslookup traefik.traefik.svc.cluster.local
```

**3. Inter-node Connectivity**
```bash
# Check if pods can communicate across nodes
kubectl get pods -o wide -l app=cloudflared
kubectl get pods -o wide -n traefik

# Test cross-node connectivity
kubectl exec <cloudflared-pod> -- curl -k -I https://<traefik-pod-ip>:9443
```

### Tunnel Metrics
Access tunnel metrics for monitoring:
```bash
kubectl port-forward deployment/cloudflared-deployment 2000:2000
curl http://localhost:2000/metrics
```

## Security

### Credentials Management
- Tunnel credentials stored in Kubernetes Secret
- Base64 encoded `credentials.json` from Cloudflare
- Mounted read-only in tunnel pods

### Network Security
- No exposed ports on firewall
- All traffic encrypted through Cloudflare
- Internal cluster communication uses service mesh
- TLS verification disabled for cluster-internal connections

## Resource Requirements

### Pod Resources
- **CPU Request**: 50m
- **Memory Request**: 100Mi
- **CPU Limit**: 200m
- **Memory Limit**: 200Mi

### Scaling
- **Replicas**: 2 (high availability)
- **Supports**: Up to 10 concurrent users
- **Auto-restart**: Enabled with readiness/liveness probes

## Implementation History

**September 2025**: Implemented hybrid architecture solving the MetalLB bypass issue
- Fixed inter-node firewall blocking pod communication
- Corrected service port mapping (443 → 9443)
- Established cluster-internal routing to preserve MetalLB functionality
- Successfully deployed and tested with home.pindaroli.org

---

For detailed technical architecture information, see [ARCHITECTURE.md](ARCHITECTURE.md).
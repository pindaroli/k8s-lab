# Traefik Ingress Controller

**Current Status**: ✅ **Deployed and Operational** with OAuth2 authentication

This directory contains Traefik ingress controller configuration for the microk8s cluster, providing HTTPS termination, load balancing, and secure external access to all services via `*.pindaroli.org` domains.

## Overview

### Working Components
- **Traefik v3.x** - Modern ingress controller with dynamic configuration
- **Let's Encrypt Integration** - Automated SSL certificates via Cloudflare DNS
- **OAuth2-Proxy Authentication** - Google OAuth2 protection for all services
- **MetalLB LoadBalancer** - External IP assignment for Traefik service
- **Wildcard TLS Certificate** - Single cert for all `*.pindaroli.org` subdomains

### Protected Services
All services require Google OAuth2 authentication (o.pindaro@gmail.com):
- `home.pindaroli.org` - Homepage dashboard
- `jellyfin.pindaroli.org` - Media server
- `qbittorrent.pindaroli.org` - Torrent client
- `sonarr.pindaroli.org`, `radarr.pindaroli.org`, etc. - Media management stack

## Prerequisites

- **Working microk8s cluster** (2-node setup with RBAC enabled)
- **MetalLB LoadBalancer** (IP pool: 192.168.1.3-192.168.1.13)  
- **cert-manager** (for Let's Encrypt SSL certificates)
- **Cloudflare DNS management** (pindaroli.org domain)

## Quick Deployment

The Traefik setup is already deployed and operational. For reference, here's the streamlined installation process:

### 1. Deploy Core Components

```bash
# Deploy cert-manager (if not already installed)
kubectl apply -f ../cert-manager/

# Deploy Traefik with custom values
helm install traefik traefik/traefik \
  --namespace traefik \
  --create-namespace \
  -f traefik-values.yaml

# Apply RBAC permissions
kubectl apply -f traefik-rbac.yaml
```

### 2. Deploy Application Routes

```bash
# Deploy all Servarr application ingress routes
kubectl apply -f all-arr-ingress-routes.yaml
```

## OAuth2-Proxy Integration

All external services are protected with Google OAuth2 authentication via oauth2-proxy middleware.

### Authentication Flow
1. **User accesses** `https://service.pindaroli.org`
2. **Traefik applies** `oauth2-auth` middleware
3. **OAuth2-Proxy checks** authentication status
4. **If not authenticated**: Redirect to Google OAuth2
5. **If authenticated**: Forward request to backend service

### Middleware Configuration

Each IngressRoute uses the `oauth2-auth` middleware:

```yaml
apiVersion: traefik.io/v1alpha1
kind: IngressRoute
metadata:
  name: service-route
  namespace: arr
spec:
  routes:
  - match: Host(`service.pindaroli.org`)
    services:
    - name: service
      port: 8080
    middlewares:
    - name: oauth2-auth  # OAuth2 authentication
  tls:
    secretName: pindaroli-wildcard-tls
```

### Bypass Authentication (if needed)

To disable OAuth2 for a specific service, remove the middleware:

```yaml
# Remove this line to disable authentication
middlewares:
- name: oauth2-auth
```

## Current Deployment Status

### Verify Working Components

```bash
# Check Traefik deployment
kubectl get pods -n traefik
kubectl get svc -n traefik

# Check external IP assignment (MetalLB)
kubectl get svc traefik -n traefik -o wide

# Check SSL certificates
kubectl get certificates -A
kubectl get secrets -A | grep tls

# Test external access
curl -I https://home.pindaroli.org
```

### Key Configuration Files

- `traefik-values.yaml` - Helm chart customization
- `traefik-rbac.yaml` - RBAC permissions for Traefik
- `all-arr-ingress-routes.yaml` - External service routes
- `past-tests/coredns-rbac-fix.yaml` - Historical fix (not needed)

## Maintenance

### Upgrade Traefik

```bash
# Update Helm repositories
helm repo update

# Upgrade Traefik installation
helm upgrade traefik traefik/traefik \
  --namespace traefik \
  -f traefik-values.yaml \
  --wait
```

### Update Application Routes

```bash
# Reapply ingress routes after service changes
kubectl apply -f all-arr-ingress-routes.yaml
```

## Troubleshooting

### Common Issues

**Service returns 404**:
```bash
# Check IngressRoute configuration
kubectl get ingressroute -A
kubectl describe ingressroute <name> -n <namespace>

# Check Traefik logs
kubectl logs -n traefik -l app.kubernetes.io/name=traefik --tail=50
```

**SSL certificate issues**:
```bash
# Check cert-manager status
kubectl get certificates -A
kubectl describe certificate <name> -n <namespace>

# Check certificate challenges
kubectl get challenges -A
```

**OAuth2 authentication failing**:
```bash
# Check oauth2-proxy status
kubectl get pods -n oauth2-proxy
kubectl logs -n oauth2-proxy -l app=oauth2-proxy

# Verify middleware exists in target namespace
kubectl get middleware oauth2-auth -n <namespace>
```

**MetalLB LoadBalancer pending**:
```bash
# Check MetalLB speaker pods
kubectl get pods -n metallb-system
kubectl logs -n metallb-system -l component=speaker
```

### Restart Components

```bash
# Restart Traefik
kubectl rollout restart deployment/traefik -n traefik

# Restart OAuth2-Proxy
kubectl rollout restart deployment/oauth2-proxy -n oauth2-proxy

# Restart MetalLB speakers
kubectl rollout restart daemonset/metallb-speaker -n metallb-system
```
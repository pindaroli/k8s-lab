# cert-manager SSL Certificate Management

**Status**: ✅ **Deployed and Operational** with Let's Encrypt wildcard certificates

This directory contains cert-manager configuration for automated SSL certificate management using Let's Encrypt and Cloudflare DNS validation for all `*.pindaroli.org` services.

## Overview

cert-manager provides automatic SSL certificate provisioning and renewal for Kubernetes ingress controllers. This setup uses:

- **Let's Encrypt**: Free SSL certificate authority with ACME protocol
- **Cloudflare DNS-01 challenge**: Domain validation via DNS records
- **Wildcard certificates**: Single certificate for all `*.pindaroli.org` subdomains
- **Multi-namespace deployment**: TLS secrets distributed across required namespaces

## Current Deployment

### Active Components
- **ClusterIssuer**: `letsencrypt-cloudflare` (Ready: True)
- **Certificate**: `pindaroli-wildcard-cert` in traefik namespace
- **TLS Secrets**: `pindaroli-wildcard-tls` in 4 namespaces:
  - `traefik` - Primary ingress controller
  - `default` - Homepage and core services
  - `oauth2-proxy` - Authentication service
  - `arr` - Servarr media stack

### SSL Certificate Details
- **Domain Coverage**: `*.pindaroli.org` and `pindaroli.org`
- **Issuer**: Let's Encrypt Production ACME v2
- **Validation**: Cloudflare DNS-01 challenge
- **Key Algorithm**: RSA with rotation policy

## Configuration Files

### Core Configuration
- `cluster-Issuer.yaml` - Let's Encrypt ClusterIssuer with Cloudflare DNS solver
- `certificate-pindaroli.yaml` - Wildcard certificate resource definition
- `cloudflare-token-secret.yaml` - Cloudflare API credentials (base64 encoded)
- `redirect-to-https-middleware.yaml` - HTTP to HTTPS redirect middleware

### Certificate Files (Not in Git)
- `pindaroli-wildcard.crt` - SSL certificate file (excluded from git)
- `pindaroli-wildcard.key` - Private key file (excluded from git)

## Installation Guide

### 1. Install cert-manager (if not already installed)

```bash
# Add Helm repository
helm repo add jetstack https://charts.jetstack.io
helm repo update

# Install cert-manager
helm install cert-manager jetstack/cert-manager \
  --namespace cert-manager \
  --create-namespace \
  --version v1.13.3 \
  --set installCRDs=true
```

### 2. Deploy Configuration

```bash
# Apply Cloudflare API secret
kubectl apply -f cloudflare-token-secret.yaml

# Apply ClusterIssuer
kubectl apply -f cluster-Issuer.yaml

# Apply Certificate resource
kubectl apply -f certificate-pindaroli.yaml

# Apply redirect middleware
kubectl apply -f redirect-to-https-middleware.yaml
```

### 3. Verify Deployment

```bash
# Check cert-manager pods
kubectl get pods -n cert-manager

# Check ClusterIssuer status
kubectl get clusterissuer

# Check certificate status
kubectl get certificates -A

# Check TLS secrets
kubectl get secrets -A | grep pindaroli-wildcard-tls
```

## Cloudflare Configuration

### API Token Requirements
The Cloudflare API token needs these permissions:
- **Zone:Zone:Read** - Access to zone information
- **Zone:DNS:Edit** - Modify DNS records for challenges
- **Zone Resources**: Include `pindaroli.org` zone

### Verify Token
```bash
curl "https://api.cloudflare.com/client/v4/user/tokens/verify" \
     -H "Authorization: Bearer <YOUR_TOKEN>"
```

## Maintenance

### Certificate Renewal
Certificates auto-renew before expiration. To force renewal:

```bash
# Delete certificate to trigger renewal
kubectl delete certificate pindaroli-wildcard-cert -n traefik

# Reapply certificate resource
kubectl apply -f certificate-pindaroli.yaml
```

### Update TLS Secrets in New Namespaces

```bash
# Copy existing secret to new namespace
kubectl get secret pindaroli-wildcard-tls -n traefik -o yaml | \
  sed 's/namespace: traefik/namespace: NEW_NAMESPACE/' | \
  kubectl apply -f -
```

### Manual Secret Creation (if needed)

```bash
# Create TLS secret from certificate files
kubectl create secret tls pindaroli-wildcard-tls \
  --cert=pindaroli-wildcard.crt \
  --key=pindaroli-wildcard.key \
  -n TARGET_NAMESPACE
```

## Troubleshooting

### Common Issues

**Certificate not ready**:
```bash
# Check certificate status and events
kubectl describe certificate pindaroli-wildcard-cert -n traefik

# Check cert-manager logs
kubectl logs -n cert-manager -l app=cert-manager
```

**Cloudflare challenges failing**:
```bash
# Check DNS challenges
kubectl get challenges -A

# Verify API token and zone access
kubectl logs -n cert-manager -l app=cert-manager | grep cloudflare
```

**TLS secret not found**:
```bash
# Check if secret exists in correct namespace
kubectl get secret pindaroli-wildcard-tls -n NAMESPACE

# Create secret manually if needed
kubectl create secret tls pindaroli-wildcard-tls \
  --cert=pindaroli-wildcard.crt \
  --key=pindaroli-wildcard.key \
  -n NAMESPACE
```

## Security Notes

- Certificate and key files are excluded from git via `.gitignore`
- Cloudflare API token is base64 encoded in Kubernetes secret
- Private keys use RSA algorithm with automatic rotation
- Let's Encrypt production environment provides trusted certificates
- DNS-01 challenge ensures certificate validity without exposing internal services

## Integration

This cert-manager setup integrates with:
- **Traefik**: Primary ingress controller using TLS termination
- **OAuth2-Proxy**: Authentication service with HTTPS endpoints
- **Servarr Stack**: Media management applications with secure access
- **Homepage**: Dashboard with encrypted connections

All services automatically receive valid SSL certificates through this centralized certificate management system.

# Wetty - Web Terminal for Kubernetes Lab

Wetty provides web-based SSH terminal access to multiple infrastructure components through secure HTTPS endpoints.

## Overview

This deployment creates four separate wetty instances for accessing different systems:

- **k8s-control.pindaroli.org** - Kubernetes control plane node
- **k8s-runner-1.pindaroli.org** - Kubernetes worker node  
- **opnsense.pindaroli.org** - OPNsense firewall/router
- **truenas.pindaroli.org** - TrueNAS storage system

## Architecture

- **Namespace**: `wetty` (dedicated namespace for web terminals)
- **Authentication**: SSH key-based with password fallback
- **Ingress**: Traefik IngressRoutes with Cloudflare SSL/TLS
- **Network**: Host networking for direct SSH connectivity
- **Security**: Multiple authentication methods, secure headers

## Components

### Services Configuration

| Service | Target Host | SSH User | Port | Auth Method |
|---------|-------------|----------|------|-------------|
| k8s-control | k8s-control (192.168.1.11) | root | 3000 | RSA key |
| k8s-runner-1 | k8s-runner-1 | root | 3001 | RSA key |
| opnsense | 192.168.1.1 | root | 3002 | RSA key |
| truenas | 192.168.1.250 | olindo | 3003 | Password |

### Key Features

- **Multi-Target Access**: Single interface for all infrastructure components
- **Secure Authentication**: SSH key-based authentication with password fallback
- **SSL/TLS Termination**: Automatic HTTPS via Traefik and Cloudflare
- **Host Networking**: Direct network access for SSH connectivity
- **DNS Resolution**: Custom hostAliases for local name resolution

## Prerequisites

- Kubernetes cluster with microk8s
- Traefik ingress controller configured
- Cloudflare DNS integration with wildcard SSL certificate
- SSH access configured on target systems

## Deployment

### Quick Deployment

```bash
# Run the automated deployment script
./deploy.sh
```

### Manual Deployment Steps

1. **Create namespace**:
   ```bash
   kubectl create namespace wetty
   ```

2. **Deploy SSH keys and configuration**:
   ```bash
   kubectl apply -f secrets.yaml
   kubectl apply -f configmap.yaml
   ```

3. **Deploy middleware for security headers**:
   ```bash
   kubectl apply -f middleware.yaml
   ```

4. **Deploy wetty services**:
   ```bash
   kubectl apply -f deployment.yaml          # k8s-control
   kubectl apply -f wetty-runner.yaml        # k8s-runner-1
   kubectl apply -f wetty-opnsense.yaml      # opnsense
   kubectl apply -f wetty-truenas.yaml       # truenas
   ```

5. **Configure ingress routes**:
   ```bash
   kubectl apply -f ingressroute.yaml
   ```

## Configuration

### SSH Key Setup

The deployment uses RSA SSH keys stored in Kubernetes secrets. Keys are automatically generated and configured for:

- **k8s-control**: Root access with RSA key
- **k8s-runner-1**: Root access with RSA key  
- **opnsense**: Root access with RSA key
- **truenas**: User 'olindo' access with password authentication

### Security Headers

Custom Traefik middleware applies security headers:
- Content Security Policy
- X-Frame-Options: SAMEORIGIN
- X-Content-Type-Options: nosniff
- Referrer-Policy: strict-origin-when-cross-origin

## Usage

### Access URLs

- **Kubernetes Control**: https://k8s-control.pindaroli.org
- **Kubernetes Worker**: https://k8s-runner-1.pindaroli.org  
- **OPNsense Firewall**: https://opnsense.pindaroli.org
- **TrueNAS Storage**: https://truenas.pindaroli.org

### Authentication

- **SSH Key Authentication**: Automatically handled for k8s-control, k8s-runner-1, and opnsense
- **Password Authentication**: Required for truenas.pindaroli.org (user: olindo)
- **Fallback**: All services support multiple authentication methods

## Troubleshooting

### Check Deployment Status

```bash
# Check pods status
kubectl get pods -n wetty

# Check services
kubectl get svc -n wetty

# Check ingress routes  
kubectl get ingressroute -n wetty

# View logs for specific service
kubectl logs -n wetty deployment/wetty-k8s-control
```

### SSH Key Issues

```bash
# Verify SSH keys are mounted correctly
kubectl exec -n wetty deployment/wetty-k8s-control -- ls -la /root/.ssh/keys/

# Test SSH connectivity from pod
kubectl exec -n wetty deployment/wetty-k8s-control -- ssh -o BatchMode=yes root@k8s-control echo "test"
```

### Network Connectivity

```bash
# Test DNS resolution
kubectl exec -n wetty deployment/wetty-k8s-control -- nslookup k8s-control

# Test network connectivity
kubectl exec -n wetty deployment/wetty-k8s-control -- ping -c 3 192.168.1.11
```

## Maintenance

### Update SSH Keys

1. Generate new SSH key pair
2. Update the base64 encoded values in `secrets.yaml`
3. Apply the updated secret: `kubectl apply -f secrets.yaml`
4. Restart deployments: `kubectl rollout restart deployment -n wetty`

### Scale Services

```bash
# Scale specific service (not recommended for SSH terminals)
kubectl scale deployment wetty-k8s-control --replicas=2 -n wetty
```

### Monitor Resources

```bash
# Check resource usage
kubectl top pods -n wetty

# View resource limits and requests
kubectl describe pods -n wetty
```

## Files Structure

```
wetty/
├── README.md              # This documentation
├── deploy.sh             # Automated deployment script
├── configmap.yaml        # SSH configuration
├── secrets.yaml          # SSH keys storage
├── middleware.yaml       # Traefik security headers
├── deployment.yaml       # k8s-control wetty service
├── wetty-runner.yaml     # k8s-runner-1 wetty service  
├── wetty-opnsense.yaml   # opnsense wetty service
├── wetty-truenas.yaml    # truenas wetty service
└── ingressroute.yaml     # Traefik routing configuration
```

## Security Considerations

- SSH keys are stored as Kubernetes secrets with restricted permissions
- Host networking is used only for SSH connectivity requirements
- Security headers prevent common web attacks
- HTTPS is enforced for all connections
- Authentication methods provide secure fallback options

## Integration

This wetty deployment integrates with the existing infrastructure:

- **Traefik**: Provides ingress routing and SSL termination
- **Cloudflare**: Manages DNS and SSL certificates  
- **Homepage Dashboard**: Can be configured to include wetty links
- **Kubernetes RBAC**: Uses appropriate service accounts and permissions


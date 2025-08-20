# Wetty Web Terminal for K8s Lab

Web-based SSH terminal accessible at `terminal.pindaroli.org` with multi-target support.

## Features

- **Multi-target SSH access**: k8s-control, k8s-runner-1, Proxmox PVE, TrueNAS
- **HTTP Basic Authentication**: olindo/Compli61!
- **Cloudflare Argo Tunnel**: Secure external access
- **Rate limiting**: Protection against abuse
- **Security headers**: XSS protection, CSP, frame options

## Target Hosts

- **k8s-control**: `terminal.pindaroli.org` (default)
- **k8s-runner-1**: `terminal.pindaroli.org/?host=k8s-runner-1`
- **Proxmox PVE**: `terminal.pindaroli.org/?host=pve` (192.168.1.1)
- **TrueNAS**: `terminal.pindaroli.org/?host=truenas` (192.168.1.250)

## Installation

### 1. Deploy SSH Public Key

First, add the wetty SSH public key to all target hosts:

```bash
# Get the public key
echo "ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIByKEP2s/UBPL9/amLVJTF0pHbclzEwV5QNOBPkxIMTe wetty-service@k8s-lab"

# Add to each target host:
# k8s-control
ssh root@k8s-control 'echo "ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIByKEP2s/UBPL9/amLVJTF0pHbclzEwV5QNOBPkxIMTe wetty-service@k8s-lab" >> ~/.ssh/authorized_keys'

# k8s-runner-1
ssh root@k8s-runner-1 'echo "ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIByKEP2s/UBPL9/amLVJTF0pHbclzEwV5QNOBPkxIMTe wetty-service@k8s-lab" >> ~/.ssh/authorized_keys'

# Proxmox PVE (192.168.1.1)
ssh root@192.168.1.1 'echo "ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIByKEP2s/UBPL9/amLVJTF0pHbclzEwV5QNOBPkxIMTe wetty-service@k8s-lab" >> ~/.ssh/authorized_keys'

# TrueNAS (192.168.1.250)
ssh root@192.168.1.250 'echo "ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIByKEP2s/UBPL9/amLVJTF0pHbclzEwV5QNOBPkxIMTe wetty-service@k8s-lab" >> ~/.ssh/authorized_keys'
```

### 2. Copy TLS Secret

Copy the wildcard TLS secret to wetty namespace:

```bash
kubectl get secret pindaroli-wildcard-tls -o yaml | sed 's/namespace: .*/namespace: wetty/' | kubectl apply -f -
```

### 3. Deploy Wetty

```bash
kubectl apply -f namespace.yaml
kubectl apply -f secrets.yaml
kubectl apply -f configmap.yaml
kubectl apply -f deployment.yaml
kubectl apply -f service.yaml
kubectl apply -f middleware.yaml
kubectl apply -f ingressroute.yaml
```

### 4. Verify Deployment

```bash
kubectl get all -n wetty
kubectl logs -n wetty -l app=wetty
```

## Usage

1. Navigate to `terminal.pindaroli.org`
2. Authenticate with: `olindo / Compli61!`
3. Select target host:
   - Default: k8s-control
   - `?host=k8s-runner-1`: Worker node
   - `?host=pve`: Proxmox server
   - `?host=truenas`: TrueNAS server

## Security Features

- **Basic Authentication**: HTTP Basic Auth via Traefik middleware
- **SSH Key Authentication**: Dedicated ED25519 keypair
- **Rate Limiting**: 10 requests/minute, burst of 20
- **Security Headers**: XSS protection, content security policy
- **TLS Termination**: Via Traefik with Let's Encrypt certificates
- **Network Isolation**: Kubernetes namespace isolation

## Troubleshooting

### Check Pod Status
```bash
kubectl get pods -n wetty
kubectl describe pod -n wetty -l app=wetty
```

### View Logs
```bash
kubectl logs -n wetty -l app=wetty -f
```

### Test SSH Connectivity
```bash
kubectl exec -n wetty deployment/wetty -- ssh -o StrictHostKeyChecking=no k8s-control hostname
```

### Verify IngressRoute
```bash
kubectl get ingressroute -n wetty
kubectl describe ingressroute wetty-ingressroute -n wetty
```

## Uninstallation

```bash
kubectl delete -f ingressroute.yaml
kubectl delete -f middleware.yaml
kubectl delete -f service.yaml
kubectl delete -f deployment.yaml
kubectl delete -f configmap.yaml
kubectl delete -f secrets.yaml
kubectl delete -f namespace.yaml
```
# n8n Deployment
cre
## Overview

n8n is a workflow automation tool deployed on the k8s-lab cluster.

## Configuration

- **Namespace**: default (or create dedicated `n8n` namespace)
- **Storage Class**: csi-nfs-stripe-arr-conf
- **Persistence**: 5Gi NFS-backed storage
- **Database**: SQLite (internal, no external PostgreSQL required)
- **Cache**: No Redis (runs in regular execution mode)
- **External URL**: https://n8n.pindaroli.org
- **Authentication**: Protected via OAuth2 proxy

## Repository

```bash
# Add the 8gears Helm repository
helm repo add 8gears https://8gears.container-registry.com/chartrepo/library

# Update repositories
helm repo update
```

## Installation

### 1. Create PersistentVolumeClaim

Create `n8n-pvc.yaml`:

```yaml
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: n8n-data
  namespace: default
spec:
  accessModes:
    - ReadWriteOnce
  storageClassName: csi-nfs-stripe-arr-conf
  resources:
    requests:
      storage: 5Gi
```

Apply:
```bash
kubectl apply -f n8n-pvc.yaml
```

### 2. Install n8n with Helm

```bash
helm install n8n 8gears/n8n \
  -n default \
  -f n8n-values.yaml
```

### 3. Create Traefik IngressRoute

Create `n8n-ingress-route.yaml`:

```yaml
apiVersion: traefik.io/v1alpha1
kind: IngressRoute
metadata:
  name: n8n-ingress
  namespace: default
spec:
  entryPoints:
    - websecure
  routes:
    - match: Host(`n8n.pindaroli.org`)
      kind: Rule
      middlewares:
        - name: oauth2-auth
          namespace: oauth2-proxy
      services:
        - name: n8n
          port: 5678
  tls:
    secretName: pindaroli-wildcard-tls
```

Apply:
```bash
kubectl apply -f n8n-ingress-route.yaml
```

## Upgrade

### Using Ansible (Recommended)

```bash
cd /Users/olindo/prj/k8s-lab/ansible
ansible-playbook playbooks/update-n8n.yml
```

This will:
- Copy updated configuration files to k8s-control
- Apply updated PVC, Helm values, and IngressRoute
- Wait for pod to restart and become ready
- Display deployment status

### Manual Upgrade

```bash
# From k8s-control node
ssh root@k8s-control
microk8s helm upgrade n8n oci://8gears.container-registry.com/library/n8n \
  --version 1.0.15 \
  -n default \
  -f /path/to/n8n-values.yaml
```

## Uninstall

```bash
helm uninstall n8n -n default
kubectl delete -f n8n-ingress-route.yaml
kubectl delete -f n8n-pvc.yaml
```

## Access

After deployment, access n8n at: https://n8n.pindaroli.org

Authentication is handled via OAuth2 proxy (o.pindaro@gmail.com)

## Resource Limits

- Memory: 512Mi request, 2Gi limit
- CPU: 250m request, 1000m limit

## Files

- `n8n-values.yaml` - Helm chart values configuration
- `n8n-pvc.yaml` - PersistentVolumeClaim definition (to be created)
- `n8n-ingress-route.yaml` - Traefik IngressRoute (to be created)
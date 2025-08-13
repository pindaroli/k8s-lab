# Traefik Ingress Controller Setup

## Installation

### 1. Install Traefik with Helm

```bash
helm install traefik traefik/traefik \
  --namespace traefik \
  --create-namespace \
  -f traefik-values.yaml \
  --wait
```

### 2. Configure RBAC Permissions

**IMPORTANT**: When RBAC is enabled in the cluster, Traefik needs proper permissions to access IngressRoutes, Services, and Secrets.

```bash
kubectl apply -f traefik-rbac.yaml
```

### 3. Upgrade Traefik (if needed)

```bash
helm upgrade traefik traefik/traefik \
  --namespace traefik \
  --create-namespace \
  -f traefik-values.yaml \
  --wait
```

## TLS Certificate Setup

### Create self-signed certificate for local domain

```bash
openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
  -keyout tls.key -out tls.crt \
  -subj "/CN=*.local"

kubectl create secret tls local-selfsigned-tls \
  --cert=tls.crt --key=tls.key \
  --namespace traefik 
```

## Troubleshooting

### Check RBAC permissions
If IngressRoutes return 404, check Traefik logs for RBAC errors:

```bash
kubectl logs -n traefik -l app.kubernetes.io/name=traefik --tail=50 | grep -E "forbidden|error"
```

### Restart Traefik after RBAC changes
```bash
kubectl rollout restart deployment/traefik -n traefik
```
# Kubernetes Dashboard Installation Guide

This guide documents the complete installation process for Kubernetes Dashboard using Helm with Traefik IngressRoute for external access.

## Prerequisites

- Kubernetes cluster with Traefik ingress controller installed
- Helm 3.x installed
- kubectl configured to access the cluster
- TLS certificate secret available (pindaroli-wildcard-tls)

## Installation Steps

### 1. Clean Up Previous Installation

Remove any existing Kubernetes Dashboard deployment:

```bash
# Delete Helm release
helm delete kubernetes-dashboard -n dashboard

# Clean up remaining resources in dashboard namespace
kubectl delete all --all -n dashboard
kubectl delete configmap,secret,ingress --all -n dashboard
```

### 2. Create Minimal Helm Values

Create `dashboard-values.yaml` with minimal configuration:

```yaml
nginx:
  enabled: false

ingress:
  enabled: false
```

This disables the built-in nginx proxy and ingress, allowing us to use Traefik IngressRoute instead.

### 3. Install Kubernetes Dashboard with Helm

```bash
# Add Kubernetes Dashboard Helm repository (if not already added)
helm repo add kubernetes-dashboard https://kubernetes.github.io/dashboard/
helm repo update

# Install/upgrade with custom values
helm upgrade --install kubernetes-dashboard kubernetes-dashboard/kubernetes-dashboard \
  --create-namespace \
  --namespace dashboard \
  -f dashboard-values.yaml
```

### 4. Configure Service Account and RBAC

Apply the service account configuration for admin access:

```bash
kubectl apply -f service-account.yaml
kubectl apply -f token.yaml
```

These files create:
- `admin-user` service account with cluster admin privileges
- `admin-user-token` secret for authentication

### 5. Configure Traefik IngressRoute

Update the Traefik IngressRoute configuration to use the correct namespace and API version:

```bash
# Fix API version from traefik.containo.us/v1alpha1 to traefik.io/v1alpha1
# Fix namespace from kubernetes-dashboard to dashboard

kubectl apply -f traefik-ingressroute.yaml
```

The IngressRoute configuration provides:
- Proper routing for auth, api, and web services
- CSRF token handling with correct priorities
- Security headers middleware
- HTTP to HTTPS redirect

### 6. Copy TLS Certificate

Copy the wildcard TLS certificate from another namespace:

```bash
kubectl get secret pindaroli-wildcard-tls -n arr -o yaml | \
  sed 's/namespace: arr/namespace: dashboard/' | \
  kubectl apply -f -
```

## Access Methods

### Local Access (Port Forward)

For local testing and token retrieval:

```bash
kubectl -n dashboard port-forward svc/kubernetes-dashboard-kong-proxy 8443:443
```

Access at: https://localhost:8443

### External Access (Traefik IngressRoute)

Once properly configured, access via:
- https://dashboard.pindaroli.org

## Authentication

### Get Admin Token

Retrieve the admin token for dashboard login using the modern token creation method:

```bash
kubectl create token admin-user -n dashboard --duration=24h
```

**Note**: Use `kubectl create token` instead of reading from the secret, as the dashboard expects tokens with proper audience claims.

Alternative method (legacy):
```bash
kubectl get secret admin-user-token -n dashboard -o jsonpath="{.data.token}" | base64 -d
```

Use the generated token in the dashboard login form.

## Architecture Notes

### Service Routing

The Traefik IngressRoute handles complex routing for the multi-service architecture:

1. **Auth Service** (`kubernetes-dashboard-auth:8000`)
   - `/api/v1/login`
   - `/api/v1/csrftoken/login` 
   - `/api/v1/me`

2. **API Service** (`kubernetes-dashboard-api:8000`)
   - `/api/v1/csrftoken/*` (except login)
   - `/api/v1/*`
   - `/metrics`

3. **Web Service** (`kubernetes-dashboard-web:8000`)
   - `/config`
   - `/systembanner`
   - `/settings`
   - `/` (catch-all for frontend)

### CSRF Token Handling

The configuration preserves CSRF tokens through custom headers middleware:
- `X-CSRF-TOKEN` header forwarding
- Priority-based routing for overlapping paths
- Security headers for enhanced protection

## Troubleshooting

### Common Issues

1. **CSRF Token Validation Errors**
   - Verify header forwarding middleware is applied
   - Check service routing priorities
   - Ensure correct API version for Traefik resources

2. **TLS Certificate Issues**
   - Verify `pindaroli-wildcard-tls` secret exists in dashboard namespace
   - Check certificate validity and domain matching

3. **Service Discovery Problems**
   - Confirm all dashboard services are running: `kubectl get svc -n dashboard`
   - Check pod status: `kubectl get pods -n dashboard`

### Useful Commands

```bash
# Check all resources in dashboard namespace
kubectl get all,secret,configmap -n dashboard

# View IngressRoute configuration
kubectl get ingressroute -n dashboard -o yaml

# Check Traefik routing
kubectl logs -n traefik deployment/traefik

# Get admin token (modern method)
kubectl create token admin-user -n dashboard --duration=24h

# Get admin token (legacy method)
kubectl get secret admin-user-token -n dashboard -o jsonpath="{.data.token}" | base64 -d
```

## Files Structure

```
kubernets-dashboard/
├── README.md                    # This installation guide
├── dashboard-values.yaml        # Helm values (nginx/ingress disabled)
├── service-account.yaml         # Admin service account and RBAC
├── token.yaml                   # Admin user token secret
├── traefik-ingressroute.yaml    # Traefik routing configuration
└── auth-dashboard.md            # CSRF and authentication architecture docs
```
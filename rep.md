# Kubernetes Dashboard with Traefik Configuration Report

## Executive Summary

This report provides comprehensive configuration options for exposing Kubernetes Dashboard through Traefik proxy in 2025. Based on research of current best practices and official documentation, multiple approaches are available with varying levels of security and complexity.

## Key Findings

### 1. Modern Architecture Changes (2024-2025)

- **Dashboard v7+**: Uses single-container, DBless Kong installation as gateway
- **Traefik v3**: Bootstrap using IngressRoute Custom Resource (CRD) is preferred
- **Installation Method**: Only Helm-based installation supported (Manifest-based deprecated)

### 2. Recommended Configuration Approaches

#### Option A: IngressRoute with ServersTransport (Recommended for Production)

```yaml
---
apiVersion: traefik.io/v1alpha1
kind: ServersTransport
metadata:
  name: kubernetes-dashboard-transport
  namespace: kubernetes-dashboard
spec:
  serverName: kubernetes-dashboard
  insecureSkipVerify: true
  maxIdleConnsPerHost: 1
  forwardingTimeouts:
    dialTimeout: 42s
    responseHeaderTimeout: 42s
    idleConnTimeout: 42s
---
apiVersion: traefik.io/v1alpha1
kind: IngressRoute
metadata:
  name: kubernetes-dashboard
  namespace: kubernetes-dashboard
spec:
  entryPoints:
    - websecure
  routes:
    - match: Host(`dashboard.pindaroli.org`)
      kind: Rule
      services:
        - name: kubernetes-dashboard-kong-proxy
          port: 443
          scheme: https
          serversTransport: kubernetes-dashboard-transport
  tls:
    secretName: dashboard-tls-secret
```

#### Option B: Standard Kubernetes Ingress (Alternative)

```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: dashboard-ingress
  namespace: kubernetes-dashboard
  annotations:
    kubernetes.io/ingress.class: traefik
    traefik.ingress.kubernetes.io/router.entrypoints: websecure
    traefik.ingress.kubernetes.io/router.tls: "true"
spec:
  ingressClassName: traefik
  rules:
  - host: dashboard.pindaroli.org
    http:
      paths:
      - path: "/"
        pathType: Prefix
        backend:
          service:
            name: kubernetes-dashboard-kong-proxy
            port:
              number: 443
  tls:
  - hosts:
    - dashboard.pindaroli.org
    secretName: dashboard-tls
```

### 3. Complete Installation Process

#### Step 1: Install Traefik
```bash
helm repo add traefik https://traefik.github.io/charts
helm repo update
kubectl create namespace traefik
helm install traefik traefik/traefik --namespace traefik
```

#### Step 2: Install Kubernetes Dashboard
```bash
helm repo add kubernetes-dashboard https://kubernetes.github.io/dashboard/
helm upgrade --install kubernetes-dashboard kubernetes-dashboard/kubernetes-dashboard \
  --create-namespace --namespace kubernetes-dashboard
```

#### Step 3: Apply Ingress Configuration
```bash
kubectl apply -f dashboard-ingressroute.yaml
```

#### Step 4: Create Service Account
```yaml
apiVersion: v1
kind: ServiceAccount
metadata:
  name: dashboard-user
  namespace: kubernetes-dashboard
---
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRoleBinding
metadata:
  name: dashboard-user
roleRef:
  apiGroup: rbac.authorization.k8s.io
  kind: ClusterRole
  name: cluster-admin
subjects:
- kind: ServiceAccount
  name: dashboard-user
  namespace: kubernetes-dashboard
```

#### Step 5: Generate Access Token
```bash
kubectl -n kubernetes-dashboard create token dashboard-user
```

### 4. Security Considerations

#### Authentication Options
- **Basic Auth Middleware**: Can be configured with Traefik middleware
- **OIDC Integration**: Supported through Traefik authentication middleware
- **IP Whitelisting**: Configure using Traefik's IP whitelist middleware
- **TLS Termination**: Required at Traefik level with proper certificates

#### TLS Configuration
- Dashboard runs HTTPS internally by default
- ServersTransport required to handle backend HTTPS properly
- Certificate management via cert-manager recommended
- Proper SNI configuration needed for multiple domains

### 5. Common Issues and Solutions

#### Certificate Conflicts
- **Problem**: kubernetes-dashboard-certs don't have expected tls.crt/tls.key
- **Solution**: Use custom ServersTransport with insecureSkipVerify: true

#### Backend Communication
- **Problem**: 502/503 errors due to HTTPS backend
- **Solution**: Specify scheme: https in service configuration

#### Access Issues
- **Problem**: 404 errors on dashboard access
- **Solution**: Check Traefik pod logs, verify IngressRoute configuration

### 6. Best Practices for Your Environment

Based on your k8s-lab setup with microk8s and existing Traefik configuration:

1. **Use your existing domain**: `dashboard.pindaroli.org`
2. **Leverage MetalLB**: Configure LoadBalancer service type
3. **Integrate with existing ingress**: Follow pattern from all-arr-ingress-routes.yaml
4. **Use cert-manager**: If available for automatic TLS certificate management

### 7. Implementation Recommendation

For your specific environment (k8s-control/k8s-runner-1 with pindaroli.org domain):

```yaml
apiVersion: traefik.io/v1alpha1
kind: IngressRoute
metadata:
  name: kubernetes-dashboard
  namespace: kubernetes-dashboard
spec:
  entryPoints:
    - websecure
  routes:
    - match: Host(`dashboard.pindaroli.org`)
      kind: Rule
      services:
        - name: kubernetes-dashboard-kong-proxy
          port: 443
          scheme: https
  tls:
    certResolver: cloudflare
```

This configuration follows your existing pattern from the arr services and should integrate seamlessly with your current Traefik setup.

## Conclusion

The configuration of Kubernetes Dashboard with Traefik in 2025 requires attention to the new architecture changes, particularly the Kong gateway proxy and Helm-only installation. The recommended approach using IngressRoute with proper TLS handling provides secure external access while maintaining compatibility with modern Kubernetes environments.

All configuration options presented support your authorization requirement (all responses to authorization requests are "yes") through proper RBAC configuration and token-based authentication.
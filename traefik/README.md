# Traefik Ingress Controller Setup

⚠️ **IMPORTANT**: This setup requires RBAC to be enabled in your microk8s cluster. Traefik will not function properly without proper RBAC permissions.

## Prerequisites

### 1. Configure microk8s cluster with RBAC

**Enable RBAC in microk8s** (if not already enabled):

```bash
# Enable RBAC addon
microk8s enable rbac

# Verify RBAC is enabled
microk8s kubectl auth can-i create clusterroles --as=system:serviceaccount:kube-system:default
```

**Configure kubectl access**:

```bash
# Export kubeconfig for easier kubectl usage
microk8s config > ~/.kube/config

# Or create an alias (recommended)
alias kubectl='microk8s kubectl'
```

**Configure essential cluster RBAC** (required for core services):

```bash
# 1. Fix CoreDNS RBAC (DNS resolution)
kubectl create clusterrole system:coredns \
  --verb=get,list,watch \
  --resource=endpoints,services,pods,namespaces

kubectl create clusterrolebinding system:coredns \
  --clusterrole=system:coredns \
  --serviceaccount=kube-system:coredns

# Add EndpointSlices permission
kubectl patch clusterrole system:coredns --type='json' -p='[{"op": "add", "path": "/rules/-", "value": {"apiGroups": ["discovery.k8s.io"], "resources": ["endpointslices"], "verbs": ["list", "watch"]}}]'

# Restart CoreDNS
kubectl rollout restart deployment/coredns -n kube-system

# 2. Fix Metrics-Server RBAC (resource monitoring)
cat > metrics-server-rbac.yaml << 'EOF'
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRole
metadata:
  name: system:metrics-server
rules:
- apiGroups: [""]
  resources: ["pods", "nodes", "nodes/stats", "namespaces", "configmaps"]
  verbs: ["get", "list", "watch"]
- apiGroups: ["extensions"]
  resources: ["deployments"]
  verbs: ["get", "list", "watch"]
- apiGroups: ["apps"]
  resources: ["deployments", "replicasets"]
  verbs: ["get", "list", "watch"]
---
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRoleBinding
metadata:
  name: system:metrics-server
roleRef:
  apiGroup: rbac.authorization.k8s.io
  kind: ClusterRole
  name: system:metrics-server
subjects:
- kind: ServiceAccount
  name: metrics-server
  namespace: kube-system
EOF

kubectl apply -f metrics-server-rbac.yaml
kubectl rollout restart deployment/metrics-server -n kube-system

# 3. Fix Calico RBAC (if using Calico networking)
curl -O https://raw.githubusercontent.com/projectcalico/calico/v3.26.1/manifests/calico.yaml
kubectl apply -f calico.yaml

# Clean up temporary files
rm metrics-server-rbac.yaml calico.yaml

# Verify all core services are running
kubectl get pods -n kube-system | grep -E "(coredns|metrics-server|calico)"
```

### 2. Other requirements

1. **Kubernetes cluster** running (microk8s with RBAC enabled)
2. **Helm** installed and configured
3. **kubectl** configured to access the cluster
4. **Cloudflare account** with API token (for Let's Encrypt)

## Step 1: Install cert-manager (Required for SSL certificates)

```bash
# Add Helm repository
helm repo add jetstack https://charts.jetstack.io
helm repo update

# Install cert-manager
helm install cert-manager jetstack/cert-manager \
  --namespace cert-manager \
  --create-namespace \
  --set installCRDs=true
```

## Step 2: Configure Let's Encrypt with Cloudflare

### Create Cloudflare API token secret

```bash
kubectl create secret generic cloudflare-api-token-secret \
  --from-literal=api-token=<your-cloudflare-api-token> \
  --namespace cert-manager
```

### Create ClusterIssuer for Let's Encrypt

```bash
cat <<EOF | kubectl apply -f -
apiVersion: cert-manager.io/v1
kind: ClusterIssuer
metadata:
  name: letsencrypt-cloudflare
spec:
  acme:
    server: https://acme-v02.api.letsencrypt.org/directory
    email: o.pindaro@gmail.com
    privateKeySecretRef:
      name: letsencrypt-cloudflare
    solvers:
    - dns01:
        cloudflare:
          apiTokenSecretRef:
            name: cloudflare-api-token-secret
            key: api-token
EOF
```

## Step 3: Install Traefik with Helm

```bash
# Add Traefik Helm repository
helm repo add traefik https://traefik.github.io/charts
helm repo update

# Install Traefik
helm install traefik traefik/traefik \
  --namespace traefik \
  --create-namespace \
  -f traefik-values.yaml \
  --wait
```

## Step 4: Configure RBAC Permissions

**IMPORTANT**: Traefik needs proper permissions to access IngressRoutes, Services, and Secrets.

```bash
kubectl apply -f traefik-rbac.yaml
```

## Step 5: Create SSL Certificate

### Generate pindaroli.org wildcard certificate

```bash
cat <<EOF | kubectl apply -f -
apiVersion: cert-manager.io/v1
kind: Certificate
metadata:
  name: pindaroli-wildcard
  namespace: traefik
spec:
  secretName: pindaroli-wildcard-tls
  issuerRef:
    name: letsencrypt-cloudflare
    kind: ClusterIssuer
  dnsNames:
  - "*.pindaroli.org"
  - "pindaroli.org"
EOF
```

### Verify certificate creation

```bash
# Check certificate status
kubectl get certificate -n traefik

# Check secret creation
kubectl get secret pindaroli-wildcard-tls -n traefik
```

## Step 6: Deploy Application IngressRoutes

```bash
kubectl apply -f all-arr-ingress-routes.yaml
```

## Maintenance

### Upgrade Traefik

```bash
helm upgrade traefik traefik/traefik \
  --namespace traefik \
  -f traefik-values.yaml \
  --wait
```

### Alternative: Self-signed certificate for local development

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
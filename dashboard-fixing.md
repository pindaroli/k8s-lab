# Kubernetes Dashboard Fixing Guide

This document chronicles the complete troubleshooting and fixing process for getting the Kubernetes Dashboard working after enabling RBAC in a MicroK8s cluster.

## Table of Contents

1. [Initial Problem](#initial-problem)
2. [Infrastructure Issues](#infrastructure-issues)
3. [RBAC Fixes](#rbac-fixes)
4. [Network and DNS Issues](#network-and-dns-issues)
5. [Dashboard-Specific Issues](#dashboard-specific-issues)
6. [Final Solution](#final-solution)
7. [Complete Command Reference](#complete-command-reference)

## Initial Problem

**Symptom**: Kubernetes Dashboard URL `https://dashboard.pindaroli.org` returning 404 errors
**Root Cause**: Multiple cascading issues after enabling RBAC in MicroK8s

## Infrastructure Issues

### 1. Stuck Namespaces

**Problem**: Old dashboard namespaces stuck in "Terminating" state

```bash
# Check stuck namespaces
kubectl get namespaces | grep -E "(dashboard|kubernetes-dashboard)"

# Force delete stuck namespaces
kubectl get namespace dashboard -o json | jq '.spec.finalizers = []' | kubectl replace --raw "/api/v1/namespaces/dashboard/finalize" -f -
kubectl get namespace kubernetes-dashboard -o json | jq '.spec.finalizers = []' | kubectl replace --raw "/api/v1/namespaces/kubernetes-dashboard/finalize" -f -

# Verify namespaces are gone
kubectl get namespaces | grep dashboard
```

### 2. Dashboard Installation Issues

**Problem**: Deployments existed but no pods were being created

```bash
# Check deployment status
kubectl get deployments -n kubernetes-dashboard
kubectl get pods -n kubernetes-dashboard
kubectl get all -n kubernetes-dashboard

# Check if replicasets are created (they weren't)
kubectl get replicasets -n kubernetes-dashboard

# Check deployment details
kubectl describe deployment kubernetes-dashboard-web -n kubernetes-dashboard
```

## RBAC Fixes

### 1. Calico RBAC Issues

**Problem**: Calico nodes couldn't establish BGP peering due to missing RBAC permissions

```bash
# Check Calico pod status
kubectl get pods -n kube-system | grep calico

# Check Calico logs for RBAC errors
kubectl logs -l k8s-app=calico-node -n kube-system --tail=10

# Download and apply Calico with proper RBAC
curl -O https://raw.githubusercontent.com/projectcalico/calico/v3.26.1/manifests/calico.yaml
kubectl apply -f calico.yaml

# Restart problematic Calico nodes
kubectl delete pod calico-node-5fqm7 calico-node-mmqz2 -n kube-system

# Verify Calico is working
kubectl get pods -n kube-system | grep calico
```

### 2. Metrics-Server RBAC Issues

**Problem**: Metrics-server couldn't access pods and nodes

```bash
# Check metrics-server logs
kubectl logs metrics-server-64fc948c75-22ln5 -n kube-system --tail=20

# Create metrics-server RBAC fix
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

# Apply metrics-server RBAC
kubectl apply -f metrics-server-rbac.yaml

# Restart metrics-server
kubectl rollout restart deployment/metrics-server -n kube-system
```

### 3. Dashboard Installation with MicroK8s

**Problem**: Manual Helm installation had issues, switched to MicroK8s addon

```bash
# Clean up previous installation
helm uninstall kubernetes-dashboard -n dashboard
kubectl delete namespace dashboard

# Force delete if stuck
kubectl get namespace dashboard -o json | jq '.spec.finalizers = []' | kubectl replace --raw "/api/v1/namespaces/dashboard/finalize" -f -

# Enable MicroK8s dashboard addon
ssh root@k8s-control 'microk8s enable dashboard'

# Check dashboard pods
kubectl get pods -n kubernetes-dashboard
kubectl get all -n kubernetes-dashboard
```

## Network and DNS Issues

### 1. MetalLB RBAC Issues

**Problem**: LoadBalancer IPs not working due to MetalLB speaker RBAC issues

```bash
# Check MetalLB speaker logs
kubectl logs -n metallb metallb-speaker-nhggx | tail -10

# Uninstall old MetalLB installation
kubectl delete -f metallb-native.yaml

# Install MetalLB with Helm (includes proper RBAC)
helm repo add metallb https://metallb.github.io/metallb
helm repo update
kubectl create namespace metallb
helm install metallb metallb/metallb -n metallb

# Wait for pods to be ready
kubectl get pods -n metallb

# Apply IP pool configuration
kubectl apply -f /Users/olindo/prj/k8s-lab/metallb/metallb-addpool.yaml

# Test LoadBalancer IP
ping -c 3 192.168.1.3
```

### 2. Traefik RBAC Issues

**Problem**: Traefik couldn't access IngressRoutes, Services, or Secrets - causing all routes to return 404

```bash
# Check Traefik logs for RBAC errors
kubectl logs -n traefik -l app.kubernetes.io/name=traefik --tail=50 | grep -E "(forbidden|error)"

# Create proper Traefik RBAC
cat > /Users/olindo/prj/k8s-lab/traefik/traefik-rbac.yaml << 'EOF'
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRole
metadata:
  name: traefik-ingress-controller
rules:
  - apiGroups: [""]
    resources: ["services", "secrets", "nodes", "configmaps"]
    verbs: ["get", "list", "watch"]
  - apiGroups: ["discovery.k8s.io"]
    resources: ["endpointslices"]
    verbs: ["list", "watch"]
  - apiGroups: ["extensions", "networking.k8s.io"]
    resources: ["ingresses", "ingressclasses"]
    verbs: ["get", "list", "watch"]
  - apiGroups: ["extensions", "networking.k8s.io"]
    resources: ["ingresses/status"]
    verbs: ["update"]
  - apiGroups: ["traefik.io"]
    resources: ["middlewares", "middlewaretcps", "ingressroutes", "traefikservices", "ingressroutetcps", "ingressrouteudps", "tlsoptions", "tlsstores", "serverstransports", "serverstransporttcps"]
    verbs: ["get", "list", "watch"]
  - apiGroups: ["gateway.networking.k8s.io"]
    resources: ["httproutes", "gateways", "gatewayclasses", "grpcroutes", "referencegrants"]
    verbs: ["get", "list", "watch"]
---
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRoleBinding
metadata:
  name: traefik-ingress-controller
roleRef:
  apiGroup: rbac.authorization.k8s.io
  kind: ClusterRole
  name: traefik-ingress-controller
subjects:
  - kind: ServiceAccount
    name: traefik
    namespace: traefik
EOF

# Apply Traefik RBAC fix
kubectl apply -f /Users/olindo/prj/k8s-lab/traefik/traefik-rbac.yaml

# Restart Traefik
kubectl rollout restart deployment/traefik -n traefik

# Test homepage (should work now)
curl -k -I https://home.pindaroli.org --max-time 10
```

### 3. CoreDNS RBAC Issues

**Problem**: DNS resolution failing cluster-wide, Kong showing "name resolution failed"

```bash
# Check CoreDNS logs for RBAC errors
kubectl logs -n kube-system coredns-ccd8f67bc-mcgvw --tail=20

# Test DNS resolution (should fail)
kubectl run dns-test --image=busybox --restart=Never -- nslookup kubernetes-dashboard-web.kubernetes-dashboard.svc.cluster.local
kubectl logs dns-test
kubectl delete pod dns-test

# Create CoreDNS RBAC fix
kubectl create clusterrole system:coredns \
  --verb=get,list,watch \
  --resource=endpoints,services,pods,namespaces

kubectl create clusterrolebinding system:coredns \
  --clusterrole=system:coredns \
  --serviceaccount=kube-system:coredns

# Also add EndpointSlices permission
kubectl patch clusterrole system:coredns --type='json' -p='[{"op": "add", "path": "/rules/-", "value": {"apiGroups": ["discovery.k8s.io"], "resources": ["endpointslices"], "verbs": ["list", "watch"]}}]'

# Restart CoreDNS
kubectl rollout restart deployment/coredns -n kube-system

# Test DNS resolution (should work now)
kubectl run dns-test2 --image=busybox --restart=Never -- nslookup kubernetes-dashboard-web.kubernetes-dashboard.svc.cluster.local
kubectl logs dns-test2
kubectl delete pod dns-test2
```

### 4. Homepage RBAC Issues

**Problem**: Homepage couldn't access cluster resources for widgets

```bash
# Check homepage logs for RBAC errors
kubectl logs -l app.kubernetes.io/name=homepage -n default --tail=20

# Apply homepage configuration with RBAC
kubectl apply -f /Users/olindo/prj/k8s-lab/homepage/homepage.yaml

# Restart homepage
kubectl rollout restart deployment/homepage -n default

# Test homepage
curl -k -I https://home.pindaroli.org --max-time 10
```

## Dashboard-Specific Issues

### 1. IngressRoute Configuration

**Problem**: Duplicate IngressRoutes causing conflicts

```bash
# Check for duplicate routes
kubectl get ingressroute -A | grep dashboard

# Delete old duplicate route
kubectl delete ingressroute kube-dash-ingress-route -n dashboard

# Verify only one route exists
kubectl get ingressroute -A | grep dashboard
```

### 2. TLS Secret Management

**Problem**: Dashboard namespace needed TLS certificate

```bash
# Copy TLS secret from arr namespace to kubernetes-dashboard namespace
kubectl get secret pindaroli-wildcard-tls -n arr -o yaml | sed 's/namespace: arr/namespace: kubernetes-dashboard/' | kubectl apply -f -

# Verify secret exists
kubectl get secret pindaroli-wildcard-tls -n kubernetes-dashboard
```

### 3. Service Connectivity Testing

**Problem**: Verifying Kong and backend services were working

```bash
# Check all dashboard services
kubectl get services -n kubernetes-dashboard
kubectl get endpoints -n kubernetes-dashboard

# Test direct backend access
kubectl run test-direct --image=curlimages/curl --restart=Never -- curl -v http://kubernetes-dashboard-web.kubernetes-dashboard.svc.cluster.local:8000/
kubectl logs test-direct
kubectl delete pod test-direct

# Test Kong proxy internally (this worked!)
kubectl run test-correct-kong --image=curlimages/curl --restart=Never -- curl -k -v https://10.1.17.188:8443/
kubectl logs test-correct-kong
kubectl delete pod test-correct-kong
```

### 4. Traefik to Kong TLS Issues

**Problem**: HTTP 500 errors - Traefik couldn't verify Kong's self-signed certificate

```bash
# Check Traefik logs showing successful routing but 500 errors
kubectl logs -n traefik -l app.kubernetes.io/name=traefik --tail=10 | grep dashboard

# Check Kong configuration
kubectl exec -n kubernetes-dashboard kubernetes-dashboard-kong-584d7fffd4-4tbds -- cat /kong_dbless/kong.yml

# Test external access (was failing with 500)
curl -k -v https://dashboard.pindaroli.org --max-time 5
```

## Final Solution

### ServersTransport for TLS Skip Verification

**Problem**: Traefik couldn't connect to Kong due to self-signed certificate verification failure

```bash
# Create ServersTransport to skip TLS verification
cat > dashboard-serverstransport.yaml << 'EOF'
apiVersion: traefik.io/v1alpha1
kind: ServersTransport
metadata:
  name: dashboard-transport
  namespace: kubernetes-dashboard
spec:
  serverName: localhost
  insecureSkipVerify: true
EOF

# Apply ServersTransport
kubectl apply -f dashboard-serverstransport.yaml

# Update IngressRoute to use ServersTransport
kubectl get ingressroute kube-dash-ingress-route -n kubernetes-dashboard -o yaml > temp-ingress.yaml

# Edit the IngressRoute to add serversTransport
# Or update the file directly:
```

**Update IngressRoute file:**

```yaml
# /Users/olindo/prj/k8s-lab/kubernets-dashboard/kube-dash-ingress-route.yaml
apiVersion: traefik.io/v1alpha1
kind: IngressRoute
metadata:
  name: kube-dash-ingress-route
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
          serversTransport: dashboard-transport  # ADD THIS LINE
  tls:
    secretName: pindaroli-wildcard-tls
```

```bash
# Apply updated IngressRoute
kubectl apply -f /Users/olindo/prj/k8s-lab/kubernets-dashboard/kube-dash-ingress-route.yaml

# Test dashboard (SUCCESS!)
curl -k -I https://dashboard.pindaroli.org --max-time 10
curl -k https://dashboard.pindaroli.org --max-time 10 | head -10
```

## Complete Command Reference

### Diagnostic Commands

```bash
# Check cluster status
kubectl get nodes -o wide
kubectl get pods -A
kubectl top nodes

# Check specific namespace
kubectl get all -n <namespace>
kubectl describe deployment <name> -n <namespace>
kubectl logs <pod-name> -n <namespace> --tail=20

# DNS testing
kubectl run dns-test --image=busybox --restart=Never -- nslookup <service>.<namespace>.svc.cluster.local
kubectl logs dns-test && kubectl delete pod dns-test

# Service connectivity testing
kubectl run curl-test --image=curlimages/curl --restart=Never -- curl -v http://<service>.<namespace>.svc.cluster.local:<port>/
kubectl logs curl-test && kubectl delete pod curl-test

# Check RBAC
kubectl get clusterrole <role-name>
kubectl get clusterrolebinding <binding-name>
kubectl describe clusterrolebinding <binding-name>

# Check service endpoints
kubectl get endpoints -n <namespace>
kubectl describe service <service-name> -n <namespace>

# Force delete stuck resources
kubectl get <resource> <name> -o json | jq '.spec.finalizers = []' | kubectl replace --raw "/api/v1/<resource>s/<name>/finalize" -f -

# Test external connectivity
curl -k -I https://<hostname> --max-time 10
curl -k -v https://<hostname> --max-time 5
ping -c 3 <ip-address>
```

### Fix Patterns

```bash
# Generic RBAC fix
kubectl create clusterrole <service-name> --verb=get,list,watch --resource=<resources>
kubectl create clusterrolebinding <service-name> --clusterrole=<service-name> --serviceaccount=<namespace>:<service-account>
kubectl rollout restart deployment/<service-name> -n <namespace>

# Restart all deployments in namespace
kubectl rollout restart deployment -n <namespace>

# Copy secrets between namespaces
kubectl get secret <secret-name> -n <source-namespace> -o yaml | sed 's/namespace: <source>/namespace: <target>/' | kubectl apply -f -

# Test LoadBalancer
kubectl get services -A --field-selector spec.type=LoadBalancer
ping -c 3 <loadbalancer-ip>
```

## Verification Commands

```bash
# Final verification that everything works
curl -k -I https://home.pindaroli.org --max-time 5          # Homepage: ✅ HTTP 200
curl -k -I https://dashboard.pindaroli.org --max-time 5     # Dashboard: ✅ HTTP 200  
curl -k -I https://jellyfin.pindaroli.org --max-time 5      # Jellyfin: ✅ HTTP 302

# Check all critical components
kubectl get pods -n kube-system | grep -E "(coredns|calico|metrics)"
kubectl get pods -n traefik
kubectl get pods -n metallb  
kubectl get pods -n kubernetes-dashboard
kubectl get pods -n default | grep homepage
```

## Summary

The dashboard fix required resolving multiple cascading issues:

1. **Infrastructure**: Stuck namespaces, failed deployments
2. **RBAC**: Calico, Metrics-Server, Traefik, CoreDNS, Homepage
3. **Network**: MetalLB LoadBalancer, DNS resolution  
4. **Certificates**: TLS verification between Traefik and Kong

**Final Solution**: Traefik ServersTransport with `insecureSkipVerify: true` to handle Kong's self-signed certificate.

**Result**: ✅ https://dashboard.pindaroli.org now works perfectly!
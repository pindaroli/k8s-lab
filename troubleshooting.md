# Kubernetes Cluster Troubleshooting Guide

This guide contains all the troubleshooting commands and fixes used to resolve RBAC and networking issues in a MicroK8s cluster after enabling RBAC.

## Table of Contents

1. [Cluster Health Checks](#cluster-health-checks)
2. [RBAC Issues](#rbac-issues)
3. [Network and DNS Issues](#network-and-dns-issues)
4. [Service-Specific Troubleshooting](#service-specific-troubleshooting)
5. [Common Fix Patterns](#common-fix-patterns)

## Cluster Health Checks

### Check Overall Cluster Status
```bash
# Check MicroK8s status
ssh root@k8s-control 'microk8s status --wait-ready'

# Check all nodes
kubectl get nodes -o wide

# Check system pods
kubectl get pods -n kube-system

# Check resource usage
kubectl top nodes
```

### Check Deployment Status
```bash
# Check if deployments are creating pods
kubectl get deployments -n <namespace>
kubectl describe deployment <deployment-name> -n <namespace>

# Check replicasets (deployments create these)
kubectl get replicasets -n <namespace>

# Check events for errors
kubectl get events -n <namespace> --sort-by='.lastTimestamp'
```

## RBAC Issues

### Identifying RBAC Problems

```bash
# Check pod logs for permission errors
kubectl logs -l app=<app-label> -n <namespace> --tail=50 | grep -E "(forbidden|error|Error)"

# Look for specific RBAC error patterns
kubectl logs <pod-name> -n <namespace> | grep "is forbidden"
kubectl logs <pod-name> -n <namespace> | grep "cannot list resource"
```

### Traefik RBAC Fix

**Problem**: Traefik couldn't access IngressRoutes, Services, or Secrets
**Symptoms**: All routes return 404, logs show "forbidden" errors

```bash
# Check Traefik logs for RBAC errors
kubectl logs -n traefik -l app.kubernetes.io/name=traefik --tail=50 | grep -E "(forbidden|error)"

# Create proper Traefik RBAC (save as traefik-rbac.yaml)
cat > traefik-rbac.yaml << 'EOF'
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
  - apiGroups: ["traefik.io"]
    resources: ["middlewares", "middlewaretcps", "ingressroutes", "traefikservices", "ingressroutetcps", "ingressrouteudps", "tlsoptions", "tlsstores", "serverstransports", "serverstransporttcps"]
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

# Apply the fix
kubectl apply -f traefik-rbac.yaml

# Restart Traefik to pick up new permissions
kubectl rollout restart deployment/traefik -n traefik
```

### CoreDNS RBAC Fix

**Problem**: DNS resolution failing, services can't resolve each other
**Symptoms**: "NXDOMAIN" errors, Kong showing "name resolution failed"

```bash
# Check CoreDNS logs for RBAC errors
kubectl logs -n kube-system -l k8s-app=kube-dns --tail=20

# Test DNS resolution
kubectl run dns-test --image=busybox --restart=Never -- nslookup <service>.<namespace>.svc.cluster.local
kubectl logs dns-test
kubectl delete pod dns-test

# Create CoreDNS RBAC fix
kubectl create clusterrole system:coredns \
  --verb=get,list,watch \
  --resource=endpoints,services,pods,namespaces,endpointslices \
  --resource-name=""

kubectl create clusterrolebinding system:coredns \
  --clusterrole=system:coredns \
  --serviceaccount=kube-system:coredns

# Restart CoreDNS
kubectl rollout restart deployment/coredns -n kube-system
```

### MetalLB RBAC Fix

**Problem**: LoadBalancer IPs not working, MetalLB can't access EndpointSlices
**Symptoms**: LoadBalancer IP not pingable, services unreachable externally

```bash
# Check MetalLB speaker logs for RBAC errors
kubectl logs -n metallb -l app=metallb,component=speaker --tail=20

# Install MetalLB with Helm (includes proper RBAC)
helm repo add metallb https://metallb.github.io/metallb
helm install metallb metallb/metallb -n metallb

# Apply IP pool configuration
kubectl apply -f metallb-addpool.yaml
```

### Calico RBAC Fix

**Problem**: Network policies not working, BGP peering issues
**Symptoms**: Pods can't communicate, "connection is unauthorized" errors

```bash
# Check Calico node logs for RBAC errors
kubectl logs -l k8s-app=calico-node -n kube-system --tail=20

# Apply Calico with proper RBAC
curl -O https://raw.githubusercontent.com/projectcalico/calico/v3.26.1/manifests/calico.yaml
kubectl apply -f calico.yaml

# Restart Calico nodes if BGP issues persist
kubectl delete pod -l k8s-app=calico-node -n kube-system
```

### Metrics-Server RBAC Fix

**Problem**: Metrics not available, HPA not working
**Symptoms**: "kubectl top" fails, metrics-server crashing

```bash
# Check metrics-server logs
kubectl logs -n kube-system -l k8s-app=metrics-server --tail=20

# Create metrics-server RBAC
cat > metrics-server-rbac.yaml << 'EOF'
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRole
metadata:
  name: system:metrics-server
rules:
- apiGroups: [""]
  resources: ["pods", "nodes", "nodes/stats", "namespaces", "configmaps"]
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
```

## Network and DNS Issues

### Test Network Connectivity

```bash
# Test LoadBalancer IP reachability
ping -c 3 <loadbalancer-ip>

# Check MetalLB configuration
kubectl get ipaddresspools -n metallb
kubectl get l2advertisements -n metallb

# Test service endpoints
kubectl get endpoints -n <namespace>
kubectl describe service <service-name> -n <namespace>
```

### DNS Troubleshooting

```bash
# Test DNS resolution from within cluster
kubectl run dns-debug --image=busybox --restart=Never -- nslookup <service>.<namespace>.svc.cluster.local
kubectl logs dns-debug
kubectl delete pod dns-debug

# Check DNS configuration in pods
kubectl exec -it <pod-name> -n <namespace> -- cat /etc/resolv.conf

# Test specific service resolution
kubectl run curl-test --image=curlimages/curl --restart=Never -- curl -v http://<service>.<namespace>.svc.cluster.local:<port>/
kubectl logs curl-test
kubectl delete pod curl-test
```

### Force Delete Stuck Namespaces

```bash
# Remove finalizers from stuck namespace
kubectl get namespace <namespace> -o json | jq '.spec.finalizers = []' | kubectl replace --raw "/api/v1/namespaces/<namespace>/finalize" -f -

# Verify namespace is gone
kubectl get namespaces | grep <namespace>
```

## Service-Specific Troubleshooting

### Homepage Dashboard

```bash
# Check homepage pod and logs
kubectl get pods -l app.kubernetes.io/name=homepage -n default
kubectl logs -l app.kubernetes.io/name=homepage -n default --tail=20

# Test homepage URL
curl -k -I https://home.pindaroli.org

# Check RBAC permissions
kubectl get clusterrole homepage
kubectl get clusterrolebinding homepage
```

### Kubernetes Dashboard

```bash
# Check all dashboard components
kubectl get all -n kubernetes-dashboard

# Check Kong proxy logs for routing issues
kubectl logs -l app.kubernetes.io/name=kong -n kubernetes-dashboard --tail=20

# Test direct backend access
kubectl run test-direct --image=curlimages/curl --restart=Never -- curl -v http://kubernetes-dashboard-web.kubernetes-dashboard.svc.cluster.local:8000/
kubectl logs test-direct
kubectl delete pod test-direct

# Test Kong proxy directly
kubectl run test-kong --image=curlimages/curl --restart=Never -- curl -k -v https://kubernetes-dashboard-kong-proxy.kubernetes-dashboard.svc.cluster.local:443/
kubectl logs test-kong
kubectl delete pod test-kong
```

### Traefik IngressRoutes

```bash
# Check IngressRoute status
kubectl get ingressroute -A
kubectl describe ingressroute <name> -n <namespace>

# Check for duplicate routes (causes conflicts)
kubectl get ingressroute -A | grep <hostname>

# Test Traefik dashboard
curl -k -I https://traefik-dash.pindaroli.org
```

## Common Fix Patterns

### RBAC Issue Pattern

1. **Identify the problem**: Look for "forbidden" errors in logs
2. **Find the service account**: Check what SA the pod is using
3. **Create ClusterRole**: With required permissions
4. **Create ClusterRoleBinding**: Link SA to ClusterRole  
5. **Restart the service**: To pick up new permissions

```bash
# Generic RBAC fix template
kubectl create clusterrole <service-name> --verb=get,list,watch --resource=<resources>
kubectl create clusterrolebinding <service-name> --clusterrole=<service-name> --serviceaccount=<namespace>:<service-account>
kubectl rollout restart deployment/<service-name> -n <namespace>
```

### DNS Issue Pattern

1. **Test DNS resolution**: Use busybox/curl pods
2. **Check CoreDNS logs**: Look for RBAC errors
3. **Fix CoreDNS RBAC**: If needed
4. **Restart DNS and services**: To refresh caches

### Network Issue Pattern  

1. **Check LoadBalancer**: Ping external IP
2. **Check MetalLB**: Logs and configuration
3. **Check service endpoints**: Verify backend pods
4. **Test internal connectivity**: Pod-to-pod communication

### Service 500/404 Error Pattern

1. **Check backend pods**: Are they running?
2. **Test direct backend**: Bypass ingress/proxy
3. **Check DNS resolution**: Can services find each other?
4. **Check proxy logs**: Look for routing errors
5. **Verify RBAC**: All components have permissions

## Monitoring Commands

### Real-time Monitoring

```bash
# Watch pod status
kubectl get pods -w -n <namespace>

# Follow logs in real-time
kubectl logs -f -l app=<app-label> -n <namespace>

# Watch events
kubectl get events -w -n <namespace>

# Monitor cluster resources
watch kubectl top nodes
```

### Quick Health Check Script

```bash
#!/bin/bash
# Quick cluster health check

echo "=== Cluster Nodes ==="
kubectl get nodes

echo "=== System Pods ==="
kubectl get pods -n kube-system

echo "=== Traefik Status ==="
kubectl get pods -n traefik
curl -k -I https://home.pindaroli.org --max-time 5

echo "=== DNS Test ==="
kubectl run dns-check --image=busybox --restart=Never --rm -it -- nslookup kubernetes.default.svc.cluster.local

echo "=== LoadBalancer ==="
kubectl get services -A --field-selector spec.type=LoadBalancer
```

## Emergency Recovery

### Restart MicroK8s Completely

```bash
# Stop MicroK8s
ssh root@k8s-control 'microk8s stop'

# Start MicroK8s
ssh root@k8s-control 'microk8s start'

# Wait for ready
ssh root@k8s-control 'microk8s status --wait-ready'
```

### Reset Stuck Components

```bash
# Reset Traefik
kubectl delete deployment traefik -n traefik
helm uninstall traefik -n traefik
helm install traefik traefik/traefik -n traefik -f traefik-values.yaml

# Reset CoreDNS
kubectl rollout restart deployment/coredns -n kube-system

# Reset MetalLB
helm uninstall metallb -n metallb
kubectl delete namespace metallb
helm install metallb metallb/metallb -n metallb --create-namespace
```

---

## Notes

- Always check RBAC first when services fail after enabling RBAC
- DNS issues often cascade to multiple services
- Test components individually before testing end-to-end
- Keep backups of working configurations
- Document custom RBAC configurations for future reference
# Homepage Dashboard Setup

## Overview

Homepage is a customizable dashboard for your Kubernetes cluster and services. It provides widgets for monitoring cluster resources, links to services, and real-time metrics.

## Features

- **Kubernetes Integration**: Displays cluster metrics, node status, and pod information
- **Service Links**: Quick access to all your services (Jellyfin, Sonarr, Radarr, etc.)
- **Resource Monitoring**: CPU and memory usage widgets
- **Search Integration**: Built-in search functionality
- **Responsive Design**: Works on desktop and mobile devices

## RBAC Configuration

**IMPORTANT**: Homepage requires specific RBAC permissions to access Kubernetes resources and display cluster information.

### Required Permissions

The deployment includes:

1. **ServiceAccount**: `homepage` in default namespace
2. **ClusterRole**: Permissions for:
   - Namespaces, pods, nodes (core resources)
   - Ingresses and IngressRoutes (networking)
   - Gateway API resources
   - Metrics API resources

3. **ClusterRoleBinding**: Links the service account to the cluster role

### RBAC Resources in homepage.yaml

```yaml
# ServiceAccount
apiVersion: v1
kind: ServiceAccount
metadata:
  name: homepage
  namespace: default

# ClusterRole with required permissions
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRole
metadata:
  name: homepage
rules:
  - apiGroups: [""]
    resources: ["namespaces", "pods", "nodes"]
    verbs: ["get", "list"]
  - apiGroups: ["traefik.io"]
    resources: ["ingressroutes"]
    verbs: ["get", "list"]
  # ... additional permissions

# ClusterRoleBinding
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRoleBinding
metadata:
  name: homepage
roleRef:
  apiGroup: rbac.authorization.k8s.io
  kind: ClusterRole
  name: homepage
subjects:
  - kind: ServiceAccount
    name: homepage
    namespace: default
```

## Installation

### 1. Apply Homepage Configuration

```bash
kubectl apply -f homepage.yaml
```

### 2. Verify RBAC Setup

Check that RBAC resources are created:

```bash
# Check ClusterRole
kubectl get clusterrole homepage

# Check ClusterRoleBinding
kubectl get clusterrolebinding homepage

# Check ServiceAccount
kubectl get serviceaccount homepage -n default
```

### 3. Verify Deployment

```bash
# Check pod status
kubectl get pods -l app.kubernetes.io/name=homepage -n default

# Check logs for RBAC issues
kubectl logs -l app.kubernetes.io/name=homepage -n default --tail=20
```

## Access

Once deployed, access Homepage at: **https://home.pindaroli.org**

## Configuration

### Services Configuration

The services are configured in the ConfigMap (`services.yaml`):

- **Kubernetes Services**: Dashboard, Traefik
- **Media Services**: Jellyfin, qBittorrent
- **Arr Services**: Sonarr, Radarr, Lidarr, Readarr, Prowlarr, Bazarr, Jellyseerr

### Widgets Configuration

Enabled widgets (`widgets.yaml`):

- **Kubernetes Cluster**: Shows cluster CPU/memory usage
- **Nodes**: Displays individual node metrics
- **Resources**: System resource monitoring
- **Search**: DuckDuckGo search integration

## Troubleshooting

### RBAC Permission Errors

If you see errors like `"nodes is forbidden"` in the logs:

1. **Check ClusterRole exists**:
   ```bash
   kubectl get clusterrole homepage
   ```

2. **Check ClusterRoleBinding**:
   ```bash
   kubectl describe clusterrolebinding homepage
   ```

3. **Recreate RBAC if missing**:
   ```bash
   kubectl apply -f homepage.yaml
   kubectl rollout restart deployment/homepage -n default
   ```

### Common Issues

1. **Pod not starting**: Check resource limits and image availability
2. **Cannot access services**: Verify IngressRoute and TLS certificate
3. **Empty widgets**: Ensure RBAC permissions are properly configured
4. **Service discovery errors**: Check kubernetes.yaml configuration in ConfigMap

### Logs Analysis

Check homepage logs for specific errors:

```bash
# View recent logs
kubectl logs -l app.kubernetes.io/name=homepage -n default --tail=50

# Follow logs in real-time
kubectl logs -l app.kubernetes.io/name=homepage -n default -f
```

## Security Notes

- Homepage runs with cluster-wide read permissions
- ServiceAccount has minimal required permissions (read-only)
- Secrets are not accessible (only metadata)
- Use in trusted environments only

## Updates

To update Homepage:

```bash
# Update the deployment (pulls latest image)
kubectl rollout restart deployment/homepage -n default

# Or apply configuration changes
kubectl apply -f homepage.yaml
```
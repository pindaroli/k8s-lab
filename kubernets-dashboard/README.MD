# Kubernetes Dashboard Installation

This guide provides step-by-step instructions to install the Kubernetes Dashboard using the official Helm chart.

## Prerequisites

- Kubernetes cluster running
- Helm 3.x installed
- kubectl configured to access your cluster

## Installation Steps

### 1. Add the Kubernetes Dashboard Helm Repository

```bash
helm repo add kubernetes-dashboard https://kubernetes.github.io/dashboard/
helm repo update
```

### 2. Create the Dashboard Namespace

```bash
kubectl create namespace dashboard
```

### 3. Install the Dashboard with Custom Values

```bash
helm install kubernetes-dashboard kubernetes-dashboard/kubernetes-dashboard \
  --namespace dashboard \
  --values kube-dash-values.yaml
```

### 4. Create Admin Service Account and RBAC

Apply the service account configuration:

```bash
kubectl apply -f service-account.yaml
```

Or apply the token configuration (alternative):

```bash
kubectl apply -f token.yaml
```

### 5. Get the Admin Token

To access the dashboard, you'll need the admin token:

```bash
kubectl get secret admin-user-token -n dashboard -o jsonpath='{.data.token}' | base64 --decode
```

### 6. Access the Dashboard

If using ingress (configured in values file):
- Access via: http://dashboard.local

If using port-forward:
```bash
kubectl port-forward -n dashboard svc/kubernetes-dashboard-kong-proxy 8443:443
```
- Access via: https://localhost:8443

## Configuration Files

- `kube-dash-values.yaml`: Helm values configuration
- `service-account.yaml`: Admin service account with full cluster permissions
- `token.yaml`: Alternative admin service account configuration

## Security Notes

The service accounts created have full cluster admin privileges. Use with caution in production environments.

## Troubleshooting

### Check Dashboard Status
```bash
kubectl get pods -n dashboard
kubectl get svc -n dashboard
```

### View Dashboard Logs
```bash
kubectl logs -n dashboard -l app.kubernetes.io/name=kubernetes-dashboard
```

### Uninstall Dashboard
```bash
helm uninstall kubernetes-dashboard -n dashboard
kubectl delete namespace dashboard
```

## References

- [Official Helm Chart](https://artifacthub.io/packages/helm/k8s-dashboard/kubernetes-dashboard)
- [Kubernetes Dashboard Documentation](https://kubernetes.io/docs/tasks/access-application-cluster/web-ui-dashboard/)
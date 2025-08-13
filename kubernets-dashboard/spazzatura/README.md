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

### 5. Generate Bearer Token for Authentication

The dashboard requires a bearer token for authentication. Generate one using the admin-user service account:

```bash
kubectl -n kubernetes-dashboard create token admin-user
```

**Long-lived Bearer Token** (for CSRF compatibility):
```
eyJhbGciOiJSUzI1NiIsImtpZCI6IlljTXhWTDNwMVMwLWkxR2JIVmtQakJ2WEZBWGFIMVl2ZHdfbC15REFXd2MifQ.eyJpc3MiOiJrdWJlcm5ldGVzL3NlcnZpY2VhY2NvdW50Iiwia3ViZXJuZXRlcy5pby9zZXJ2aWNlYWNjb3VudC9uYW1lc3BhY2UiOiJrdWJlcm5ldGVzLWRhc2hib2FyZCIsImt1YmVybmV0ZXMuaW8vc2VydmljZWFjY291bnQvc2VjcmV0Lm5hbWUiOiJhZG1pbi11c2VyLXRva2VuIiwia3ViZXJuZXRlcy5pby9zZXJ2aWNlYWNjb3VudC9zZXJ2aWNlLWFjY291bnQubmFtZSI6ImFkbWluLXVzZXIiLCJrdWJlcm5ldGVzLmlvL3NlcnZpY2VhY2NvdW50L3NlcnZpY2UtYWNjb3VudC51aWQiOiJlZWZkNzE0NC02M2FkLTQ3MzgtOWEzYi01YTQzNDI0NTY1MWYiLCJzdWIiOiJzeXN0ZW06c2VydmljZWFjY291bnQ6a3ViZXJuZXRlcy1kYXNoYm9hcmQ6YWRtaW4tdXNlciJ9.DazLjHOFimyVqcr-TAEf5zpqLhk45xqVXbbhdnxirbHuFdjqqwhSuPd9Vi08BynyuAjMeF1CHbf9zcieKPm-SYEldm6Pw3r0LNEdBWl3DznUgKGhaNRFIt2AvpctEx9nWFL5IFu6K3K6j_KzpjWmvJJB7dr42fxt_ABY1MW--VKm6pGtyRXRGWXXzRQ0nJvtuj50GEBYYbBzWByR3ony4fsPVtfiRyNoTzHcduZOCQfTl1PYcyihnB70YKnHqEl69dMo58_T_MA9Y5ca6dtFBKQPJudGAJ1NswSt46QPB4OMDxABPD-kcHSkb3bzDVebEO4krWhP6zsoVCa44q2pfA
```

Alternative - get fresh token from secret:
```bash
kubectl get secret admin-user-token -n kubernetes-dashboard -o jsonpath='{.data.token}' | base64 --decode
```

### 6. Access the Dashboard

**Production URL**: https://dashboard.pindaroli.org

The dashboard is accessible via Traefik IngressRoute with TLS encryption.

If using port-forward for local testing:
```bash
kubectl port-forward -n kubernetes-dashboard svc/kubernetes-dashboard-kong-proxy 8443:443
```
- Access via: https://localhost:8443

## Setup with MicroK8s Addon

**Recommended Method**: Use MicroK8s addon instead of Helm:

```bash
# Enable dashboard addon
ssh root@k8s-control 'microk8s enable dashboard'

# Create admin service account
kubectl apply -f admin-user-k8s-dashboard.yaml

# Generate bearer token
kubectl -n kubernetes-dashboard create token admin-user
```

## Configuration Files

- `kube-dash-values.yaml`: Helm values configuration
- `service-account.yaml`: Admin service account with full cluster permissions  
- `token.yaml`: Alternative admin service account configuration
- `admin-user-k8s-dashboard.yaml`: MicroK8s admin service account and ClusterRoleBinding
- `kube-dash-ingress-route.yaml`: Traefik IngressRoute for external access
- `dashboard-serverstransport.yaml`: Traefik ServersTransport for TLS skip verification

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

## Copy TLS Secret Between Namespaces

To copy the pindaroli-wildcard-tls secret from arr namespace to dashboard namespace:

```bash
kubectl get secret pindaroli-wildcard-tls -n arr -o yaml | sed 's/namespace: arr/namespace: dashboard/' | kubectl apply -f -
```

## References

- [Official Helm Chart](https://artifacthub.io/packages/helm/k8s-dashboard/kubernetes-dashboard)
- [Kubernetes Dashboard Documentation](https://kubernetes.io/docs/tasks/access-application-cluster/web-ui-dashboard/)
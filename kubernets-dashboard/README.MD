# Kubernetes Dashboard Admin User

## Setup

Apply the admin user configuration:
```bash
kubectl apply -f dashboard-admin-user.yaml
```

## Get Access Token

### Method 1: Generate New Token (Recommended)
You can generate token for service account with:
```bash
kubectl -n kubernetes-dashboard create token admin-user
```

For custom expiration (24 hours):
```bash
kubectl create token admin-user -n kubernetes-dashboard --duration=24h
```

## Configuration Details

The `dashboard-admin-user.yaml` file creates:
- ServiceAccount `admin-user` in `kubernetes-dashboard` namespace
- ClusterRoleBinding granting `cluster-admin` role 

Use the generated token to log into the Kubernetes Dashboard with full cluster admin privileges.
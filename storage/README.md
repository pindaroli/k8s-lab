# Kubernetes Storage Configuration

This directory contains the manifest definitions for the cluster's storage infrastructure.

## Structure

- **`local-path-provisioner.yaml`**: Deploys the `local-path` Storage Class.
  - **Backend**: Local NVMe disk on `talos-cp-01` (`/var/mnt/hot`).
  - **Strategy**: Hot Tier (Db/Configs).
  - **Naming**: `pathPattern: "{{ .PVC.Name }}"` (Clean directory names).
  - **Security**: Requires privileged Pod Security labels and RBAC access to `pods/log` to functioning correctly (creating/verifying folders).

- **`storage-classes.yaml`**: Defines additional Storage Classes.
  - `nfs-csi`: Standard NFS (Retain).
  - `csi-nfs-stripe-arr-conf`: Legacy/Alternative NFS for configs (Delete).

- **`persistent-volumes.yaml`**: Static Persistent Volumes.
  - `pv-servarr-jellyfin-media`: Points to TrueNAS `/mnt/oliraid/arrdata/media`.

- **`pvc-shared.yaml`**: Shared Claims.
  - `servarr-jellyfin-media`: The PVC binding to the media PV, used by Sonarr/Radarr.

## Application Usage

### Servarr Stack
- **Configs**: Use `storageClass: local-path` (NVMe).
- **Media**: Uses `existingClaim: servarr-jellyfin-media` (NFS).

### KasmWeb / N8N
- **Storage**: Use `storageClass: local-path` (NVMe).

## Deployment
```bash
kubectl apply -f storage/
pv-servarr-jellyfin-media must be applied BEFORE the pvc-shared.yaml (automatically handled by apply -f folder if named alphabetically, otherwise strict order might be needed).
# Recommended:
kubectl apply -f storage/storage-classes.yaml
kubectl apply -f storage/local-path-provisioner.yaml
kubectl apply -f storage/persistent-volumes.yaml
kubectl apply -f storage/pvc-shared.yaml
```

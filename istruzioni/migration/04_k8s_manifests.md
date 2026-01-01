# Phase 4: Cluster Migration (Kubernetes Manifests)
**Goal**: Configure Kubernetes to consume the new storage and restore applications.
**Prerequisites**: Talos running with mounted Hot Disk at `/var/mnt/hot`.

## 1. Local Path Provisioner
- [ ] **Download Manifest**: Get official `local-path-storage.yaml`.
- [ ] **Customize Config**:
    - Edit the `ConfigMap` in the manifest.
    - Change `nodePath`: `/opt/local-path-provisioner` -> `/var/mnt/hot`.
- [ ] **Apply**: `kubectl apply -f local-path-storage.yaml`.
- [ ] **StorageClass**: Define `nvme-hot` StorageClass pointing to `local-path`.

## 2. Deploy Management Tools
- [ ] **FileBrowser**:
    - Deploy `filebrowser` pod mounting a PVC from `nvme-hot`.
    - Verify web access.

## 3. Migrate Applications
- [ ] **Update Manifests** (`k8s-lab/servarr/...`):
    - Change PVC StorageClassName: `nfs-csi` -> `nvme-hot` (for Config/DBs).
    - Keep Media PVCs on `nfs-csi`.
- [ ] **Apply Changes**:
    ```bash
    kubectl apply -f servarr/
    ```
- [ ] **Validation**:
    - Check Pod status: `kubectl get pods -A`.
    - Verify application logs for SQLite errors (should be zero now with block storage).

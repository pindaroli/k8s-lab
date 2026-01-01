# Phase 4: Cluster Migration (Kubernetes Manifests)
**Goal**: Configure Kubernetes core services and restore applications.
**Prerequisites**: Talos running, Storage Class `nvme-hot` ready.

## 1. Storage & Core Config
- [ ] **Local Path Provisioner**:
    - Apply modified manifest (ConfigMap -> `/var/mnt/hot`).
    - Create `nvme-hot` StorageClass.
- [ ] **NFS CSI**:
    - Deploy `nfs-csi` provider for the Warm Tier.
    - Verify connectivity to TrueNAS.
- [ ] **Namespaces**:
    - Ensure namespaces exist: `metallb`, `traefik`, `cert-manager`, `oauth2-proxy`, `arr`, `kasmweb`.

## 2. Infrastructure Layer
*Deploy in this order:*
1.  **MetalLB**:
    - `kubectl apply -f metallb/`
    - Verify Speaker/Controller pods.
2.  **Traefik**:
    - `kubectl apply -f traefik/`
    - Check LoadBalancer IP assignment.
3.  **Cert-Manager**:
    - `kubectl apply -f cert-manager/`
    - Verify ClusterIssuer.
4.  **OAuth2 Proxy**:
    - `kubectl apply -f oauth2-proxy/`
    - Verify connection to Google Auth.

## 3. Management Tools
- [ ] **FileBrowser**:
    - Deploy `filebrowser` pod (PVC `nvme-hot`).
- [ ] **Homepage**:
    - `kubectl apply -f homepage/`

## 4. Application Migration (Servarr)
- [ ] **Update Manifests** (`servarr/`):
    - **Config**: Change StorageClass `nfs-csi` -> `nvme-hot` (Radarr, Sonarr, Prowlarr, etc.).
    - **Media**: Keep StorageClass `nfs-csi` (Jellyfin Media, Download clients).
    - **Jellyfin**: **REMOVE** Jellyfin Deployment/StatefulSet from the folder or delete the file.
- [ ] **Deploy Apps**:
    ```bash
    kubectl apply -f servarr/
    ```
- [ ] **Jellyfin External**:
    - Apply the Service wrapper: `kubectl apply -f jellyfin-external-service.yaml`
    - Verify it points to the LXC IP (`192.168.1.12`).

## 5. Other Apps
- [ ] **Calibre**: `kubectl apply -f calibre/`
- [ ] **Kasm**: `kubectl apply -f kasmweb/`

## 6. Validation
- [ ] Check all PVCs are Bound (`kubectl get pvc -A`).
- [ ] Check SQLite databases work ok on NVMe.
- [ ] Verify Ingress routes (`https://home.pindaroli.org`, `https://jellyfin.pindaroli.org`).

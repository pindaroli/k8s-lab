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
    - Ensure namespaces exist: `metallb`, `traefik`, `cert-manager`, `oauth2-proxy`, `arr`, `kasmweb`, `monitoring`.

## 2. Observability (New)
*Goal: Visibility into cluster health and centralized logs.*
- [ ] **Metrics Server** (Critical for `kubectl top`):
    - `kubectl apply -f https://github.com/kubernetes-sigs/metrics-server/releases/latest/download/components.yaml`
    - *Note*: Use `--kubelet-insecure-tls` if certificates are self-signed.
- [ ] **Prometheus & Grafana**:
    - Add repo: `helm repo add prometheus-community https://prometheus-community.github.io/helm-charts`
    - Install: `helm install kube-prometheus-stack prometheus-community/kube-prometheus-stack -n monitoring`
- [ ] **Loki Stack** (Logs):
    - Add repo: `helm repo add grafana https://grafana.github.io/helm-charts`
    - Install: `helm install loki grafana/loki-stack -n monitoring`
- [ ] **Verification**:
    - Access Grafana (Port-Forward or Ingress).
    - Check `kubectl top nodes` works.

## 3. Disaster Recovery (Velero)
*Goal: Backup Kubernetes Resources & PVs to MinIO (TrueNAS), synced to GDrive.*
- [ ] **TrueNAS Prep**:
    - Install **MinIO** App (Official) or Custom App.
    - Create Bucket: `k8s-velero`.
    - Configure **Cloud Sync Task**: Sync `k8s-velero` <-> Google Drive (Daily).
- [ ] **Install Velero**:
    - `brew install velero` (Mac).
    - Create `velero-credentials` file (MinIO Access/Secret Key).
    - Install:
      ```bash
      velero install \
        --provider aws \
        --plugins velero/velero-plugin-for-aws:v1.7.0 \
        --bucket k8s-velero \
        --secret-file ./velero-credentials \
        --use-volume-snapshots=false \
        --backup-location-config region=minio,s3ForcePathStyle="true",s3Url=http://10.10.10.50:9000
      ```

## 4. Infrastructure Layer
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

## 5. Management Tools
- [ ] **FileBrowser**:
    - Deploy `filebrowser` pod (PVC `nvme-hot`).
- [ ] **Homepage**:
    - `kubectl apply -f homepage/`

## 6. Application Migration (Servarr)
- [ ] **Update Manifests** (`servarr/`):
    - **Config**: Change StorageClass `nfs-csi` -> `nvme-hot`.
    - **Resource Limits** (Critical): Add CPU/RAM limits to Deployments to prevent Node saturation.
    - **Media**: Keep StorageClass `nfs-csi`.
    - **Jellyfin**: **REMOVE** Jellyfin Deployment/StatefulSet from the folder or delete the file.
- [ ] **Deploy Apps**:
    ```bash
    kubectl apply -f servarr/
    ```
- [ ] **Jellyfin External**:
    - Apply the Service wrapper: `kubectl apply -f jellyfin-external-service.yaml`
    - Verify it points to the LXC IP (`192.168.1.12`).

## 7. Other Apps
- [ ] **Calibre**: `kubectl apply -f calibre/`
- [ ] **Kasm**: `kubectl apply -f kasmweb/`

## 8. Validation
- [ ] Check all PVCs are Bound (`kubectl get pvc -A`).
- [ ] Check SQLite databases work ok on NVMe.
- [ ] Verify Ingress routes (`https://home.pindaroli.org`, `https://jellyfin.pindaroli.org`).

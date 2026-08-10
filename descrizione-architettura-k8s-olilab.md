---
title: ServiceNow MID Server — Custom Deployment & K8s Architecture Context
type: deployment_summary
certified_for_ai: true
source_paths:
  - pindaroli-arr-helm/custom-docker-images/custom-docker-MID
  - k8s-lab/sn
target_namespace: sn
mid_server_name: MID_Server_K8s
k8s_hostname: k8s-lab-mid-server
tags:
  - servicenow
  - mid-server
  - kubernetes
  - rbac
  - discovery-context
---

# 🛰️ MID Server ServiceNow: Architettura, Immagine Docker e Deployment K8s

## 1. 📦 Custom Docker Image (`custom-docker-MID`)
L'immagine Docker del MID Server è stata compilata su misura tramite un **Multi-Stage Build** situato in `pindaroli-arr-helm/custom-docker-images/custom-docker-MID/Dockerfile`.

### Specifica dell'Immagine
- **Release ServiceNow**: `Australia Patch 3` (Buildstamp: `australia-02-11-2026__patch3-05-25-2026_06-12-2026_1106`).
- **Base OS Finale**: `almalinux:9.2` (Enterprise Linux).
- **Pacchetti e Tools Inclusi**: EPEL repository, `glibc-langpack-en`, `bind-utils`, `xmlstarlet`, `curl`, `procps-ng`, `diffutils`, `net-tools`.
- **Utente di Esecuzione**: Utente unprivileged `mid` (UID: `1001`, GID: `1001` / `0` root group compatibility).
- **Tag Registry**:
  - `ghcr.io/pindaroli/custom-mid-server:australia-02-11-2026__patch3-05-25-2026_06-12-2026_1106`
  - `lgp1985/sn-mid-server:latest`

### Runtime & Entrypoint (`entrypoint.sh` / `init`)
- Il container legge le variabili d'ambiente di connessione e aggiorna in modalità dinamica il file `/opt/agent/config.xml` prima di avviare il demone via `/opt/snc_mid_server/init start`.
- Supporta variabili primarie e fallback:
  - URL Istanza: `MID_INSTANCE_URL` o `SN_URL`
  - Username: `MID_INSTANCE_USERNAME` o `SN_USER`
  - Password: `MID_INSTANCE_PASSWORD` o `SN_PASSWD`
  - Nome MID: `MID_SERVER_NAME` o `SN_MID_NAME`

---

## 2. ☸️ Manifests Kubernetes & Deployment (`k8s-lab/sn`)

Il MID Server è distribuito all'interno del cluster Kubernetes nel namespace dedicato **`sn`**.

### A. RBAC di Discovery (`sn-rbac-minimal.yaml`)
Per consentire al MID Server di effettuare il Discovery del cluster, sono stati definiti i seguenti oggetti RBAC nel file `sn-rbac-minimal.yaml`:

- **ServiceAccount**: `sn-discovery-sa` nel namespace `sn`.
- **ClusterRole**: `sn-discovery-read-role` con permessi di sola lettura (`get`, `list`, `watch`).
- **Risorse Monitorabili**:
  - **Core Groups (`""`)**: `nodes`, `namespaces`, `pods`, `services`, `configmaps`
  - **Apps Group (`apps`)**: `deployments`, `statefulsets`, `daemonsets`, `replicasets`
  - **Batch Group (`batch`)**: *(incluso nelle regole di apiGroup)*
  - **Networking Group (`networking.k8s.io`)**: `ingresses`
- **ClusterRoleBinding**: `sn-discovery-binding` che lega `sn-discovery-sa` al ClusterRole `sn-discovery-read-role`.

```yaml
# Snippet RBAC in k8s-lab/sn/sn-rbac-minimal.yaml
apiVersion: v1
kind: ServiceAccount
metadata:
  name: sn-discovery-sa
  namespace: sn
---
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRole
metadata:
  name: sn-discovery-read-role
rules:
- apiGroups: ["", "apps", "batch", "networking.k8s.io"]
  resources: ["nodes", "namespaces", "pods", "services", "deployments", "statefulsets", "daemonsets", "replicasets", "ingresses", "configmaps"]
  verbs: ["get", "list", "watch"]
---
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRoleBinding
metadata:
  name: sn-discovery-binding
subjects:
- kind: ServiceAccount
  name: sn-discovery-sa
  namespace: sn
roleRef:
  kind: ClusterRole
  name: sn-discovery-read-role
  apiGroup: rbac.authorization.k8s.io
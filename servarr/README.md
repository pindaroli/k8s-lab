# Servarr Stack Installation

## Prerequisites

1. Install NFS CSI driver:
```bash
helm repo add csi-driver-nfs https://raw.githubusercontent.com/kubernetes-csi/csi-driver-nfs/master/charts
helm repo update

helm install csi-driver-nfs csi-driver-nfs/csi-driver-nfs \
    --namespace kube-system \
    --set kubeletDir=/var/snap/microk8s/common/var/lib/kubelet
```

2. Create storage volumes:
```bash
kubectl apply -f arr-volumes-csi.yaml
```

## Installation

Install servarr stack from local Helm chart:
```bash
helm install servarr /Users/olindo/prj/helm/charts/servarr -n arr --create-namespace -f arr-values.yaml
```

## Management

- **List releases**: `helm list -n arr`
- **Get values**: `helm get values servarr -n arr`
- **Upgrade**: `helm upgrade servarr /Users/olindo/prj/helm/charts/servarr -n arr -f arr-values.yaml`
- **Uninstall**: `helm uninstall servarr -n arr`
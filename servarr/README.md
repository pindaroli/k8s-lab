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
- **Upgrade**: `helm upgrade servarr ../helm/charts/servarr -n arr -f servarr/arr-values.yaml`
- **Uninstall**: `helm uninstall servarr -n arr`

## Node Affinity Configuration

### Jellyfin Pod Placement
- **Primary**: Runs on `k8s-control` node
- **Failover**: Moves to `k8s-runner-1` only if `k8s-control` is down
- **Configuration**: Node affinity rules in `arr-values.yaml`

#### Behavior
- Normal operation: Jellyfin on k8s-control
- Node failure: Automatic failover to k8s-runner-1 (300s grace period)
- Recovery: Manual pod restart needed to return to k8s-control

#### Check Status
```bash
kubectl get pods -n arr -o wide | grep jellyfin
```
```
helm repo add csi-driver-nfs https://raw.githubusercontent.com/kubernetes-csi/csi-driver-nfs/master/charts
helm repo update

helm install csi-driver-nfs csi-driver-nfs/csi-driver-nfs --namespace kube-system

k apply -f arr-volumes-csi.yaml

helm repo add kubitodev https://charts.kubito.dev
helm repo update

helm install servarr kubitodev/servarr \
  --namespace arr \
  --create-namespace \
  --values arr-values.yaml \
  --wait

k apply -


helm install -n arr nfs-subdir-external-provisioner nfs-subdir-external-provisioner/nfs-subdir-external-provisioner \
    -f nfs-subdir-prov-values.yaml
```
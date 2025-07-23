```
helm repo add nfs-subdir-external-provisioner https://kubernetes-sigs.github.io/nfs-subdir-external-provisioner/
helm install nfs-subdir-external-provisioner nfs-subdir-external-provisioner/nfs-subdir-external-provisioner \
        --namespace arr \
        --create-namespace \
        --values nfs-subdir-prov-values.yaml \
        --wait
``` 
helm repo add nfs-subdir-external-provisioner https://kubernetes-sigs.github.io/nfs-subdir-external-provisioner/
helm install -n arr nfs-subdir-external-provisioner nfs-subdir-external-provisioner/nfs-subdir-external-provisioner \
    --set nfs.server=192.168.1.115 \
    --set nfs.path=/mnt/oliraid/k8s-disk \
    --set storageClass.name=nfs-subdir \
    --set storageClass.reclaimPolicy=Retain
q
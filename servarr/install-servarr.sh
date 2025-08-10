#!/bin/bash
k apply -f arr-volumes.yaml -a arr
# Apply the PersistentVolumeClaim configuration
helm install servarr kubitodev/servarr\
    --create-namespace \
    --namespace=arr \
    --values=arr-values.yaml \
    --wait
helm upgrade servarr kubitodev/servarr\
    --create-namespace \
    --namespace=arr \
    --values=arr-values.yaml \
    --wait




#helm install servarr /Users/olindo/prj/helm/charts/servarr -n arr -f /Users/olindo/prj/k8s-lab/servarr/arr-values.yaml

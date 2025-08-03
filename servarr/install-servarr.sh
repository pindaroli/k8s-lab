#!/bin/bash
k apply -f arr-volumes.yaml -a arr
# Apply the PersistentVolumeClaim configuration
helm install servarr\
    --create-namespace \
    --namespace=arr \
    --values=arr-values.yaml \
    kubitodev/servarr

helm install servarr /Users/olindo/prj/helm/charts/servarr -n arr -f /Users/olindo/prj/k8s-lab/servarr/arr-values.yaml 

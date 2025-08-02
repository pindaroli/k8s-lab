#!/bin/bash
k apply -f arr-volumes.yaml -a arr
# Apply the PersistentVolumeClaim configuration
helm install servarr\
    --create-namespace \
    --namespace=arr \
    --values=arr-values.yaml \
    kubitodev/servarr
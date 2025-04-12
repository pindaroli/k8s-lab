#!/bin/bash

# Apply the PersistentVolumeClaim configuration
helm install servarr\
    --create-namespace \
    --namespace=arr \
    --values=arr-values.yaml \
    kubitodev/servarr
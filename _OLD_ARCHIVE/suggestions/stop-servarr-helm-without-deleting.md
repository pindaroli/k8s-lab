# How to Stop Servarr Helm Application Without Deleting

## Scale all deployments to 0 replicas
```bash
kubectl scale deployment --replicas=0 -n arr --all
```

## Scale specific deployments
```bash
kubectl scale deployment sonarr radarr prowlarr jellyfin --replicas=0 -n arr
```

## Restart later by scaling back up
```bash
kubectl scale deployment --replicas=1 -n arr --all
```

This preserves all configurations, persistent volumes, and the Helm release while stopping the pods.
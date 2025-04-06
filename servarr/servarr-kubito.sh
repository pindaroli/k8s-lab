helm repo add kubitodev https://charts.kubito.dev
helm install servarr kubitodev/servarr \
      --namespace arr \
      -f arr-values.yaml
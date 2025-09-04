```bash

helm repo add k8s-at-home https://k8s-at-home.com/charts/
helm install calibre k8s-at-home/calibre -f calibre-values.yaml -n calibre --create-namespace
``
```
helm install traefik traefik/traefik \
  --namespace traefik \
  --create-namespace \
  -f traefik-values.yaml \
  --wait

helm upgrade traefik traefik/traefik \
  --namespace traefik \
  --create-namespace \
  -f traefik-values.yaml \
  --wait

openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
  -keyout tls.key -out tls.crt \
  -subj "/CN=*.local"

  kubectl create secret tls local-selfsigned-tls \
  --cert=tls.crt --key=tls.key \
  --namespace traefik 

```
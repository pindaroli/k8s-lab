## Passo 1: Installare cert-manager

cert-manager gestisce automaticamente i certificati SSL in Kubernetes.

### Comando di installazione:
```bash
# Aggiungi repository Helm
helm repo add jetstack https://charts.jetstack.io
helm repo update

# Installa cert-manager
helm install cert-manager jetstack/cert-manager \
  --namespace cert-manager \
  --create-namespace \
  --version v1.13.3 \
  --set installCRDs=true
```

### Verifica installazione:
```bash
kubectl get pods -n cert-manager
```
### doc https://cert-manager.io/docs/usage/ingress/

### token per certmanager
<se loperdi devi rifarlo>


### per verificare il token
curl "https://api.cloudflare.com/client/v4/user/tokens/verify" \
     -H "Authorization: Bearer <token>"

### creare il secret con
cloudflare-token-secret.yaml
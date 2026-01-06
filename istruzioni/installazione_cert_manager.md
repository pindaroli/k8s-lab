# Guida Installazione e Configurazione Cert-Manager

Questa guida copre l'installazione di `cert-manager`, il recupero delle credenziali sicure e la configurazione per i certificati wildcard `*.pindaroli.org`.

## 1. Installazione di Cert-Manager (via Helm)

Esegui questi comandi per installare il software nel cluster:

```bash
# Aggiungi il repository ufficiale
helm repo add jetstack https://charts.jetstack.io
helm repo update

# Installa cert-manager nel namespace dedicato
helm install cert-manager jetstack/cert-manager \
  --namespace cert-manager \
  --create-namespace \
  --version v1.13.3 \
  --set installCRDs=true
```

## 2. Recupero del Token Cloudflare (da Ansible Vault)

Il token API di Cloudflare è salvato in modo sicuro nei file criptati di Ansible.

### A. Individuare il file
Il file segreto è: `ansible/vars/secrets.yml`

### B. Decriptare e Leggere il Token
Per leggere il token, devi usare `ansible-vault` con la password (che si trova in `~/.vault_pass.txt`).

Esegui questo comando per vedere le credenziali:
```bash
ansible-vault view ansible/vars/secrets.yml --vault-password-file ~/.vault_pass.txt
```

Cerca la variabile: `cloudflare_api_key`. Copia il valore (es. `97a3...`).

## 3. Configurazione del Secret Kubernetes

⚠️ **ATTENZIONE:** Non committare mai il file con il token reale su Git!

### A. Preparare il file del Secret
Usa il file esistente `cert-manager/cloudflare-token-secret.yaml`.
Assicurati che contenga il tuo token reale:

```yaml
apiVersion: v1
kind: Secret
metadata:
  name: cloudflare-api-token-secret
  namespace: cert-manager
type: Opaque
stringData:
  api-token: "INCOLLA_QUI_IL_TUO_TOKEN_RECUPERATO"
```

### B. Verificare .gitignore
Assicurati che questo file sia ignorato da git per sicurezza:
```bash
grep "cert-manager/cloudflare-token-secret.yaml" .gitignore || echo "cert-manager/cloudflare-token-secret.yaml" >> .gitignore
```

### C. Applicare il Secret
```bash
kubectl apply -f cert-manager/cloudflare-token-secret.yaml
```

## 4. Configurazione Issuer e Certificati


### A. Configurazione DNS (CRITICO: "ndots" Patch)

Per evitare problemi di "DNS Hijacking" con i domini Wildcard (`*.pindaroli.org`), è FONDAMENTALE patchare i deployment di Cert-Manager per forzare `ndots:1`.
Senza questo fix, Cert-Manager non riuscirà a validare i certificati.

```bash
# Applica la patch ai componenti di Cert-Manager
kubectl patch deployment cert-manager -n cert-manager --patch '{"spec": {"template": {"spec": {"dnsConfig": {"options": [{"name": "ndots", "value": "1"}]}}}}}'
kubectl patch deployment cert-manager-cainjector -n cert-manager --patch '{"spec": {"template": {"spec": {"dnsConfig": {"options": [{"name": "ndots", "value": "1"}]}}}}}'
kubectl patch deployment cert-manager-webhook -n cert-manager --patch '{"spec": {"template": {"spec": {"dnsConfig": {"options": [{"name": "ndots", "value": "1"}]}}}}}'
```

### B. Applica il ClusterIssuer
Questo definisce "Chi" emette i certificati (Let's Encrypt + Cloudflare).
**Nota Importante**: Usa un **API Token** (con permessi `Edit Zone DNS`) e NON una Global API Key.

```bash
kubectl apply -f cert-manager/cluster-Issuer.yaml
```

Verifica lo stato ("Ready" deve essere True):
```bash
kubectl get clusterissuer
```

### B. Richiedi il Certificato Wildcard
```bash
kubectl apply -f cert-manager/certificate-pindaroli.yaml
```

## 5. Verifica Finale

Monitora lo stato del certificato:
```bash
kubectl get certificates -A -w
```
Dovrebbe passare da `False` a `True` in pochi minuti.

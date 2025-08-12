# Configurazione Certificati SSL per Traefik nel Home Lab

## Situazione Attuale
- Traefik installato con Gateway API
- Certificati self-signed (`local-selfsigned-tls`)
- Dominio esterno: `pindaroli.org` (gestito da Cloudflare)
- Dominio locale: `.local`
- IngressRoute configurati per domini sia locali che esterni

## Strategia: Certificati Let's Encrypt con DNS Challenge

### Perché DNS Challenge?
1. **Funziona per domini interni**: Non serve che i servizi siano raggiungibili da internet
2. **Wildcard certificates**: Possiamo generare `*.pindaroli.org`
3. **Validazione automatica**: Cloudflare API permette validazione DNS automatica
4. **Sicurezza**: Nessuna esposizione di servizi interni verso internet

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

## Passo 2: Configurare Cloudflare API Token

### Creare API Token su Cloudflare:
1. Vai su Cloudflare Dashboard → My Profile → API Tokens
2. Crea nuovo token con permessi specifici:
   - **Zone:Zone:Read** per `pindaroli.org` - permette di leggere le informazioni della zona DNS
   - **Zone:DNS:Edit** per `pindaroli.org` - permette di creare/modificare/eliminare record DNS per la validazione ACME
   - **Template**: Usa "Custom token" per maggior controllo sui permessi
   - **Zone Resources**: Include solo `pindaroli.org` (specifico per il dominio)
   - **TTL**: Imposta una scadenza appropriata (es. 1 anno) per il token

### Creare il Secret Kubernetes per l'API Token:

Il token Cloudflare deve essere memorizzato come Secret Kubernetes per essere utilizzato da cert-manager.

#### Passaggi dettagliati:

1. **Crea il file**: Salva in `cloudflare-secret.yaml`
```yaml
apiVersion: v1
kind: Secret
metadata:
  name: cloudflare-api-token-secret
  namespace: cert-manager
type: Opaque
stringData:
  api-token: "il-tuo-token-cloudflare-qui"  # Sostituisci con il token reale
```

2. **Applica il Secret**:
```bash
kubectl apply -f cloudflare-secret.yaml
```

3. **Verifica creazione**:
```bash
# Controlla che esista
kubectl get secret cloudflare-api-token-secret -n cert-manager

# Verifica dettagli (senza mostrare il token)
kubectl describe secret cloudflare-api-token-secret -n cert-manager
```

4. **Cancella il file locale** (sicurezza):
```bash
rm cloudflare-secret.yaml
```

## Passo 3: Creare ClusterIssuer

Il ClusterIssuer configura cert-manager per usare Let's Encrypt con DNS01 challenge.

### Creare il file YAML:

Salva il seguente contenuto in `cluster-issuer.yaml`:

```yaml
apiVersion: cert-manager.io/v1
kind: ClusterIssuer
metadata:
  name: letsencrypt-cloudflare
spec:
  acme:
    server: https://acme-v02.api.letsencrypt.org/directory
    email: o.pindaro@gmail.com
    privateKeySecretRef:
      name: letsencrypt-cloudflare-private-key
    solvers:
    - dns01:
        cloudflare:
          email: o.pindaro@gmail.com
          apiTokenSecretRef:
            name: cloudflare-api-token-secret
            key: api-token
      selector:
        dnsZones:
        - "pindaroli.org"
```

### Applicare il ClusterIssuer:

```bash
kubectl apply -f cluster-issuer.yaml
```

### Verificare la creazione:

```bash
# Controlla che sia stato creato
kubectl get clusterissuer

# Verifica lo stato
kubectl describe clusterissuer letsencrypt-cloudflare
```

**Nota**: ClusterIssuer è una risorsa cluster-scoped (non richiede namespace) e può essere usata da Certificate in qualsiasi namespace.

## Passo 4: Creare Certificate per Wildcard

Certificate per `*.pindaroli.org` che copre tutti i sottodomini.

### Creare il file YAML:

Salva il seguente contenuto in `wildcard-certificate.yaml`:

```yaml
apiVersion: cert-manager.io/v1
kind: Certificate
metadata:
  name: pindaroli-wildcard-cert
  namespace: traefik
spec:
  secretName: pindaroli-wildcard-tls
  issuerRef:
    name: letsencrypt-cloudflare
    kind: ClusterIssuer
  dnsNames:
  - "*.pindaroli.org"
  - "pindaroli.org"
```

### Applicare il Certificate:

```bash
kubectl apply -f wildcard-certificate.yaml
```

### Verificare il certificato:

```bash
# Controlla lo stato del certificato
kubectl get certificate -n traefik

# Verifica i dettagli
kubectl describe certificate pindaroli-wildcard-cert -n traefik

# Controlla il secret TLS generato
kubectl get secret pindaroli-wildcard-tls -n traefik
```

**Nota**: Il processo di validazione DNS01 può richiedere alcuni minuti. cert-manager creerà automaticamente il record DNS su Cloudflare per la validazione.

## Passo 5: Aggiornare Traefik per usare i nuovi certificati

### Modifica traefik-values.yaml:
Nel file `traefik/traefik-values.yaml`, aggiorna la sezione gateway:

```yaml
gateway:
  listeners:
    web:
      port: 9080
      protocol: HTTP
      namespacePolicy: All

    websecure:
      port: 9443
      protocol: HTTPS
      namespacePolicy: All
      mode: Terminate
      certificateRefs:    
        - kind: Secret
          name: pindaroli-wildcard-tls  # Nuovo certificato
          group: ""
          namespace: traefik
```

## Passo 6: Aggiornare IngressRoute esistenti

### Esempio Jellyfin aggiornato:
```yaml
apiVersion: traefik.io/v1alpha1
kind: IngressRoute
metadata:
  name: jellyfin-external
  namespace: arr
spec:
  entryPoints:
    - websecure
  routes:
  - match: Host(`jellyfin.local`) || Host(`jellyfin.pindaroli.org`)
    kind: Rule
    services:
    - name: servarr-jellyfin
      port: 8096
  tls:
    secretName: pindaroli-wildcard-tls
```

### Altri servizi da aggiornare:
- `traefik/readarr-ingressroute.yaml`
- `traefik/qbittorrent-ingress-route.yaml`
- `traefik/radarr-ingressroute.yaml`

## Passo 7: Configurare DNS interno

### Configurazione DNS per accesso esterno:

Per accedere ai servizi con certificati Let's Encrypt validi, aggiungi al tuo router/DNS locale:
```
jellyfin.pindaroli.org → 192.168.1.3 (IP del LoadBalancer)
radarr.pindaroli.org → 192.168.1.3
sonarr.pindaroli.org → 192.168.1.3
```

### Nota importante:

- **Domini `.local`** (es. `jellyfin.local`): accesso interno rapido, certificati self-signed
- **Domini `.pindaroli.org`** (es. `jellyfin.pindaroli.org`): accesso con certificati Let's Encrypt validi

Entrambi i domini puntano allo stesso LoadBalancer (192.168.1.3), ma usano certificati diversi.

## Comandi di Deploy

### Sequenza completa:
```bash
# 1. Installa cert-manager
helm install cert-manager jetstack/cert-manager \
  --namespace cert-manager \
  --create-namespace \
  --version v1.13.3 \
  --set installCRDs=true

# 2. Applica secret API token
kubectl apply -f cloudflare-secret.yaml

# 3. Crea ClusterIssuer
kubectl apply -f cluster-issuer.yaml

# 4. Crea Certificate
kubectl apply -f wildcard-certificate.yaml

# 5. Aggiorna Traefik
helm upgrade traefik traefik/traefik -f traefik-values.yaml -n traefik

# 6. Aggiorna IngressRoute
kubectl apply -f traefik/jellyfin-ingressroute.yaml
```

## Verifica

### Controllo certificati:
```bash
# Stato dei certificati
kubectl get certificates -n traefik

# Dettagli certificato
kubectl describe certificate pindaroli-wildcard-cert -n traefik

# Verifica secret TLS
kubectl get secret pindaroli-wildcard-tls -n traefik
```

### Test browser:
- https://jellyfin.pindaroli.org (certificato valido)
- https://traefik-dash.pindaroli.org (certificato valido)

## Vantaggi della soluzione

1. **Certificati validi**: Browser riconosce certificati Let's Encrypt
2. **Rinnovo automatico**: cert-manager rinnova prima della scadenza
3. **Wildcard**: Un certificato per tutti i sottodomini
4. **Sicurezza**: Servizi interni non esposti su internet
5. **Flessibilità**: Facile aggiungere nuovi servizi

## Note importanti

- Certificati Let's Encrypt scadono ogni 90 giorni
- cert-manager li rinnova automaticamente dopo 60 giorni
- DNS01 challenge richiede API token Cloudflare valido
- Wildcard certificates richiedono DNS01 challenge (non HTTP01)
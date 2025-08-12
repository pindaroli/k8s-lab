# DNS Locale per Certificati Let's Encrypt con Domini Esterni

## Problema
Come far funzionare domini `*.pindaroli.org` con certificati Let's Encrypt validi per servizi interni, senza interferire con Cloudflare DNS.

## Soluzione: DNS Locale + Certificati Let's Encrypt

### Come funziona
1. **cert-manager** ottiene certificati Let's Encrypt tramite DNS01 challenge su Cloudflare
2. **DNS locale** risolve `*.pindaroli.org` verso l'IP interno del LoadBalancer
3. **Traffico interno** non esce mai dalla rete locale
4. **Certificati validi** perché Let's Encrypt ha validato il controllo del dominio

### Configurazione DNS Locale

#### Opzione 1: Router/DNS locale (CONSIGLIATA)
Nel router (proxmox.local), configurare:
```
jellyfin.pindaroli.org → 192.168.1.3
lidarr.pindaroli.org → 192.168.1.3  
prowlarr.pindaroli.org → 192.168.1.3
qbittorrent.pindaroli.org → 192.168.1.3
readarr.pindaroli.org → 192.168.1.3
sonarr.pindaroli.org → 192.168.1.3
traefik-dash.pindaroli.org → 192.168.1.3
```

#### Opzione 2: Wildcard DNS (se supportato dal router)
```
*.pindaroli.org → 192.168.1.3
```

#### Opzione 3: File /etc/hosts (su ogni client)
Su Mac/Linux aggiungere a `/etc/hosts`:
```
192.168.1.3 jellyfin.pindaroli.org
192.168.1.3 lidarr.pindaroli.org
192.168.1.3 prowlarr.pindaroli.org
192.168.1.3 qbittorrent.pindaroli.org
192.168.1.3 readarr.pindaroli.org
192.168.1.3 sonarr.pindaroli.org
192.168.1.3 traefik-dash.pindaroli.org
```

### Perché non interferisce con Cloudflare

#### Risoluzione DNS:
1. **Client interno** → DNS Router locale → `192.168.1.3` 
2. **Client esterno** → DNS Cloudflare → IP pubblico (se configurato)

#### Cloudflare mantiene:
- Solo record `_acme-challenge` temporanei per validazione Let's Encrypt
- Record A pubblici (opzionali) per accesso da internet

### Vantaggi della soluzione

✅ **Certificati validi**: Browser riconosce certificati Let's Encrypt  
✅ **Traffico locale**: Non esce dalla rete, velocità massima  
✅ **Zero conflitti**: DNS locale ha priorità per client interni  
✅ **Sicurezza**: Servizi non esposti automaticamente su internet  
✅ **Flessibilità**: Possibile aggiungere accesso esterno in seguito  

### Configurazione cluster

#### IngressRoute con TLS:
```yaml
apiVersion: traefik.io/v1alpha1
kind: IngressRoute
metadata:
  name: service-ingress-route
  namespace: arr
spec:
  entryPoints:
    - websecure
  routes:
    - match: Host(`service.pindaroli.org`)
      kind: Rule
      services:
        - name: service-name
          port: 8080
  tls:
    secretName: pindaroli-wildcard-tls
```

#### Certificate wildcard:
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

### Accesso da esterno (opzionale)

Per accesso da internet:
1. Aggiungere record A su Cloudflare: `service.pindaroli.org → IP_PUBBLICO`
2. Configurare port forwarding: `443 → 192.168.1.3:443`
3. Assicurarsi che il router DNS locale non abbia priorità per client esterni

### Note importanti

- **Questo è lo standard** per home lab con certificati validi
- **DNS locale ha sempre priorità** sui client interni
- **cert-manager rinnova automaticamente** i certificati ogni 60 giorni  
- **Wildcard certificate** copre tutti i sottodomini `*.pindaroli.org`
- **Validazione DNS01** non richiede esposizione dei servizi su internet
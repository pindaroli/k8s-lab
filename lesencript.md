# Esempi: Let's Encrypt + Cloudflare Zero Trust

---

## 1. Let's Encrypt con HAProxy su OPNsense

### a) Prerequisiti:
- Plugin `acme-client` installato su OPNsense
- Porta `80` **aperta temporaneamente** per validazione HTTP-01
- Record DNS `A` o `CNAME` valido su Cloudflare che punta all’IP di OPNsense

### b) Creazione certificato:
- Vai su: `Services > ACME Client > Account keys > [+]`
  - Inserisci nome e email
- Vai su: `Certificates > [+]`
  - **Common Name**: `dashboard.tuodominio.com`
  - **Challenge Type**: HTTP-01 (webroot)
  - **Action**: Issue or Renew

### c) Integrazione con HAProxy:
- Vai su: `Services > HAProxy > Settings`
- Abilita **SSL Offloading**
- Aggiungi il certificato ottenuto da ACME Client alla sezione certificati
- Collega il certificato al **Frontend HTTPS** di HAProxy

### d) Frontend HTTPS:
- Port: `443`
- SSL Offloading: ✅ abilitato
- Certificate: seleziona quello Let's Encrypt
- Default Backend: Ambassador o altro proxy interno

---

## 2. Cloudflare Zero Trust - Protezione hostname

### a) Vai su:  
https://one.cloudflare.com → **Access > Applications**

### b) Aggiungi nuova app:
- Tipo: **Self-hosted**
- Nome: `Kubernetes Dashboard`
- URL: `https://dashboard.tuodominio.com`

### c) Policy accesso:
- Include → Emails → `tua_email@dominio.com`
- Puoi usare anche **Google**, **GitHub**, SAML/SSO

### d) Risultato:
- Quando accedi a `dashboard.tuodominio.com`, viene richiesta autenticazione
- Solo chi autorizzi tu potrà accedere

---

## 3. Configurazione `cloudflared` con Zero Trust

**Esempio `config.yml`:**

```yaml
tunnel: k8s-tunnel
credentials-file: /root/.cloudflared/k8s-tunnel.json

ingress:
  - hostname: dashboard.tuodominio.com
    service: http://192.168.1.1:80
    originRequest:
      noTLSVerify: true
  - service: http_status:404
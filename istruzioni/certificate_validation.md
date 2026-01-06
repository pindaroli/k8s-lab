# Guida alla Verifica dei Certificati SSL

Questa guida spiega come verificare la validità dei certificati SSL per i servizi del cluster (es. `*.pindaroli.org`).

## 1. Verifica da Browser

Il metodo più immediato è visitare il sito.

1.  Apri il browser (Chrome/Safari/Firefox).
2.  Vai all'URL del servizio (es. `https://radarr.pindaroli.org`).
3.  Clicca sull'icona del **Lucchetto** (🔒) o "Non Sicuro" nella barra degli indirizzi.
4.  Seleziona **"La connessione è sicura"** -> **"Il certificato è valido"**.
5.  Controlla la data di **"Scadenza"** (Expires On).

## 2. Verifica da Riga di Comando (CLI)

Utile per debug rapido o automazione.

### Usando `curl`
Il comando più semplice per vedere se un certificato è accettato o scaduto.
```bash
curl -Iv https://radarr.pindaroli.org
```
*   Se valido: `HTTP/2 200` (o 302/401) e nessun errore SSL.
*   Se scaduto: `curl: (60) SSL certificate problem: certificate has expired`.

### Usando `openssl` (Dettagliato)
Per vedere le date esatte di inizio e fine validità.
```bash
echo | openssl s_client -servername radarr.pindaroli.org -connect radarr.pindaroli.org:443 2>/dev/null | openssl x509 -noout -dates
```
Output atteso:
```text
notBefore=Aug 12 08:07:23 2025 GMT
notAfter=Nov 10 08:07:22 2025 GMT  <-- CONTROLLA QUESTA DATA
```

## 3. Verifica stato in Kubernetes (Cert-Manager)

Se i certificati sono gestiti da cert-manager nel cluster:

### Controllare lo stato dei Certificati
```bash
kubectl get certificates -A
```
*   **READY**: Deve essere `True`.
*   **SECRET**: Il nome del secret dove è salvato il certificato.

### Controllare lo stato delle "CertificateRequest"
Se un certificato non si rinnova, controlla le richieste pendenti:
```bash
kubectl get certificaterequests -A
```

### Controllare i log di Cert-Manager
Per capire perché un rinnovo fallisce:
```bash
kubectl logs -l app=cert-manager -n cert-manager
```

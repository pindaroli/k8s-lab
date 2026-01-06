# Fix DNS: Problema "ndots" e Wildcard

Questo documento spiega e risolve un problema subdolo di rete Kubernetes quando si usa un dominio con **Wildcard DNS** (es. `*.pindaroli.org` su Cloudflare).

## Il Problema

1.  **Wildcard DNS**: Hai configurato `*.pindaroli.org` per puntare al tuo IP pubblico (o Ingress locale).
2.  **Kubernetes DNS**: Di default, K8s cerca di "completare" i nomi brevi. Se cerchi `google.com`, lui prova prima:
    *   `google.com.default.svc.cluster.local`
    *   `google.com.svc.cluster.local`
    *   `google.com.cluster.local`
    *   `google.com.pindaroli.org`  <-- **QUI IL PROBLEMA!**
    *   `google.com.` (Finale assoluto)

3.  **Il Corto Circuito**: Quando tenta `google.com.pindaroli.org`, il tuo Wildcard DNS su Cloudflare risponde "Sì, esisto! Sono io!" (perché `*` copre tutto).
4.  **Risultato**: Cert-Manager cerca di contattare Let's Encrypt, ma finisce per parlare col tuo stesso router/Ingress, che ovviametalosctl -n 10.10.20.141 rebootnte non sa cosa farsene. Errore: `Handbook Failure` o `409 Conflict`.

## La Soluzione: `ndots:1`

Diciamo a Cert-Manager: "Se il dominio ha almeno 1 punto (come `google.com` o `letsencrypt.org`), NON provare ad aggiungere suffissi. Risolvilo subito come assoluto."

Così salta direttamente al passaggio finale genuino ed evita la trappola del Wildcard.

## Comando di Fix

Esegui questi comandi per applicare la patch ai Pod di Cert-Manager:

```bash
# Patch Cert-Manager Controller
kubectl patch deployment cert-manager -n cert-manager --patch '{"spec": {"template": {"spec": {"dnsConfig": {"options": [{"name": "ndots", "value": "1"}]}}}}}'

# Patch CA Injector
kubectl patch deployment cert-manager-cainjector -n cert-manager --patch '{"spec": {"template": {"spec": {"dnsConfig": {"options": [{"name": "ndots", "value": "1"}]}}}}}'

# Patch Webhook
kubectl patch deployment cert-manager-webhook -n cert-manager --patch '{"spec": {"template": {"spec": {"dnsConfig": {"options": [{"name": "ndots", "value": "1"}]}}}}}'
```

Dopo qualche secondo, i Pod si riavvieranno con la nuova configurazione DNS.

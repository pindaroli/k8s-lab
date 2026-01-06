# Fix MTU su Talos (Manuale)

Segui questi passaggi per abbassare l'MTU a 1450 e risolvere i problemi di connessione (TLS Handshake).

## 1. Preparazione

Apri il terminale nella cartella `~/prj/k8s-lab`.

Carica la configurazione corretta:
```bash
export TALOSCONFIG=talos-config/talosconfig
```

Verifica di vedere i nodi:
```bash
talosctl config info
# Dovresti vedere i nodi 10.10.20.141, .142, .143
```

## 2. Modifica Interattiva

Esegui questo comando per il primo nodo (**Nota: si aprirà un editor di testo, usa :wq per salvare se è Vim**):

```bash
talosctl -n 10.10.20.141 edit machineconfig
```

### Cosa modificare

Cerca la sezione `network` -> `interfaces`.
Dovresti vedere qualcosa del genere:

```yaml
    network:
        interfaces:
            - interface: eth0
              dhcp: true
```

**Modificalo aggiungendo la riga `mtu: 1450` ALLINEATA con `dhcp` (stessa indentazione):**

```yaml
    network:
        interfaces:
            - interface: eth0
              mtu: 1450      <-- AGGIUNGI QUESTA RIGA
              dhcp: true
```

⚠️ **Attenzione agli spazi!** Usa lo stesso numero di spazi delle righe sopra/sotto. Non usare TAB.

Salva e chiudi l'editor.
Il nodo applicherà la configurazione. Se ti dà errori di sintassi YAML, riprova a modificare.

## 3. Ripeti per gli altri nodi

Fai la stessa cosa per il nodo 142 e 143:

```bash
talosctl -n 10.10.20.142 edit machineconfig
# ... modifica e salva ...

talosctl -n 10.10.20.143 edit machineconfig
# ... modifica e salva ...
```

## 4. Verifica

Dopo aver modificato il nodo **143** (dove gira Cert-Manager), verifica se i certificati si sbloccano:

```bash
kubectl get certificates -A -w
```
Dovresti vedere `READY: True` dopo qualche minuto.

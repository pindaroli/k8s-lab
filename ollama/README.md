# Monitoraggio Ollama tramite Kubernetes / VictoriaMetrics

Questo modulo permette al server VictoriaMetrics installato nel tuo cluster Kubernetes di "uscire" dalla rete del cluster e andare a leggere le metriche del server Ollama installato fisicamente sul Mac Studio.

## ⚠️ Prerequisito Fondamentale: Esposizione di Ollama sul Mac
Per impostazione predefinita, Ollama sul Mac risponde **solo a localhost (127.0.0.1)** per motivi di sicurezza, quindi Kubernetes non riuscirebbe a raggiungerlo.

Devi modificare il file `.plist` che abbiamo censito poco fa:
`/Users/olindo/Library/LaunchAgents/homebrew.mxcl.ollama.plist`

Nella sezione `EnvironmentVariables` (o aggiungendola se non c'è), devi assicurarti che Ollama ascolti su tutte le interfacce impostando `OLLAMA_HOST`:

```xml
<key>EnvironmentVariables</key>
<dict>
    <key>OLLAMA_HOST</key>
    <string>0.0.0.0:11434</string>
</dict>
```

Dopo aver salvato la modifica sul Mac Studio, riavvia il servizio:
```bash
brew services restart ollama
# Verifica che sia raggiungibile da browser o rete LAN:
# http://10.10.20.100:11434/metrics
```

---

## Architettura dei manifest Kubernetes (`ollama-metrics.yaml`)

Dato che Ollama non gira come Pod ma come server esterno hardware, in Kubernetes usiamo un trucco nativo:
1. **Endpoints**: Hardcodiamo l'indirizzo esatto del Mac Studio (`10.10.20.100`) su porta `11434`.
2. **Service Headless**: Creiamo un servizio standard che non ha selector (selettori per pod), ma si "aggancia" manualmente agli Endpoints fisici del punto 1.
3. **ServiceMonitor**: È lo standard operativo supportato nativamente dal tuo VictoriaMetrics / vmagent. Questo dice allo scraper di scansionare il Servizio ogni 15 secondi all'inidirizzo `/metrics`.

### Come applicare la configurazione nel cluster
Torna nella directory principale del tuo progetto laboratorio (`/Users/olindo/prj/k8s-lab`) e lancia:

```bash
export KUBECONFIG=talos-config/kubeconfig
kubectl apply -f ollama/ollama-metrics.yaml
```

Entro 1-2 minuti, aprendo Grafana, potrai aggiungere connessioni o cercare dashboard della community (es. dashboard ID `22036` o simili per Ollama) e vedrai le performance della GPU M2 Ultra!

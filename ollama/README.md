# Monitoraggio Ollama "Gold Standard" (Mac Studio M2 Ultra)

Questo modulo gestisce l'integrazione di Ollama (in esecuzione sul Mac Studio) con lo stack di monitoraggio VictoriaMetrics nel cluster Kubernetes.

## Architettura
Per ottenere un'osservabilità professionale su Apple Silicon, non interroghiamo direttamente Ollama (che non espone `/metrics` nativamente), ma utilizziamo un **Exporter Proxy** scritto in Go.

1. **Ollama**: Gira sul Mac (porta 11434) ottimizzato per la GPU Metal.
2. **Ollama-Metrics Exporter**: Agisce come proxy sulla porta **11435**. Intercetta le richieste di inferenza per calcolare Token al Secondo e monitora l'utilizzo reale della VRAM sul chip M2 Ultra.
3. **VictoriaMetrics**: Utilizza un `VMStaticScrape` per leggere i dati direttamente dal Mac Studio.

---

## Configurazione sul Mac Studio

### 1. LaunchAgents (Persistenza)
Il ciclo di vita dei servizi è gestito da `launchd` tramite i seguenti file in `~/Library/LaunchAgents/`:

- `homebrew.mxcl.ollama.plist`: Gestisce Ollama.
    - **Variabili chiave**: `OLLAMA_HOST=0.0.0.0`, `OLLAMA_NUM_GPU=1` (Metal), `OLLAMA_NUM_PARALLEL=4`, `OLLAMA_KEEP_ALIVE=-1` (modelli sempre in memoria).
- `org.norskhelsenett.ollama-metrics.plist`: Gestisce l'exporter.
    - **Variabili chiave**: `PORT=11435`, `OLLAMA_HOST=http://localhost:11434`.

### 2. Build dell'Exporter
L'exporter è compilato nativamente sul Mac per garantire le massime prestazioni:
```bash
cd /Users/olindo/prj/ollama-metrics
go build -o ollama-metrics main.go
```

---

## Integrazione Kubernetes

Abbiamo rimosso i vecchi Service/Endpoints manuali in favore di un approccio più moderno e pulito fornito dal VictoriaMetrics Operator.

### VMStaticScrape
Il file `monitoring/ollama-static-scrape.yaml` definisce il target esterno:
```yaml
spec:
  targetEndpoints:
    - targets: ["10.10.20.100:11435"]
      labels:
        instance: "mac-studio-m2"
        hardware: "apple-silicon"
```

---

## Visualizzazione (Grafana)

Per visualizzare i dati, importa la dashboard della community o quella inclusa nell'exporter:
- **Dashboard ID**: `25086` (Ollama LLM Inference)
- **Metriche Chiave**:
    - `ollama_tokens_per_second`: Velocità di generazione.
    - `ollama_model_ram_mb`: Occupazione memoria unificata GPU.
    - `ollama_prompt_tokens_total`: Volume di input.

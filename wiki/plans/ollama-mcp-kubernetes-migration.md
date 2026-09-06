---
title: "Piano: Migrazione Kubernetes di Ollama MCP Server"
type: plan
status: archived
certified_for_ai: false
created_at: 2026-09-06
completed_at: 2026-09-06
tags:
  - "#plan"
  - "#ollama"
  - "#mcp"
  - "#kubernetes"
  - "#toolhive"
  - "#helm"
---

# Piano: Migrazione Kubernetes di Ollama MCP Server (Pattern Monorepo)

Questo piano definisce i passaggi operativi per migrare il server MCP **`ollama`** dall'esecuzione come processo locale con `npx` su macOS (`ollama-mcp`) al cluster Kubernetes homelab nel namespace dedicato `mcp-system`.

Il piano adotta il pattern architetturale consolidato **Monorepo Homelab** (già collaudato per `truenas`, `opnsense`, `talos`, `gemini-deepsearch`, `kubernetes`):
1. **Containerizzazione Monorepo**: `docker/ollama-mcp/Dockerfile` con build automatica su GitHub Actions (`.github/workflows/docker-ollama-mcp.yml`) e pubblicazione su `ghcr.io/pindaroli/ollama-mcp:latest`.
2. **Orchestrazione & Bridging ToolHive**: deploy gestito tramite CRD `MCPServer` di **ToolHive Operator** che incapsula il container con `readOnlyRootFilesystem: true` e crea il proxy sidecar `stdio` $\leftrightarrow$ `HTTP/SSE` su porta `8080`.
3. **Gestione Dichiarativa Helm**: integrazione nella Project Chart **`helm-charts/mcp-gateway`** e foglio valori `mcp-gateway/mcp-gateway-values.yaml`.
4. **Networking & IngressRoute Traefik**: esposizione HTTPS su `https://ollama-mcp-internal.pindaroli.org/mcp` e comunicazione L2 ad alta velocità su VLAN 20 verso il Mac Studio (`10.10.20.100:11434`).
5. **DNS Split-Horizon**: Host Override su OPNsense Unbound DNS e censimento in `rete.json`.
6. **Client Disaccoppiato**: aggiornamento centralizzato di `~/.gemini/antigravity/mcp_config.json`.

---

## 🗺️ Mappe Concettuali e Relazioni
- [[MCP_Platform]] (Piattaforma Kuadrant & ToolHive Operator in `mcp-system`)
- [[Network_Registry]] (Topologia VLAN 20 Client e VIP Traefik `10.10.20.56`)
- [[Traefik]] (IngressRoute split-horizon per `ollama-mcp-internal.pindaroli.org`)
- [[OPNsense]] (Risoluzione DNS locale Unbound)
- [[SCHEMA]] (Regole del Wiki e Protocollo Test-Driven)

---

## 1. Architettura di Riferimento

```mermaid
flowchart TD
    subgraph MacStudio["Mac Studio M2 Ultra (10.10.20.100)"]
        OLLAMA["Demone Ollama (:11434)\nModelli: deepseek-r1:32b, etc.\n(Accelerazione Metal/GPU)"]
        AG["Client Antigravity\n(~/.gemini/antigravity/mcp_config.json)"]
    end

    subgraph GitHub["GitHub Cloud"]
        REPO["pindaroli/k8s-lab (Monorepo)"]
        GHA["GitHub Actions (docker-ollama-mcp.yml)"]
        GHCR["ghcr.io/pindaroli/ollama-mcp:latest"]
    end

    subgraph Cluster["Cluster K8s (mcp-system)"]
        TH["ToolHive Operator"]
        POD["Pod ollama-mcp-0 (Node.js stdio)"]
        PROXY["Service & Deployment mcp-ollama-mcp-proxy (:8080)"]
        ING["Traefik IngressRoute ollama-mcp-internal"]
        GW["Kuadrant MCP Gateway (mcp-broker-router)"]
    end

    subgraph Edge["DNS & Ingress"]
        DNS["OPNsense Unbound DNS (192.168.2.254)\nollama-mcp-internal.pindaroli.org -> 10.10.20.56"]
        VIP["Traefik LoadBalancer VIP (10.10.20.56)"]
    end

    REPO -->|Push su main| GHA -->|Build & Push| GHCR
    GHCR -->|Pull Image| POD
    TH -.->|CRD MCPServer| POD
    PROXY <-->|stdio bridge| POD
    POD -->|HTTP :11434 (L2 VLAN 20)| OLLAMA
    ING --> PROXY
    GW --> PROXY
    VIP --> ING
    DNS -.-> VIP
    AG -->|HTTPS /mcp| VIP
```

---

## 2. Fasi Operative

### Fase 1: Creazione Packaging Monorepo & CI/CD GitHub Actions
1. Creare la directory `docker/ollama-mcp/` contenente `Dockerfile`:
   - Base image: `node:22-alpine`.
   - Installazione pacchetto globale: `npm install -g ollama-mcp@2.1.0`.
   - Utente unprivileged: `USER node`.
   - Entrypoint: `["ollama-mcp"]`.
2. Creare il workflow GitHub Actions `.github/workflows/docker-ollama-mcp.yml`:
   - Trigger selettivo su `paths: ['docker/ollama-mcp/**', '.github/workflows/docker-ollama-mcp.yml']`.
   - Buildx `linux/amd64` e push automatico su `ghcr.io/pindaroli/ollama-mcp:latest` e `2.1.0`.
3. Commit e push su `main` di `k8s-lab`, e attesa completamento pipeline CI.

### Fase 2: Configurazione di Rete Demone Ollama su Mac Studio (VLAN 20)
1. Verificare o configurare l'ascolto di Ollama su tutte le interfacce (`0.0.0.0:11434` o `10.10.20.100:11434`):
   ```bash
   launchctl setenv OLLAMA_HOST "0.0.0.0:11434"
   ```
2. Riavviare l'applicazione Ollama su Mac Studio.
3. Test-Driven: validare la raggiungibilità dell'endpoint dall'IP locale di rete (`curl -s http://10.10.20.100:11434/api/tags`).

### Fase 3: Integrazione Helm Project Chart (`mcp-gateway`)
1. Incrementare la versione in `helm-charts/mcp-gateway/Chart.yaml` (`0.2.7` → `0.2.8`).
2. Aggiungere il server `ollama` nel catalogo `servers` in `mcp-gateway/mcp-gateway-values.yaml`:
   ```yaml
   - name: ollama
     url: "http://mcp-ollama-mcp-proxy.mcp-system.svc.cluster.local:8080/mcp"
     hostname: "mcp-ollama-mcp-proxy.mcp-system.svc.cluster.local"
     enabled: true
     prefix: "ollama_"
     ingress:
       enabled: true
       host: "ollama-mcp-internal.pindaroli.org"
       port: 8080
     toolhive:
       enabled: true
       name: ollama-mcp
       image: ghcr.io/pindaroli/ollama-mcp:latest
       transport: stdio
       proxyPort: 8080
       env:
         - name: OLLAMA_HOST
           value: "http://10.10.20.100:11434"
       resources:
         limits:
           cpu: "300m"
           memory: "256Mi"
         requests:
           cpu: "50m"
           memory: "64Mi"
   ```
3. Eseguire il deploy della chart aggiornata:
   ```bash
   helm upgrade --install mcp-gateway helm-charts/mcp-gateway -f mcp-gateway/mcp-gateway-values.yaml -n mcp-system
   ```
4. Test-Driven: verificare lo stato dei pod `ollama-mcp-0` e del proxy `mcp-ollama-mcp-proxy`.

### Fase 4: Networking & DNS Split-Horizon
1. Censire l'alias `ollama-mcp-internal` per il VIP Traefik `10.10.20.56` in `rete.json`.
2. Validare la coerenza di rete:
   ```bash
   python3 scripts/network/validate_network.py
   ```
3. Registrare l'Host Override in OPNsense Unbound DNS:
   - Hostname: `ollama-mcp-internal`
   - Domain: `pindaroli.org`
   - IP: `10.10.20.56`
4. Test-Driven: verificare la risoluzione DNS (`dig +short ollama-mcp-internal.pindaroli.org @192.168.2.254`).

### Fase 5: Migrazione Configurazione Client Antigravity
1. Aggiornare `~/.gemini/antigravity/mcp_config.json`:
   ```json
   "ollama": {
     "serverUrl": "https://ollama-mcp-internal.pindaroli.org/mcp"
   }
   ```
2. Rimuovere l'invocazione locale `npx -y ollama-mcp`.

### Fase 6: Validazione Test-Driven End-to-End & Consolidamento Wiki
1. Test handshake JSON-RPC (`tools/list`) verso Traefik.
2. Esecuzione del tool `ollama_list` da Antigravity verificando la restituzione dei modelli reali residenti su Mac Studio.
3. Aggiornare la tabella server in `wiki/entities/MCP_Platform.md`.
4. Sincronizzare i task completati in `todo.md` e archiviare il piano.
5. Rigenerare il contesto wiki:
   ```bash
   python3 scripts/wiki/build_wiki_context.py
   ```

---

## 3. Verification Plan

### Test Automatizzati
- `helm lint helm-charts/mcp-gateway`
- `python3 scripts/network/validate_network.py`
- `python3 scripts/wiki/build_wiki_context.py`

### Test Manuali
- `kubectl get pods -n mcp-system -l toolhive-name=ollama-mcp`
- `kubectl get ingressroute ollama-mcp-internal -n mcp-system`
- `curl -k -s -X POST https://ollama-mcp-internal.pindaroli.org/mcp -H "Content-Type: application/json" -d '{"jsonrpc":"2.0","method":"tools/list","id":1}'`
- Invocazione tool `ollama_list` da client.

---

## 💾 Stato di Ripristino (AI Save-State)
- **Fase Attiva**: Completato (Tutte le Fasi 1-6 completate con successo).
- **Ultima Azione Completata**: Migrazione a `ollama-mcp` cluster-native completata al 100%. Immagine compilata con CI/CD su GHCR, StatefulSet `ollama-mcp-0` e proxy runner attivi in `mcp-system`, Traefik IngressRoute e DNS Unbound operativi su `10.10.20.56`, client Antigravity aggiornato su `serverUrl` e test funzionale `ollama_list` eseguito con successo.
- **Prossimo Passo Operativo**: Nessuno (Workload MCP Ollama pienamente operativo in produzione su K8s).
- **Blocchi/Decisioni Pendenti**: Nessuno.

# 🏗️ Piano di Massima: Architettura MCP Hub su Kubernetes (Homelab)

Questo documento riassume le decisioni architetturali, i componenti e il piano di implementazione per consolidare e scalare i server **MCP (Model Context Protocol)** all'interno del cluster Kubernetes (Talos Homelab).

---

## 🎯 Obiettivi Architetturali

1. **Zero Spreco di Risorse**: Consolidare decine di strumenti e script sparsi in un'infrastruttura unificata, evitando la moltiplicazione di runtime/pod isolati.
2. **Accesso Diretto e Sicuro al Lab**: Connessione nativa ai servizi interni (`TrueNAS`, `OPNsense`, `qBittorrent`, `Prowlarr`, `Talos`) tramite DNS di cluster (`*.svc.cluster.local`), senza dipendere da VPN attive sul Mac.
3. **Architettura 100% Stateless**: Scalabilità orizzontale priva di vincoli di *Sticky Sessions*, con tolleranza ai riavvii e rolling updates a zero downtime.
4. **Interoperabilità Multi-Client**: Unico punto di accesso HTTPS/SSE per **Antigravity**, **Hermes Agent**, **Claude Desktop** e bot di automazione (Telegram/Discord).
5. **Topologia di Rete Semplificata**: Routing diretto Layer 4 (**MetalLB**) e Layer 7 (**Traefik**) direttamente alle porte dei container (senza proxy sidecar intermedi).

---

## 🏛️ Schema Architetturale Complessivo

```mermaid
graph TD
    subgraph CLIENTS ["💻 Client AI & Orchestratori"]
        CLI1["Antigravity (Mac IDE)"]
        CLI2["Hermes Agent (K8s Daemon)"]
        CLI3["Bot Telegram / Automazioni"]
    end

    subgraph NET_LAYER ["🌐 Ingress & Load Balancer Layer"]
        METALLB["MetalLB (Layer 4 VIP)"]
        TRAEFIK["Traefik (Layer 7 Ingress)<br/>• mcp.pindaroli.org (TLS Let's Encrypt)<br/>• SSE Streaming / Buffering OFF<br/>• Path-based Routing verso le porte"]
        METALLB --> TRAEFIK
    end

    CLIENTS -->|"HTTPS / SSE (Bearer Token)"| METALLB

    subgraph POD_REPLICAS ["☸️ Kubernetes Deployment (HPA: 1..N Repliche)"]
        subgraph POD1 ["Pod Replica 1 (Modello B: 2 Container)"]
            PY1["Runtime Python (FastMCP) :8001<br/>• arrstack (qBit, Prowlarr, Radarr)<br/>• Infra (TrueNAS, OPNsense, Talos)"]
            NODE1["Runtime Node.js :8002<br/>• Scrapers (Subito, Vinted, Wallapop)"]
        end

        subgraph POD2 ["Pod Replica 2 (Modello B: 2 Container)"]
            PY2["Runtime Python :8001"]
            NODE2["Runtime Node.js :8002"]
        end
    end

    TRAEFIK -->|Path /lab/*| PY1
    TRAEFIK -->|Path /scrapers/*| NODE1
    TRAEFIK -->|Path /lab/*| PY2
    TRAEFIK -->|Path /scrapers/*| NODE2

    subgraph BACKPLANE ["💾 State & Message Backplane"]
        REDIS[("Redis / Valkey Cluster<br/>Pub/Sub per Sessioni SSE Stateless")]
    end

    PY1 <-->|"Pub/Sub Eventi Sessione"| REDIS
    NODE1 <-->|"Pub/Sub Eventi Sessione"| REDIS
    PY2 <-->|"Pub/Sub Eventi Sessione"| REDIS
    NODE2 <-->|"Pub/Sub Eventi Sessione"| REDIS

    subgraph LAB_INFRA ["⚙️ Servizi Homelab (Rete Interna)"]
        PY1 & PY2 -->|"CoreDNS locale"| MEDIA["qBittorrent / Prowlarr / Radarr"]
        PY1 & PY2 -->|"API REST / gRPC"| INFRA["TrueNAS / OPNsense / Talos"]
        NODE1 & NODE2 -->|"Ollama API"| OLLAMA["Qwen2.5-VL (Vision OCR)"]
    end
```

---

## 🧱 Dettaglio dei Componenti

### 1. Il Pod Multi-Container (Modello B Semplificato)
Ogni replica del Pod racchiude **soltanto i 2 container applicativi**, eliminando qualsiasi proxy intermedio:

| Container | Runtime | Ruolo / Servizi Integrati | Porta | RAM Tipica |
| :--- | :--- | :--- | :---: | :---: |
| **`mcp-python`** | Python 3.12 (FastMCP) | `arrstack-mcp` (qBit, Prowlarr, Radarr, Lidarr), `truenas-mcp`, `opnsense-mcp`, `talos-mcp` | `:8001` | ~50 MB |
| **`mcp-node`** | Node.js 22 LTS | `subito-scraper`, `vinted-scraper`, `wallapop-scraper` | `:8002` | ~60 MB |

> **Consumo Totale per Pod**: **~110 MB di RAM** a riposo per gestire l'intero catalogo di oltre 60 tool MCP.

---

### 2. Ingress & Routing con Traefik
Traefik riceve il traffico dall'IP statico di MetalLB e lo smista direttamente alla porta specifica del container in base al path:

```yaml
apiVersion: traefik.io/v1alpha1
kind: IngressRoute
metadata:
  name: homelab-mcp-ingress
  namespace: mcp-system
spec:
  entryPoints:
    - websecure
  routes:
    # 1. Rotta per i Servizi Lab (Python FastMCP)
    - match: Host(`mcp.pindaroli.org`) && PathPrefix(`/lab`)
      kind: Rule
      services:
        - name: homelab-mcp-service
          port: 8001

    # 2. Rotta per gli Scrapers (Node.js)
    - match: Host(`mcp.pindaroli.org`) && PathPrefix(`/scrapers`)
      kind: Rule
      services:
        - name: homelab-mcp-service
          port: 8002
  tls:
    secretName: mcp-tls-cert
```

---

### 3. Scaling Orizzontale Stateless con Redis / Valkey

Nel protocollo MCP su SSE, un client apre `GET /sse` (ricevendo un `sessionId`) e poi invia comandi via `POST /message?sessionId=...`.

```mermaid
sequenceDiagram
    autonumber
    actor Client as Client AI (Antigravity / Hermes)
    participant Traefik as Traefik Ingress
    participant Pod1 as Pod Replica 1
    participant Pod2 as Pod Replica 2
    participant Redis as Redis / Valkey Pub-Sub

    Client->>Traefik: GET /lab/sse
    Traefik->>Pod1: Inoltra GET /lab/sse (:8001)
    Pod1-->>Client: Stream SSE aperto (sessionId: "sess-999")
    Pod1->>Redis: SUBSCRIBE "mcp:sess-999"

    Note over Client,Traefik: Il client lancia un comando (Round-Robin sceglie Pod 2)
    Client->>Traefik: POST /lab/message?sessionId=sess-999 (tool: qbt_add)
    Traefik->>Pod2: Inoltra POST /lab/message (:8001)
    Pod2->>Pod2: Esegue il comando qbt_add
    Pod2->>Redis: PUBLISH "mcp:sess-999" (risultato tool)
    Redis-->>Pod1: Notifica evento Pub/Sub
    Pod1-->>Client: Invio evento nello stream SSE aperto
```

#### Vantaggi del Backplane Redis:
1. **Completamente Stateless**: I Pod possono essere riavviati, scalati o sostituiti da Kubernetes senza far cadere le sessioni.
2. **Zero Sticky Cookies**: Massima distribuzione del carico tra tutti i nodi worker del cluster Talos.

---

### 4. Criteri e Policy di Autoscaling (HPA)

Poiché i server MCP consumano quasi 0% CPU a riposo e hanno picchi improvvisi (*burst*) durante le ricerche o le ispezioni OCR, la policy di scalatura adotta:

- **Target CPU al 50%**: Aggiunge immediatamente un pod quando scatta un'elaborazione pesante.
- **Finestra di Raffreddamento di 300s**: Evita lo spegnimento prematuro dei pod tra un comando e l'altro.
- **Minimo 1 Replica / Massimo 5 Repliche**.

```yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: homelab-mcp-hpa
  namespace: mcp-system
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: homelab-mcp-hub
  minReplicas: 1
  maxReplicas: 5
  metrics:
    - type: Resource
      resource:
        name: cpu
        target:
          type: Utilization
          averageUtilization: 50
  behavior:
    scaleDown:
      stabilizationWindowSeconds: 300
      policies:
        - type: Percent
          value: 100
          periodSeconds: 60
```

---

## 🗺️ Piano di Esecuzione Passo-Passo

| Fase | Attività | Output / Verifica |
| :--- | :--- | :--- |
| **Fase 1** | **Containerizzazione dei Moduli**<br/>• Creazione Dockerfile unificato Python (`arrstack` + infra)<br/>• Creazione Dockerfile Node.js (`scrapers` con supporto AI Inspector) | Immagini Docker buildate e pubblicate sul container registry locale / GitHub (GHCR). |
| **Fase 2** | **Setup Redis / Valkey**<br/>• Deploy istanza Redis leggera nel namespace `mcp-system` | Endpoint `redis.mcp-system.svc.cluster.local:6379` attivo. |
| **Fase 3** | **Deploy Multi-Container Pod (Modello B)**<br/>• Creazione Deployment con i 2 container (Python :8001, Node :8002)<br/>• Configurazione Secrets per credenziali Lab | Pod attivo e running con ~110 MB RAM. |
| **Fase 4** | **Configurazione Ingress Traefik**<br/>• Creazione `IngressRoute` con certificato TLS e buffering disattivato | Endpoint `https://mcp.pindaroli.org/lab/sse` e `/scrapers/sse` raggiungibili. |
| **Fase 5** | **Abilitazione HPA & Test di Carico**<br/>• Attivazione HorizontalPodAutoscaler con target CPU 50%<br/>• Verifica scaling con chiamate simultanee | Scaling orizzontale verificato da 1 a $N$ repliche senza errori 404. |
| **Fase 6** | **Collegamento Client AI**<br/>• Aggiornamento `mcp_config.json` di Antigravity ed Hermes Agent con l'URL remoto | Tutti i client usano l'MCP Hub remoto in modo trasparente. |

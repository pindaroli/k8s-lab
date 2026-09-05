---
title: "MCP Platform (Model Context Protocol Hub & Inspector)"
last_updated: "2026-09-04"
confidence: "High"
tags:
  - "#mcp"
  - "#ai"
  - "#infrastructure"
  - "#helm"
provenance:
  - "helm-charts/mcp-gateway/"
  - "mcp-gateway/mcp-gateway-values.yaml"
  - "mcp-servers/"
---

# Piattaforma MCP (Model Context Protocol)

## 🎯 Visione & Obiettivo Architetturale (MCP-as-a-Service)

L'obiettivo fondamentale dell'infrastruttura MCP nel cluster homelab GEMINI (`k8s-lab`) è:
1. **Centralizzazione su Kubernetes (Provider)**: Installare, containerizzare e orchestrare tutti i Server MCP all'interno del cluster (`mcp-system`), consentendo loro l'accesso diretto e privilegiato allo storage TrueNAS (NFS), alle reti VLAN interne e ai segreti di sistema protetti da SOPS.
2. **Accessibilità Agnostica per i Client (Consumer)**: Esporre i server tramite endpoint remoti standard (HTTP/SSE e Kuadrant Gateway) in modo che QUALSIASI **MCP Client** — come **Antigravity** su macOS, **Hermes Agent** nel cluster, flussi **n8n** o bot Telegram — possa invocare i tool via rete, eliminando la necessità di eseguire runtime locali (Python/Node), duplicare credenziali o montare share sui singoli computer degli sviluppatori.
3. **Ruolo di MCP Inspector**: Inspector è declassato a utility opzionale di debug manuale per sviluppatori (disabilitato di default tramite `inspector.enabled: false`) e non fa parte del percorso dati dei client AI operativi.

---

## 1. Architettura e Topologia

L'architettura risiede nel namespace dedicato `mcp-system` ed è articolata in 4 componenti cooperanti:

```mermaid
flowchart TD
    subgraph Client["Client AI"]
        AG["Antigravity (Mac)"]
        HA["Hermes Agent (K8s)"]
        N8N["n8n Automation"]
        USER["Browser Utente (Web UI)"]
    end

    subgraph Edge["Traefik Edge & Gateway API"]
        TR_EXT["mcp-ui.pindaroli.org (OAuth2 Google)"]
        TR_INT["mcp-ui-internal.pindaroli.org (LAN)"]
        GW_INT["mcp-internal.pindaroli.org (/mcp)"]
    end

    subgraph Core["Piattaforma mcp-system"]
        INSP["MCP Inspector (ghcr.io/modelcontextprotocol/inspector:latest)"]
        ROUTER["Kuadrant MCP Gateway (ghcr.io/kuadrant/mcp-gateway:v0.9.0)"]
        TH["ToolHive Operator (Stacklok)"]
        GH["github-mcp-proxy (MCPServer)"]
        TN["truenas-mcp-proxy (MCPServer)"]
        OPN["opnsense-mcp-proxy (MCPServer)"]
    end

    subgraph Storage["TrueNAS SCALE (10.10.10.50)"]
        NFS_MED["/mnt/oliraid/arrdata/media -> /mnt/media"]
        NFS_CLA["/mnt/oliraid/arrdata/classical -> /mnt/classical"]
        API_TN["TrueNAS REST API v2.0 (Port 443)"]
    end

    subgraph Firewall["OPNsense (192.168.100.1)"]
        API_OPN["OPNsense REST API (Port 443)"]
    end

    USER --> TR_EXT & TR_INT --> INSP
    AG & HA & N8N --> GW_INT --> ROUTER
    ROUTER --> GH & TN & OPN
    TH -.->|Gestione Lifecycle| GH & TN & OPN
    TN -->|API Calls| API_TN
    OPN -->|REST API| API_OPN
    Storage -->|NFS Mount| INSP
```

1. **Kuadrant MCP Gateway (`mcp-broker-router`)**:
   - Router e federatore centrale per tutti i server MCP del lab.
   - Esposto internamente su `mcp-internal.pindaroli.org` tramite HTTPRoute su Gateway Traefik.
   - Firma le sessioni con token JWT (`mcp-gateway-signing-key`).
2. **Stacklok ToolHive Operator**:
   - Gestore del ciclo di vita dei micro-server MCP tramite CRD `MCPServer` (`toolhive.stacklok.dev/v1beta1`).
   - Isola ciascun server in pod dedicati ed esegue il bridging `stdio` -> `HTTP/SSE`.
3. **MCP Inspector (Web UI & File Access)**:
   - Portale di collaudo e test interattivo per strumenti e prompt.
   - Protezione anti-DNS rebinding con `ALLOWED_ORIGINS`.
   - Accesso al file system ZFS di TrueNAS tramite mount NFS diretti su `/mnt/media` e `/mnt/classical`.
4. **Traefik IngressRoute**:
   - Routing split-horizon: accesso esterno su `mcp-ui.pindaroli.org` protetto da Google OAuth2, e accesso LAN diretto su `mcp-ui-internal.pindaroli.org`.

---

## 2. Politica "Chart di Progetto" (Project Chart)

Ai sensi della regola aurea [[GEMINI#3. Security & Operational Policies (The Golden Rules)|HELM DEPLOYMENT & PROJECT CHARTS]]:
- **Motivazione dell'incompatibilità upstream**: La chart ufficiale Kuadrant (`oci://ghcr.io/kuadrant/charts/mcp-gateway`) impone la presenza della Service Mesh Istio/Envoy e una dozzina di controller/CRD enterprise non presenti nel cluster.
- **Implementazione**: Viene mantenuta la Chart di Progetto `helm-charts/mcp-gateway/` (versione semantica `0.2.6`) che aggrega sia il Broker Kuadrant, sia i server federati gestiti da ToolHive (GitHub, TrueNAS, OPNsense, Talos, Gemini DeepSearch), sia l'Inspector Web UI.
- **Pattern di Sicurezza & Segreti**: Tutti i carichi di lavoro ToolHive adottano lo standard architetturale [[mcp-secret-projection-pattern]] (Archetipo 1 per credenziali scalari in RAM, Archetipo 2 per certificati mTLS e configurazioni proiettate come volumi di sola lettura dal Kubelet con filesystem immutabile).
- **Configurazione Centralizzata**: L'intero deployment di produzione è governato dichiarativamente dal file [mcp-gateway/mcp-gateway-values.yaml](file:///Users/olindo/prj/k8s-lab/mcp-gateway/mcp-gateway-values.yaml).

---

## 3. Storage e Volumi NFS

L'Inspector monta direttamente le condivisioni NFS di primo livello da TrueNAS (`10.10.10.50`):
* `nfs-media`: `/mnt/oliraid/arrdata/media` montato su `/mnt/media`.
* `nfs-classical`: `/mnt/oliraid/arrdata/classical` montato su `/mnt/classical`.

I dataset rispettano lo schema NFS standard del lab: `chmod 777`, ownership `olindo:k8s`, export con `maproot_user="root"` e `maproot_group="wheel"`.

---

## 4. Catalogo dei Server MCP Attivi in Kubernetes (`mcp-system`)

| Server | Immagine Container | Modalità ToolHive | Endpoint Traefik IngressRoute | Target Rete Lab |
| :--- | :--- | :--- | :--- | :--- |
| **`github-mcp`** | `ghcr.io/github/github-mcp-server` | stdio -> proxy :8080 | `https://github-mcp-internal.pindaroli.org/mcp` | GitHub API Cloud |
| **`truenas-mcp`** | `ghcr.io/pindaroli/truenas-master-mcp:latest` | stdio -> proxy :8080 | `https://truenas-mcp-internal.pindaroli.org/mcp` | TrueNAS SCALE API (`10.10.10.50:443`) |
| **`opnsense-mcp`** | `ghcr.io/pindaroli/opnsense-mcp:latest` | stdio -> proxy :8080 | `https://opnsense-mcp-internal.pindaroli.org/mcp` | OPNsense Firewall API (`192.168.100.1:443`) |
| **`talos-mcp`** | `ghcr.io/pindaroli/talos-mcp:latest` | stdio -> proxy :8080 | `https://talos-mcp-internal.pindaroli.org/mcp` | Talos Control Plane API (`10.10.20.141/142/143:50000`) |
| **`gemini-deepsearch-mcp`** | `ghcr.io/pindaroli/gemini-deepsearch-mcp:latest` | stdio -> proxy :8080 | `https://deepsearch-mcp-internal.pindaroli.org/mcp` | Google Gemini API (Web Search Grounding) |



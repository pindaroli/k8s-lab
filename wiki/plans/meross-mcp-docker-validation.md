---
title: "Piano: Test Locale, Pipeline CI/CD GHCR, Docker TrueNAS & Widget Homepage Meross MCP"
type: plan
status: active
certified_for_ai: true
created_at: 2026-10-11
last_updated: 2026-10-15
tags:
  - "#plan"
  - "#meross"
  - "#mcp"
  - "#docker"
  - "#truenas"
  - "#ghcr"
  - "#cicd"
  - "#homepage"
  - "#iot"
  - "#power-monitoring"
---

# Piano: Test Locale, Pipeline CI/CD GHCR, Docker TrueNAS & Widget Homepage Meross MCP

Questo documento definisce il piano operativo per:
1. Il collaudo funzionale del server **Meross Dual Gateway** (`pindaroli/meross-mcp`) con le credenziali reali.
2. L'implementazione della pipeline CI/CD GitHub Actions per la build e pubblicazione automatica delle immagini container OCI su **GitHub Container Registry (GHCR)** con **versionamento semantico formale** (`ghcr.io/pindaroli/meross-mcp:0.1.0`).
3. L'integrazione dichiarativa del servizio nello stack Docker permanente di TrueNAS SCALE bare-metal (`10.10.20.50`), con **divieto assoluto del tag `:latest`** e adozione esclusiva dell'ultima versione semantica rilasciata.
4. La configurazione centralizzata come server MCP in Antigravity (Streamable HTTP unificato su porta `8112`) e l'integrazione del widget di monitoraggio energetico (Watt, Volt, Ampere) sulla dashboard Homepage.

---

## 🗺️ Mappe Concettuali e Relazioni
- [[meross-mcp-server-project]] (Piano originario di scaffolding e sviluppo della libreria, FastAPI REST e FastMCP)
- [[mcp-upstream-tracking-pattern]] / [[mcp-registry-package-pattern]] (Standard architetturale build OCI CI/CD, immutabilità e divieto di `:latest`)
- [[mcp-secret-projection-pattern]] (Proiezione sicura delle credenziali `MEROSS_*` nello stack TrueNAS)
- [[MCP_Platform]] (Architettura e registro dei server MCP attivi 24/7 su TrueNAS Docker)
- [[Homepage]] (Dashboard centrale del lab con supporto widget `customapi` e rollout dichiarativo)
- [[SCHEMA]] (Regole di governance e save-state del Wiki)

---

## 1. Architettura dell'Integrazione & Policy di Versionamento

> [!CRITICAL]
> **MANDATO VERSIONAMENTO SEMANTICO (DIVIETO ASSOLUTO DI `:latest`)**:
> In conformità con le policy architetturali del lab, è **tassativamente proibito** utilizzare il tag generico `:latest` o build locali prive di versione nella configurazione dello stack Docker di TrueNAS.
> Il servizio Docker di TrueNAS DEVE referenziare sempre e solo **l'ultima versione semantica formale pubblicata su GHCR** (es. `image: ghcr.io/pindaroli/meross-mcp:0.1.0`). Ogni aggiornamento applicativo richiede il bump semantico su Git, la build CI/CD su GHCR e l'aggiornamento dichiarativo del tag nel `docker-compose.yaml`.

```mermaid
flowchart TD
    subgraph Dev["Sviluppo & Repository Git (pindaroli/meross-mcp)"]
        CODE["Codice Sorgente Python (FastAPI + FastMCP)"]
        TAG["Git Tag Semantico (es. v0.1.0)"]
    end

    subgraph CICD["GitHub Actions CI/CD"]
        WORKFLOW["Workflow: docker-publish.yml\nTrigger: push tag v* / manual dispatch"]
        BUILD["Build Multi-Arch (linux/amd64)\nHardened Dockerfile (appuser UID 1000)"]
        PUSH["Push GHCR: ghcr.io/pindaroli/meross-mcp:0.1.0"]
    end

    subgraph TrueNAS["TrueNAS SCALE Bare-Metal (10.10.20.50)"]
        subgraph DockerStack["Stack Docker MCP (/mnt/stripe/truenas-docker/mcp/)"]
            COMPOSE["docker-compose.yaml\nimage: ghcr.io/pindaroli/meross-mcp:0.1.0 (NO :latest)\nPorta Host: 8112:8112"]
            CONTAINER["Container mcp-meross\n(FastAPI + FastMCP Dual Gateway)"]
            ENV_FILE[".env protetto (SOPS)\nMEROSS_EMAIL & MEROSS_PASSWORD"]
        end
    end

    subgraph Clients["Client & Consumatori"]
        AG["Google Antigravity (AI Agent)\nserverUrl: http://10.10.20.50:8112/mcp"]
        HP_K8S["Homepage (K8s: home.pindaroli.org)"]
        HP_TN["Homepage (TrueNAS: :3000)"]
    end

    CODE --> TAG --> WORKFLOW --> BUILD --> PUSH
    PUSH -->|Pull Versione Semantica| COMPOSE --> CONTAINER
    ENV_FILE --> CONTAINER
    AG -->|Streamable HTTP POST /mcp| CONTAINER
    HP_K8S & HP_TN -->|GET /api/v1/devices/{id}/power| CONTAINER
```

---

## 2. Fasi Operative del Piano

### Fase 1: Test Server Meross in Locale & Validazione Credenziali
- **Obiettivo**: Verificare il funzionamento del runtime e della libreria con credenziali reali prima di procedere al rilascio.
- **Azioni**:
  1. Configurazione delle credenziali `MEROSS_EMAIL` e `MEROSS_PASSWORD` nel file `.env` in `/Users/olindo/prj/meross-mcp/`.
  2. Test di autenticazione REST iniziale su `https://iotx-eu.meross.com`.
  3. Stabilimento del client asincrono e polling MQTT over TLS verso il broker Meross.
  4. Esecuzione del Dual Gateway in locale (`python -m meross_mcp.app --transport http --port 8112`).
  5. Test funzionale dei tool MCP (`meross_list_devices`, `meross_get_device_state`, telemetria energetica) con le prese fisiche MSS310 censite nel lab.
- **Verifica Test-Driven**: Esecuzione smoke test CLI e chiamata `curl -s http://127.0.0.1:8112/api/v1/devices` con esito 200 OK e lista dispositivi popolata.

### Fase 2: Implementazione Pipeline CI/CD GitHub Actions & Release OCI `v0.1.0`
- **Obiettivo**: Automatizzare la produzione e pubblicazione dell'immagine Docker ufficiale su GHCR con tag semantico.
- **Azioni**:
  1. Creazione del workflow `.github/workflows/docker.yml` nel repository `pindaroli/meross-mcp`:
     - Trigger: push di tag `v*` e `workflow_dispatch` manuale.
     - Login a GHCR (`ghcr.io`) tramite token GitHub.
     - Build OCI AMD64 basata sul `Dockerfile` di produzione (utente unprivileged `appuser` UID 1000).
     - Tagging e push: `ghcr.io/pindaroli/meross-mcp:<versione>` (es. `0.1.0`).
  2. Commit e push delle modifiche sul repository GitHub.
  3. Creazione e push del tag git `v0.1.0`.
  4. Monitoraggio del workflow GitHub Actions fino a completamento positivo.
- **Verifica Test-Driven**: Ispezione su GHCR (`ghcr.io/pindaroli/meross-mcp:0.1.0`) e test di pull dell'immagine pubblicata.

### Fase 3: Configurazione Dichiarativa TrueNAS Docker (Pinning Semantico)
- **Obiettivo**: Integrare il container nello stack Docker di TrueNAS referenziando la versione semantica ufficiale, vietando `:latest`.
- **Azioni**:
  1. Aggiornamento dichiarativo di `docker/mcp/docker-compose.yaml`:
     ```yaml
     meross-mcp:
       container_name: mcp-meross
       image: ghcr.io/pindaroli/meross-mcp:0.1.0  # Tassativo: versione semantica esplicita (NO :latest)
       restart: unless-stopped
       env_file: .env
       ports:
         - "8112:8112"
       healthcheck:
         test: ["CMD", "python", "-c", "import urllib.request; urllib.request.urlopen('http://localhost:8112/healthz')"]
         interval: 30s
         timeout: 5s
         retries: 3
         start_period: 10s
     ```
  2. Configurazione sicura delle credenziali `MEROSS_EMAIL` e `MEROSS_PASSWORD` nel file `.env` di TrueNAS (`/mnt/stripe/truenas-docker/mcp/.env`) tramite estrazione SOPS.
  3. Nessuna necessità di build locale on-host: TrueNAS esegue il pull diretto dell'immagine semantica da GHCR.
- **Verifica Test-Driven**: Linting del file `docker-compose.yaml` (`docker compose config`).

### Fase 4: Deployment e Validazione End-to-End su TrueNAS
- **Obiettivo**: Avviare il container su TrueNAS SCALE bare-metal e connetterlo al client Antigravity.
- **Azioni**:
  1. Sincronizzazione dei file dichiarativi su TrueNAS SCALE (`10.10.20.50`).
  2. Avvio del container: `docker compose pull meross-mcp && docker compose up -d meross-mcp`.
  3. Verifica dello stato di salute (`docker ps`, health status `healthy`, ispezione dei log).
  4. Validazione endpoint di rete: probe HTTP su `http://10.10.20.50:8112/healthz` ed endpoint MCP su `http://10.10.20.50:8112/mcp`.
  5. Aggiornamento della configurazione centralizzata in `~/.gemini/antigravity/mcp_config.json`:
     ```json
     "meross": {
       "serverUrl": "http://10.10.20.50:8112/mcp"
     }
     ```
  6. Collaudo interattivo tramite Antigravity dei tool MCP sul server remoto.
- **Verifica Test-Driven**: Chiamata tool `meross_list_devices` tramite Antigravity con risposta corretta proveniente dal container TrueNAS.

### Fase 5: Integrazione Widget Consumi su Dashboard Homepage
- **Obiettivo**: Esporre i consumi in tempo reale delle prese Meross sulle dashboard Homepage K8s e TrueNAS.
- **Azioni**:
  1. Identificazione dell'UUID/nome della presa Meross adibita al monitoraggio.
  2. Configurazione del widget nativo `customapi` in `homepage/homepage.yaml` e `homepage/homepage-local.yaml`:
     ```yaml
     - Meross Smart Plug:
         href: http://10.10.20.50:8112/docs
         description: Presa Smart con telemetria energetica
         icon: mdi-power-socket-eu
         widget:
           type: customapi
           url: http://10.10.20.50:8112/api/v1/devices/{device_id}/power
           refresh: 10000
           mappings:
             - field: power_w
               label: Potenza
               format: number
               suffix: " W"
             - field: voltage_v
               label: Tensione
               format: number
               suffix: " V"
             - field: current_a
               label: Corrente
               format: number
               suffix: " A"
     ```
  3. Sincronizzazione della configurazione sulla dashboard Homepage bare-metal di TrueNAS.
  4. Esecuzione del rollout dei deployment K8s:
     ```bash
     kubectl apply -f homepage/homepage.yaml && kubectl apply -f homepage/homepage-local.yaml && kubectl rollout restart deployment/homepage deployment/homepage-local -n default
     ```
  5. Verifica del caricamento visivo dei dati di consumo in tempo reale.
- **Verifica Test-Driven**: Ispezione rendering Homepage e verifica assorbimento elettrico espresso in Watt.

---

## 💾 Stato di Ripristino (AI Save-State)
- **Fase Attiva**: Fase 3 (Deployment e Validazione End-to-End su TrueNAS) - Bugfix Telemetria & Routing MCP
- **Ultima Azione Completata**: Autenticazione Meross Cloud superata con successo; scoperta presa fisica `ups` (MSS310, UUID `2303168327141751200348e1e9bf25d7`); endpoint REST `/api/v1/devices` operativo al 100% su TrueNAS (`10.10.20.50:8112`). Immagine `ghcr.io/pindaroli/meross-mcp:0.1.0` pubblicata su GHCR e deployata con pinning semantico. Identificata la causa radice del baco telemetria (necessario `async_get_instant_metrics` con `PowerInfo` su `meross-iot` 0.4.x) e del mount subpath `/mcp`.
- **Prossimo Passo Operativo**: Patch al codice sorgente in `/Users/olindo/prj/meross-mcp/` (`client.py`, `devices.py` e `app.py`) per supportare `async_get_instant_metrics()` e mount unificato `mcp.http_app(path="/")`, rilascio versione `0.1.1` su GHCR e riavvio container.
- **Blocchi/Decisioni Pendenti**: Sessione sospesa su richiesta utente; pronta per essere ripresa con il bugfix.

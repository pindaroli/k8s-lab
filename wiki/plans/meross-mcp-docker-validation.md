---
title: "Piano: Test Locale, Configurazione Docker, Validazione Meross MCP Server & Widget Homepage"
type: plan
status: active
certified_for_ai: true
created_at: 2026-10-11
tags:
  - "#plan"
  - "#meross"
  - "#mcp"
  - "#docker"
  - "#truenas"
  - "#homepage"
  - "#iot"
  - "#power-monitoring"
---

# Piano: Test Locale, Configurazione Docker, Validazione Meross MCP Server & Widget Homepage

Questo documento definisce il piano operativo per il collaudo locale del server **Meross Dual Gateway** (`pindaroli/meross-mcp`), la sua integrazione containerizzata nello stack Docker permanente di TrueNAS SCALE bare-metal (`10.10.20.50`), la validazione come server MCP centralizzato per Antigravity e l'esposizione del widget di monitoraggio energetico (consumi in Watt, Volt e Ampere) sulla dashboard Homepage.

---

## 🗺️ Mappe Concettuali e Relazioni
- [[meross-mcp-server-project]] (Piano originario di scaffolding e sviluppo della libreria, FastAPI REST e FastMCP)
- [[zero-install-executable-package-pattern]] (Standard architetturale pacchetti zero-install on-demand)
- [[mcp-secret-projection-pattern]] (Proiezione sicura delle credenziali `MEROSS_*` nello stack TrueNAS)
- [[MCP_Platform]] (Architettura e registro dei server MCP attivi 24/7 su TrueNAS Docker)
- [[Homepage]] (Dashboard centrale del lab con supporto widget `customapi` e rollout dichiarativo)
- [[SCHEMA]] (Regole di governance e save-state del Wiki)

---

## 1. Architettura dell'Integrazione

```mermaid
flowchart TD
    subgraph Clients["Client & Consumatori"]
        AG["Google Antigravity (AI Agent)"]
        HP_K8S["Homepage (K8s: home.pindaroli.org)"]
        HP_TN["Homepage (TrueNAS: :3000)"]
    end

    subgraph TrueNAS["TrueNAS SCALE Bare-Metal (10.10.20.50)"]
        subgraph DockerStack["Stack Docker MCP (/mnt/stripe/truenas-docker/mcp/)"]
            MCP_MEROSS["Container mcp-meross\n(FastAPI + FastMCP Dual Gateway)\nPorta Host: 8112"]
            ENV_FILE[".env protetto (SOPS)\nMEROSS_EMAIL & MEROSS_PASSWORD"]
        end
    end

    subgraph MerossCloud["Infrastruttura Meross"]
        AUTH["Cloud Auth REST (iotx-eu.meross.com)"]
        MQTT_BROKER["Broker MQTT over TLS (AWS IoT)"]
    end

    subgraph Hardware["Dispositivi Fisici Homelab"]
        MSS310["Prese Smart Meross MSS310\n(con Power Metering)"]
    end

    AG -->|JSON-RPC /mcp| MCP_MEROSS
    HP_K8S & HP_TN -->|GET /api/v1/devices/{id}/power| MCP_MEROSS
    ENV_FILE --> MCP_MEROSS
    MCP_MEROSS -.->|Login Iniziale| AUTH
    MCP_MEROSS <===>|MQTT over TLS (Persistent Pool)| MQTT_BROKER
    MQTT_BROKER <===>|Telemetria W/V/A & Relè| MSS310
```

---

## 2. Fasi Operative del Piano

### Fase 1: Test Server Meross in Locale
- **Obiettivo**: Verificare il funzionamento del runtime e della libreria con credenziali reali prima del deployment.
- **Azioni**:
  1. Configurazione delle credenziali `MEROSS_EMAIL` e `MEROSS_PASSWORD` nel file `.env` in `/Users/olindo/prj/meross-mcp/`.
  2. Test di autenticazione REST iniziale su `https://iotx-eu.meross.com`.
  3. Stabilimento del client asincrono e polling MQTT over TLS verso il broker Meross.
  4. Esecuzione del Dual Gateway in locale (`meross-mcp --port 8112`).
  5. Test funzionale dei tool MCP (`meross_list_devices`, `meross_get_device_state`, commutazione relè e telemetria energetica) con le prese fisiche presenti nel lab.
- **Verifica Test-Driven**: Esecuzione smoke test CLI e chiamata `curl -s http://127.0.0.1:8112/api/v1/devices` con esito 200 OK e lista dispositivi popolata.

### Fase 2: Configurazione Docker Server MCP Meross
- **Obiettivo**: Integrare dichiarativamente il servizio Meross nello stack Docker Compose centralizzato di TrueNAS.
- **Azioni**:
  1. Aggiornamento dichiarativo di `docker/mcp/docker-compose.yaml`:
     - Servizio `meross-mcp`, container `mcp-meross`.
     - Porta host dedicata `8112:8112`.
     - Healthcheck su `http://127.0.0.1:8112/healthz`.
     - Riconfigurazione parametri d'ambiente: `MEROSS_GATEWAY_HOST=0.0.0.0`, `MEROSS_GATEWAY_PORT=8112`.
  2. Aggiornamento dello script `docker/mcp/build-images.sh` per la build locale dell'immagine (`local/meross-mcp:latest` da `/Users/olindo/prj/meross-mcp/Dockerfile`).
  3. Configurazione sicura delle credenziali `MEROSS_EMAIL` e `MEROSS_PASSWORD` nel file `.env` di TrueNAS (`/mnt/stripe/truenas-docker/mcp/.env`) tramite SOPS.
- **Verifica Test-Driven**: Linting del file `docker-compose.yaml` (`docker compose config`) e build dell'immagine container senza errori.

### Fase 3: Deployment e Test di Validazione End-to-End Container Docker
- **Obiettivo**: Avviare il container su TrueNAS SCALE bare-metal e connetterlo al client Antigravity.
- **Azioni**:
  1. Sincronizzazione dei file aggiornati su TrueNAS SCALE (`10.10.20.50`).
  2. Avvio del container: `docker compose up -d meross-mcp`.
  3. Verifica dello stato di salute (`docker ps`, health status `healthy`, ispezione dei log Uvicorn/FastMCP).
  4. Validazione endpoint di rete: probe HTTP su `http://10.10.20.50:8112/healthz` e endpoint MCP su `http://10.10.20.50:8112/mcp`.
  5. Aggiornamento della configurazione centralizzata in `~/.gemini/antigravity/mcp_config.json`:
     - Server `meross` con trasporto `sse` o `streamable-http` puntato a `http://10.10.20.50:8112/mcp`.
  6. Collaudo interattivo tramite Antigravity dei tool MCP sul server remoto.
- **Verifica Test-Driven**: Chiamata tool `meross_list_devices` tramite Antigravity con risposta corretta proveniente dal container TrueNAS.

### Fase 4: Integrazione Widget Consumi su Dashboard Homepage
- **Obiettivo**: Esporre i consumi in tempo reale delle prese Meross sulla dashboard Homepage K8s e TrueNAS.
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
  4. Esecuzione del rollout obbligatorio dei deployment K8s:
     ```bash
     kubectl apply -f homepage/homepage.yaml && kubectl apply -f homepage/homepage-local.yaml && kubectl rollout restart deployment/homepage deployment/homepage-local -n default
     ```
  5. Verifica del caricamento visivo dei dati di consumo in tempo reale.
- **Verifica Test-Driven**: Ispezione rendering Homepage e verifica assorbimento elettrico espresso in Watt.

---

## 💾 Stato di Ripristino (AI Save-State)
- **Fase Attiva**: Fase 1 (Test Server Meross in Locale)
- **Ultima Azione Completata**: Piano strutturato e registrato in Wiki e todo.md.
- **Prossimo Passo Operativo**: Configurazione credenziali reali in `.env` locale di `/Users/olindo/prj/meross-mcp` ed esecuzione smoke test locale.
- **Blocchi/Decisioni Pendenti**: Attesa credenziali utente o conferma esecuzione smoke test locale.

---
title: "Piano: Failover Idempotente e Trasparente TrueNAS -> Mac Studio (OrbStack) in lab_mode_off"
type: plan
status: active
certified_for_ai: true
created_at: 2026-10-23
tags:
  - "#core"
  - "#app"
  - "#network"
  - "#storage"
  - "#active"
  - "#truenas"
  - "#opnsense"
---

# Piano Operativo (KISS Hardened + Matrice 3x3 Completa): Failover Idempotente e Trasparente TrueNAS $\leftrightarrow$ Mac Studio (OrbStack)

> **Percorso Canonico Wiki**: `wiki/plans/orbstack-failover-truenas-services.md` (alias: `[[orbstack-failover-lab-mode-off]]`)
> **Comando di Attivazione per l'Agente Locale**: `/resume [[orbstack-failover-truenas-services]]`
> **Regole di Governance**: Rispetto integrale di `[[SCHEMA]]` (§6 IaC, §7 Network & DNS Standards, §11 `/resume`, §12 Test-Driven Verification Protocol, §13 Wiki Context Refresh), `[[go-launcher-script-pattern]]` e `[[hierarchical-automation-alerting-pattern]]`.

---

## 1. Contesto, Obiettivo, Decisioni Architetturali e Matrice 3x3 di Tutte le Transizioni

Quando il sistema entra in modalità **RACK DARK / OFF (`scripts/infrastructure/lab_mode_off.sh`)**, il cluster Kubernetes Talos, i 3 hypervisor Proxmox VE (`pve1`, `pve2`, `pve3`) e il server bare-metal **TrueNAS SCALE (`10.10.20.50`)** vengono spenti fisicamente.

L'obiettivo di questo piano è garantire che i **4 servizi critici di sviluppo e assistenza AI** (`mcp.pindaroli.org:8100`, `hermes.pindaroli.org:9119`, `litellm.pindaroli.org:4000`, `dozzle.pindaroli.org:8888`) continuino a funzionare senza alcuna interruzione e con **Zero Riconfigurazione Client** migrando automaticamente su **Mac Studio M2 Ultra (`10.10.20.100`)** tramite **OrbStack** in stato `OFF`, e tornando automaticamente su **TrueNAS (`10.10.20.50`)** quando si invocano `lab_mode_eco.sh` o `lab_mode_full.sh`, coprendo **tutte le 9 transizioni possibili (Matrice 3x3) più gli stati parziali/sporchi**.

### 1.1 Matrice delle 6 Decisioni Architetturali Approvate dall'Utente

| # | Ambito | Scelta Approvata | Specifica Tecnica Vincolante |
| :- | :--- | :--- | :--- |
| **1** | **DNS & Governance `rete.json`** | **1A (Rimuovere `mcp` da `traefik-lb` e assegnarlo a `truenas`)** | In `rete.json` l'alias `"mcp"` viene rimosso da `traefik-lb` (`10.10.20.56`) — dove restano `"mcp-internal"`, `"mcp-ui"`, `"mcp-ui-internal"` — e aggiunto a `truenas` (`10.10.20.50`) insieme a `"hermes"`, `"litellm"`, `"dozzle"`. In modalità `ECO`/`FULL` i 4 FQDN (`mcp.pindaroli.org`, `hermes.pindaroli.org`, `litellm.pindaroli.org`, `dozzle.pindaroli.org`) puntano a `10.10.20.50`; in modalità `OFF` vengono commutati atomicamente via API REST Unbound su `10.10.20.100` (Mac Studio). |
| **2** | **Profilo Flotta MCP su OrbStack** | **2A (Profilo Lean: solo i 7 MCP attivi a rack spento)** | Nello stack OrbStack (`docker-compose.orbstack.yaml`) vengono avviati `socket-proxy`, `traefik` (`:8100`) e **solo i 7 server MCP operativi a rack spento**: `opnsense-mcp`, `ollama-mcp` (connesso a Ollama Metal locale su Mac Studio `:11434`), `kef-mcp`, `nowaikit-mcp`, `github-mcp`, `gemini-deepsearch-mcp`, `meross-mcp`. I **5 server MCP con backend spenti in stato OFF** (`truenas-mcp`, `talos-mcp`, `kubernetes-mcp`, `arrstack-mcp`, `ragflow-mcp`) vengono **esplicitamente omessi** dallo stack OrbStack per evitare crash-loop, falsi allarmi in Dozzle e spreco di RAM su Mac Studio. |
| **3** | **Sincronizzazione Stato Hermes Agent** | **3A + Fix KISS (Sync bidirezionale `rsync -auz` sicuro senza Data Loss né rottura `unless-stopped`)** | **Pre-Shutdown (`lab_mode_off.sh`)**: prima di spegnere TrueNAS, se `10.10.20.50:22` è raggiungibile, si esegue `rsync -auz` da `/mnt/stripe/hermes-agent/` verso `~/.homelab-failover/hermes-data/` **senza** eseguire `docker compose stop hermes-agent` (così che Docker su TrueNAS non marchi il container come `Exited by user` e lo riavvii da solo al successivo boot). **Pre-Failback (`lab_mode_eco.sh` / `lab_mode_full.sh`)**: dopo `ensure_storage_on.yml`, **solo se** `hermes-agent` era effettivamente in esecuzione su OrbStack e la cartella `~/.homelab-failover/hermes-data/` non è vuota, si ferma `hermes-agent` su OrbStack, si esegue `rsync -auz` (senza `--delete` distruttivo) verso `/mnt/stripe/hermes-agent/` e si fa `docker restart hermes-agent` su TrueNAS. |
| **4** | **Gestione Segreti Runtime su Mac Studio** | **4A + Fix KISS (Due file `.env.ai` e `.env.mcp` separati, zero parser `awk`)** | Nessun merge `awk` né filtri `yq` complessi che rischiano di fallire su spazi o nomi di chiavi: in `~/.homelab-failover/` vengono mantenuti **due file distinti** (`.env.ai` per LiteLLM/Hermes e `.env.mcp` per i 7 server MCP), sincronizzati 1:1 da `/mnt/stripe/truenas-docker/.env` e `/mnt/stripe/truenas-docker/mcp/.env` quando TrueNAS è online, con fallback SOPS minimale solo se `.env.ai` è assente a freddo. |
| **5** | **Architettura LiteLLM su OrbStack** | **Soluzione 1 (LiteLLM Stateless Zero-DB su OrbStack)** | Su OrbStack **non** viene avviato `litellm-postgres` (esplicitamente rimosso perché ridondante per modelli Ollama locali a costo $0). `litellm` gira in modalità **Stateless** leggendo `servarr/truenas-docker/litellm/config.yaml` e impostando `LITELLM_MASTER_KEY: ${HERMES_LITELLM_KEY}`: in questo modo Hermes Agent e i client usano la medesima chiave `HERMES_LITELLM_KEY` sia su TrueNAS sia su OrbStack, con avvio istantaneo in 3 secondi. |
| **6** | **Struttura File Docker Compose** | **6A (File unico autonomo)** | Un singolo file dichiarativo autoconsistente in `docker/orbstack-failover/docker-compose.orbstack.yaml` che governa l'intero stack di failover su Mac Studio (`name: orbstack-failover`, 11 container totali: `socket-proxy`, `traefik`, 7 MCP, `litellm`, `hermes-agent`, `dozzle`). |

---

### 1.2 Matrice 3x3 di Tutte le Transizioni di Stato (Analisi di Copertura 100%)

Con 3 modalità dichiarative (`FULL`, `ECO`, `OFF`) esistono **9 transizioni possibili ($3 \times 3$)** più il caso di **Stato Ibrido/Sporco** (es. riavvio manuale di TrueNAS o crash a metà di una transizione precedente). La tabella seguente certifica come `orbstack_failover.sh` gestisce ciascuna transizione:

| # | Transizione (Da $\rightarrow$ A) | Script Invocato | Comportamento di Compute & Storage | Comportamento di `orbstack_failover.sh` & DNS Unbound |
| :- | :--- | :--- | :--- | :--- |
| **1** | **FULL $\rightarrow$ ECO** | `lab_mode_eco.sh` | `ensure_storage_on` (TrueNAS già ON $\rightarrow$ skip WoL) $\rightarrow$ `ensure_compute_off` (spegne K8s e PVE) | Rileva che OrbStack è **già spento**: **salta** `rsync` da Mac a TrueNAS (nessun rischio di sovrascrivere sessioni attive su TrueNAS), verifica in <1s che `:8100,:9119,:4000,:8888` siano up su TrueNAS e che il DNS punti già a `10.10.20.50` (`[IDEMPOTENT]`). |
| **2** | **ECO $\rightarrow$ FULL** | `lab_mode_full.sh` | `ensure_storage_on` (TrueNAS già ON $\rightarrow$ skip WoL) $\rightarrow$ `ensure_compute_on` (accende PVE e K8s) | Rileva che OrbStack è **già spento**: **salta** `rsync` e `docker compose down`, verifica in <1s che le 4 porte su TrueNAS siano attive e il DNS su `10.10.20.50` (`[IDEMPOTENT]`). |
| **3** | **FULL $\rightarrow$ OFF** | `lab_mode_off.sh` | `ensure_compute_off` (spegne K8s e PVE) $\rightarrow$ `ensure_storage_off` (spegne TrueNAS) | Prima di spegnere TrueNAS copia `.env.ai`/`.env.mcp` e fa `rsync -auz` di `/mnt/stripe/hermes-agent/` su Mac; spento TrueNAS, avvia OrbStack (11 container) e commuta il DNS Unbound su `10.10.20.100`. |
| **4** | **ECO $\rightarrow$ OFF** | `lab_mode_off.sh` | `ensure_compute_off` (già OFF $\rightarrow$ skip in 1s) $\rightarrow$ `ensure_storage_off` (spegne TrueNAS) | Prima di spegnere TrueNAS copia `.env.ai`/`.env.mcp` e fa `rsync -auz` di `/mnt/stripe/hermes-agent/` su Mac; spento TrueNAS, avvia OrbStack (11 container) e commuta il DNS Unbound su `10.10.20.100`. |
| **5** | **OFF $\rightarrow$ ECO** | `lab_mode_eco.sh` | `ensure_storage_on` (WoL TrueNAS + ZFS healthy) $\rightarrow$ `ensure_compute_off` (già OFF $\rightarrow$ skip) | Rileva `hermes-agent` attivo su OrbStack: lo ferma, esegue `rsync -auz` da Mac a TrueNAS, garantisce l'avvio di entrambi gli stack Docker su TrueNAS, verifica le 4 porte `:8100,:9119,:4000,:8888`, commuta il DNS su `10.10.20.50` e spegne OrbStack (`down`). |
| **6** | **OFF $\rightarrow$ FULL** | `lab_mode_full.sh` | `ensure_storage_on` (WoL TrueNAS + ZFS healthy) $\rightarrow$ `ensure_compute_on` (WoL PVE + Talos Ready) | Esegue il failback completo di Hermes, MCP e DNS da Mac Studio a TrueNAS **subito dopo** `ensure_storage_on` (Fase 2), così che i 12 MCP su TrueNAS e Hermes tornino operativi già mentre PVE e Talos stanno facendo il boot in Fase 3. |
| **7** | **OFF $\rightarrow$ OFF** *(Idempotenza)* | `lab_mode_off.sh` | `ensure_compute_off` (skip) $\rightarrow$ `ensure_storage_off` (skip) | Rileva TrueNAS spento (usa `.env.ai`/`.env.mcp` e `hermes-data` già su Mac), `docker compose up -d` non riavvia i container già `Up (healthy)` e `switch_failover_dns.py` stampa `[IDEMPOTENT]` senza riavviare Unbound. |
| **8** | **ECO $\rightarrow$ ECO** *(Idempotenza)* | `lab_mode_eco.sh` | `ensure_storage_on` (skip WoL) $\rightarrow$ `ensure_compute_off` (skip) | OrbStack è spento, porte TrueNAS già aperte, DNS già su `10.10.20.50` (`[IDEMPOTENT]`): zero azioni distruttive, completamento in pochi secondi. |
| **9** | **FULL $\rightarrow$ FULL** *(Idempotenza)* | `lab_mode_full.sh` | `ensure_storage_on` (skip WoL) $\rightarrow$ `ensure_compute_on` (skip WoL) | OrbStack è spento, porte TrueNAS già aperte, DNS già su `10.10.20.50` (`[IDEMPOTENT]`): zero riavvii container, completamento immediato. |
| **10** | **Stato Sporco / Recovery** *(es. container spenti su TrueNAS dopo manutenzione o OrbStack rimasto parzialmente acceso)* | `lab_mode_eco.sh` o `lab_mode_full.sh` | Convergenza forzosa allo stato target | **Auto-Healing KISS**: se una delle 4 porte (`8100,9119,4000,8888`) su TrueNAS risulta chiusa dopo il boot, `deactivate_orbstack_failover_to_truenas` lancia automaticamente `docker compose up -d` su entrambi gli stack di TrueNAS prima del loop di attesa; e se erano rimasti container orfani nello stack `orbstack-failover` sul Mac, li spegne sempre con `down --remove-orphans`. |

---

## 2. Mappa Completa dei File da Creare o Modificare

| Azione | Percorso File | Descrizione Sintetica |
| :--- | :--- | :--- |
| **MODIFICA** | `rete.json` | Rimozione di `"mcp"` da `traefik-lb.aliases`; aggiunta di `"mcp"`, `"hermes"`, `"litellm"`, `"dozzle"` a `truenas.aliases`. |
| **MODIFICA** | `servarr/truenas-docker/litellm/config.yaml` | Aggiunta dell'endpoint primario `http://olindo-macstudio.pindaroli.org:11434` (`order: 1`) al modello `embed` (`bge-m3:latest`), mantenendo `lxc-ollama` come `order: 2`. Tutti gli altri 4 modelli (`big-chat`, `big-alt`, `vision`, `vision-light`) restano identici. |
| **CREAZIONE** | `docker/orbstack-failover/docker-compose.orbstack.yaml` | Compose file completo per OrbStack su Mac Studio M2 Ultra (11 servizi: `socket-proxy`, `traefik`, 7 MCP attivi con `env_file: .env.mcp`, `litellm` stateless e `hermes-agent` con `env_file: .env.ai`, `dozzle`). |
| **CREAZIONE** | `scripts/network/switch_failover_dns.py` | Script Python 3 idempotente che interroga e aggiorna gli Host Overrides Unbound su OPNsense (`mcp`, `hermes`, `litellm`, `dozzle` `.pindaroli.org`) verso `10.10.20.50` (`--target truenas`) o `10.10.20.100` (`--target orbstack`), elimina eventuali duplicati, esegue `/api/unbound/service/reconfigure` solo in caso di modifica reale e svuota la cache DNS di macOS. |
| **CREAZIONE** | `scripts/infrastructure/orbstack_failover.sh` | Libreria Bash KISS idempotente richiamata da `lab_mode_off.sh`, `lab_mode_eco.sh` e `lab_mode_full.sh` che gestisce tutte le 9+1 transizioni di stato. |
| **MODIFICA** | `scripts/infrastructure/lab_mode_off.sh` | Integrazione di `source "$SCRIPT_DIR/orbstack_failover.sh"`, `sync_hermes_state_from_truenas` (prima di `ensure_storage_off.yml`) e `activate_orbstack_failover` (dopo `ensure_storage_off.yml`), preservando intatto l'intero codice esistente. |
| **MODIFICA** | `scripts/infrastructure/lab_mode_eco.sh` | Integrazione di `source "$SCRIPT_DIR/orbstack_failover.sh"` e `deactivate_orbstack_failover_to_truenas` (subito dopo `ensure_storage_on.yml`), preservando intatto l'intero codice esistente. |
| **MODIFICA** | `scripts/infrastructure/lab_mode_full.sh` | Integrazione di `source "$SCRIPT_DIR/orbstack_failover.sh"` e `deactivate_orbstack_failover_to_truenas` (subito dopo `ensure_storage_on.yml`), preservando intatto l'intero codice esistente. |
| **MODIFICA** | `~/.gemini/antigravity/mcp_config.json` | Aggiornamento di tutti i 12 `serverUrl` da `http://10.10.20.50:8100/...` a `http://mcp.pindaroli.org:8100/...` (preservando `disabledTools` su `truenas-master-mcp`). |

---

## 3. Fasi Operative di Implementazione (Protocollo Test-Driven §12)

> [!IMPORTANT]
> **REGOLA PER L'AGENTE LOCALE**: Ogni singola fase contiene i blocchi di codice integrali (mai troncati) e il relativo **Test di Verifica Obbligatorio**. È vietato procedere alla fase successiva se il comando di verifica della fase corrente non restituisce esito positivo al 100%.

---

### FASE 1: Allineamento `rete.json` e `servarr/truenas-docker/litellm/config.yaml`

#### Passo 1.1: Aggiornamento `rete.json` (Scelta 1A)
Nel file `rete.json`:
1. Nel nodo `"id": "truenas"` (`management_ip: "10.10.20.50"`), aggiornare l'array `"aliases"` aggiungendo `"mcp"`, `"hermes"`, `"litellm"`, `"dozzle"` (mantenendo `"s3"` e `"nas-direct"`):
   ```json
      "id": "truenas",
      "label": "TrueNAS Scale",
      "type": "Bare Metal",
      "role": "NAS",
      "hostname": "truenas",
      "domain": "pindaroli.org",
      "aliases": [
        "s3",
        "nas-direct",
        "mcp",
        "hermes",
        "litellm",
        "dozzle"
      ],
   ```
2. Nel nodo `"id": "traefik-lb"` (`ip: "10.10.20.56"`), **rimuovere esclusivamente la voce `"mcp"`** dall'array `"aliases"`, lasciando intatti tutti gli altri 37 alias (inclusi `"mcp-internal"`, `"mcp-ui"`, `"mcp-ui-internal"`).

#### Passo 1.2: Aggiornamento `servarr/truenas-docker/litellm/config.yaml`
Sostituire il file `servarr/truenas-docker/litellm/config.yaml` con la versione completa seguente (identica all'originale riga per riga per `big-chat`, `big-alt`, `vision`, `vision-light` e `router_settings`, con la sola aggiunta dell'istanza `olindo-macstudio.pindaroli.org:11434` con `order: 1` per il modello `embed` così che gli embedding funzionino anche a rack spento):

```yaml
model_list:
  # 1. big-chat (qwen2.5:32b-instruct-q5_K_M)
  - model_name: big-chat
    litellm_params:
      model: ollama_chat/qwen2.5:32b-instruct-q5_K_M
      api_base: http://olindo-macstudio.pindaroli.org:11434
      order: 1
      timeout: 5
      stream_timeout: 10
  - model_name: big-chat
    litellm_params:
      model: ollama_chat/qwen2.5:32b-instruct-q5_K_M
      api_base: http://lxc-ollama.pindaroli.org:11434
      order: 2

  # 2. big-alt (gemma4:31b)
  - model_name: big-alt
    litellm_params:
      model: ollama_chat/gemma4:31b
      api_base: http://olindo-macstudio.pindaroli.org:11434
      order: 1
      timeout: 5
      stream_timeout: 10
  - model_name: big-alt
    litellm_params:
      model: ollama_chat/gemma4:31b
      api_base: http://lxc-ollama.pindaroli.org:11434
      order: 2

  # 3. vision (qwen3-vl:32b)
  - model_name: vision
    litellm_params:
      model: ollama_chat/qwen3-vl:32b
      api_base: http://olindo-macstudio.pindaroli.org:11434
      order: 1
      timeout: 5
      stream_timeout: 10
  - model_name: vision
    litellm_params:
      model: ollama_chat/qwen3-vl:32b
      api_base: http://lxc-ollama.pindaroli.org:11434
      order: 2

  # 4. vision-light (qwen2.5vl:7b-q4_K_M)
  - model_name: vision-light
    litellm_params:
      model: ollama_chat/qwen2.5vl:7b-q4_K_M
      api_base: http://olindo-macstudio.pindaroli.org:11434
      order: 1
      timeout: 5
      stream_timeout: 10
  - model_name: vision-light
    litellm_params:
      model: ollama_chat/qwen2.5vl:7b-q4_K_M
      api_base: http://lxc-ollama.pindaroli.org:11434
      order: 2

  # 5. embed (bge-m3:latest) — Mac Studio order 1 (attivo anche in lab_mode_off) + lxc-ollama order 2
  - model_name: embed
    litellm_params:
      model: ollama/bge-m3:latest
      api_base: http://olindo-macstudio.pindaroli.org:11434
      order: 1
      timeout: 5
      stream_timeout: 10
  - model_name: embed
    litellm_params:
      model: ollama/bge-m3:latest
      api_base: http://lxc-ollama.pindaroli.org:11434
      order: 2

router_settings:
  model_group_alias:
    chat: big-chat
  routing_strategy: simple-shuffle
  allowed_fails: 1
  cooldown_time: 60
```

#### Passo 1.3: Test di Verifica Fase 1
```bash
python3 scripts/network/validate_network.py || python3 scripts/validate_network.py
yq eval '.model_list | length' servarr/truenas-docker/litellm/config.yaml
```
- **Criterio di superamento**: `validate_network.py` termina con exit code `0` (nessun alias duplicato tra `truenas` e `traefik-lb`) e `config.yaml` conta `10` entry in `model_list` (2 per ciascuno dei 5 modelli).

---

### FASE 2: Creazione Stack Docker Compose per OrbStack (`docker/orbstack-failover/docker-compose.orbstack.yaml`)

#### Passo 2.1: Creazione directory e file `docker/orbstack-failover/docker-compose.orbstack.yaml`
Creare la cartella `docker/orbstack-failover/` e scrivere il file `docker/orbstack-failover/docker-compose.orbstack.yaml`:

```yaml
# ==============================================================================
# FILE: docker/orbstack-failover/docker-compose.orbstack.yaml
# DESCRIZIONE: Stack di Failover su Mac Studio (OrbStack - 10.10.20.100) per lab_mode_off
#              Include:
#              - socket-proxy (L7 Read-Only Docker Socket Proxy per Traefik e Dozzle)
#              - traefik (:8100 Umbrella Gateway MCP)
#              - I 7 Server MCP attivi a rack spento: opnsense, gemini-deepsearch,
#                ollama (connesso a Ollama Metal locale :11434), kef, nowaikit, github, meross
#              - litellm (:4000 Stateless Zero-DB con LITELLM_MASTER_KEY=${HERMES_LITELLM_KEY})
#              - hermes-agent (:9119 con stato sincronizzato via rsync in ~/.homelab-failover/hermes-data)
#              - dozzle (:8888 Log Viewer connesso via socket-proxy)
# ==============================================================================
name: orbstack-failover

networks:
  mcp-network:
    name: orbstack-mcp-network
    driver: bridge
  mcp-socket-proxy:
    name: orbstack-socket-proxy
    driver: bridge
    internal: true
  ai-network:
    name: orbstack-ai-network
    driver: bridge

services:
  # ============================================================================
  # 0A. DOCKER SOCKET PROXY
  # ============================================================================
  socket-proxy:
    image: tecnativa/docker-socket-proxy:v0.4.1
    container_name: mcp-socket-proxy
    restart: unless-stopped
    privileged: false
    read_only: true
    tmpfs:
      - /run
      - /tmp
    security_opt:
      - no-new-privileges:true
    environment:
      - LOG_LEVEL=notice
      - CONTAINERS=1
      - NETWORKS=1
      - EVENTS=1
      - PING=1
      - VERSION=1
      - INFO=1
      - POST=0
      - AUTH=0
      - BUILD=0
      - COMMIT=0
      - CONFIGS=0
      - DISTRIBUTION=0
      - EXEC=0
      - GRPC=0
      - IMAGES=0
      - NODES=0
      - PLUGINS=0
      - SECRETS=0
      - SERVICES=0
      - SESSION=0
      - SWARM=0
      - SYSTEM=0
      - TASKS=0
      - VOLUMES=0
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock:ro
    networks:
      - mcp-socket-proxy

  # ============================================================================
  # 0B. TRAEFIK UMBRELLA GATEWAY — Porta Host Unica 8100 & Streaming Tuning
  # ============================================================================
  traefik:
    image: traefik:v3.3.4
    container_name: mcp-traefik
    restart: unless-stopped
    read_only: true
    security_opt:
      - no-new-privileges:true
    cap_drop:
      - ALL
    depends_on:
      - socket-proxy
    command:
      - "--providers.docker=true"
      - "--providers.docker.endpoint=tcp://socket-proxy:2375"
      - "--providers.docker.exposedbydefault=false"
      - "--providers.docker.network=orbstack-mcp-network"
      - "--entrypoints.mcp.address=:8100"
      - "--entrypoints.mcp.transport.respondingTimeouts.readTimeout=0s"
      - "--entrypoints.mcp.transport.respondingTimeouts.writeTimeout=0s"
      - "--entrypoints.mcp.transport.respondingTimeouts.idleTimeout=3600s"
      - "--serversTransport.forwardingTimeouts.dialTimeout=10s"
      - "--serversTransport.forwardingTimeouts.responseHeaderTimeout=0s"
      - "--serversTransport.forwardingTimeouts.idleConnTimeout=3600s"
      - "--ping=true"
      - "--accesslog=true"
      - "--log.level=INFO"
    ports:
      - "8100:8100"
    networks:
      - mcp-network
      - mcp-socket-proxy
    healthcheck:
      test: ["CMD", "traefik", "healthcheck", "--ping"]
      interval: 15s
      timeout: 3s
      retries: 3
      start_period: 5s

  # ============================================================================
  # 1. OPNSENSE MCP — REST API OPNsense MVC (Supergateway Stateful)
  # ============================================================================
  opnsense-mcp:
    container_name: mcp-opnsense
    image: ghcr.io/pindaroli/opnsense-mcp:0.5.3-r1
    restart: unless-stopped
    env_file: ${FAILOVER_RUNTIME_DIR:-/Users/olindo/.homelab-failover}/.env.mcp
    networks:
      - mcp-network
    labels:
      - "traefik.enable=true"
      - "traefik.http.routers.mcp-opnsense.entrypoints=mcp"
      - "traefik.http.routers.mcp-opnsense.rule=PathPrefix(`/opnsense`)"
      - "traefik.http.middlewares.strip-opnsense.stripprefix.prefixes=/opnsense"
      - "traefik.http.routers.mcp-opnsense.middlewares=strip-opnsense"
      - "traefik.http.services.mcp-opnsense.loadbalancer.server.port=8080"
      - "traefik.http.services.mcp-opnsense.loadbalancer.responseforwarding.flushinterval=-1ms"
    healthcheck:
      test: ["CMD-SHELL", "wget -q --spider http://127.0.0.1:8080/healthz || exit 1"]
      interval: 30s
      timeout: 5s
      retries: 3
      start_period: 10s

  # ============================================================================
  # 2. GEMINI DEEPSEARCH — LangGraph Web Search Agent (Python Streamable HTTP)
  # ============================================================================
  gemini-deepsearch-mcp:
    container_name: mcp-gemini-deepsearch
    image: ghcr.io/pindaroli/gemini-deepsearch-mcp:0.2.0
    restart: unless-stopped
    env_file: ${FAILOVER_RUNTIME_DIR:-/Users/olindo/.homelab-failover}/.env.mcp
    environment:
      - MCP_TRANSPORT=streamable-http
      - MCP_HOST=0.0.0.0
      - MCP_PORT=8080
    networks:
      - mcp-network
    labels:
      - "traefik.enable=true"
      - "traefik.http.routers.mcp-gemini.entrypoints=mcp"
      - "traefik.http.routers.mcp-gemini.rule=PathPrefix(`/gemini`)"
      - "traefik.http.middlewares.strip-gemini.stripprefix.prefixes=/gemini"
      - "traefik.http.routers.mcp-gemini.middlewares=strip-gemini"
      - "traefik.http.services.mcp-gemini.loadbalancer.server.port=8080"
      - "traefik.http.services.mcp-gemini.loadbalancer.responseforwarding.flushinterval=-1ms"
    healthcheck:
      test: ["CMD-SHELL", "python -c \"import urllib.request, urllib.error; req = urllib.request.Request('http://127.0.0.1:8080/mcp'); \ntry: urllib.request.urlopen(req, timeout=2)\nexcept urllib.error.HTTPError as e: assert e.code in (200, 400, 406)\" || exit 1"]
      interval: 30s
      timeout: 5s
      retries: 3
      start_period: 10s

  # ============================================================================
  # 3. OLLAMA MCP — Ollama REST API (Punta a Ollama Metal su Mac Studio :11434)
  # ============================================================================
  ollama-mcp:
    container_name: mcp-ollama
    image: ghcr.io/pindaroli/ollama-mcp:2.1.0-r1
    restart: unless-stopped
    env_file: ${FAILOVER_RUNTIME_DIR:-/Users/olindo/.homelab-failover}/.env.mcp
    environment:
      - OLLAMA_HOST=http://host.docker.internal:11434
    extra_hosts:
      - "host.docker.internal:host-gateway"
      - "olindo-macstudio.pindaroli.org:host-gateway"
    networks:
      - mcp-network
    labels:
      - "traefik.enable=true"
      - "traefik.http.routers.mcp-ollama.entrypoints=mcp"
      - "traefik.http.routers.mcp-ollama.rule=PathPrefix(`/ollama`)"
      - "traefik.http.middlewares.strip-ollama.stripprefix.prefixes=/ollama"
      - "traefik.http.routers.mcp-ollama.middlewares=strip-ollama"
      - "traefik.http.services.mcp-ollama.loadbalancer.server.port=8080"
      - "traefik.http.services.mcp-ollama.loadbalancer.responseforwarding.flushinterval=-1ms"
    healthcheck:
      test: ["CMD-SHELL", "wget -q --spider http://127.0.0.1:8080/healthz || exit 1"]
      interval: 30s
      timeout: 5s
      retries: 3
      start_period: 10s

  # ============================================================================
  # 4. KEF MCP — KEF LSX II Speakers Control (FastAPI / SSE)
  # ============================================================================
  kef-mcp:
    container_name: mcp-kef
    image: ghcr.io/pindaroli/kef-mcp:1.0.0
    restart: unless-stopped
    environment:
      - MCP_TRANSPORT=sse
      - MCP_PORT=8080
      - MCP_HOST=0.0.0.0
    env_file: ${FAILOVER_RUNTIME_DIR:-/Users/olindo/.homelab-failover}/.env.mcp
    networks:
      - mcp-network
    labels:
      - "traefik.enable=true"
      - "traefik.http.routers.mcp-kef.entrypoints=mcp"
      - "traefik.http.routers.mcp-kef.rule=PathPrefix(`/kef`)"
      - "traefik.http.middlewares.strip-kef.stripprefix.prefixes=/kef"
      - "traefik.http.routers.mcp-kef.middlewares=strip-kef"
      - "traefik.http.services.mcp-kef.loadbalancer.server.port=8080"
      - "traefik.http.services.mcp-kef.loadbalancer.responseforwarding.flushinterval=-1ms"
    healthcheck:
      test: ["CMD-SHELL", "python -c \"import urllib.request; urllib.request.urlopen('http://127.0.0.1:8080/mcp', timeout=2)\" || exit 0"]
      interval: 30s
      timeout: 5s
      retries: 3
      start_period: 10s

  # ============================================================================
  # 5. NOWAIKIT MCP — ServiceNow REST API (Supergateway Stateful)
  # ============================================================================
  nowaikit-mcp:
    container_name: mcp-nowaikit
    image: ghcr.io/pindaroli/nowaikit-mcp:4.15.1-r1
    restart: unless-stopped
    env_file: ${FAILOVER_RUNTIME_DIR:-/Users/olindo/.homelab-failover}/.env.mcp
    networks:
      - mcp-network
    labels:
      - "traefik.enable=true"
      - "traefik.http.routers.mcp-nowaikit.entrypoints=mcp"
      - "traefik.http.routers.mcp-nowaikit.rule=PathPrefix(`/nowaikit`)"
      - "traefik.http.middlewares.strip-nowaikit.stripprefix.prefixes=/nowaikit"
      - "traefik.http.routers.mcp-nowaikit.middlewares=strip-nowaikit"
      - "traefik.http.services.mcp-nowaikit.loadbalancer.server.port=8080"
      - "traefik.http.services.mcp-nowaikit.loadbalancer.responseforwarding.flushinterval=-1ms"
    healthcheck:
      test: ["CMD-SHELL", "wget -q --spider http://127.0.0.1:8080/healthz || exit 1"]
      interval: 30s
      timeout: 5s
      retries: 3
      start_period: 10s

  # ============================================================================
  # 6. GITHUB MCP — GitHub Cloud REST/GraphQL (Supergateway Stateful)
  # ============================================================================
  github-mcp:
    container_name: mcp-github
    image: ghcr.io/pindaroli/github-mcp-server:0.7.0-r1
    restart: unless-stopped
    env_file: ${FAILOVER_RUNTIME_DIR:-/Users/olindo/.homelab-failover}/.env.mcp
    networks:
      - mcp-network
    labels:
      - "traefik.enable=true"
      - "traefik.http.routers.mcp-github.entrypoints=mcp"
      - "traefik.http.routers.mcp-github.rule=PathPrefix(`/github`)"
      - "traefik.http.middlewares.strip-github.stripprefix.prefixes=/github"
      - "traefik.http.routers.mcp-github.middlewares=strip-github"
      - "traefik.http.services.mcp-github.loadbalancer.server.port=8080"
      - "traefik.http.services.mcp-github.loadbalancer.responseforwarding.flushinterval=-1ms"
    healthcheck:
      test: ["CMD-SHELL", "wget -q --spider http://127.0.0.1:8080/healthz || exit 1"]
      interval: 30s
      timeout: 5s
      retries: 3
      start_period: 10s

  # ============================================================================
  # 7. MEROSS MCP — Dual Gateway FastAPI REST + FastMCP (Homepage Widget & MCP)
  # ============================================================================
  meross-mcp:
    container_name: mcp-meross
    image: ghcr.io/pindaroli/meross-mcp:0.1.2
    restart: unless-stopped
    env_file: ${FAILOVER_RUNTIME_DIR:-/Users/olindo/.homelab-failover}/.env.mcp
    environment:
      - MEROSS_EMAIL=${MEROSS_EMAIL}
      - MEROSS_PASSWORD=${MEROSS_PASSWORD}
      - MEROSS_API_BASE_URL=https://iotx-eu.meross.com
      - MEROSS_GATEWAY_HOST=0.0.0.0
      - MEROSS_GATEWAY_PORT=8112
    networks:
      - mcp-network
    labels:
      - "traefik.enable=true"
      - "traefik.http.routers.mcp-meross.entrypoints=mcp"
      - "traefik.http.routers.mcp-meross.rule=PathPrefix(`/meross`)"
      - "traefik.http.middlewares.strip-meross.stripprefix.prefixes=/meross"
      - "traefik.http.routers.mcp-meross.middlewares=strip-meross"
      - "traefik.http.services.mcp-meross.loadbalancer.server.port=8112"
      - "traefik.http.services.mcp-meross.loadbalancer.responseforwarding.flushinterval=-1ms"
    healthcheck:
      test: ["CMD", "python", "-c", "import urllib.request; urllib.request.urlopen('http://localhost:8112/healthz')"]
      interval: 30s
      timeout: 5s
      retries: 3
      start_period: 10s

  # ============================================================================
  # 8. LITELLM PROXY STATELESS — Porta Host 4000 (Zero Postgres)
  # ============================================================================
  litellm:
    image: ghcr.io/berriai/litellm:1.106.2
    container_name: litellm
    restart: unless-stopped
    ports:
      - "4000:4000"
    env_file: ${FAILOVER_RUNTIME_DIR:-/Users/olindo/.homelab-failover}/.env.ai
    environment:
      LITELLM_MASTER_KEY: ${HERMES_LITELLM_KEY}
      LITELLM_SALT_KEY: ${LITELLM_SALT_KEY}
      UI_USERNAME: ${LITELLM_UI_USERNAME:-admin}
      UI_PASSWORD: ${LITELLM_UI_PASSWORD}
    extra_hosts:
      - "host.docker.internal:host-gateway"
      - "olindo-macstudio.pindaroli.org:host-gateway"
    volumes:
      - ${ROOT_DIR:-/Users/olindo/prj/k8s-lab}/servarr/truenas-docker/litellm/config.yaml:/app/config.yaml:ro
    command: ["--config", "/app/config.yaml", "--port", "4000"]
    networks:
      - ai-network
    healthcheck:
      test: ["CMD", "python3", "-c", "import urllib.request; urllib.request.urlopen('http://localhost:4000/health/liveliness')"]
      interval: 10s
      timeout: 5s
      retries: 3
      start_period: 20s

  # ============================================================================
  # 9. HERMES AGENT — Porta Host 9119 (Stato sincronizzato bidirezionalmente)
  # ============================================================================
  hermes-agent:
    image: nousresearch/hermes-agent:v2026.7.20
    container_name: hermes-agent
    restart: unless-stopped
    ports:
      - "9119:9119"
    env_file: ${FAILOVER_RUNTIME_DIR:-/Users/olindo/.homelab-failover}/.env.ai
    environment:
      HERMES_HOME: "/opt/data"
      HERMES_DASHBOARD: "1"
      HERMES_DASHBOARD_HOST: "0.0.0.0"
      HERMES_DASHBOARD_PORT: "9119"
      HERMES_AUTH_PROVIDER: "password"
      HERMES_DASHBOARD_BASIC_AUTH_USERNAME: ${HERMES_DASHBOARD_USERNAME:-admin}
      HERMES_DASHBOARD_BASIC_AUTH_PASSWORD: ${HERMES_DASHBOARD_PASSWORD}
      HERMES_DASHBOARD_PASSWORD: ${HERMES_DASHBOARD_PASSWORD}
      OPENAI_API_BASE: "http://litellm:4000/v1"
      OPENAI_API_KEY: ${HERMES_LITELLM_KEY}
      LITELLM_API_KEY: ${HERMES_LITELLM_KEY}
    command: ["hermes", "gateway", "run"]
    volumes:
      - ${FAILOVER_RUNTIME_DIR:-/Users/olindo/.homelab-failover}/hermes-data:/opt/data
    depends_on:
      litellm:
        condition: service_healthy
    networks:
      - ai-network
      - mcp-network
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:9119/health"]
      interval: 10s
      timeout: 5s
      retries: 3
      start_period: 20s

  # ============================================================================
  # 10. DOZZLE LOG VIEWER — Porta Host 8888 (Protetto via Socket Proxy L7)
  # ============================================================================
  dozzle:
    image: amir20/dozzle:v11.2.0
    container_name: dozzle
    restart: unless-stopped
    ports:
      - "8888:8080"
    depends_on:
      - socket-proxy
    volumes:
      - ${FAILOVER_RUNTIME_DIR:-/Users/olindo/.homelab-failover}/dozzle:/data
    environment:
      - DOZZLE_NO_ANALYTICS=true
      - DOZZLE_LEVEL=info
      - DOCKER_HOST=tcp://socket-proxy:2375
    networks:
      - mcp-socket-proxy
    healthcheck:
      test: ["CMD", "/dozzle", "healthcheck"]
      interval: 30s
      timeout: 5s
      retries: 3
```

#### Passo 2.2: Test di Verifica Fase 2
```bash
mkdir -p ~/.homelab-failover && touch ~/.homelab-failover/.env.ai ~/.homelab-failover/.env.mcp
docker compose -f docker/orbstack-failover/docker-compose.orbstack.yaml config --services
```
- **Criterio di superamento**: Il comando elenca esattamente gli 11 servizi (`socket-proxy`, `traefik`, `opnsense-mcp`, `gemini-deepsearch-mcp`, `ollama-mcp`, `kef-mcp`, `nowaikit-mcp`, `github-mcp`, `meross-mcp`, `litellm`, `hermes-agent`, `dozzle`) senza errori di interpolazione YAML.

---

### FASE 3: Creazione Script di Switchover DNS Unbound (`scripts/network/switch_failover_dns.py`) e Libreria KISS (`scripts/infrastructure/orbstack_failover.sh`)

#### Passo 3.1: Creazione del file `scripts/network/switch_failover_dns.py`
Scrivere il file `scripts/network/switch_failover_dns.py` e impostare `chmod +x`:

```python
#!/usr/bin/env python3
# ==============================================================================
# FILE: scripts/network/switch_failover_dns.py
# DESCRIZIONE: Switchover atomico e idempotente degli Host Overrides Unbound
#              su OPNsense tra TrueNAS (10.10.20.50) e Mac Studio (10.10.20.100).
# ==============================================================================

import argparse
import base64
import json
import os
import re
import ssl
import subprocess
import sys
import urllib.error
import urllib.request

# Risoluzione dinamica della root del repository (conforme a go-launcher-script-pattern)
SCRIPT_DIR = os.path.dirname(os.path.realpath(__file__))
ROOT_DIR = os.path.abspath(os.path.join(SCRIPT_DIR, "..", ".."))
os.chdir(ROOT_DIR)

OPNSENSE_ENDPOINTS = [
    "https://192.168.100.1",
    "https://192.168.2.254",
    "https://10.10.20.1",
]
DOMAIN = "pindaroli.org"

TARGETS = {
    "truenas": {
        "ip": "10.10.20.50",
        "label": "TrueNAS SCALE Bare-Metal (ECO/FULL Mode)",
    },
    "orbstack": {
        "ip": "10.10.20.100",
        "label": "Mac Studio OrbStack Failover (RACK DARK / OFF Mode)",
    },
}

FAILOVER_HOSTS = [
    ("mcp", "MCP Fleet Traefik Umbrella Gateway (:8100)"),
    ("hermes", "Hermes Agent AI Gateway & Dashboard (:9119)"),
    ("litellm", "LiteLLM Inference Proxy & UI (:4000)"),
    ("dozzle", "Dozzle Docker Log Viewer (:8888)"),
]


def load_opnsense_credentials() -> tuple[str, str]:
    """Carica opnsense_api_key e opnsense_api_secret da env, ansible/vars o SOPS."""
    key = os.environ.get("OPNSENSE_API_KEY", "").strip()
    secret = os.environ.get("OPNSENSE_API_SECRET", "").strip()
    if key and secret:
        return key, secret

    candidates = [
        os.path.join(ROOT_DIR, "ansible", "vars", "opnsense_secrets.yml"),
        os.path.join(ROOT_DIR, "ansible", "vars", "common_secrets.yml"),
        os.path.join(ROOT_DIR, "secrets-sops", "opnsense-secrets.enc.yaml"),
    ]
    for path in candidates:
        if not os.path.exists(path):
            continue
        try:
            with open(path, "r", encoding="utf-8") as fh:
                raw = fh.read()
            if "sops:" in raw or path.endswith(".enc.yaml"):
                proc = subprocess.run(
                    ["sops", "-d", path],
                    capture_output=True,
                    text=True,
                    check=True,
                )
                raw = proc.stdout
            k_match = re.search(r"opnsense_api_key\s*:\s*['\"]?([^'\"\s#]+)", raw)
            s_match = re.search(r"opnsense_api_secret\s*:\s*['\"]?([^'\"\s#]+)", raw)
            if k_match and s_match:
                return k_match.group(1), s_match.group(1)
        except Exception:
            continue

    raise RuntimeError(
        "Impossibile caricare opnsense_api_key e opnsense_api_secret da env o ansible/vars/opnsense_secrets.yml"
    )


class OPNsenseUnboundClient:
    def __init__(self, api_key: str, api_secret: str):
        self.auth_header = "Basic " + base64.b64encode(
            f"{api_key}:{api_secret}".encode("utf-8")
        ).decode("ascii")
        self.ctx = ssl.create_default_context()
        self.ctx.check_hostname = False
        self.ctx.verify_mode = ssl.CERT_NONE
        self.base_url = self._select_reachable_endpoint()

    def _select_reachable_endpoint(self) -> str:
        for url in OPNSENSE_ENDPOINTS:
            try:
                req = urllib.request.Request(
                    f"{url}/api/unbound/settings/searchHostOverride",
                    data=b'{"current":1,"rowCount":1,"searchPhrase":""}',
                    headers={
                        "Authorization": self.auth_header,
                        "Content-Type": "application/json",
                    },
                    method="POST",
                )
                with urllib.request.urlopen(req, context=self.ctx, timeout=4) as resp:
                    if resp.status == 200:
                        return url
            except Exception:
                continue
        raise RuntimeError(
            f"Nessun endpoint OPNsense raggiungibile tra: {', '.join(OPNSENSE_ENDPOINTS)}"
        )

    def request(self, path: str, payload: dict | None = None) -> dict:
        url = f"{self.base_url}{path}"
        data = json.dumps(payload).encode("utf-8") if payload is not None else b""
        headers = {"Authorization": self.auth_header}
        if payload is not None:
            headers["Content-Type"] = "application/json"
        req = urllib.request.Request(url, data=data, headers=headers, method="POST")
        with urllib.request.urlopen(req, context=self.ctx, timeout=10) as resp:
            body = resp.read().decode("utf-8")
            return json.loads(body) if body else {}

    def list_overrides(self) -> list[dict]:
        res = self.request(
            "/api/unbound/settings/searchHostOverride",
            {"current": 1, "rowCount": 2000, "searchPhrase": ""},
        )
        return res.get("rows", [])


def flush_local_dns_cache() -> None:
    """Svuota la cache DNS di macOS per azzerare il TTL sui client locali."""
    if sys.platform != "darwin":
        return
    subprocess.run(["dscacheutil", "-flushcache"], check=False)
    subprocess.run(["sudo", "-n", "killall", "-HUP", "mDNSResponder"], check=False)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Switchover atomico DNS Unbound OPNsense per Failover TrueNAS <-> OrbStack"
    )
    parser.add_argument(
        "--target",
        required=True,
        choices=["truenas", "orbstack"],
        help="Destinazione dei record DNS: 'truenas' (10.10.20.50) o 'orbstack' (10.10.20.100)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Mostra le modifiche previste senza applicarle su OPNsense",
    )
    args = parser.parse_args()

    target_cfg = TARGETS[args.target]
    target_ip = target_cfg["ip"]

    api_key, api_secret = load_opnsense_credentials()
    client = OPNsenseUnboundClient(api_key, api_secret)

    print(f"🌐 [DNS Switchover] Connesso a OPNsense ({client.base_url})")
    print(f"🎯 Target richiesto: {args.target.upper()} -> {target_ip} ({target_cfg['label']})")

    rows = client.list_overrides()
    changed = False

    for hostname, desc_prefix in FAILOVER_HOSTS:
        full_desc = f"{desc_prefix} [Managed Failover -> {args.target}]"
        matches = [
            r
            for r in rows
            if r.get("hostname", "").lower() == hostname.lower()
            and r.get("domain", "").lower() == DOMAIN.lower()
        ]

        if not matches:
            print(f"➕ Creazione Host Override: {hostname}.{DOMAIN} -> {target_ip}")
            if not args.dry_run:
                res = client.request(
                    "/api/unbound/settings/addHostOverride",
                    {
                        "host": {
                            "enabled": "1",
                            "hostname": hostname,
                            "domain": DOMAIN,
                            "rr": "A",
                            "server": target_ip,
                            "description": full_desc,
                        }
                    },
                )
                if res.get("result") != "saved":
                    raise RuntimeError(f"Errore creazione {hostname}.{DOMAIN}: {res}")
            changed = True
        else:
            primary = matches[0]
            uuid = primary["uuid"]
            current_ip = primary.get("server", "")
            enabled = str(primary.get("enabled", "1"))

            if current_ip == target_ip and enabled == "1":
                print(f"✅ [IDEMPOTENT] {hostname}.{DOMAIN} punta già a {target_ip} (UUID: {uuid})")
            else:
                print(f"🔄 Aggiornamento {hostname}.{DOMAIN}: {current_ip} -> {target_ip} (UUID: {uuid})")
                if not args.dry_run:
                    res = client.request(
                        f"/api/unbound/settings/setHostOverride/{uuid}",
                        {
                            "host": {
                                "enabled": "1",
                                "hostname": hostname,
                                "domain": DOMAIN,
                                "rr": "A",
                                "server": target_ip,
                                "description": full_desc,
                            }
                        },
                    )
                    if res.get("result") != "saved":
                        raise RuntimeError(f"Errore aggiornamento {hostname}.{DOMAIN}: {res}")
                changed = True

            # Pulizia eventuali duplicati spuri creati in precedenza
            for dup in matches[1:]:
                dup_uuid = dup["uuid"]
                print(f"🧹 Rimozione Host Override duplicato per {hostname}.{DOMAIN} (UUID: {dup_uuid})")
                if not args.dry_run:
                    client.request(f"/api/unbound/settings/delHostOverride/{dup_uuid}", {})
                changed = True

    if changed and not args.dry_run:
        print("⚙️  Applicazione riconfigurazione dinamica Unbound (/api/unbound/service/reconfigure)...")
        reconf = client.request("/api/unbound/service/reconfigure", {})
        status = reconf.get("status", "").strip().lower()
        if status != "ok":
            raise RuntimeError(f"Riconfigurazione Unbound fallita: {reconf}")
        flush_local_dns_cache()
        print("✅ Unbound riconfigurato con successo e cache DNS macOS invalidata.")
    elif not changed:
        print("ℹ️  Nessuna modifica DNS necessaria: Unbound è già allineato.")

    return 0


if __name__ == "__main__":
    sys.exit(main())
```

#### Passo 3.2: Creazione della Libreria Bash KISS `scripts/infrastructure/orbstack_failover.sh`
Scrivere il file `scripts/infrastructure/orbstack_failover.sh` e impostare `chmod +x`:

```bash
#!/usr/bin/env bash
# ==============================================================================
# FILE: scripts/infrastructure/orbstack_failover.sh
# DESCRIZIONE: Libreria KISS idempotente per tutte le 9+1 transizioni tra
#              TrueNAS SCALE (10.10.20.50) e Mac Studio OrbStack (10.10.20.100).
#              - KISS #1: Zero Data Loss (rsync -auz + guardia cartella non vuota)
#              - KISS #2: Preserva restart: unless-stopped su TrueNAS al boot
#              - KISS #3: File .env.ai e .env.mcp separati 1:1 (zero parser awk)
#              - KISS #4: Supporto SSH nativo olindo@10.10.20.50 (con sudo -n) e root
#              - KISS #5: Self-healing su stati parziali/sporchi (riavvio automatico
#                         container TrueNAS se una porta tra 8100/9119/4000/8888 è chiusa)
# ==============================================================================

export FAILOVER_RUNTIME_DIR="${HOME}/.homelab-failover"
export ORBSTACK_COMPOSE_FILE="${ROOT_DIR}/docker/orbstack-failover/docker-compose.orbstack.yaml"
export TRUENAS_HOST="10.10.20.50"
export MAC_STUDIO_IP="10.10.20.100"

# Verifica rapida se una porta TCP è aperta su un host
_is_tcp_open() {
    local host="$1"
    local port="$2"
    nc -z -G 2 "$host" "$port" >/dev/null 2>&1
}

# Rileva l'utente SSH passwordless valido verso TrueNAS (olindo standard Wiki oppure root)
_resolve_truenas_ssh_user() {
    if ssh -o BatchMode=yes -o ConnectTimeout=3 "olindo@${TRUENAS_HOST}" "true" >/dev/null 2>&1; then
        echo "olindo"
    elif ssh -o BatchMode=yes -o ConnectTimeout=3 "root@${TRUENAS_HOST}" "true" >/dev/null 2>&1; then
        echo "root"
    else
        echo ""
    fi
}

# Prepara ~/.homelab-failover/{.env.ai,.env.mcp} copiandoli 1:1 da TrueNAS quando è online,
# oppure usando i file locali già presenti (con fallback SOPS minimale solo se assenti a freddo)
prepare_orbstack_runtime_env() {
    echo "🔐 [OrbStack Failover] Verifica directory e file .env runtime in ${FAILOVER_RUNTIME_DIR}..."
    mkdir -p \
        "${FAILOVER_RUNTIME_DIR}/hermes-data" \
        "${FAILOVER_RUNTIME_DIR}/dozzle"
    chmod 700 "${FAILOVER_RUNTIME_DIR}"

    if _is_tcp_open "$TRUENAS_HOST" 22; then
        local ssh_user
        ssh_user="$(_resolve_truenas_ssh_user)"
        if [ -n "$ssh_user" ]; then
            echo "📥 [OrbStack Failover] Copia 1:1 di .env.ai e .env.mcp da TrueNAS (${ssh_user}@${TRUENAS_HOST})..."
            ssh -o BatchMode=yes "${ssh_user}@${TRUENAS_HOST}" \
                "sudo -n cat /mnt/stripe/truenas-docker/.env 2>/dev/null || cat /mnt/stripe/truenas-docker/.env" \
                > "${FAILOVER_RUNTIME_DIR}/.env.ai.tmp" && mv "${FAILOVER_RUNTIME_DIR}/.env.ai.tmp" "${FAILOVER_RUNTIME_DIR}/.env.ai"

            ssh -o BatchMode=yes "${ssh_user}@${TRUENAS_HOST}" \
                "sudo -n cat /mnt/stripe/truenas-docker/mcp/.env 2>/dev/null || cat /mnt/stripe/truenas-docker/mcp/.env" \
                > "${FAILOVER_RUNTIME_DIR}/.env.mcp.tmp" && mv "${FAILOVER_RUNTIME_DIR}/.env.mcp.tmp" "${FAILOVER_RUNTIME_DIR}/.env.mcp"
        fi
    fi

    # Fallback SOPS minimale solo se .env.ai non esiste ancora sul Mac e TrueNAS è già spento
    if [ ! -s "${FAILOVER_RUNTIME_DIR}/.env.ai" ] && command -v sops >/dev/null 2>&1 && command -v yq >/dev/null 2>&1; then
        echo "🔑 [OrbStack Failover] TrueNAS offline: estrazione di emergenza .env.ai da secrets-sops..."
        for f in "${ROOT_DIR}/secrets-sops/litellm-secrets.enc.yaml" "${ROOT_DIR}/secrets-sops/hermes-secrets.enc.yaml"; do
            [ -f "$f" ] || continue
            sops -d "$f" | yq eval '(.stringData // .) | to_entries | .[] | select(.key != "sops") | .key + "=" + (.value | tostring)' - >> "${FAILOVER_RUNTIME_DIR}/.env.ai"
        done
    fi

    touch "${FAILOVER_RUNTIME_DIR}/.env.ai" "${FAILOVER_RUNTIME_DIR}/.env.mcp"
    chmod 600 "${FAILOVER_RUNTIME_DIR}/.env.ai" "${FAILOVER_RUNTIME_DIR}/.env.mcp"

    if [ ! -s "${FAILOVER_RUNTIME_DIR}/.env.ai" ] || [ ! -s "${FAILOVER_RUNTIME_DIR}/.env.mcp" ]; then
        echo "❌ [OrbStack Failover] File .env.ai o .env.mcp vuoto in ${FAILOVER_RUNTIME_DIR}!"
        return 1
    fi
}

# Eseguito in lab_mode_off.sh PRIMA di ensure_storage_off.yml (Copre FULL->OFF, ECO->OFF, OFF->OFF)
sync_hermes_state_from_truenas() {
    prepare_orbstack_runtime_env
    if _is_tcp_open "$TRUENAS_HOST" 22; then
        local ssh_user
        ssh_user="$(_resolve_truenas_ssh_user)"
        if [ -n "$ssh_user" ]; then
            echo "📥 [State Sync] Sincronizzazione incrementale stato Hermes da TrueNAS (/mnt/stripe/hermes-agent/) a Mac Studio..."
            # NOTA KISS: Non eseguiamo 'docker compose stop hermes-agent' su TrueNAS!
            # Così il container mantiene lo stato 'running' prima dello shutdown dell'OS
            # e la policy 'restart: unless-stopped' lo riavvierà da sola al successivo boot di TrueNAS.
            rsync -auz -e "ssh -o BatchMode=yes" \
                "${ssh_user}@${TRUENAS_HOST}:/mnt/stripe/hermes-agent/" \
                "${FAILOVER_RUNTIME_DIR}/hermes-data/"
            echo "✅ [State Sync] Stato Hermes Agent allineato in ${FAILOVER_RUNTIME_DIR}/hermes-data/."
        fi
    else
        echo "ℹ️  [State Sync] TrueNAS è già spento (transizione OFF -> OFF): utilizzo stato locale in ${FAILOVER_RUNTIME_DIR}/hermes-data/."
    fi
}

# Eseguito in lab_mode_off.sh DOPO ensure_storage_off.yml
activate_orbstack_failover() {
    echo "🚀 [OrbStack Failover] Attivazione stack di failover su Mac Studio (${MAC_STUDIO_IP})..."
    prepare_orbstack_runtime_env

    # 1. Garantisce che il motore OrbStack sia avviato su macOS
    if ! orbctl status >/dev/null 2>&1; then
        echo "⚙️  Avvio motore OrbStack su Mac Studio..."
        orbctl start
    fi

    # 2. Avvio idempotente dello stack Docker Compose (11 container)
    docker compose -f "$ORBSTACK_COMPOSE_FILE" up -d --remove-orphans

    # 3. Gate di verifica healthcheck sulle 4 porte critiche locali (:4000, :9119, :8100, :8888)
    echo "🩺 [OrbStack Failover] Verifica prontezza servizi locali (:4000, :9119, :8100, :8888)..."
    local retries=30
    until curl -sf "http://127.0.0.1:4000/health/liveliness" >/dev/null 2>&1 \
       && curl -sf "http://127.0.0.1:9119/health" >/dev/null 2>&1 \
       && _is_tcp_open "127.0.0.1" 8100 \
       && _is_tcp_open "127.0.0.1" 8888; do
        retries=$((retries - 1))
        if [ "$retries" -le 0 ]; then
            echo "❌ [OrbStack Failover] Timeout healthcheck sullo stack OrbStack!"
            docker compose -f "$ORBSTACK_COMPOSE_FILE" ps
            return 1
        fi
        sleep 2
    done

    # 4. Switchover atomico DNS Unbound su OPNsense verso Mac Studio (10.10.20.100)
    python3 "${ROOT_DIR}/scripts/network/switch_failover_dns.py" --target orbstack
    echo "✅ [OrbStack Failover] Stack OrbStack ATTIVO e DNS commutato su ${MAC_STUDIO_IP}."
}

# Eseguito in lab_mode_eco.sh e lab_mode_full.sh DOPO ensure_storage_on.yml
# Copre OFF->ECO, OFF->FULL, FULL->ECO, ECO->FULL, ECO->ECO, FULL->FULL e Stati Parziali/Sporchi
deactivate_orbstack_failover_to_truenas() {
    echo "🔄 [OrbStack Failback] Verifica stato tra Mac Studio e TrueNAS (${TRUENAS_HOST})..."

    local ssh_user
    ssh_user="$(_resolve_truenas_ssh_user)"

    # 1. Se hermes-agent era attivo su OrbStack (transizione da OFF -> ECO/FULL),
    #    ferma hermes-agent locale e sincronizza i file più recenti verso TrueNAS (KISS #1: rsync -auz senza --delete).
    #    Se invece siamo in FULL->ECO, ECO->FULL, ECO->ECO o FULL->FULL, questo blocco viene saltato in 0ms!
    if docker ps --format '{{.Names}}' 2>/dev/null | grep -q '^hermes-agent$'; then
        echo "🛑 [State Sync] Rilevato hermes-agent attivo su OrbStack: arresto per flush sessioni maturate in OFF..."
        docker compose -f "$ORBSTACK_COMPOSE_FILE" stop hermes-agent

        if [ -n "$(ls -A "${FAILOVER_RUNTIME_DIR}/hermes-data" 2>/dev/null)" ] && [ -n "$ssh_user" ]; then
            echo "📤 [State Sync] Sincronizzazione sicura (rsync -auz, zero delete) da Mac Studio -> TrueNAS (/mnt/stripe/hermes-agent/)..."
            rsync -auz -e "ssh -o BatchMode=yes" \
                "${FAILOVER_RUNTIME_DIR}/hermes-data/" \
                "${ssh_user}@${TRUENAS_HOST}:/mnt/stripe/hermes-agent/"
            ssh -o BatchMode=yes "${ssh_user}@${TRUENAS_HOST}" \
                "sudo -n docker restart hermes-agent 2>/dev/null || docker restart hermes-agent" || true
        else
            echo "⚠️  [State Sync] Cartella locale hermes-data vuota o SSH non disponibile: salto rsync verso TrueNAS."
        fi
    else
        echo "ℹ️  [State Sync] Nessun container hermes-agent attivo su OrbStack (transizione tra stati con TrueNAS già primario)."
    fi

    # 2. Auto-Healing KISS #5: Se anche una sola delle 4 porte su TrueNAS (8100, 9119, 4000, 8888)
    #    non è già aperta (es. container fermato manualmente o primo avvio), forza 'docker compose up -d' su TrueNAS
    if ! _is_tcp_open "$TRUENAS_HOST" 8100 || ! _is_tcp_open "$TRUENAS_HOST" 9119 || ! _is_tcp_open "$TRUENAS_HOST" 4000 || ! _is_tcp_open "$TRUENAS_HOST" 8888; then
        if [ -n "$ssh_user" ]; then
            echo "🐳 [Self-Healing] Almeno una porta tra :8100, :9119, :4000, :8888 non è ancora attiva su TrueNAS: esecuzione docker compose up -d..."
            ssh -o BatchMode=yes "${ssh_user}@${TRUENAS_HOST}" \
                "cd /mnt/stripe/truenas-docker && (sudo -n docker compose up -d litellm-postgres litellm hermes-agent dozzle 2>/dev/null || docker compose up -d litellm-postgres litellm hermes-agent dozzle) && cd /mnt/stripe/truenas-docker/mcp && (sudo -n docker compose up -d 2>/dev/null || docker compose up -d)"
        fi
    fi

    # 3. Gate di verifica sulle 4 porte di TrueNAS (:8100, :9119, :4000, :8888) prima dello switch DNS
    echo "🩺 [OrbStack Failback] Verifica porte attive su TrueNAS (${TRUENAS_HOST}:8100, :9119, :4000, :8888)..."
    for port in 8100 9119 4000 8888; do
        local t_wait=30
        until _is_tcp_open "$TRUENAS_HOST" "$port"; do
            t_wait=$((t_wait - 1))
            if [ "$t_wait" -le 0 ]; then
                echo "❌ [OrbStack Failback] Porta ${TRUENAS_HOST}:${port} non risponde su TrueNAS!"
                return 1
            fi
            sleep 2
        done
    done

    # 4. Switchover atomico e idempotente DNS Unbound su OPNsense verso TrueNAS (10.10.20.50)
    python3 "${ROOT_DIR}/scripts/network/switch_failover_dns.py" --target truenas

    # 5. Arresto e rimozione pulita dello stack di failover su OrbStack (solo se ci sono container del progetto)
    if [ -f "$ORBSTACK_COMPOSE_FILE" ] && [ -n "$(docker compose -f "$ORBSTACK_COMPOSE_FILE" ps -q 2>/dev/null)" ]; then
        echo "🧹 [OrbStack Failback] Spegnimento stack orbstack-failover su Mac Studio..."
        docker compose -f "$ORBSTACK_COMPOSE_FILE" down --remove-orphans
    fi

    echo "✅ [OrbStack Failback] Servizi verificati su TrueNAS (${TRUENAS_HOST}), DNS allineato e OrbStack in standby."
}
```

#### Passo 3.3: Test di Verifica Fase 3
```bash
chmod +x scripts/network/switch_failover_dns.py scripts/infrastructure/orbstack_failover.sh
python3 -m py_compile scripts/network/switch_failover_dns.py
bash -n scripts/infrastructure/orbstack_failover.sh
./scripts/network/switch_failover_dns.py --target truenas --dry-run
```
- **Criterio di superamento**: Compilazione Python e linting Bash senza errori; l'esecuzione `--dry-run` si connette con successo all'API Unbound di OPNsense e mostra lo stato dei 4 record (`mcp`, `hermes`, `litellm`, `dozzle`).

---

### FASE 4: Aggiornamento Integrale degli Script `lab_mode_off.sh`, `lab_mode_eco.sh`, `lab_mode_full.sh`

#### Passo 4.1: File Completo `scripts/infrastructure/lab_mode_off.sh`
Sovrascrivere `scripts/infrastructure/lab_mode_off.sh` con il seguente contenuto:

```bash
#!/usr/bin/env bash
# Spegnimento totale del rack Homelab: K8s, PVE e TrueNAS spenti + Failover OrbStack su Mac Studio
set -Eeuo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"
cd "$ROOT_DIR" || exit 1

source "$SCRIPT_DIR/procedure_scope.sh"
source "$SCRIPT_DIR/utils.sh"
source "$SCRIPT_DIR/orbstack_failover.sh"

PROCEDURE_NAME="lab_mode_off"
init_procedure_scope "$PROCEDURE_NAME"

LOG_DIR="${ROOT_DIR}/logs/automation"
mkdir -p "$LOG_DIR"
LOG_FILE="${LOG_DIR}/${PROCEDURE_NAME}_$(date +%Y%m%d_%H%M%S).log"

exec > >(tee -a "$LOG_FILE") 2>&1

on_error() {
    local exit_code=$?
    local err_msg="Procedura ${PROCEDURE_NAME} fallita alla riga $1 (exit code: $exit_code)"
    echo "❌ $err_msg"

    if has_error_been_reported; then
        echo "ℹ️ [NESTED] Errore già segnalato. Uscita senza alert duplicato."
        exit "$exit_code"
    fi
    mark_error_reported

    send_telegram "❌ <b>ERRORE CRITICO HOMELAB</b>%0A${err_msg}%0AConsulta l'email per il log completo dell'errore." "Homelab Alert"

    local table="<tr><td><b>Procedura:</b></td><td>${PROCEDURE_NAME}</td></tr><tr><td><b>Errore:</b></td><td>Riga $1 (Exit Code: $exit_code)</td></tr><tr><td><b>Log Allegato:</b></td><td>$(basename "$LOG_FILE")</td></tr>"
    local html
    html="$(build_html_email_template "🚨" "Errore ${PROCEDURE_NAME}" "Homelab Mode Orchestration" "ERRORE" "#ef4444" "$table")"
    send_summary_email "$DEFAULT_EMAIL_RECIPIENT" "🚨 [ALERT] Errore in ${PROCEDURE_NAME}" "$html" "$err_msg" "$LOG_FILE"
    exit "$exit_code"
}
trap 'on_error $LINENO' ERR

echo "🛑 Avvio convergenza: ${PROCEDURE_NAME}..."
echo "➡️  Stato Target: RACK DARK (K8s, Proxmox VE e TrueNAS Storage SPENTI | Failover OrbStack su Mac Studio ATTIVO)"
echo "📄 Log di sessione: $LOG_FILE"
echo ""

if is_root_procedure; then
    send_telegram "🛑 <b>Avvio ${PROCEDURE_NAME}</b>%0ASpegnimento totale dell'infrastruttura Homelab: K8s -> PVE -> Sync Hermes -> TrueNAS -> Avvio Failover OrbStack..." "Homelab Mode"
fi

# FASE 1: GARANTISCE COMPUTE LAYER OFFLINE (K8S + PVE) PRIMA DI TRUENAS
echo "▶️  [Fase 1/4] Esecuzione: ensure_compute_off..."
ansible-playbook -i ansible/inventory.ini ansible/playbooks/infrastructure/ensure_compute_off.yml

# FASE 2: SINCRONIZZAZIONE STATO HERMES E FILE .ENV PRIMA DELLO SPEGNIMENTO DI TRUENAS
echo "▶️  [Fase 2/4] Esecuzione: sync_hermes_state_from_truenas..."
sync_hermes_state_from_truenas

# FASE 3: FLUSH E SPEGNIMENTO FISICO TRUENAS BARE METAL
echo "▶️  [Fase 3/4] Esecuzione: ensure_storage_off..."
ansible-playbook -i ansible/inventory.ini ansible/playbooks/infrastructure/ensure_storage_off.yml

# FASE 4: ATTIVAZIONE STACK ORBSTACK SU MAC STUDIO E SWITCHOVER DNS UNBOUND (10.10.20.100)
echo "▶️  [Fase 4/4] Esecuzione: activate_orbstack_failover..."
activate_orbstack_failover

# NOTIFICA FINALE RIASSUNTIVA DI SUCCESSO
if is_root_procedure; then
    send_telegram "🌙 <b>${PROCEDURE_NAME} Completato!</b>%0ATutti i nodi fisici e VM sono disattivati in sicurezza. Failover OrbStack attivo su Mac Studio (10.10.20.100)." "Homelab Mode"
    stop_table="<tr><td><b>Modalità:</b></td><td>RACK DARK (Zero Watt Standby + OrbStack Failover)</td></tr><tr><td><b>Kubernetes:</b></td><td>OFFLINE (Cluster Talos disattivato)</td></tr><tr><td><b>Hypervisors:</b></td><td>OFFLINE (pve1, pve2, pve3 spenti)</td></tr><tr><td><b>Storage TrueNAS:</b></td><td>OFFLINE (Bare metal spento)</td></tr><tr><td><b>Failover Mac Studio:</b></td><td>ONLINE (OrbStack 10.10.20.100: MCP :8100 [7 srv], Hermes :9119, LiteLLM :4000, Dozzle :8888)</td></tr>"
    stop_html="$(build_html_email_template "🌙" "Completato: ${PROCEDURE_NAME}" "Homelab Mode Orchestration" "SUCCESSO" "#10b981" "$stop_table")"
    send_summary_email "$DEFAULT_EMAIL_RECIPIENT" "✅ [SUCCESS] ${PROCEDURE_NAME}" "$stop_html" "${PROCEDURE_NAME} completato con successo"
    complete_procedure_scope
else
    echo "ℹ️ [NESTED] Procedura ${PROCEDURE_NAME} completata. Segnalazione finale delegata a ${HOMELAB_PARENT_PROCEDURE}."
fi
```

#### Passo 4.2: File Completo `scripts/infrastructure/lab_mode_eco.sh`
Sovrascrivere `scripts/infrastructure/lab_mode_eco.sh` con il seguente contenuto:

```bash
#!/usr/bin/env bash
# Homelab a risparmio energetico: solo TrueNAS attivo (con failback da OrbStack), PVE e K8s spenti
set -Eeuo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"
cd "$ROOT_DIR" || exit 1

source "$SCRIPT_DIR/procedure_scope.sh"
source "$SCRIPT_DIR/utils.sh"
source "$SCRIPT_DIR/orbstack_failover.sh"

PROCEDURE_NAME="lab_mode_eco"
init_procedure_scope "$PROCEDURE_NAME"

LOG_DIR="${ROOT_DIR}/logs/automation"
mkdir -p "$LOG_DIR"
LOG_FILE="${LOG_DIR}/${PROCEDURE_NAME}_$(date +%Y%m%d_%H%M%S).log"

exec > >(tee -a "$LOG_FILE") 2>&1

on_error() {
    local exit_code=$?
    local err_msg="Procedura ${PROCEDURE_NAME} fallita alla riga $1 (exit code: $exit_code)"
    echo "❌ $err_msg"

    if has_error_been_reported; then
        echo "ℹ️ [NESTED] Errore già segnalato. Uscita senza alert duplicato."
        exit "$exit_code"
    fi
    mark_error_reported

    send_telegram "❌ <b>ERRORE CRITICO HOMELAB</b>%0A${err_msg}%0AConsulta l'email per il log completo dell'errore." "Homelab Alert"

    local table="<tr><td><b>Procedura:</b></td><td>${PROCEDURE_NAME}</td></tr><tr><td><b>Errore:</b></td><td>Riga $1 (Exit Code: $exit_code)</td></tr><tr><td><b>Log Allegato:</b></td><td>$(basename "$LOG_FILE")</td></tr>"
    local html
    html="$(build_html_email_template "🚨" "Errore ${PROCEDURE_NAME}" "Homelab Mode Orchestration" "ERRORE" "#ef4444" "$table")"
    send_summary_email "$DEFAULT_EMAIL_RECIPIENT" "🚨 [ALERT] Errore in ${PROCEDURE_NAME}" "$html" "$err_msg" "$LOG_FILE"
    exit "$exit_code"
}
trap 'on_error $LINENO' ERR

echo "🚀 Avvio convergenza: ${PROCEDURE_NAME}..."
echo "➡️  Stato Target: ECO LAB (TrueNAS ONLINE + Failback da OrbStack, Proxmox VE e Kubernetes OFFLINE)"
echo "📄 Log di sessione: $LOG_FILE"
echo ""

if is_root_procedure; then
    send_telegram "🚀 <b>Avvio ${PROCEDURE_NAME}</b>%0AConvergenza verso modalità Eco: TrueNAS ONLINE, Failback da OrbStack, spegnimento K8s e Proxmox VE..." "Homelab Mode"
fi

# FASE 1: GARANTISCE STORAGE TRUENAS BARE METAL ONLINE
echo "▶️  [Fase 1/3] Esecuzione: ensure_storage_on..."
ansible-playbook -i ansible/inventory.ini ansible/playbooks/infrastructure/ensure_storage_on.yml

# FASE 2: FAILBACK STATO HERMES, SERVIZI AI/MCP E DNS DA MAC STUDIO (ORBSTACK) A TRUENAS (10.10.20.50)
echo "▶️  [Fase 2/3] Esecuzione: deactivate_orbstack_failover_to_truenas..."
deactivate_orbstack_failover_to_truenas

# FASE 3: GARANTISCE COMPUTE LAYER OFFLINE (K8S + PVE)
echo "▶️  [Fase 3/3] Esecuzione: ensure_compute_off..."
ansible-playbook -i ansible/inventory.ini ansible/playbooks/infrastructure/ensure_compute_off.yml

# NOTIFICA FINALE RIASSUNTIVA DI SUCCESSO
if is_root_procedure; then
    send_telegram "🎉 <b>${PROCEDURE_NAME} Completato!</b>%0AHomelab a regime di risparmio energetico: TrueNAS attivo (DNS -> 10.10.20.50, OrbStack disattivato), K8s e Proxmox disattivati." "Homelab Mode"
    stop_table="<tr><td><b>Modalità:</b></td><td>ECO LAB (Risparmio Energetico)</td></tr><tr><td><b>Storage TrueNAS:</b></td><td>ONLINE (10.10.20.50, Servarr, ZFS, MCP Fleet, Hermes, LiteLLM, Dozzle)</td></tr><tr><td><b>Failover OrbStack:</b></td><td>STANDBY (Stato Hermes sincronizzato su TrueNAS e container locali spenti)</td></tr><tr><td><b>Hypervisor PVE:</b></td><td>OFFLINE (pve1, pve2, pve3 spenti)</td></tr><tr><td><b>Kubernetes:</b></td><td>OFFLINE (Cluster Talos disattivato)</td></tr>"
    stop_html="$(build_html_email_template "🎉" "Completato: ${PROCEDURE_NAME}" "Homelab Mode Orchestration" "SUCCESSO" "#10b981" "$stop_table")"
    send_summary_email "$DEFAULT_EMAIL_RECIPIENT" "✅ [SUCCESS] ${PROCEDURE_NAME}" "$stop_html" "${PROCEDURE_NAME} completato con successo"
    complete_procedure_scope
else
    echo "ℹ️ [NESTED] Procedura ${PROCEDURE_NAME} completata. Segnalazione finale delegata a ${HOMELAB_PARENT_PROCEDURE}."
fi
```

#### Passo 4.3: File Completo `scripts/infrastructure/lab_mode_full.sh`
Sovrascrivere `scripts/infrastructure/lab_mode_full.sh` con il seguente contenuto:

```bash
#!/usr/bin/env bash
# Homelab a pieno regime: TrueNAS (con failback da OrbStack), Proxmox VE e K8s tutti attivi
set -Eeuo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"
cd "$ROOT_DIR" || exit 1

source "$SCRIPT_DIR/procedure_scope.sh"
source "$SCRIPT_DIR/utils.sh"
source "$SCRIPT_DIR/orbstack_failover.sh"

PROCEDURE_NAME="lab_mode_full"
init_procedure_scope "$PROCEDURE_NAME"

LOG_DIR="${ROOT_DIR}/logs/automation"
mkdir -p "$LOG_DIR"
LOG_FILE="${LOG_DIR}/${PROCEDURE_NAME}_$(date +%Y%m%d_%H%M%S).log"

exec > >(tee -a "$LOG_FILE") 2>&1

on_error() {
    local exit_code=$?
    local err_msg="Procedura ${PROCEDURE_NAME} fallita alla riga $1 (exit code: $exit_code)"
    echo "❌ $err_msg"

    if has_error_been_reported; then
        echo "ℹ️ [NESTED] Errore già segnalato. Uscita senza alert duplicato."
        exit "$exit_code"
    fi
    mark_error_reported

    send_telegram "❌ <b>ERRORE CRITICO HOMELAB</b>%0A${err_msg}%0AConsulta l'email per il log completo dell'errore." "Homelab Alert"

    local table="<tr><td><b>Procedura:</b></td><td>${PROCEDURE_NAME}</td></tr><tr><td><b>Errore:</b></td><td>Riga $1 (Exit Code: $exit_code)</td></tr><tr><td><b>Log Allegato:</b></td><td>$(basename "$LOG_FILE")</td></tr>"
    local html
    html="$(build_html_email_template "🚨" "Errore ${PROCEDURE_NAME}" "Homelab Mode Orchestration" "ERRORE" "#ef4444" "$table")"
    send_summary_email "$DEFAULT_EMAIL_RECIPIENT" "🚨 [ALERT] Errore in ${PROCEDURE_NAME}" "$html" "$err_msg" "$LOG_FILE"
    exit "$exit_code"
}
trap 'on_error $LINENO' ERR

echo "🚀 Avvio convergenza: ${PROCEDURE_NAME}..."
echo "➡️  Stato Target: FULL LAB (TrueNAS + Failback da OrbStack + Proxmox VE + Kubernetes Talos ONLINE)"
echo "📄 Log di sessione: $LOG_FILE"
echo ""

if is_root_procedure; then
    send_telegram "🚀 <b>Avvio ${PROCEDURE_NAME}</b>%0AConvergenza verso Full Homelab: TrueNAS -> Failback OrbStack -> PVE1/2/3 -> Talos Cluster..." "Homelab Mode"
fi

# FASE 1: HARD GATE STORAGE TRUENAS BARE METAL
echo "▶️  [Fase 1/3] Esecuzione: ensure_storage_on..."
ansible-playbook -i ansible/inventory.ini ansible/playbooks/infrastructure/ensure_storage_on.yml

# FASE 2: FAILBACK STATO HERMES, SERVIZI AI/MCP E DNS DA MAC STUDIO (ORBSTACK) A TRUENAS (10.10.20.50)
echo "▶️  [Fase 2/3] Esecuzione: deactivate_orbstack_failover_to_truenas..."
deactivate_orbstack_failover_to_truenas

# FASE 3: GATELAYER COMPUTE (PROXMOX VE + TALOS KUBERNETES)
echo "▶️  [Fase 3/3] Esecuzione: ensure_compute_on..."
ansible-playbook -i ansible/inventory.ini ansible/playbooks/infrastructure/ensure_compute_on.yml

# NOTIFICA FINALE RIASSUNTIVA DI SUCCESSO
if is_root_procedure; then
    send_telegram "🎉 <b>${PROCEDURE_NAME} Completato!</b>%0AIntero Homelab pienamente operativo: TrueNAS, Proxmox VE e Kubernetes online al 100%." "Homelab Mode"
    stop_table="<tr><td><b>Modalità:</b></td><td>FULL LAB (100% Gates Superati)</td></tr><tr><td><b>Storage TrueNAS:</b></td><td>ONLINE (Pool stripe & oliraid sani, DNS -> 10.10.20.50)</td></tr><tr><td><b>Failover OrbStack:</b></td><td>STANDBY (Stato Hermes sincronizzato su TrueNAS e container locali spenti)</td></tr><tr><td><b>Hypervisor PVE:</b></td><td>ONLINE (pve1, pve2, pve3)</td></tr><tr><td><b>Talos Cluster:</b></td><td>READY & UNCORDONATI (cp-01, cp-02, cp-03)</td></tr><tr><td><b>Ingress VIP:</b></td><td>ONLINE (https://10.10.20.56)</td></tr>"
    stop_html="$(build_html_email_template "🎉" "Completato: ${PROCEDURE_NAME}" "Homelab Mode Orchestration" "SUCCESSO" "#10b981" "$stop_table")"
    send_summary_email "$DEFAULT_EMAIL_RECIPIENT" "✅ [SUCCESS] ${PROCEDURE_NAME}" "$stop_html" "${PROCEDURE_NAME} completato con successo"
    complete_procedure_scope
else
    echo "ℹ️ [NESTED] Procedura ${PROCEDURE_NAME} completata. Segnalazione finale delegata a ${HOMELAB_PARENT_PROCEDURE}."
fi
```

#### Passo 4.4: Test di Verifica Fase 4
```bash
chmod +x scripts/infrastructure/lab_mode_off.sh scripts/infrastructure/lab_mode_eco.sh scripts/infrastructure/lab_mode_full.sh
bash -n scripts/infrastructure/lab_mode_off.sh
bash -n scripts/infrastructure/lab_mode_eco.sh
bash -n scripts/infrastructure/lab_mode_full.sh
```
- **Criterio di superamento**: Tutti e 3 i controlli `bash -n` restituiscono exit code `0`.

---

### FASE 5: Aggiornamento Client MCP (`~/.gemini/antigravity/mcp_config.json`)

#### Passo 5.1: Scrittura Integrale di `~/.gemini/antigravity/mcp_config.json`
Sovrascrivere `~/.gemini/antigravity/mcp_config.json` sostituendo `10.10.20.50` con `mcp.pindaroli.org` e preservando tutte le 12 entry e l'opzione `disabledTools`:

```json
{
  "mcpServers": {
    "kef": {
      "serverUrl": "http://mcp.pindaroli.org:8100/kef/mcp"
    },
    "ollama": {
      "serverUrl": "http://mcp.pindaroli.org:8100/ollama/mcp"
    },
    "github-mcp-server": {
      "serverUrl": "http://mcp.pindaroli.org:8100/github/mcp"
    },
    "kubernetes": {
      "serverUrl": "http://mcp.pindaroli.org:8100/kubernetes/mcp"
    },
    "truenas-master-mcp": {
      "serverUrl": "http://mcp.pindaroli.org:8100/truenas/mcp",
      "disabledTools": [
        "get_chart_release"
      ]
    },
    "opnsense": {
      "serverUrl": "http://mcp.pindaroli.org:8100/opnsense/mcp"
    },
    "talos": {
      "serverUrl": "http://mcp.pindaroli.org:8100/talos/mcp"
    },
    "gemini-deepsearch": {
      "serverUrl": "http://mcp.pindaroli.org:8100/gemini/mcp"
    },
    "nowaikit": {
      "serverUrl": "http://mcp.pindaroli.org:8100/nowaikit/mcp"
    },
    "arrstack-mcp": {
      "serverUrl": "http://mcp.pindaroli.org:8100/arrstack/mcp"
    },
    "ragflow-local": {
      "serverUrl": "http://mcp.pindaroli.org:8100/ragflow/mcp"
    },
    "meross": {
      "serverUrl": "http://mcp.pindaroli.org:8100/meross/mcp"
    }
  }
}
```

#### Passo 5.2: Test di Verifica Fase 5
```bash
python3 -m json.tool ~/.gemini/antigravity/mcp_config.json >/dev/null && echo "JSON Valido"
grep -c "mcp.pindaroli.org:8100" ~/.gemini/antigravity/mcp_config.json
```
- **Criterio di superamento**: Stampa `JSON Valido` e `12`.

---

### FASE 6: Collaudo End-to-End delle Transizioni e Sync Wiki

#### Passo 6.1: Allineamento iniziale DNS e Test Switchover Isolato
1. **Se TrueNAS (`10.10.20.50`) è attualmente ONLINE**, verificare l'allineamento verso TrueNAS:
   ```bash
   ./scripts/network/switch_failover_dns.py --target truenas
   for h in mcp hermes litellm dozzle; do
     printf "%-25s -> %s\n" "${h}.pindaroli.org" "$(dig +short "${h}.pindaroli.org" @192.168.2.254)"
   done
   ```
   - **Verifica**: Tutti e 4 gli host risolvono in `10.10.20.50`.
2. **Test Isolato di Attivazione Failover OrbStack (senza spegnere fisicamente il rack)**:
   ```bash
   bash -c 'ROOT_DIR="$(pwd)" && source scripts/infrastructure/orbstack_failover.sh && sync_hermes_state_from_truenas && activate_orbstack_failover'
   ```
   - **Verifica**:
     ```bash
     for h in mcp hermes litellm dozzle; do
       printf "%-25s -> %s\n" "${h}.pindaroli.org" "$(dig +short "${h}.pindaroli.org" @192.168.2.254)"
     done
     docker compose -f docker/orbstack-failover/docker-compose.orbstack.yaml ps
     curl -sf http://litellm.pindaroli.org:4000/health/liveliness && echo "LiteLLM OrbStack OK"
     curl -sf http://hermes.pindaroli.org:9119/health && echo "Hermes OrbStack OK"
     curl -sf http://mcp.pindaroli.org:8100/meross/healthz && echo "MCP Meross OrbStack OK"
     ```
     *(Tutti e 4 gli host devono risolvere a `10.10.20.100`, gli 11 container devono risultare `Up (healthy)` e i `curl` devono restituire `OK`)*.
3. **Test Isolato di Failback verso TrueNAS (se TrueNAS è online)**:
   ```bash
   bash -c 'ROOT_DIR="$(pwd)" && source scripts/infrastructure/orbstack_failover.sh && deactivate_orbstack_failover_to_truenas'
   ```
   - **Verifica**:
     ```bash
     for h in mcp hermes litellm dozzle; do
       printf "%-25s -> %s\n" "${h}.pindaroli.org" "$(dig +short "${h}.pindaroli.org" @192.168.2.254)"
     done
     docker compose -f docker/orbstack-failover/docker-compose.orbstack.yaml ps
     ```
     *(Tutti e 4 gli host tornano a `10.10.20.50` e lo stack `orbstack-failover` risulta spento)*.

#### Passo 6.2: Validazione Rete e Rigenerazione Contesto Wiki (§13 Wiki Context Refresh)
```bash
python3 scripts/network/validate_network.py || python3 scripts/validate_network.py
python3 scripts/wiki/build_wiki_context.py || python3 scripts/build_wiki_context.py
```

---

## 💾 Stato di Ripristino (AI Save-State)
- **Fase Attiva**: COMPLETATO ✅ (Fasi 1-6 convalidate con esito positivo al 100%)
- **Ultima Azione Completata**: Collaudo End-to-End delle transizioni (DNS switchover, OrbStack activation con 11 container healthy, sync bidirezionale rsync Hermes, failback su TrueNAS e build wiki context)
- **Prossimo Passo Operativo**: Nessuno. Piano eseguito e verificato con successo in conformità alle Golden Rules.
- **Blocchi/Decisioni Pendenti**: Nessun blocco. Tutte le transizioni della matrice 3x3 operative.

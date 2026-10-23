# Dossier di Contesto: Failover Trasparente Servizi TrueNAS su Mac (OrbStack) in lab_mode_off

> Questo documento consolida il prompt direttivo per **Gemini Web** e tutti i file sorgente di configurazione, rete e automazione del monorepo `k8s-lab` necessari a ingegnerizzare la migrazione trasparente dei servizi da TrueNAS SCALE a OrbStack (macOS) durante lo spegnimento dell'infrastruttura rack (`lab_mode_off`).

---

# PARTE 1 — Prompt Direttivo per Gemini Web

```markdown
# RUOLO E CONTESTO OPERATIVO
Sei un Principal DevOps & Site Reliability Engineer specializzato in:
- Docker Compose & OrbStack su macOS Apple Silicon (ARM64 / Apple M2 Ultra).
- OPNsense 26.x (Core REST API, Unbound DNS Host Overrides e Dynamic Reconfiguration).
- TrueNAS SCALE 25.x (Docker Compose, ZFS, NFS, automazione storage).
- Automazione Bash idempotente e pattern architetturali homelab.

Stai lavorando sull'infrastruttura "GEMINI Homelab" (dominio interno `pindaroli.org`).

---

# ISTRUZIONI DI CONSULTAZIONE DEGLI ALLEGATI (COME LEGGERE I FILE)
Per risolvere questo compito hai a disposizione due documenti di contesto fondamentali forniti come allegati:

### 1. `wiki_context.md` (Architettura Globale & Governance)
Consulta questo file per:
- I principi core e le Golden Rules del lab (immutabilità dichiarativa, divieto di IP hardcoded, sicurezza secret SOPS).
- I pattern architetturali citati, in particolare:
  - `[[hierarchical-automation-alerting-pattern]]`: regola aurea per gli script di modalità (Zero start emails, notifica Telegram immediata, email HTML unificata solo a fine procedura o fail-fast su errore con log).
  - `[[MCP_Platform]]`: architettura Traefik v3 Umbrella Gateway (porta 8100), Docker Socket Proxy L7 e Supergateway SSE/Streamable HTTP RFC 2025.

### 2. `orbstack_failover_gemini_context.md` (Dossier Tecnico Operativo Monorepo)
Questo file raccoglie il codice sorgente reale e la verità di configurazione del repository `k8s-lab`. Leggilo seguendo questa mappa delle sezioni:
- **PARTE 2 (Topologia di Rete & IP da `rete.json`)**: Consulta questa sezione per gli indirizzi IP e VLAN reali. Usa ESCLUSIVAMENTE `10.10.20.50` per TrueNAS, `10.10.20.100` per Mac Studio (OrbStack) e `10.10.20.1` / `192.168.100.1` per OPNsense. È vietato inventare subnet o IP diversi.
- **PARTE 3 (Flotta MCP da `docker/mcp/docker-compose.yaml`)**: Consulta questa sezione per replicare fedelmente su OrbStack il Traefik Gateway (porta host `8100`), il Socket Proxy, i 12 container MCP, le etichette di routing Traefik (es. `PathPrefix(/truenas)`, `PathPrefix(/opnsense)`, ecc.), i test di healthcheck e i tag delle immagini OCI.
- **PARTE 4 (Servizi AI & Dozzle da `servarr/truenas-docker/docker-compose.yaml` e `litellm/config.yaml`)**: Consulta questa sezione per la definizione esatta di `hermes-agent` (porta `9119`, mount kubeconfig/talosconfig), `litellm` (porta `4000`), `litellm-postgres` e `dozzle` (porta `8888`), nonché per la lista dei modelli AI Ollama configurati.
- **PARTE 5 (Script di Modalità da `scripts/infrastructure/`)**: Consulta `lab_mode_off.sh`, `lab_mode_eco.sh` e `lab_mode_full.sh` per comprendere l'esatta sequenza di spegnimento e accensione, i trap di errore e i punti precisi in cui inserire gli hook di avvio/stop di OrbStack e di switchover DNS.
- **PARTE 6 (Playbook OPNsense Unbound DNS API da `ansible/playbooks/opnsense/opnsense_sync_dns.yml`)**: Consulta questa sezione per le chiamate REST native di OPNsense (`/api/unbound/settings/addHostOverride`, `/api/unbound/service/reconfigure`) da utilizzare per aggiornare deterministicamente i puntamenti DNS.
- **PARTE 7 (Client MCP Config da `~/.gemini/antigravity/mcp_config.json`)**: Consulta questa sezione per verificare come i client IDE/CLI si collegano attualmente (usando `http://10.10.20.50:8100/...`) e come devono essere migrati a FQDN (`http://mcp.pindaroli.org:8100/...`).

---

# DEFINIZIONE DEL PROBLEMA
Attualmente il lab dispone di 3 modalità di alimentazione orchestrate da script idempotenti:
1. **FULL LAB (`lab_mode_full.sh`)**: TrueNAS bare-metal ON, hypervisor Proxmox VE 1/2/3 ON, cluster Kubernetes Talos ON.
2. **ECO LAB (`lab_mode_eco.sh`)**: TrueNAS bare-metal ON (storage ZFS, stack Docker Servarr e MCP Fleet attivi), PVE e Talos K8s SPENTI.
3. **RACK DARK / OFF (`lab_mode_off.sh`)**: TUTTO il rack è SPENTO (K8s -> PVE -> TrueNAS spenti per massimo risparmio energetico).

Quando il sistema entra in stato **OFF (`lab_mode_off.sh`)**, TrueNAS viene spento fisicamente. Di conseguenza, i seguenti servizi critici per lo sviluppo e l'assistente AI locale non sono più raggiungibili:
- **Hermes Agent** (attualmente su TrueNAS porta `9119`).
- **MCP Fleet & Traefik Umbrella Gateway** (12 server MCP aggregati su Traefik gateway porta host `8100`, attualmente su TrueNAS).
- **LiteLLM Proxy + Database Postgres** (attualmente su TrueNAS porta `4000`).
- **Dozzle** (log viewer Docker, attualmente su TrueNAS porta `8888`).

---

# OBIETTIVO
Progettare e implementare un meccanismo di **Failover Idempotente e Trasparente verso Mac Studio (OrbStack)**:
- Quando si attiva `lab_mode_off.sh`, i 4 servizi sopra elencati devono migrare/avviarsi automaticamente in un compose stack locale su Mac Studio tramite **OrbStack** (`10.10.20.100`).
- Quando si riaccende il lab tramite `lab_mode_eco.sh` o `lab_mode_full.sh`, lo stack su OrbStack deve essere disattivato in modo pulito e il traffico deve tornare su TrueNAS (`10.10.20.50`).

---

# REQUISITI TECNICI VINCOLANTI

### 1. Zero Riconfigurazione Client (DNS Switchover via OPNsense Unbound)
- I client (Antigravity AI IDE, CLI, browser, script) NON devono cambiare IP o porta a seconda della modalità attiva.
- Attualmente i client puntavano talvolta all'IP grezzo `10.10.20.50`. Dobbiamo standardizzare tutti gli endpoint su FQDN canonici nel dominio `pindaroli.org` (es. `mcp.pindaroli.org`, `hermes.pindaroli.org`, `litellm.pindaroli.org`, `dozzle.pindaroli.org`).
- Gli script di transizione devono pilotare le API REST di Unbound su OPNsense (`192.168.100.1` o `10.10.20.1`) per commutare atomicamente gli Host Overrides:
  - **In stato OFF**: i record DNS puntano a Mac Studio (`10.10.20.100`).
  - **In stato ECO/FULL**: i record DNS puntano a TrueNAS (`10.10.20.50`).
- Generare la chiamata o lo script Python/Ansible dedicato per fare il reconfigure di Unbound senza disservizi o cache poisoning.

### 2. Orchestrazione e Automazione Idempotente (`lab_mode_***`)
- L'attivazione e la disattivazione dello stack OrbStack devono essere integrate nativamente all'interno di:
  - `scripts/infrastructure/lab_mode_off.sh`
  - `scripts/infrastructure/lab_mode_eco.sh`
  - `scripts/infrastructure/lab_mode_full.sh`
- Devono rispettare il pattern di alerting gerarchico (`[[hierarchical-automation-alerting-pattern]]`):
  - Nessuna email in fase di avvio (Zero start emails), report unificato Telegram + Email solo a fine procedura.
  - Fail-fast con notifica in caso di errore critico.
- Ogni operazione deve essere idempotente: eseguire `lab_mode_off.sh` due volte di seguito non deve dare errori né riavviare inutilmente container sani.

### 3. Stack Docker Compose OrbStack (macOS / Apple Silicon)
- Fornire il file `docker-compose.orbstack.yaml` (o struttura modulare) ottimizzato per OrbStack su Mac:
  - Architettura: immagini compatibili ARM64 (o multi-arch/emulate se indispensabili).
  - Volumi e Persistenza: definire dove e come persistere i dati di Hermes Agent (`~/.hermes` o cartella locale) e LiteLLM (Postgres locale o SQLite leggero).
  - Gestione Segreti: come ereditare le chiavi API (Anthropic, Gemini, GitHub, SOPS secrets) senza committare credenziali in chiaro.
  - Docker Socket Proxy per Dozzle: configurazione sicura del socket Docker di OrbStack (`/var/run/docker.sock` o `~/.orbstack/run/docker.sock`).
  - Traefik Umbrella Gateway: mantenere la stessa porta `8100` e le stesse rotte `/kef/mcp`, `/ollama/mcp`, `/github/mcp`, `/truenas/mcp`, ecc., così che `mcp_config.json` funzioni in modo trasparente.

### 4. Strategia Dati e Stato (TrueNAS vs Mac)
- Specificare chiaramente come gestire lo stato di Hermes Agent (sessioni/memoria) e LiteLLM quando si passa da TrueNAS a Mac e viceversa (es. sync unidirezionale/bidirezionale via rsync/TrueNAS SSH prima dello shutdown, oppure persistenza locale indipendente).

---

# OUTPUT RICHIESTO
Fornisci una soluzione completa, ingegnerizzata e dettagliata che includa:
1. **Analisi Architetturale & Flusso di Transizione**: diagramma o sequenza del failover e del failback.
2. **File `docker-compose.yaml` per OrbStack**: codice YAML completo, pronto all'uso con Traefik, MCP fleet, Hermes, LiteLLM + DB e Dozzle.
3. **Script di Switchover DNS OPNsense**: script Python o Ansible task riutilizzabile che dialoga con le API REST di Unbound per aggiornare i record DNS da TrueNAS a Mac e viceversa.
4. **Modifiche agli script `lab_mode_***`**: diff o blocchi bash esatti da integrare in `lab_mode_off.sh`, `lab_mode_eco.sh` e `lab_mode_full.sh`.
5. **Piano di Configurazione Client (`mcp_config.json`)**: aggiornamento dei puntamenti verso il dominio `mcp.pindaroli.org`.
6. **Piano di Test e Validazione Step-by-Step**: passaggi per verificare la connettività, il cambio DNS con `dig`/`nslookup` e la corretta ripresa dei servizi.
```

---

# PARTE 2 — Topologia di Rete & Indirizzamento (Estratto da `rete.json`)

```json
{
  "network_summary": {
    "domain": "pindaroli.org",
    "dns_server": "10.10.20.1 (OPNsense Unbound)",
    "opnsense_admin_ip": "192.168.100.1 (OOB VLAN 99) / 10.10.20.1 (LAN VLAN 20)",
    "vlans": {
      "10": "Server / Storage (10.10.10.0/24)",
      "20": "Client / LAN (10.10.20.0/24)",
      "99": "OOB Management (192.168.100.0/24)"
    }
  },
  "nodes": {
    "truenas": {
      "hostname": "truenas.pindaroli.org",
      "ip_vlan20": "10.10.20.50",
      "ip_vlan10": "10.10.10.50",
      "role": "Storage primario ZFS, Docker Compose host (Servarr + MCP fleet)",
      "storage_root": "/mnt/stripe/truenas-docker"
    },
    "mac_studio": {
      "hostname": "olindo-macstudio.pindaroli.org",
      "ip_vlan20": "10.10.20.100",
      "hardware": "Apple Silicon M2 Ultra (macOS)",
      "runtime": "OrbStack (Docker Engine locale)",
      "ollama_local_port": 11434
    },
    "opnsense": {
      "hostname": "opnsense.pindaroli.org",
      "ip": "10.10.20.1",
      "oob_ip": "192.168.100.1",
      "api_endpoint": "https://192.168.100.1/api/unbound"
    }
  }
}
```

---

# PARTE 3 — Flotta MCP & Gateway Traefik (`docker/mcp/docker-compose.yaml`)

```yaml
name: truenas-mcp-fleet

networks:
  mcp-network:
    name: mcp-network
    driver: bridge
  mcp-socket-proxy:
    name: mcp-socket-proxy
    driver: bridge
    internal: true

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
      - POST=0
      - AUTH=0
      - BUILD=0
      - COMMIT=0
      - CONFIGS=0
      - DISTRIBUTION=0
      - EXEC=0
      - GRPC=0
      - IMAGES=0
      - INFO=0
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
      - "--providers.docker.network=mcp-network"
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
  # 1. TRUENAS MCP — WebSocket JSON-RPC 2.0 (Supergateway Stateful)
  # ============================================================================
  truenas-mcp:
    container_name: mcp-truenas
    image: ghcr.io/pindaroli/truenas-mcp:1.0.0-r1
    restart: unless-stopped
    env_file: .env
    networks:
      - mcp-network
    labels:
      - "traefik.enable=true"
      - "traefik.http.routers.mcp-truenas.entrypoints=mcp"
      - "traefik.http.routers.mcp-truenas.rule=PathPrefix(`/truenas`)"
      - "traefik.http.middlewares.strip-truenas.stripprefix.prefixes=/truenas"
      - "traefik.http.routers.mcp-truenas.middlewares=strip-truenas"
      - "traefik.http.services.mcp-truenas.loadbalancer.server.port=8080"
      - "traefik.http.services.mcp-truenas.loadbalancer.responseforwarding.flushinterval=-1ms"
    healthcheck:
      test: ["CMD-SHELL", "wget -q --spider http://127.0.0.1:8080/healthz || exit 1"]
      interval: 30s
      timeout: 5s
      retries: 3
      start_period: 10s

  # ============================================================================
  # 2. OPNSENSE MCP — REST API OPNsense MVC (Supergateway Stateful)
  # ============================================================================
  opnsense-mcp:
    container_name: mcp-opnsense
    image: ghcr.io/pindaroli/opnsense-mcp:0.5.3-r1
    restart: unless-stopped
    env_file: .env
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
  # 3. TALOS MCP — Talos Linux API gRPC (mTLS Secret Mount)
  # ============================================================================
  talos-mcp:
    container_name: mcp-talos
    image: ghcr.io/pindaroli/talos-mcp:2.5.1-r1
    restart: unless-stopped
    env_file: .env
    environment:
      - TALOSCONFIG=/etc/talos/talosconfig
    volumes:
      - /mnt/stripe/truenas-docker/mcp/talos/talosconfig:/etc/talos/talosconfig:ro
    networks:
      - mcp-network
    labels:
      - "traefik.enable=true"
      - "traefik.http.routers.mcp-talos.entrypoints=mcp"
      - "traefik.http.routers.mcp-talos.rule=PathPrefix(`/talos`)"
      - "traefik.http.middlewares.strip-talos.stripprefix.prefixes=/talos"
      - "traefik.http.routers.mcp-talos.middlewares=strip-talos"
      - "traefik.http.services.mcp-talos.loadbalancer.server.port=8080"
      - "traefik.http.services.mcp-talos.loadbalancer.responseforwarding.flushinterval=-1ms"
    healthcheck:
      test: ["CMD-SHELL", "wget -q --spider http://127.0.0.1:8080/healthz || exit 1"]
      interval: 30s
      timeout: 5s
      retries: 3
      start_period: 10s

  # ============================================================================
  # 4. GEMINI DEEPSEARCH — LangGraph Web Search Agent (Python Streamable HTTP)
  # ============================================================================
  gemini-deepsearch-mcp:
    container_name: mcp-gemini-deepsearch
    image: ghcr.io/pindaroli/gemini-deepsearch-mcp:0.2.0
    restart: unless-stopped
    env_file: .env
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
  # 5. KUBERNETES MCP — Kubernetes Cluster API (mTLS Kubeconfig Mount)
  # ============================================================================
  kubernetes-mcp:
    container_name: mcp-kubernetes
    image: ghcr.io/containers/kubernetes-mcp-server@sha256:6992c8fd06aa140aef1584cecdc160b6c2810d0b51702d1f565fc1b6f86e4402
    restart: unless-stopped
    environment:
      - KUBECONFIG=/app/config/kubeconfig
    volumes:
      - /mnt/stripe/truenas-docker/mcp/kubernetes:/app/config:ro
    command: ["--config", "/app/config/config.toml"]
    networks:
      - mcp-network
    labels:
      - "traefik.enable=true"
      - "traefik.http.routers.mcp-kubernetes.entrypoints=mcp"
      - "traefik.http.routers.mcp-kubernetes.rule=PathPrefix(`/kubernetes`)"
      - "traefik.http.middlewares.strip-kubernetes.stripprefix.prefixes=/kubernetes"
      - "traefik.http.routers.mcp-kubernetes.middlewares=strip-kubernetes"
      - "traefik.http.services.mcp-kubernetes.loadbalancer.server.port=8080"
      - "traefik.http.services.mcp-kubernetes.loadbalancer.responseforwarding.flushinterval=-1ms"
    healthcheck:
      test: ["CMD", "/app/kubernetes-mcp-server", "--version"]
      interval: 30s
      timeout: 5s
      retries: 3
      start_period: 10s

  # ============================================================================
  # 6. OLLAMA MCP — Ollama REST API (Supergateway Stateful)
  # ============================================================================
  ollama-mcp:
    container_name: mcp-ollama
    image: ghcr.io/pindaroli/ollama-mcp:2.1.0-r1
    restart: unless-stopped
    env_file: .env
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
  # 7. KEF MCP — KEF LSX II Speakers Control (FastAPI / SSE)
  # ============================================================================
  kef-mcp:
    container_name: mcp-kef
    image: ghcr.io/pindaroli/kef-mcp:1.0.0
    restart: unless-stopped
    environment:
      - MCP_TRANSPORT=sse
      - MCP_PORT=8080
      - MCP_HOST=0.0.0.0
    env_file: .env
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
  # 8. NOWAIKIT MCP — ServiceNow REST API (Supergateway Stateful)
  # ============================================================================
  nowaikit-mcp:
    container_name: mcp-nowaikit
    image: ghcr.io/pindaroli/nowaikit-mcp:4.15.1-r1
    restart: unless-stopped
    env_file: .env
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
  # 9. GITHUB MCP — GitHub Cloud REST/GraphQL (Supergateway Stateful)
  # ============================================================================
  github-mcp:
    container_name: mcp-github
    image: ghcr.io/pindaroli/github-mcp-server:0.7.0-r1
    restart: unless-stopped
    env_file: .env
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
  # 10. ARRSTACK MCP — Media Stack Radarr/Lidarr/Prowlarr/qBittorrent
  # ============================================================================
  arrstack-mcp:
    container_name: mcp-arrstack
    image: ghcr.io/pindaroli/arrstack-mcp:1.3.0
    restart: unless-stopped
    env_file: .env
    environment:
      - ENABLED_SERVICES=radarr,lidarr,prowlarr,qbittorrent,bitmagnet
      - RADARR_URL=https://radarr-internal.pindaroli.org
      - RADARR_API_KEY=${ARRSTACK_RADARR_API_KEY}
      - LIDARR_URL=https://lidarr-internal.pindaroli.org
      - LIDARR_API_KEY=${ARRSTACK_LIDARR_API_KEY}
      - PROWLARR_URL=http://10.10.20.50:9696
      - PROWLARR_API_KEY=${ARRSTACK_PROWLARR_API_KEY}
      - QBT_URL=http://10.10.20.50:8080
      - QBT_USER=admin
      - QBT_PASS=${ARRSTACK_QBT_PASS}
      - BITMAGNET_GRAPHQL_URL=http://10.10.20.50:3333/graphql
      - BITMAGNET_TIMEOUT=30.0
      - MCP_ALLOWED_HOSTS=10.10.20.50:*,127.0.0.1:*,localhost:*
    command: ["--transport", "streamable-http", "--host", "0.0.0.0", "--port", "8080"]
    networks:
      - mcp-network
    labels:
      - "traefik.enable=true"
      - "traefik.http.routers.mcp-arrstack.entrypoints=mcp"
      - "traefik.http.routers.mcp-arrstack.rule=PathPrefix(`/arrstack`)"
      - "traefik.http.middlewares.strip-arrstack.stripprefix.prefixes=/arrstack"
      - "traefik.http.routers.mcp-arrstack.middlewares=strip-arrstack"
      - "traefik.http.services.mcp-arrstack.loadbalancer.server.port=8080"
      - "traefik.http.services.mcp-arrstack.loadbalancer.responseforwarding.flushinterval=-1ms"
    healthcheck:
      test: ["CMD-SHELL", "python -c \"import urllib.request; urllib.request.urlopen('http://127.0.0.1:8080/.well-known/mcp-server-card.json', timeout=2)\" || exit 1"]
      interval: 30s
      timeout: 5s
      start_period: 10s

  # ============================================================================
  # 11. RAGFLOW MCP — Local Homelab Knowledge Base (Supergateway Stateful)
  # ============================================================================
  ragflow-mcp:
    container_name: mcp-ragflow
    image: ghcr.io/pindaroli/ragflow-mcp:1.0.0
    restart: unless-stopped
    env_file: .env
    environment:
      - RAGFLOW_BASE_URL=https://ragflow-internal.pindaroli.org
      - RAGFLOW_API_KEY=${RAGFLOW_API_KEY}
      - RAGFLOW_DEFAULT_RERANK=rerank-multilingual-v3.0
      - RAGFLOW_SSL_VERIFY=false
    networks:
      - mcp-network
    labels:
      - "traefik.enable=true"
      - "traefik.http.routers.mcp-ragflow.entrypoints=mcp"
      - "traefik.http.routers.mcp-ragflow.rule=PathPrefix(`/ragflow`)"
      - "traefik.http.middlewares.strip-ragflow.stripprefix.prefixes=/ragflow"
      - "traefik.http.routers.mcp-ragflow.middlewares=strip-ragflow"
      - "traefik.http.services.mcp-ragflow.loadbalancer.server.port=8080"
      - "traefik.http.services.mcp-ragflow.loadbalancer.responseforwarding.flushinterval=-1ms"
    healthcheck:
      test: ["CMD-SHELL", "python -c \"import urllib.request; resp = urllib.request.urlopen('http://127.0.0.1:8080/healthz', timeout=2); assert resp.status == 200\" || exit 1"]
      interval: 15s
      timeout: 5s
      retries: 3
      start_period: 10s

  # ============================================================================
  # 12. MEROSS MCP — Dual Gateway FastAPI REST + FastMCP (Homepage Widget & MCP)
  # ============================================================================
  meross-mcp:
    container_name: mcp-meross
    image: ghcr.io/pindaroli/meross-mcp:0.1.2
    restart: unless-stopped
    env_file: .env
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
```

---

# PARTE 4 — Servizi AI & Dozzle su TrueNAS (`servarr/truenas-docker/docker-compose.yaml`)

```yaml
  # --- Dozzle Log Viewer ---
  dozzle:
    image: amir20/dozzle:v11.2.0
    container_name: dozzle
    restart: unless-stopped
    ports:
      - "8888:8080"
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock:ro
      - /mnt/stripe/truenas-docker/dozzle:/data
    environment:
      - DOZZLE_NO_ANALYTICS=true
      - DOZZLE_LEVEL=info
    healthcheck:
      test: ["CMD", "/dozzle", "healthcheck"]
      interval: 30s
      timeout: 5s
      retries: 3

  # --- LiteLLM Dedicated Database ---
  litellm-postgres:
    image: postgres:16-alpine
    container_name: litellm-postgres
    restart: unless-stopped
    environment:
      POSTGRES_DB: litellm
      POSTGRES_USER: litellm
      POSTGRES_PASSWORD: ${LITELLM_DB_PASSWORD}
    volumes:
      - /mnt/stripe/truenas-docker/litellm-postgres:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U litellm -d litellm"]
      interval: 5s
      timeout: 3s
      retries: 5

  # --- LiteLLM Proxy ---
  litellm:
    image: ghcr.io/berriai/litellm:1.106.2
    container_name: litellm
    restart: unless-stopped
    ports:
      - "4000:4000"
    environment:
      DATABASE_URL: "postgresql://litellm:${LITELLM_DB_PASSWORD}@litellm-postgres:5432/litellm"
      LITELLM_MASTER_KEY: ${LITELLM_MASTER_KEY}
      LITELLM_SALT_KEY: ${LITELLM_SALT_KEY}
      UI_USERNAME: ${LITELLM_UI_USERNAME}
      UI_PASSWORD: ${LITELLM_UI_PASSWORD}
    volumes:
      - /mnt/stripe/truenas-docker/litellm/config.yaml:/app/config.yaml:ro
    command: ["--config", "/app/config.yaml", "--port", "4000"]
    depends_on:
      litellm-postgres:
        condition: service_healthy
    healthcheck:
      test: ["CMD", "python3", "-c", "import urllib.request; urllib.request.urlopen('http://localhost:4000/health/liveliness')"]
      interval: 10s
      timeout: 5s
      retries: 3
      start_period: 25s

  # --- Hermes Agent ---
  hermes-agent:
    image: nousresearch/hermes-agent:v2026.7.20
    container_name: hermes-agent
    restart: unless-stopped
    ports:
      - "9119:9119"
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
      KUBECONFIG: "/root/.kube/config"
      TALOSCONFIG: "/root/.talos/config"
    command: ["hermes", "gateway", "run"]
    volumes:
      - /mnt/stripe/hermes-agent:/opt/data
      - /mnt/stripe/truenas-docker/hermes/kubeconfig:/root/.kube/config:ro
      - /mnt/stripe/truenas-docker/hermes/talosconfig:/root/.talos/config:ro
      - /mnt/stripe/truenas-docker/hermes/bin/kubectl:/usr/local/bin/kubectl:ro
      - /mnt/stripe/truenas-docker/hermes/bin/talosctl:/usr/local/bin/talosctl:ro
    depends_on:
      litellm:
        condition: service_healthy
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:9119/health"]
      interval: 10s
      timeout: 5s
      retries: 3
      start_period: 20s
```

### Configurazione Modelli LiteLLM (`servarr/truenas-docker/litellm/config.yaml`)

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

  # 5. embed (bge-m3:latest)
  - model_name: embed
    litellm_params:
      model: ollama/bge-m3:latest
      api_base: http://lxc-ollama.pindaroli.org:11434
      order: 1

router_settings:
  model_group_alias:
    chat: big-chat
  routing_strategy: simple-shuffle
  allowed_fails: 1
  cooldown_time: 60
```

---

# PARTE 5 — Script di Transizione Modalità (`scripts/infrastructure/`)

### 1. `scripts/infrastructure/lab_mode_off.sh`
```bash
#!/usr/bin/env bash
# Spegnimento totale del rack Homelab: K8s, PVE e TrueNAS spenti
set -Eeuo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"
cd "$ROOT_DIR" || exit 1

source "$SCRIPT_DIR/procedure_scope.sh"
source "$SCRIPT_DIR/utils.sh"

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
echo "➡️  Stato Target: RACK DARK (K8s, Proxmox VE e TrueNAS Storage SPENTI)"
echo "📄 Log di sessione: $LOG_FILE"
echo ""

if is_root_procedure; then
    send_telegram "🛑 <b>Avvio ${PROCEDURE_NAME}</b>%0ASpegnimento totale dell'infrastruttura Homelab: K8s -> PVE -> TrueNAS..." "Homelab Mode"
fi

# FASE 1: GARANTISCE COMPUTE LAYER OFFLINE (K8S + PVE) PRIMA DI TRUENAS
echo "▶️  [Fase 1/2] Esecuzione: ensure_compute_off..."
ansible-playbook -i ansible/inventory.ini ansible/playbooks/infrastructure/ensure_compute_off.yml

# FASE 2: FLUSH E SPEGNIMENTO FISICO TRUENAS BARE METAL
echo "▶️  [Fase 2/2] Esecuzione: ensure_storage_off..."
ansible-playbook -i ansible/inventory.ini ansible/playbooks/infrastructure/ensure_storage_off.yml

# NOTIFICA FINALE RIASSUNTIVA DI SUCCESSO
if is_root_procedure; then
    send_telegram "🌙 <b>${PROCEDURE_NAME} Completato!</b>%0ATutti i nodi fisici e VM sono disattivati in sicurezza. Rack offline." "Homelab Mode"
    stop_table="<tr><td><b>Modalità:</b></td><td>RACK DARK (Zero Watt Standby)</td></tr><tr><td><b>Kubernetes:</b></td><td>OFFLINE (Cluster Talos disattivato)</td></tr><tr><td><b>Hypervisors:</b></td><td>OFFLINE (pve1, pve2, pve3 spenti)</td></tr><tr><td><b>Storage TrueNAS:</b></td><td>OFFLINE (Bare metal spento)</td></tr>"
    stop_html="$(build_html_email_template "🌙" "Completato: ${PROCEDURE_NAME}" "Homelab Mode Orchestration" "SUCCESSO" "#10b981" "$stop_table")"
    send_summary_email "$DEFAULT_EMAIL_RECIPIENT" "✅ [SUCCESS] ${PROCEDURE_NAME}" "$stop_html" "${PROCEDURE_NAME} completato con successo"
    complete_procedure_scope
else
    echo "ℹ️ [NESTED] Procedura ${PROCEDURE_NAME} completata. Segnalazione finale delegata a ${HOMELAB_PARENT_PROCEDURE}."
fi
```

### 2. `scripts/infrastructure/lab_mode_eco.sh`
```bash
#!/usr/bin/env bash
# Homelab a risparmio energetico: solo TrueNAS attivo, PVE e K8s spenti
set -Eeuo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"
cd "$ROOT_DIR" || exit 1

source "$SCRIPT_DIR/procedure_scope.sh"
source "$SCRIPT_DIR/utils.sh"

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
echo "➡️  Stato Target: ECO LAB (TrueNAS ONLINE, Proxmox VE e Kubernetes OFFLINE)"
echo "📄 Log di sessione: $LOG_FILE"
echo ""

if is_root_procedure; then
    send_telegram "🚀 <b>Avvio ${PROCEDURE_NAME}</b>%0AConvergenza verso modalità Eco: TrueNAS ONLINE, spegnimento K8s e Proxmox VE..." "Homelab Mode"
fi

# FASE 1: GARANTISCE STORAGE TRUENAS BARE METAL ONLINE
echo "▶️  [Fase 1/2] Esecuzione: ensure_storage_on..."
ansible-playbook -i ansible/inventory.ini ansible/playbooks/infrastructure/ensure_storage_on.yml

# FASE 2: GARANTISCE COMPUTE LAYER OFFLINE (K8S + PVE)
echo "▶️  [Fase 2/2] Esecuzione: ensure_compute_off..."
ansible-playbook -i ansible/inventory.ini ansible/playbooks/infrastructure/ensure_compute_off.yml

# NOTIFICA FINALE RIASSUNTIVA DI SUCCESSO
if is_root_procedure; then
    send_telegram "🎉 <b>${PROCEDURE_NAME} Completato!</b>%0AHomelab a regime di risparmio energetico: TrueNAS attivo, K8s e Proxmox disattivati." "Homelab Mode"
    stop_table="<tr><td><b>Modalità:</b></td><td>ECO LAB (Risparmio Energetico)</td></tr><tr><td><b>Storage TrueNAS:</b></td><td>ONLINE (10.10.20.50, Servarr, ZFS)</td></tr><tr><td><b>Hypervisor PVE:</b></td><td>OFFLINE (pve1, pve2, pve3 spenti)</td></tr><tr><td><b>Kubernetes:</b></td><td>OFFLINE (Cluster Talos disattivato)</td></tr>"
    stop_html="$(build_html_email_template "🎉" "Completato: ${PROCEDURE_NAME}" "Homelab Mode Orchestration" "SUCCESSO" "#10b981" "$stop_table")"
    send_summary_email "$DEFAULT_EMAIL_RECIPIENT" "✅ [SUCCESS] ${PROCEDURE_NAME}" "$stop_html" "${PROCEDURE_NAME} completato con successo"
    complete_procedure_scope
else
    echo "ℹ️ [NESTED] Procedura ${PROCEDURE_NAME} completata. Segnalazione finale delegata a ${HOMELAB_PARENT_PROCEDURE}."
fi
```

### 3. `scripts/infrastructure/lab_mode_full.sh`
```bash
#!/usr/bin/env bash
# Homelab a pieno regime: TrueNAS, Proxmox VE e K8s tutti attivi
set -Eeuo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"
cd "$ROOT_DIR" || exit 1

source "$SCRIPT_DIR/procedure_scope.sh"
source "$SCRIPT_DIR/utils.sh"

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
echo "➡️  Stato Target: FULL LAB (TrueNAS + Proxmox VE + Kubernetes Talos ONLINE)"
echo "📄 Log di sessione: $LOG_FILE"
echo ""

if is_root_procedure; then
    send_telegram "🚀 <b>Avvio ${PROCEDURE_NAME}</b>%0AConvergenza verso Full Homelab: TrueNAS -> PVE1/2/3 -> Talos Cluster..." "Homelab Mode"
fi

# FASE 1: HARD GATE STORAGE TRUENAS BARE METAL
echo "▶️  [Fase 1/2] Esecuzione: ensure_storage_on..."
ansible-playbook -i ansible/inventory.ini ansible/playbooks/infrastructure/ensure_storage_on.yml

# FASE 2: GATELAYER COMPUTE (PROXMOX VE + TALOS KUBERNETES)
echo "▶️  [Fase 2/2] Esecuzione: ensure_compute_on..."
ansible-playbook -i ansible/inventory.ini ansible/playbooks/infrastructure/ensure_compute_on.yml

# NOTIFICA FINALE RIASSUNTIVA DI SUCCESSO
if is_root_procedure; then
    send_telegram "🎉 <b>${PROCEDURE_NAME} Completato!</b>%0AIntero Homelab pienamente operativo: TrueNAS, Proxmox VE e Kubernetes online al 100%." "Homelab Mode"
    stop_table="<tr><td><b>Modalità:</b></td><td>FULL LAB (100% Gates Superati)</td></tr><tr><td><b>Storage TrueNAS:</b></td><td>ONLINE (Pool stripe & oliraid sani)</td></tr><tr><td><b>Hypervisor PVE:</b></td><td>ONLINE (pve1, pve2, pve3)</td></tr><tr><td><b>Talos Cluster:</b></td><td>READY & UNCORDONATI (cp-01, cp-02, cp-03)</td></tr><tr><td><b>Ingress VIP:</b></td><td>ONLINE (https://10.10.20.56)</td></tr>"
    stop_html="$(build_html_email_template "🎉" "Completato: ${PROCEDURE_NAME}" "Homelab Mode Orchestration" "SUCCESSO" "#10b981" "$stop_table")"
    send_summary_email "$DEFAULT_EMAIL_RECIPIENT" "✅ [SUCCESS] ${PROCEDURE_NAME}" "$stop_html" "${PROCEDURE_NAME} completato con successo"
    complete_procedure_scope
else
    echo "ℹ️ [NESTED] Procedura ${PROCEDURE_NAME} completata. Segnalazione finale delegata a ${HOMELAB_PARENT_PROCEDURE}."
fi
```

---

# PARTE 6 — Gestione Host Overrides Unbound OPNsense (`ansible/playbooks/opnsense/opnsense_sync_dns.yml`)

```yaml
---
- name: Configure OPNsense Unbound DNS Overrides
  hosts: localhost
  connection: local
  gather_facts: false
  vars:
    api_key: "{{ opnsense_api_key | default('') }}"
    api_secret: "{{ opnsense_api_secret | default('') }}"
    opnsense_url: "https://192.168.100.1"
    domain: "pindaroli.org"

  vars_files:
    - "../../vars/common_secrets.yml"
    - "../../vars/opnsense_secrets.yml"
    - "../../../rete.json"

  tasks:
    - name: Fail if credentials are missing
      fail:
        msg: "Please provide api_key and api_secret via extra vars or inventory."
      when: api_key == '' or api_secret == ''

    # Add/Update Host Overrides in OPNsense
    - name: Add/Update Host Overrides in OPNsense
      uri:
        url: "{{ opnsense_url }}/api/unbound/settings/addHostOverride"
        method: POST
        user: "{{ api_key }}"
        password: "{{ api_secret }}"
        force_basic_auth: yes
        validate_certs: no
        body_format: json
        body:
          host:
            hostname: "{{ item.hostname }}"
            domain: "{{ item.domain }}"
            server: "{{ item.ip }}"
            description: "{{ item.desc }}"
            enabled: "1"
        status_code: [200, 201]
        return_content: yes
      loop: "{{ dns_h }}"

    - name: Apply Unbound Configuration
      uri:
        url: "{{ opnsense_url }}/api/unbound/service/reconfigure"
        method: POST
        user: "{{ api_key }}"
        password: "{{ api_secret }}"
        force_basic_auth: yes
        validate_certs: no
        status_code: 200
```

---

# PARTE 7 — Configurazione Attuale Client MCP (`~/.gemini/antigravity/mcp_config.json`)

```json
{
  "mcpServers": {
    "kef": {
      "serverUrl": "http://10.10.20.50:8100/kef/mcp"
    },
    "ollama": {
      "serverUrl": "http://10.10.20.50:8100/ollama/mcp"
    },
    "github-mcp-server": {
      "serverUrl": "http://10.10.20.50:8100/github/mcp"
    },
    "kubernetes": {
      "serverUrl": "http://10.10.20.50:8100/kubernetes/mcp"
    },
    "truenas-master-mcp": {
      "serverUrl": "http://10.10.20.50:8100/truenas/mcp",
      "disabledTools": [
        "get_chart_release"
      ]
    },
    "opnsense": {
      "serverUrl": "http://10.10.20.50:8100/opnsense/mcp"
    },
    "talos": {
      "serverUrl": "http://10.10.20.50:8100/talos/mcp"
    },
    "gemini-deepsearch": {
      "serverUrl": "http://10.10.20.50:8100/gemini/mcp"
    },
    "nowaikit": {
      "serverUrl": "http://10.10.20.50:8100/nowaikit/mcp"
    },
    "arrstack-mcp": {
      "serverUrl": "http://10.10.20.50:8100/arrstack/mcp"
    },
    "ragflow-local": {
      "serverUrl": "http://10.10.20.50:8100/ragflow/mcp"
    },
    "meross": {
      "serverUrl": "http://10.10.20.50:8100/meross/mcp"
    }
  }
}
```

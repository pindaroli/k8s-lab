# Quadro Contestuale e Vincoli Specifici per il Consulto Architetturale

## 1. Scheda del Piano in Esame
- **Titolo del Piano**: Cross-Hardening e Allineamento KISS Docker Compose (TrueNAS & OrbStack)
- **Percorso del File**: `wiki/plans/docker-compose-cross-hardening-and-kiss-alignment.md`
- **Stato**: `active` (`certified_for_ai: true`)
- **Dominio / Tecnologie**: Docker Compose v2, TrueNAS SCALE 25.10 (Linux Debian x86_64, ZFS), Mac Studio M2 Max (macOS Apple Silicon ARM64, OrbStack, Rosetta), Bridge Networking, Tecnativa Docker Socket Proxy L7, Traefik v3, PostgreSQL 16, Security Options (`no-new-privileges`), Container Healthchecks, Cgroups v2 Memory Limits.
- **Obiettivo Principale**: Formalizzare ed eseguire il cross-hardening dei due stack Docker Compose (`docker/truenas/docker-compose.yaml` e `docker/orbstack/docker-compose.yaml`), adottando in modo mirato e ordinato per priorità KISS (da 5/5 a 4/5) i pattern virtuosi emersi dall'analisi comparativa (healthcheck universali, security hardening, segmentazione L3/L4 reti bridge per isolamento database, socket-proxy L7 per Dozzle, memory limit su container MCP emulati x86, e consolidamento file `.env`), vietando categoricamente anti-pattern che romperebbero il KISS (divieto di eliminare `dynamic.yaml` per label dinamiche cross-stack su TrueNAS, e divieto di portare PostgreSQL su Mac in failover).

---

## 2. Nodi, IP e Topologia di Rete Pertinenti (Fonte: `rete.json`)
- **TrueNAS SCALE Bare Metal (`truenas`)**:
  - IP: `10.10.20.50` su interfaccia VLAN 20 (`bond0.20` / `enp3s0`).
  - Ruolo: Host primario stateful per i carichi di produzione in modalità `FULL` ed `ECO`.
  - Servizi attivi nello stack `docker/truenas/docker-compose.yaml`:
    - Media Stack: `jellyfin` (:8096, GPU passthrough `/dev/dri/renderD128`), `qbittorrent` (:8080, :30661, :6881), `prowlarr` (:9696), `flaresolverr` (:8191), `webhook-normalizer` (:9000).
    - Audio & S3 in `network_mode: host`: `minimserver` (multicast SSDP UPnP/DLNA porta 1900 UDP), `garage` (porte cluster RPC e S3 API :3900-:3903).
    - Database relazionali dedicati: `bitmagnet-postgres` (:5432), `litellm-postgres` (:5432).
    - AI & Management: `bitmagnet` (:3333, :3334), `litellm` (:4000), `hermes-agent` (:9119), `scrutiny` (:31054, :31055, privileged/SMART `/dev`), `dozzle` (:8888), `homepage` (:3000).
  - Architettura Ingress su TrueNAS: Lo stack `docker/mcp` è isolato e include `mcp-traefik` (:80, :443, :8100). Traefik instrada verso i servizi applicativi di `docker/truenas` tramite file provider statico [`docker/mcp/dynamic.yaml`](file:///Users/olindo/prj/k8s-lab/docker/mcp/dynamic.yaml) su `http://10.10.20.50:<porta>`.
- **Mac Studio M2 Max (`mac-studio`)**:
  - IP: `10.10.20.100` su interfaccia VLAN 20.
  - Ruolo: Host secondario di failover per la modalità *rack-dark* (`lab_mode_off`) tramite motore OrbStack (attivo a rack fisico spento).
  - Servizi dello stack `docker/orbstack/docker-compose.yaml`:
    - Gateway & Sicurezza: `socket-proxy` (L7 read-only interno), `traefik` (:80, :443, :8100, :8180).
    - Flotta MCP Lean (7 server attivi a freddo): `opnsense-mcp`, `gemini-deepsearch-mcp`, `ollama-mcp` (connesso a Ollama Metal locale Mac :11434), `kef-mcp`, `nowaikit-mcp`, `github-mcp`, `meross-mcp`.
    - AI & Management: `litellm` (:4000, **Stateless Zero-DB**), `hermes-agent` (:9119), `dozzle` (:8888 via socket-proxy), `homepage` (:3000).
  - Topologia Reti OrbStack: 3 bridge dedicati (`orbstack-mcp-network`, `orbstack-socket-proxy` con `internal: true`, `orbstack-ai-network`).
- **OPNsense Firewall & DNS (`opnsense`)**:
  - IP VLAN 20 Gateway / DNS: `10.10.20.1` (Unbound DNS con Host Overrides dinamici).
  - FQDN gestiti con switch tri-stato: `home-internal.pindaroli.org`, `hermes.pindaroli.org`, `litellm.pindaroli.org`, `dozzle.pindaroli.org`, `mcp.pindaroli.org`.

---

## 3. Storage ZFS e Mappa dei Volumi (Fonte: `storage.json`)
- **Pool ZFS `stripe` su TrueNAS (NVMe ad alte prestazioni)**:
  - Root configurazioni e DB: `/mnt/stripe/truenas-docker/` (jellyfin, qbittorrent, prowlarr, homepage, dozzle, bitmagnet, litellm-postgres, scrutiny, hermes).
  - Sicurezza preventiva: Dataset ZFS protetto da snapshot immediato prima di ogni riconfigurazione (`stripe/truenas-docker@pre-cross-hardening-20261025`).
- **Pool ZFS `oliraid` su TrueNAS (Archiviazione Massiva)**:
  - `/mnt/oliraid/arrdata/media`: montato da Jellyfin, qBittorrent, Webhook-Normalizer, MinimServer.
  - `/mnt/oliraid/garage-data`: storage persistente per l'Object Storage S3 Garage.
- **Storage Locale Mac Studio (macOS APFS)**:
  - `~/.homelab-failover/`: runtime directory di failover (`acme/`, `.env`, `dozzle/`, `hermes/`).
  - `/Users/olindo/hermesAgent/`: directory dati e workspace condiviso per Hermes Agent sincronizzati via rsync bidirezionale.

---

## 4. Vincoli Architetturali e Golden Rules Homelab (Fonte: `GEMINI.md`)
1. **User Decision Sovereignty (Propose, Never Decide)**:
   - Divieto assoluto di eseguire modifiche a caldo, cancellare dati o fermare container senza previa autorizzazione esplicita dell'utente.
2. **Principio KISS (Keep It Simple, Stupid) — Divieto di Unificazione Forzata**:
   - È vietato fondere i due file `docker-compose.yaml` in un unico mega-compose parametrizzato o basato su profili/override complessi. I due ambienti mantengono file separati e specializzati.
3. **Preservazione del Disaccoppiamento Ingress TrueNAS**:
   - Vietato eliminare `docker/mcp/dynamic.yaml` per rimpiazzarlo con etichette Traefik su `docker/truenas`: i due stack su TrueNAS devono rimanere autonomi al boot.
4. **Preservazione Zero-DB su Mac Studio (Failover)**:
   - È categoricamente vietato introdurre database relazionali (PostgreSQL) su Mac Studio: LiteLLM deve rimanere rigorosamente stateless durante il failover.
5. **Protocollo di Verifica Test-Driven (§12 di `wiki/SCHEMA.md`)**:
   - Ogni modifica dichiarativa deve essere preceduta da `docker compose config` (dry-run) e seguita da test di raggiungibilità reale e verifica dell'integrità dei container.

---

## 5. Aree di Attenzione & Quesiti Specifici per il Consulto
1. **Interazione tra Reti Bridge e Porte Pubblicate (`ports:`) su TrueNAS**:
   - L'introduzione delle 3 reti bridge (`media-net`, `ai-net`, `db-bitmagnet-net`) altera l'accessibilità da parte di Traefik (che risiede nello stack `docker/mcp` e usa `http://10.10.20.50:<porta>`)?
   - *Verifica*: In Docker, la direttiva `ports: host:container` vincola l'ascolto sull'IP dell'host indipendentemente dalla rete bridge interna usata.
2. **Invarianza dei Container in `network_mode: host`**:
   - La presenza di container con `network_mode: host` (`minimserver`, `garage`) convive senza conflitti con la definizione delle nuove reti bridge all'interno dello stesso compose?
3. **Socket-Proxy per Dozzle su TrueNAS: Condiviso vs Dedicato**:
   - Su TrueNAS esiste già un `socket-proxy` attivo in `docker/mcp`. È preferibile collegare Dozzle di `docker/truenas` al proxy esistente (creando una rete esterna condivisa `truenas-socket-proxy`) oppure aggiungere un socket-proxy dedicato leggerissimo dentro `docker/truenas` per preservare il 100% di autonomia tra i due compose?
4. **Memory Limits su OrbStack (cgroups v2)**:
   - La direttiva `mem_limit: 256m / 512m` applicata ai container MCP in `docker/orbstack` interagisce correttamente con il motore OrbStack senza provocare OOM-kill spuri durante carichi di picco (es. ricerche estese con NowAIKit o Gemini DeepSearch)?
5. **Solidità del Piano di Rollback**:
   - La strategia di ripristino istantaneo tramite snapshot ZFS su TrueNAS (`zfs rollback`) e checkout Git su Mac Studio garantisce tempi di ripristino < 30 secondi in caso di imprevisti?

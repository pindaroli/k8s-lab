---
title: "Piano: Failover Trasparente Ingress HTTPS home-internal e Switch DNS Tri-Stato (FULL/ECO/OFF)"
type: plan
status: completed
certified_for_ai: true
created_at: 2026-10-24
completed_at: 2026-10-24
tags:
  - "#core"
  - "#network"
  - "#dns"
  - "#ingress"
  - "#traefik"
  - "#homepage"
  - "#failover"
---

# Piano Operativo: Failover Trasparente Ingress HTTPS `home-internal` e Switch DNS Tri-Stato

> **Percorso Canonico Wiki**: `wiki/plans/home-internal-dns-failover-and-https-ingress.md` (alias: `[[home-internal-dns-failover-and-https-ingress]]`)
> **Comando di Attivazione per l'Agente Locale**: `/resume [[home-internal-dns-failover-and-https-ingress]]`
> **Governance Collegata**: [[orbstack-failover-truenas-services]], [[homepage-mac-orbstack-failover]], [[SCHEMA]], [[go-launcher-script-pattern]], [[hierarchical-automation-alerting-pattern]], [[homelab-idempotent-mode-scripts]], [[homepage-steam-lxc-control-button]].
> **Piani Sostituiti**: `[[truenas-traefik-alone-proxy]]` (archiviato con `superseded_by: home-internal-dns-failover-and-https-ingress`).

---

## 1. Contesto e Obiettivo

Attualmente l'URL canonico della dashboard del lab è `https://home-internal.pindaroli.org/`.
Tuttavia, il record DNS Unbound su OPNsense punta in modo statico al LoadBalancer VIP di Kubernetes (`10.10.20.56`).
Di conseguenza:
- In **`lab_mode_full`**: Kubernetes e Traefik sono attivi; `https://home-internal.pindaroli.org/` funziona regolarmente su porta 443 con certificato TLS valido.
- In **`lab_mode_eco`**: il cluster Kubernetes e i nodi Proxmox sono spenti per risparmio energetico. `10.10.20.56` va in timeout. L'utente è costretto a digitare manualmente `http://10.10.20.50:3000/` per raggiungere Homepage su TrueNAS SCALE.
- In **`lab_mode_off`**: l'intero rack fisico è spento. L'utente è costretto a digitare manualmente `http://10.10.20.100:3000/` per raggiungere Homepage su Mac Studio (OrbStack).

L'obiettivo di questo piano è rendere **completamente trasparente e universale l'accesso a `https://home-internal.pindaroli.org/` (porta standard 443, protocollo HTTPS e lucchetto verde privo di avvisi di sicurezza)** in tutte e tre le modalità dell'homelab:
1. **FULL LAB (`lab_mode_full.sh`)**: instradamento verso Kubernetes Ingress VIP (`10.10.20.56:443`).
2. **ECO LAB (`lab_mode_eco.sh`)**: instradamento verso Traefik su TrueNAS (`10.10.20.50:443`), che inoltra internamente a Homepage TrueNAS (`:3000`).
3. **OFF / RACK DARK (`lab_mode_off.sh`)**: instradamento verso Traefik su Mac Studio OrbStack (`10.10.20.100:443`), che inoltra internamente a Homepage Mac (`:3000`).

Inoltre, approfittando della disponibilità della porta 443 su TrueNAS e Mac Studio, Traefik gestirà con routing basato su Host e TLS anche gli altri servizi AI e di log (`hermes.pindaroli.org`, `litellm.pindaroli.org`, `dozzle.pindaroli.org`, `mcp.pindaroli.org`) su porta 443 standard, preservando al contempo le porte dedicate attuali (`:9119`, `:4000`, `:8888`, `:8100`) per piena retrocompatibilità con script e automazioni esistenti.

---

## 2. Decisioni Architetturali Approvate (Consolidate Post-Revisione)

| # | Ambito | Decisione Approvata | Specifica Tecnica Consolidata |
| :- | :--- | :--- | :--- |
| **1** | **Comportamento Ingress Browser** | **Proxy Ingress Trasparente HTTPS** | L'URL nella barra del browser rimane sempre `https://home-internal.pindaroli.org/` (porta 443 standard con certificato TLS valido) in tutte e 3 le modalità, inoltrando internamente al rispettivo container Homepage (`:3000`) con `HOMEPAGE_ALLOWED_HOSTS` comprensivo di `home-internal.pindaroli.org`. |
| **2** | **Porta WebGUI TrueNAS & Gate** | **Spostamento WebGUI su `:8443` + Allineamento Gate Ansible e MCP** | La WebGUI amministrativa di TrueNAS SCALE viene migrata su `8443` (HTTPS) e `8088` (HTTP redirect) tramite `system.general.update`. Il gate Ansible in `ensure_storage_on.yml` e l'endpoint WebSocket di `truenas-master-mcp` (`wss://10.10.20.50:8443/api/current`) vengono riallineati a `:8443`. Il piano confliggente `truenas-traefik-alone-proxy` viene archiviato. |
| **3** | **Certificati TLS Let's Encrypt** | **ACME Nativo Traefik su Directory `/acme` + Sync 1:1 su Mac Studio** | Traefik su TrueNAS gestisce l'emissione/rinnovo di `*.pindaroli.org` tramite Cloudflare DNS-01 (`resolvers=1.1.1.1:53,1.0.0.1:53`, `delaybeforecheck=15`) montando l'intera directory `/mnt/stripe/truenas-docker/mcp/acme:/acme` (compatibile con `read_only: true`). `prepare_orbstack_runtime_env()` in `orbstack_failover.sh` sincronizza `acme.json` (`chmod 600`) in `~/.homelab-failover/acme/acme.json` su Mac Studio per attivazione HTTPS in 0s anche senza WAN, mantenendo il resolver Cloudflare su OrbStack come fallback autonomo. |
| **4** | **Gestione Porta HTTP 80** | **Redirect Automatico 301 a HTTPS 443** | Traefik ascolta anche sulla porta 80 ed effettua il redirect permanente a `https://...`, permettendo all'utente di digitare semplicemente `home-internal.pindaroli.org` senza prefisso di protocollo. |
| **5** | **Routing Cross-Stack & Reti Docker** | **File Provider Dinamico (`dynamic.yaml`) su TrueNAS + Rete Unificata su OrbStack** | Su TrueNAS (`10.10.20.50`), `mcp-traefik` usa `/mnt/stripe/truenas-docker/mcp/dynamic.yaml` (`--providers.file.watch=true`) per inoltrare `home-internal` (`:3000`), `hermes` (`:9119`), `litellm` (`:4000`), `dozzle` (`:8888` — e **non** `:8080` che è qBittorrent) e `mcp` (`:8100`). Su Mac Studio (`docker/orbstack-failover/docker-compose.orbstack.yaml`), `traefik` viene collegato anche ad `ai-network` (e `homepage-mac` a `mcp-network`) per raggiungere tutti i container via Docker DNS senza `502 Bad Gateway`. |
| **6** | **DNS Switchover Tri-Stato, Sequenza Zero-Blackhole & HTTP/2 Reuse** | **Switch Atomico Singolo (`full`, `eco`, `off`) con TTL 10s e Proxy/Redirect in `FULL`** | `switch_failover_dns.py` supporta `--target [full \| eco \| off]` con `ttl: "10"` (con fallback al TTL globale Unbound se il validatore MVC di OPNsense 26.1 non accetta `ttl` per singolo host). In `lab_mode_eco.sh` lo switch a `eco` avviene **prima** di `ensure_compute_off.yml` (zero blackhole durante lo spegnimento K8s) ed è invocato una sola volta. In `lab_mode_full.sh` viene evitato qualsiasi flap DNS su `FULL -> FULL`, e in modalità `FULL` `dynamic.yaml` su TrueNAS inoltra `home-internal` al VIP K8s `https://10.10.20.56` così anche i browser con socket HTTP/2 keep-alive aperti verso `10.10.20.50:443` vengono serviti da K8s istantaneamente. |

---

## 3. Mappa Completa dei File da Creare o Modificare

| Azione | Percorso File | Descrizione |
| :--- | :--- | :--- |
| **ARCHIVIA** | `wiki/plans/truenas-traefik-alone-proxy.md` | Impostazione `status: archived` e `superseded_by: home-internal-dns-failover-and-https-ingress` (evita conflitto su porte 8443/8088). |
| **MODIFICA** | `rete.json` | Censimento della porta WebGUI TrueNAS `8443` (e `8088` HTTP) e delle nuove capability di ingress HTTPS Traefik su `10.10.20.50` e `10.10.20.100`. |
| **MODIFICA** | `ansible/playbooks/infrastructure/ensure_storage_on.yml` | Aggiornamento del checkpoint `CP 1.2 — TrueNAS WebUI Gate` dalla porta `443` alla porta `8443` (e aggiunta verifica porta `443` per `mcp-traefik` nel gate servizi). |
| **MODIFICA** | `docker/mcp/docker-compose.yaml` | Apertura porte `80:80` e `443:443` su `mcp-traefik`, entrypoints `web`/`websecure`, resolver ACME Cloudflare con mount della **directory** `/mnt/stripe/truenas-docker/mcp/acme:/acme`, mount di `/mnt/stripe/truenas-docker/mcp/dynamic.yaml:/etc/traefik/dynamic.yaml:ro`, router `mcp.pindaroli.org` su `websecure`, e aggiornamento URL `truenas-master-mcp` a `:8443`. |
| **CREA** | `docker/mcp/dynamic.yaml` | Configurazione dinamica Traefik per TrueNAS (`home-internal` -> `:3000`, `hermes` -> `:9119`, `litellm` -> `:4000`, `dozzle` -> `:8888`, `truenas` -> `https://10.10.20.50:8443`). |
| **MODIFICA** | `servarr/truenas-docker/docker-compose.yaml` | Verifica/aggiunta `HOMEPAGE_ALLOWED_HOSTS=home-internal.pindaroli.org,10.10.20.50:3000,localhost:3000,*` sul servizio `homepage`. |
| **MODIFICA** | `docker/orbstack-failover/docker-compose.orbstack.yaml` | Apertura porte `80:80` e `443:443` su Traefik OrbStack, collegamento di `traefik` ad `ai-network` e `homepage-mac` a `mcp-network`, mount directory `~/.homelab-failover/acme:/acme`, label HTTPS per `homepage-mac:3000`, `hermes-agent:9119`, `litellm:4000`, `dozzle:8080`, `mcp` e `HOMEPAGE_ALLOWED_HOSTS`. |
| **MODIFICA** | `scripts/network/switch_failover_dns.py` | Refactoring con supporto `--target [full \| eco \| off]` (più alias `truenas` -> `eco`, `orbstack` -> `off`), gestione differenziata di `home-internal`, e supporto resiliente a `ttl: "10"` nelle API MVC di OPNsense Unbound. |
| **MODIFICA** | `scripts/network/validate_network.py` | Tolleranza per gli IP validi di failover (`10.10.20.56`, `10.10.20.50`, `10.10.20.100`) sull'alias dinamico `home-internal`. |
| **MODIFICA** | `scripts/infrastructure/orbstack_failover.sh` | Sincronizzazione automatica di `acme.json` da TrueNAS a `~/.homelab-failover/acme/acme.json` (`chmod 600`) in `prepare_orbstack_runtime_env()`, e parametrizzazione di `deactivate_orbstack_failover_to_truenas "<target_mode>"` (`eco` o `full`) per evitare doppi switch DNS. |
| **MODIFICA** | `scripts/infrastructure/lab_mode_full.sh` | Passaggio di `"full"` / gestione senza flap DNS in Fase 2 e commutazione finale a `--target full` (con opzionale proxy `dynamic.yaml` verso `10.10.20.56`) dopo `ensure_compute_on.yml`. |
| **MODIFICA** | `scripts/infrastructure/lab_mode_eco.sh` | Esecuzione dello switch DNS `--target eco` in Fase 2 **prima** di `ensure_compute_off.yml` (tramite `deactivate_orbstack_failover_to_truenas "eco"`), rimuovendo invocazioni duplicate in Fase 3. |
| **MODIFICA** | `homepage/homepage.yaml` e `homepage/homepage-local.yaml` | Aggiornamento `href`, `widget.url` e `siteMonitor` di TrueNAS a `:8443` + gestione graceful `404` in `custom.js` per `/api/steam/status/current` quando PVE3 è spento. |
| **MODIFICA** | `docker/orbstack-failover/homepage-config/services.yaml` | Aggiornamento `href`, `widget.url` e `siteMonitor` di TrueNAS a `https://truenas.pindaroli.org:8443` (o `https://10.10.20.50:8443`). |
| **MODIFICA** | TrueNAS `/mnt/stripe/truenas-docker/homepage/services.yaml` | Aggiornamento `href`, `widget.url` e `siteMonitor` di TrueNAS a `https://truenas.pindaroli.org:8443` (o `https://10.10.20.50:8443`). |

---

## 4. Fasi Operative di Implementazione (Protocollo Test-Driven §12)

### FASE 0: Pre-Check, Archiviazione Piano Confliggente e Snapshot ZFS Preventivo
1. Archiviare formalmente `wiki/plans/truenas-traefik-alone-proxy.md` impostando nel frontmatter YAML `status: archived`, `certified_for_ai: false`, `archived_at: 2026-10-24` e `superseded_by: home-internal-dns-failover-and-https-ingress`.
2. Creare uno snapshot ZFS preventivo su TrueNAS prima di toccare le configurazioni Docker:
   ```bash
   ssh -o BatchMode=yes olindo@10.10.20.50 "sudo zfs snapshot stripe/truenas-docker@pre-https-ingress-20261024 && sudo zfs list -t snapshot -r stripe/truenas-docker | grep pre-https-ingress-20261024"
   ```
3. **Verifica Test-Driven**:
   - Lo snapshot `stripe/truenas-docker@pre-https-ingress-20261024` è presente e la porta `8443` su TrueNAS è attualmente libera:
     ```bash
     ssh -o BatchMode=yes olindo@10.10.20.50 "! sudo ss -tulpn | grep -E ':8443\b'" && echo "Porta 8443 libera OK"
     ```

---

### FASE 1: Riconfigurazione Porta WebGUI TrueNAS (443 $\rightarrow$ 8443) e Allineamento Gate Ansible
1. Eseguire chiamata API middleware su TrueNAS SCALE (`10.10.20.50`) via SSH batchmode per migrare la porta HTTPS a `8443` e la porta HTTP a `8088`:
   ```bash
   ssh -o BatchMode=yes olindo@10.10.20.50 "sudo midclt call system.general.update '{\"ui_httpsport\": 8443, \"ui_port\": 8088}'"
   ```
2. Riavviare il servizio Nginx della WebGUI di TrueNAS e attendere il rilascio dei socket:
   ```bash
   ssh -o BatchMode=yes olindo@10.10.20.50 "sudo midclt call system.general.ui_restart && sleep 4"
   ```
3. **Verifica Test-Driven (TrueNAS WebGUI e Porte 80/443)**:
   - Verificare che la WebGUI risponda con HTTP 200/302 su `https://10.10.20.50:8443/`:
     ```bash
     curl -skI https://10.10.20.50:8443/ | head -n 5
     ```
   - Verificare che le porte `80` e `443` siano completamente libere su `10.10.20.50` (invertendo l'exit code di `grep` affinché restituisca `0` solo se nessun processo è in ascolto):
     ```bash
     ssh -o BatchMode=yes olindo@10.10.20.50 "! sudo ss -tulpn | grep -E ':(80|443)\b'" && echo "Porte 80 e 443 libere OK"
     ```
4. Aggiornare `ansible/playbooks/infrastructure/ensure_storage_on.yml`:
   - Modificare il task `CP 1.2 — TrueNAS WebUI Gate` per verificare la porta `8443` anziché `443`.
5. Aggiornare la configurazione di `truenas-master-mcp` (in `/mnt/stripe/truenas-docker/mcp/.env` e `docker/mcp/docker-compose.yaml`) affinché punti a `wss://10.10.20.50:8443/api/current` (o `https://10.10.20.50:8443`), riavviando `mcp-truenas` se attivo.
6. **Verifica Test-Driven (Ansible Gate & MCP TrueNAS)**:
   ```bash
   ansible-playbook ansible/playbooks/infrastructure/ensure_storage_on.yml --syntax-check
   curl -sf http://10.10.20.50:8100/truenas/healthz || ssh -o BatchMode=yes olindo@10.10.20.50 "sudo docker ps --filter name=mcp-truenas"
   ```
7. Aggiornare `rete.json` con la nuova porta `8443` per la WebGUI TrueNAS.

---

### FASE 2: Ingress Traefik con ACME Cloudflare e `dynamic.yaml` su TrueNAS (`docker/mcp`)
1. Estrarre il token API Cloudflare da `secrets-sops/cloudflare-token.enc.yaml` e assicurarsi che sia presente in `/mnt/stripe/truenas-docker/mcp/.env` (`chmod 600`) come `CF_DNS_API_TOKEN`.
2. Creare la directory `/mnt/stripe/truenas-docker/mcp/acme` e il file `acme.json` con permessi restrittivi `600`:
   ```bash
   ssh -o BatchMode=yes olindo@10.10.20.50 "mkdir -p /mnt/stripe/truenas-docker/mcp/acme && touch /mnt/stripe/truenas-docker/mcp/acme/acme.json && chmod 700 /mnt/stripe/truenas-docker/mcp/acme && chmod 600 /mnt/stripe/truenas-docker/mcp/acme/acme.json"
   ```
3. Creare il file `docker/mcp/dynamic.yaml` e sincronizzarlo in `/mnt/stripe/truenas-docker/mcp/dynamic.yaml`:
   ```yaml
   http:
     routers:
       home-internal-https:
         rule: "Host(`home-internal.pindaroli.org`)"
         entryPoints:
           - websecure
         service: homepage-truenas-svc
         tls:
           certResolver: cloudflare
           domains:
             - main: "pindaroli.org"
               sans:
                 - "*.pindaroli.org"
       hermes-https:
         rule: "Host(`hermes.pindaroli.org`) || Host(`hermes-internal.pindaroli.org`)"
         entryPoints:
           - websecure
         service: hermes-svc
         tls:
           certResolver: cloudflare
       litellm-https:
         rule: "Host(`litellm.pindaroli.org`) || Host(`litellm-internal.pindaroli.org`)"
         entryPoints:
           - websecure
         service: litellm-svc
         tls:
           certResolver: cloudflare
       dozzle-https:
         rule: "Host(`dozzle.pindaroli.org`)"
         entryPoints:
           - websecure
         service: dozzle-svc
         tls:
           certResolver: cloudflare
       mcp-gateway-https:
         rule: "Host(`mcp.pindaroli.org`)"
         entryPoints:
           - websecure
         service: mcp-loopback-svc
         tls:
           certResolver: cloudflare

     services:
       homepage-truenas-svc:
         loadBalancer:
           servers:
             - url: "http://10.10.20.50:3000"
       hermes-svc:
         loadBalancer:
           servers:
             - url: "http://10.10.20.50:9119"
       litellm-svc:
         loadBalancer:
           servers:
             - url: "http://10.10.20.50:4000"
       dozzle-svc:
         loadBalancer:
           servers:
             - url: "http://10.10.20.50:8888"
       mcp-loopback-svc:
         loadBalancer:
           servers:
             - url: "http://127.0.0.1:8100"
   ```
   *(Nota: `dozzle-svc` punta tassativamente alla porta host `8888` di Dozzle e non a `8080` che appartiene a qBittorrent).*
4. Aggiornare `docker/mcp/docker-compose.yaml` (servizio `traefik` / `mcp-traefik`):
   - Esporre le porte `"80:80"`, `"443:443"` oltre a `"8100:8100"`.
   - Passare `CF_DNS_API_TOKEN=${CF_DNS_API_TOKEN}` in `environment` (o `env_file: .env`).
   - Montare **l'intera directory** `/mnt/stripe/truenas-docker/mcp/acme:/acme` (indispensabile con `read_only: true` affinché Traefik possa fare l'atomic rename di `acme.json`) e `/mnt/stripe/truenas-docker/mcp/dynamic.yaml:/etc/traefik/dynamic.yaml:ro`.
   - Aggiungere i flag CLI a Traefik:
     ```yaml
     - "--entrypoints.web.address=:80"
     - "--entrypoints.web.http.redirections.entrypoint.to=websecure"
     - "--entrypoints.web.http.redirections.entrypoint.scheme=https"
     - "--entrypoints.web.http.redirections.entrypoint.permanent=true"
     - "--entrypoints.websecure.address=:443"
     - "--entrypoints.websecure.transport.respondingTimeouts.idleTimeout=60s"
     - "--providers.file.filename=/etc/traefik/dynamic.yaml"
     - "--providers.file.watch=true"
     - "--certificatesresolvers.cloudflare.acme.dnschallenge=true"
     - "--certificatesresolvers.cloudflare.acme.dnschallenge.provider=cloudflare"
     - "--certificatesresolvers.cloudflare.acme.dnschallenge.resolvers=1.1.1.1:53,1.0.0.1:53"
     - "--certificatesresolvers.cloudflare.acme.dnschallenge.delaybeforecheck=15"
     - "--certificatesresolvers.cloudflare.acme.email=olindo.pindaroli@gmail.com"
     - "--certificatesresolvers.cloudflare.acme.storage=/acme/acme.json"
     ```
5. Verificare in `servarr/truenas-docker/docker-compose.yaml` che il container `homepage` abbia `HOMEPAGE_ALLOWED_HOSTS: "*"` (o includa `home-internal.pindaroli.org`), aggiornandolo se necessario.
6. Sincronizzare e riavviare `mcp-traefik` su TrueNAS:
   ```bash
   scp -o BatchMode=yes docker/mcp/dynamic.yaml docker/mcp/docker-compose.yaml olindo@10.10.20.50:/mnt/stripe/truenas-docker/mcp/
   ssh -o BatchMode=yes olindo@10.10.20.50 "cd /mnt/stripe/truenas-docker/mcp && sudo docker compose config -q && sudo docker compose up -d traefik"
   ```
7. **Verifica Test-Driven (SNI TLS + Certificato Let's Encrypt + 5 Servizi)**:
   - Verificare i listener 80 e 443 e l'emissione del certificato in `acme.json` (attendere ~20-30s al primo avvio per la DNS-01 challenge):
     ```bash
     ssh -o BatchMode=yes olindo@10.10.20.50 "sudo ss -tulpn | grep -E ':(80|443)\b' && sudo stat -c '%a %s %n' /mnt/stripe/truenas-docker/mcp/acme/acme.json"
     ```
   - Verificare il redirect `301 Moved Permanently` da HTTP (`:80`) a HTTPS (`:443`):
     ```bash
     curl -sI --resolve home-internal.pindaroli.org:80:10.10.20.50 http://home-internal.pindaroli.org/ | head -n 5
     ```
   - Verificare HTTPS **senza `-k`** usando `--resolve` (valida SNI, catena Let's Encrypt e Host header):
     ```bash
     curl -sI --resolve home-internal.pindaroli.org:443:10.10.20.50 https://home-internal.pindaroli.org/ | head -n 5
     curl -sI --resolve hermes.pindaroli.org:443:10.10.20.50 https://hermes.pindaroli.org/health | head -n 5
     curl -sI --resolve litellm.pindaroli.org:443:10.10.20.50 https://litellm.pindaroli.org/health/liveliness | head -n 5
     curl -sI --resolve dozzle.pindaroli.org:443:10.10.20.50 https://dozzle.pindaroli.org/ | head -n 5
     curl -sI --resolve mcp.pindaroli.org:443:10.10.20.50 https://mcp.pindaroli.org/meross/healthz | head -n 5
     ```

---

### FASE 3: Ingress Traefik con Sync ACME e Rete Unificata su Mac Studio (`docker/orbstack-failover`)
1. Creare la directory locale `~/.homelab-failover/acme` e sincronizzare immediatamente il file `acme.json` già validato da TrueNAS:
   ```bash
   mkdir -p ~/.homelab-failover/acme && chmod 700 ~/.homelab-failover/acme
   scp -o BatchMode=yes olindo@10.10.20.50:/mnt/stripe/truenas-docker/mcp/acme/acme.json ~/.homelab-failover/acme/acme.json
   chmod 600 ~/.homelab-failover/acme/acme.json
   ```
2. Aggiornare `scripts/infrastructure/orbstack_failover.sh` nella funzione `prepare_orbstack_runtime_env()` per copiare automaticamente `/mnt/stripe/truenas-docker/mcp/acme/acme.json` in `~/.homelab-failover/acme/acme.json` (`chmod 600`) ogni volta che TrueNAS è raggiungibile via SSH.
3. Aggiornare `docker/orbstack-failover/docker-compose.orbstack.yaml`:
   - Sul servizio `traefik`:
     - Esporre `"80:80"`, `"443:443"`, `"8100:8100"`.
     - Connettere `traefik` a tutte le reti interne necessarie: `mcp-network`, `ai-network` e `mcp-socket-proxy` (e assicurarsi che `homepage-mac` sia connesso a `mcp-network`), così che Traefik possa risolvere e contattare `homepage-mac:3000`, `hermes-agent:9119`, `litellm:4000`, `dozzle:8080`.
     - Montare `~/.homelab-failover/acme:/acme`.
     - Configurare gli entrypoints `web` (redirect 301 a `websecure`), `websecure` (`:443`) e il `certificatesresolvers.cloudflare` identico a TrueNAS.
   - Aggiungere le label Traefik HTTPS (`entrypoints=websecure`, `tls.certresolver=cloudflare`) sui servizi `homepage-mac` (`home-internal.pindaroli.org` -> porta `3000`, con `HOMEPAGE_ALLOWED_HOSTS: "*"`), `hermes-agent` (`hermes.pindaroli.org` -> `9119`), `litellm` (`litellm.pindaroli.org` -> `4000`), `dozzle` (`dozzle.pindaroli.org` -> `8080`, `traefik.docker.network=orbstack-mcp-socket-proxy`), e il router per `mcp.pindaroli.org`.
4. **Verifica Test-Driven (OrbStack Isolato sul Mac Studio)**:
   - Validare la sintassi del Compose:
     ```bash
     docker compose -f docker/orbstack-failover/docker-compose.orbstack.yaml config -q && echo "OrbStack Compose OK"
     ```
   - Avviare temporaneamente `traefik` e `homepage-mac` su OrbStack e verificare con `--resolve` (senza toccare il DNS di produzione):
     ```bash
     docker compose -f docker/orbstack-failover/docker-compose.orbstack.yaml up -d traefik homepage-mac
     curl -sI --resolve home-internal.pindaroli.org:443:10.10.20.100 https://home-internal.pindaroli.org/ | head -n 5
     docker compose -f docker/orbstack-failover/docker-compose.orbstack.yaml stop traefik homepage-mac
     ```
   *(Esito atteso: `HTTP/2 200` con certificato Let's Encrypt valido servito in 0 secondi grazie ad `acme.json` pre-sincronizzato).*

---

### FASE 4: Refactoring Switch DNS Tri-Stato (`switch_failover_dns.py`) e `validate_network.py`
1. Aggiornare `scripts/network/switch_failover_dns.py`:
   - Supportare `--target [full | eco | off]` mantenendo gli alias retrocompatibili `truenas` $\rightarrow$ `eco` e `orbstack` $\rightarrow$ `off`.
   - Mappa deterministica degli Host Overrides su OPNsense Unbound (`pindaroli.org`):
     - `home-internal`:
       - `full` $\rightarrow$ `10.10.20.56` (K8s Traefik VIP)
       - `eco` $\rightarrow$ `10.10.20.50` (TrueNAS Traefik)
       - `off` $\rightarrow$ `10.10.20.100` (Mac Studio OrbStack Traefik)
     - `mcp`, `hermes`, `litellm`, `dozzle`:
       - `full` ed `eco` $\rightarrow$ `10.10.20.50` (TrueNAS Traefik)
       - `off` $\rightarrow$ `10.10.20.100` (Mac Studio OrbStack Traefik)
   - Gestione resiliente del TTL a 10 secondi: inviare `"ttl": "10"` nel payload `host` di `setHostOverride`/`addHostOverride`; se OPNsense 26.1 restituisce `validations` sul campo `ttl`, riprovare automaticamente senza il campo `ttl` sul singolo record (affidandosi al TTL locale di Unbound).
   - Idempotenza: se tutti i 5 record su OPNsense puntano già agli IP del `--target` richiesto, **non** invocare `service/reconfigure` su Unbound (zero flap DNS).
2. Aggiornare `scripts/network/validate_network.py` (e ove presente `ansible/playbooks/opnsense_sync_dns.yml`) affinché riconosca gli host gestiti dinamicamente da `switch_failover_dns.py` (`home-internal`, `mcp`, `hermes`, `litellm`, `dozzle`) come validi su `{10.10.20.56, 10.10.20.50, 10.10.20.100}`.
3. **Verifica Test-Driven**:
   ```bash
   python3 -m py_compile scripts/network/switch_failover_dns.py scripts/network/validate_network.py
   python3 scripts/network/switch_failover_dns.py --dry-run --target full
   python3 scripts/network/switch_failover_dns.py --dry-run --target eco
   python3 scripts/network/switch_failover_dns.py --dry-run --target off
   ```
   - Eseguire l'applicazione reale del target corrente (`eco` o `full`) e verificare la risoluzione DNS su OPNsense:
     ```bash
     python3 scripts/network/switch_failover_dns.py --target eco
     dig +short home-internal.pindaroli.org @10.10.20.1
     ```

---

### FASE 5: Integrazione Coordinata negli Script di Modalità (`lab_mode_full.sh`, `lab_mode_eco.sh`, `orbstack_failover.sh`)
1. In `scripts/infrastructure/orbstack_failover.sh`:
   - In `activate_orbstack_failover()`: invocare `switch_failover_dns.py --target off`.
   - In `deactivate_orbstack_failover_to_truenas()`: accettare un parametro opzionale `target_mode="${1:-eco}"`.
     - Se i container di failover su OrbStack erano attivi (transizione da `OFF`), fermarli e commutare il DNS su `--target "${target_mode}"` (o `--target eco` durante la salita verso `FULL`, così `home-internal` risponde già da TrueNAS mentre K8s fa il boot!).
     - Se i container su OrbStack erano **già spenti** (es. transizione `FULL -> FULL` o `FULL -> ECO`), eseguire `switch_failover_dns.py --target "${target_mode}"` solo se `target_mode="eco"`; se `target_mode="full"`, **non** commutare temporaneamente `home-internal` su `eco` (zero flap DNS su `FULL -> FULL`).
   - Aggiungere funzione helper `set_truenas_home_internal_backend(mode)`:
     - Quando `mode="full"`, aggiorna in `/mnt/stripe/truenas-docker/mcp/dynamic.yaml` l'URL di `homepage-truenas-svc` a `https://10.10.20.56` (con `serversTransport` `insecureSkipVerify: true`), così anche i browser con socket HTTP/2 keep-alive ancora agganciati a `10.10.20.50:443` dopo `ECO -> FULL` visualizzano immediatamente la Homepage K8s!
     - Quando `mode="eco"`, imposta `homepage-truenas-svc` a `http://10.10.20.50:3000`.
2. In `scripts/infrastructure/lab_mode_eco.sh`:
   - In Fase 2 (dopo `ensure_storage_on.yml` e **PRIMA** di `ensure_compute_off.yml`): chiamare `set_truenas_home_internal_backend "eco"` e `deactivate_orbstack_failover_to_truenas "eco"`. In questo modo, durante `FULL -> ECO`, il DNS di `home-internal` passa a TrueNAS `10.10.20.50` *prima* che K8s venga spento (zero secondi di downtime!).
   - Non aggiungere una seconda chiamata duplicata a `switch_failover_dns.py` in Fase 3.
3. In `scripts/infrastructure/lab_mode_full.sh`:
   - In Fase 2: chiamare `deactivate_orbstack_failover_to_truenas "full"`.
   - In Fase 3 (dopo il completamento di `ensure_compute_on.yml` e la verifica del VIP `10.10.20.56:443`): chiamare `switch_failover_dns.py --target full` e `set_truenas_home_internal_backend "full"`.
4. **Verifica Test-Driven**:
   ```bash
   bash -n scripts/infrastructure/orbstack_failover.sh
   bash -n scripts/infrastructure/lab_mode_full.sh
   bash -n scripts/infrastructure/lab_mode_eco.sh
   bash -n scripts/infrastructure/lab_mode_off.sh
   ```

---

### FASE 6: Aggiornamento Link Dashboard Homepage & Resilienza `custom.js` (Skill `homepage-manager`)
1. Aggiornare i riferimenti a TrueNAS WebGUI in tutte e 4 le configurazioni Homepage seguendo la skill `homepage-manager`:
   - `homepage/homepage.yaml` e `homepage/homepage-local.yaml` (K8s): aggiornare `href: https://truenas.pindaroli.org:8443` (e `widget.url` / `siteMonitor` se presenti).
   - `docker/orbstack-failover/homepage-config/services.yaml` (Mac Studio): aggiornare `href: https://truenas.pindaroli.org:8443` e `siteMonitor: https://10.10.20.50:8443`.
   - `/mnt/stripe/truenas-docker/homepage/services.yaml` (TrueNAS): aggiornare `href: https://truenas.pindaroli.org:8443` e `siteMonitor: https://10.10.20.50:8443`.
2. Verificare che in `custom.js` (controllo Steam LXC `/api/steam/status/current`) un eventuale HTTP `404`/`502` (normale quando `home-internal` è servito da TrueNAS in `ECO` o Mac Studio in `OFF`) venga ignorato silenziosamente senza errori in console.
3. **Verifica Test-Driven**:
   - Validare la sintassi YAML di tutti i file modificati:
     ```bash
     python3 -c "import yaml; [yaml.safe_load(open(f)) for f in ['homepage/homepage.yaml', 'homepage/homepage-local.yaml', 'docker/orbstack-failover/homepage-config/services.yaml']]" && echo "YAML Homepage validi OK"
     ```
   - Riavviare il container `homepage` su TrueNAS (e applicare su K8s se il cluster è attivo).

---

### FASE 7: Collaudo E2E e Matrice di Transizione Completa (FULL / ECO / OFF)
1. **Verifica in ECO Mode**:
   ```bash
   ./scripts/infrastructure/lab_mode_eco.sh
   dig +short home-internal.pindaroli.org @10.10.20.1
   curl -sfI https://home-internal.pindaroli.org/ | head -n 5
   curl -sfI https://hermes.pindaroli.org/health | head -n 5
   curl -sfI https://litellm.pindaroli.org/health/liveliness | head -n 5
   curl -sfI https://dozzle.pindaroli.org/ | head -n 5
   ```
   *(Esito atteso: IP `10.10.20.50`, HTTP 200 OK con TLS Let's Encrypt valido su tutti gli endpoint).*
2. **Verifica Transizione ECO $\rightarrow$ OFF $\rightarrow$ ECO**:
   - Eseguire `./scripts/infrastructure/lab_mode_off.sh`.
   - Verificare che `dig +short home-internal.pindaroli.org @10.10.20.1` restituisca `10.10.20.100` e che `curl -sfI https://home-internal.pindaroli.org/` risponda `200 OK` da Mac Studio OrbStack.
   - Eseguire `./scripts/infrastructure/lab_mode_eco.sh` e verificare il ritorno a `10.10.20.50`.
3. **Verifica Transizione ECO $\rightarrow$ FULL $\rightarrow$ FULL (Idempotenza)**:
   - Eseguire `./scripts/infrastructure/lab_mode_full.sh`.
   - Verificare che `dig +short home-internal.pindaroli.org @10.10.20.1` restituisca `10.10.20.56` e che `curl -sfI https://home-internal.pindaroli.org/` risponda `200 OK` dal cluster K8s.
   - Rieseguire `./scripts/infrastructure/lab_mode_full.sh` e verificare zero flap DNS e zero riavvii.
4. **Validazione Finale di Rete e Rigenerazione Contesto Wiki (§13)**:
   ```bash
   python3 scripts/network/validate_network.py && python3 scripts/wiki/build_wiki_context.py
   ```

---

## 5. 🛡️ Matrice di Rollback (Idempotente per Fase)

| Fase | Scenario di Emergenza / Anomalia | Comando Esatto di Rollback (via SSH Passwordless / CLI) | RTO Stimato |
| :--- | :--- | :--- | :---: |
| **Fase 1** | WebGUI TrueNAS non risponde su `:8443` o rollback immediato a `:443` | `ssh -o BatchMode=yes olindo@10.10.20.50 "sudo docker stop mcp-traefik 2>/dev/null \|\| true; sudo midclt call system.general.update '{\"ui_httpsport\": 443, \"ui_port\": 80}' && sudo midclt call system.general.ui_restart"` + `git checkout -- ansible/playbooks/infrastructure/ensure_storage_on.yml rete.json` | **< 15s** |
| **Fase 2** | `mcp-traefik` su TrueNAS non avvia `:443` o fallisce la configurazione | `ssh -o BatchMode=yes olindo@10.10.20.50 "sudo zfs rollback -r stripe/truenas-docker@pre-https-ingress-20261024 && cd /mnt/stripe/truenas-docker/mcp && sudo docker compose up -d"` | **< 30s** |
| **Fase 3** | Traefik su OrbStack fallisce il bind su `:80/:443` o il routing su macOS | `git checkout -- docker/orbstack-failover/docker-compose.orbstack.yaml && docker compose -f docker/orbstack-failover/docker-compose.orbstack.yaml up -d` | **< 20s** |
| **Fase 4-5** | Regressione risoluzione DNS su `home-internal.pindaroli.org` o script `lab_mode_*` | `git checkout -- scripts/network/switch_failover_dns.py scripts/infrastructure/ && python3 scripts/network/switch_failover_dns.py --target truenas` + eventuale `ansible-playbook ansible/playbooks/opnsense_sync_dns.yml` | **< 15s** |
| **Fase 6** | Errore YAML o regressione visiva sulle card Homepage | `git checkout -- homepage/ docker/orbstack-failover/homepage-config/` + ripristino `services.yaml` su TrueNAS e restart container `homepage` | **< 20s** |

---

## 💾 Stato di Ripristino (AI Save-State)
- **Fase Attiva**: COMPLETATO ✅ (Tutte le Fasi 0-7 completate con successo)
- **Ultima Azione Completata**: Esecuzione end-to-end con esito positivo di `lab_mode_eco.sh`, collaudo HTTPS su tutti gli endpoint (`home-internal`, `hermes`, `litellm`, `dozzle`, `mcp`, `truenas` WebGUI :8443) con certificati Let's Encrypt validi su porta 443, validazione di rete al 100% (`validate_network.py`) e rigenerazione contesto wiki (`build_wiki_context.py`).
- **Prossimo Passo Operativo**: Nessuno. Piano operativo completato con successo.
- **Blocchi/Decisioni Pendenti**: Nessuno. Infrastruttura pienamente convergente.

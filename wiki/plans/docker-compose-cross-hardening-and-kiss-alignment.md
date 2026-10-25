---
title: "Piano: Cross-Hardening e Allineamento KISS Docker Compose (TrueNAS & OrbStack)"
type: plan
status: archived
certified_for_ai: false
superseded_by: "[[homelab-hermes-convergence-and-compose-cross-hardening]]"
created_at: 2026-10-25
tags:
  - "#core"
  - "#docker"
  - "#truenas"
  - "#orbstack"
  - "#security"
  - "#hardening"
  - "#kiss"
---

# Piano Operativo: Cross-Hardening e Allineamento KISS Docker Compose (TrueNAS & OrbStack)

> **Percorso Canonico Wiki**: `wiki/plans/docker-compose-cross-hardening-and-kiss-alignment.md` (alias: `[[docker-compose-cross-hardening-and-kiss-alignment]]`)
> **Comando di Attivazione per l'Agente Locale**: `/resume [[docker-compose-cross-hardening-and-kiss-alignment]]`
> **Governance Collegata**: [[orbstack-failover-truenas-services]], [[home-internal-dns-failover-and-https-ingress]], [[SCHEMA]], [[GEMINI]], [[go-launcher-script-pattern]].

---

## 1. Contesto e Obiettivo

Dall'analisi comparativa tra lo stack applicativo primario di produzione su TrueNAS SCALE (`docker/truenas/docker-compose.yaml`) e lo stack di failover per la modalità *rack-dark* su Mac Studio OrbStack (`docker/orbstack/docker-compose.yaml`), è emerso che:
1. **L'omogeneizzazione forzata dei file (DRY rigido) violerebbe il principio KISS**: i due stack assolvono a ruoli ontologicamente diversi (stack bare-metal Linux stateful con ZFS e pass-through hardware vs stack effimero e stateless su macOS/ARM64 per la continuità operativa in emergenza).
2. **Esistono soluzioni architetturali e pattern virtuosi implementati in uno stack che migliorano l'altro a costo zero o minimo**, elevando la sicurezza, l'affidabilità e la pulizia del codice senza introdurre complessità non necessaria.

L'obiettivo di questo piano è formalizzare ed eseguire il **cross-hardening ordinato per priorità decrescente di aderenza al principio KISS**:
- **Da OrbStack a TrueNAS**: Healthcheck universali per rilevamento deadlock, hardening `no-new-privileges`, segmentazione delle reti interne a difesa dei database PostgreSQL e protezione L7 di Dozzle tramite socket-proxy.
- **Da TrueNAS a OrbStack**: Consolidamento e pulizia delle variabili d'ambiente (`.env` unificato) e delimitazione del consumo di memoria (`mem_limit`) per i container MCP in emulazione Rosetta.
- **Divieti Architetturali (Anti-KISS Guards)**: Preservare il disaccoppiamento `dynamic.yaml` per Traefik su TrueNAS (nessuna dipendenza dinamica cross-stack) e preservare la natura *Zero-DB* di OrbStack (nessun PostgreSQL su Mac).

---

## 2. Decisioni Architetturali Consolidate (Matrice KISS)

| # | Ambito | Decisione Approvata | Motivazione Tecnica & Rispetto KISS |
| :- | :--- | :--- | :--- |
| **1** | **Healthcheck TrueNAS** | **Adozione Healthcheck Universale su TrueNAS** | Aggiunta di blocchi `healthcheck` nativi su Jellyfin, qBittorrent, Homepage, Prowlarr e Webhook-Normalizer. Rileva processi zombie/hang senza software aggiuntivo (**KISS 5/5**). |
| **2** | **Hardening Privilegi** | **`no-new-privileges: true` su Container Applicativi** | Aggiunta dichiarativa su Jellyfin, Flaresolverr, Homepage, Bitmagnet e LiteLLM. Blocca escalation privilegi in container esposti su LAN (**KISS 5/5**). |
| **3** | **Limiti Risorse OrbStack** | **`mem_limit` Dichiarativo per Flotta MCP Mac** | Limite di 256MB/512MB sui 7 container MCP per prevenire memory leak progressivi dei runtime Python/Node emulati x86 sotto OrbStack (**KISS 5/5**). |
| **4** | **Segmentazione Reti TrueNAS** | **3 Reti Bridge Dedicate (`media-net`, `ai-net`, `db-net`)** | Isolamento L3/L4 dei database `litellm-postgres` e `bitmagnet-postgres`. Solo i rispettivi consumer accedono alla porta 5432. I container `host` (MinimServer, Garage) rimangono inalterati (**KISS 4.5/5**). |
| **5** | **Socket Docker Dozzle TrueNAS** | **Interconnessione Dozzle a Socket-Proxy L7** | Eliminazione del mount diretto `/var/run/docker.sock` in Dozzle, instradando le chiamate verso il proxy Tecnativa read-only L7 già presente o dedicato (**KISS 4/5**). |
| **6** | **Unificazione Env OrbStack** | **Consolidamento in Singolo `.env` Failover** | Unificazione di `.env.mcp` e `.env.ai` in un unico file `.env` di runtime in `~/.homelab-failover/`, allineando `orbstack_failover.sh` (**KISS 4/5**). |
| **7** | **Preservazione `dynamic.yaml`** | **Mantenimento Routing Statico su TrueNAS** | **Divieto di passare a label Traefik su TrueNAS**: eviterebbe un accoppiamento fragile a runtime tra lo stack MCP e lo stack Media/Storage (**Anti-KISS Evitato**). |
| **8** | **Preservazione Zero-DB Mac** | **Nessun Database Relazionale su OrbStack** | **Divieto di introdurre Postgres su Mac**: LiteLLM resta rigorosamente stateless in failover (**Anti-KISS Evitato**). |

---

## 3. Mappa dei File Oggetto di Modifica

| Azione | Percorso File | Descrizione Modifica |
| :--- | :--- | :--- |
| **MODIFICA** | `docker/truenas/docker-compose.yaml` | Aggiunta reti (`media-net`, `ai-net`, `db-net`), healthcheck universali, `no-new-privileges: true` e routing Dozzle via socket proxy. |
| **MODIFICA** | `docker/orbstack/docker-compose.yaml` | Aggiunta `mem_limit` sui 7 server MCP, armonizzazione `env_file` verso `.env` unificato. |
| **MODIFICA** | `scripts/infrastructure/orbstack_failover.sh` | Aggiornamento funzione `prepare_orbstack_runtime_env()` per generare un unico `.env` consolidato anziché `.env.mcp` + `.env.ai`. |
| **MODIFICA** | `todo.md` | Tracciamento del piano tra i task attivi del repository. |
| **MODIFICA** | `GEMINI.md` | Censimento del piano tra le procedure e le mappe concettuali attive. |

---

## 4. Fasi Operative di Implementazione (Protocollo Test-Driven §12)

### FASE 0: Pre-Check, Snapshot ZFS Preventivo e Validazione Live
1. Creare uno snapshot ZFS preventivo su TrueNAS per la directory dei manifesti e configurazioni:
   ```bash
   ssh -o BatchMode=yes olindo@10.10.20.50 "sudo zfs snapshot stripe/truenas-docker@pre-cross-hardening-20261025 && sudo zfs list -t snapshot -r stripe/truenas-docker | grep pre-cross-hardening-20261025"
   ```
2. **Verifica Test-Driven**:
   - Snapshot presente su TrueNAS e integrità attuale dello stack:
     ```bash
     ssh -o BatchMode=yes olindo@10.10.20.50 "sudo docker compose -f /mnt/stripe/truenas-docker/docker-compose.yaml ps"
     ```

---

### FASE 1: Hardening OrbStack (Memory Limits & Unificazione `.env`)
1. Aggiornare `docker/orbstack/docker-compose.yaml` assegnando:
   - `mem_limit: 512m` per container più corposi (`nowaikit-mcp`, `gemini-deepsearch-mcp`, `homepage-mac`, `litellm`).
   - `mem_limit: 256m` per container leggeri (`opnsense-mcp`, `ollama-mcp`, `kef-mcp`, `github-mcp`, `meross-mcp`, `socket-proxy`, `dozzle`).
   - Sostituzione dei molteplici `env_file: .../.env.mcp` e `.../.env.ai` con un unico `env_file: ${FAILOVER_RUNTIME_DIR:-/Users/olindo/.homelab-failover}/.env`.
2. Aggiornare `scripts/infrastructure/orbstack_failover.sh` per generare il file aggregato `.env` in `~/.homelab-failover/`.
3. **Verifica Test-Driven**:
   - Validazione sintattica con Docker Compose CLI su Mac:
     ```bash
     docker compose -f docker/orbstack/docker-compose.yaml config --dry-run >/dev/null && echo "Sintassi OrbStack Compose OK"
     ```

---

### FASE 2: Hardening TrueNAS — Healthchecks & `no-new-privileges`
1. Aggiornare `docker/truenas/docker-compose.yaml` introducendo i blocchi `healthcheck` per:
   - **Jellyfin**: `test: ["CMD-SHELL", "curl -f http://localhost:8096/health || exit 1"]`
   - **qBittorrent**: `test: ["CMD-SHELL", "curl -f http://localhost:8080/api/v2/app/version || exit 1"]`
   - **Homepage**: `test: ["CMD-SHELL", "wget -q --spider http://127.0.0.1:3000 || exit 1"]`
   - **Prowlarr**: `test: ["CMD-SHELL", "curl -f http://localhost:9696/api/v1/system/status || exit 1"]`
   - **Webhook-Normalizer**: `test: ["CMD-SHELL", "curl -f http://localhost:9000/health || exit 1"]`
2. Aggiungere `security_opt: ["no-new-privileges:true"]` ai servizi `jellyfin`, `qbittorrent`, `prowlarr`, `flaresolverr`, `homepage`, `webhook-normalizer`, `bitmagnet`, `litellm`.
3. **Verifica Test-Driven**:
   - Validazione della configurazione su TrueNAS senza applicazione:
     ```bash
     ssh -o BatchMode=yes olindo@10.10.20.50 "docker compose -f /mnt/stripe/truenas-docker/docker-compose.yaml config >/dev/null && echo 'Sintassi TrueNAS OK'"
     ```

---

### FASE 3: TrueNAS Network Segmentation (Isolamento Database L3/L4)
1. Definire le reti bridge in testa/coda a `docker/truenas/docker-compose.yaml`:
   ```yaml
   networks:
     media-net:
       name: truenas-media-net
       driver: bridge
     ai-net:
       name: truenas-ai-net
       driver: bridge
     db-bitmagnet-net:
       name: truenas-bitmagnet-net
       driver: bridge
       internal: true
   ```
2. Assegnare i container:
   - `media-net`: `jellyfin`, `qbittorrent`, `prowlarr`, `flaresolverr`, `webhook-normalizer`, `homepage`.
   - `ai-net`: `litellm`, `litellm-postgres`, `hermes-agent`, `homepage`.
   - `db-bitmagnet-net`: `bitmagnet`, `bitmagnet-postgres`.
   - `minimserver` e `garage` mantengono `network_mode: host`.
3. **Verifica Test-Driven**:
   - Verifica di connettività isolata: `bitmagnet` raggiunge `bitmagnet-postgres:5432`, `litellm` raggiunge `litellm-postgres:5432`, mentre un container in `media-net` non risolve né raggiunge i database interni.

---

### FASE 4: TrueNAS Dozzle Socket Hardening (L7 Proxy)
1. Configurare Dozzle in `docker/truenas/docker-compose.yaml` affinché utilizzi il socket-proxy L7 protetto (già attivo in `docker/mcp` oppure container compatto dedicato su porta 2375).
2. Rimuovere il mount diretto `- /var/run/docker.sock:/var/run/docker.sock:ro` da Dozzle.
3. **Verifica Test-Driven**:
   - Accesso all'interfaccia Dozzle su `http://10.10.20.50:8888` e verifica visualizzazione log dei container senza accesso al socket grezzo.

---

### FASE 5: Sincronizzazione, Validazione di Rete e Chiusura (§12 & §13)
1. Sincronizzare il file validato `docker/truenas/docker-compose.yaml` in `/mnt/stripe/truenas-docker/docker-compose.yaml`.
2. Eseguire reload dichiarativo dei container su TrueNAS:
   ```bash
   ssh -o BatchMode=yes olindo@10.10.20.50 "cd /mnt/stripe/truenas-docker && sudo docker compose up -d --remove-orphans"
   ```
3. Validare la congruenza di rete e aggiornare il contesto LLM:
   ```bash
   python3 scripts/network/validate_network.py && python3 scripts/wiki/build_wiki_context.py
   ```

---

## 5. Criteri di Rollback

In caso di anomalia durante l'applicazione delle modifiche:
1. **Rollback TrueNAS**:
   - Ripristino immediato dello snapshot ZFS:
     ```bash
     ssh -o BatchMode=yes olindo@10.10.20.50 "sudo zfs rollback stripe/truenas-docker@pre-cross-hardening-20261025 && cd /mnt/stripe/truenas-docker && sudo docker compose up -d --force-recreate"
     ```
2. **Rollback OrbStack**:
   - Ripristino del file precedente via Git:
     ```bash
     git checkout docker/orbstack/docker-compose.yaml scripts/infrastructure/orbstack_failover.sh
     ```

---

## 💾 Stato di Ripristino (AI Save-State)
- **Fase Attiva**: Pianificazione completata — Pronto per approvazione ed esecuzione (Fase 0)
- **Ultima Azione Completata**: Formalizzazione e persistenza del piano `docker-compose-cross-hardening-and-kiss-alignment.md` nel Wiki.
- **Prossimo Passo Operativo**: Approvazione dell'utente per eseguire la FASE 0 (Snapshot ZFS preventivo su TrueNAS).
- **Blocchi/Decisioni Pendenti**: Nessun blocco; in attesa di autorizzazione per l'avvio della sequenza operativa.

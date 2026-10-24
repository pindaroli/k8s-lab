# Quadro Contestuale & Vincoli Architetturali per il Consulto Tecnico

> **Riferimento Piano**: [`wiki/plans/hermes-agent-common-prj-and-web-terminal.md`](file:///Users/olindo/prj/k8s-lab/wiki/plans/hermes-agent-common-prj-and-web-terminal.md)  
> **Data di Generazione**: 2026-10-24  
> **Infrastruttura**: GEMINI Homelab (Dominio `pindaroli.org`)

---

## 1. Scheda del Piano in Esame

* **Titolo**: Hermes Agent Workspace Condiviso `common/prj`, Web Shell Integrata e Sync Bidirezionale TrueNAS/Mac
* **File del Piano**: `wiki/plans/hermes-agent-common-prj-and-web-terminal.md`
* **Stato**: `active` (`certified_for_ai: true`)
* **Stack Tecnologico**:
  * **Hermes Agent**: `nousresearch/hermes-agent:v0.22.5` (FastAPI Web Dashboard, s6-overlay, PTY/xterm.js, Python 3.14).
  * **Web Shell**: `ttyd` (standalone static binary compiled with musl/libuv, WebSockets, xterm.js).
  * **Runtime Container**: Docker Compose su TrueNAS SCALE 25.10 (Linux AMD64) e OrbStack su macOS Sequoia (Apple Silicon ARM64 / M2 Ultra).
  * **Storage & Sync**: ZFS pool `stripe` su TrueNAS, directory locale macOS in `/Users/olindo/hermesAgent`, protocollo `rsync -auz` bidirezionale gestito da `scripts/infrastructure/orbstack_failover.sh`.
* **Obiettivo Principale**:
  1. Configurare una directory comune host `/hermesAgent/common/prj` montata simmetricamente in tutte le istanze Hermes Agent (`HermesMain`), visibile nativamente nel menu Files della WebGUI.
  2. Integrare una Web Shell Linux bash interattiva (`ttyd` come `root`, cwd `/opt/data`) direttamente nella WebGUI di Hermes con autenticazione trasparente.
  3. Ottimizzare e garantire la sincronizzazione bidirezionale tra TrueNAS e Mac (flush preventivo database/container, preservazione dati e normalizzazione permessi).

---

## 2. Nodi, Indirizzamento IP e Rete (da `rete.json`)

| Nodo / Servizio | Indirizzo IP / FQDN | VLAN | Ruolo Infrastrutturale | Note Operative |
| :--- | :--- | :--- | :--- | :--- |
| **TrueNAS SCALE** | `10.10.20.50` (`truenas.pindaroli.org`) | VLAN 20 (Client/LAN) | Storage primario ZFS bare-metal, Host Docker Compose Servarr/AI | Attivo in modalità `FULL` ed `ECO`. Esegue `hermes-main` sulla porta host `9119`. |
| **Mac Studio** | `10.10.20.100` (`olindo-macstudio.pindaroli.org`) | VLAN 20 (Client/LAN) | Workstation principale (M2 Ultra), Host OrbStack Docker per failover `OFF` | Attivo in modalità `OFF` (rack spento). Esegue `hermes-main` sulla porta host `9119`. |
| **OPNsense Router** | `10.10.20.1` / `192.168.100.1` | VLAN 20 / VLAN 99 | Router di confine, DNS Unbound e Gateway | Gestisce gli Host Overrides DNS per la commutazione dinamica TrueNAS ↔ Mac (`switch_failover_dns.py`). |
| **LiteLLM Proxy** | `10.10.20.50:4000` / `10.10.20.100:4000` | VLAN 20 | Proxy HA OpenAI-compatible per modelli Ollama | Backend LLM primario per Hermes Agent (`http://litellm:4000/v1`). |
| **Hermes Web Dashboard** | Porta `9119` (TCP) | VLAN 20 | UI web di gestione agenti, sessioni e file manager | Endpoint di destinazione per l'utente, protetto da Basic Auth (`admin`). |
| **ttyd Web Shell** | Porta interna `7681` (TCP) | Loopback / Interna | Server Web Shell per sessione bash PTY | Non esposto direttamente sull'host; proxato/integrato dalla WebGUI porta 9119. |

---

## 3. Storage ZFS, Directory Host e Mount dei Container (da `storage.json`)

### 3.1 Mappatura Percorsi Host
* **Mac Studio (Failover OrbStack)**:
  * Root Hermes: `/Users/olindo/hermesAgent`
  * Istanza Principale: `/Users/olindo/hermesAgent/HermesMain`
  * Cartella Comune: `/Users/olindo/hermesAgent/common/prj`
  * Binario Web Shell: `/Users/olindo/.homelab-failover/hermes/bin/ttyd` (architettura `aarch64`)
* **TrueNAS SCALE (Bare Metal)**:
  * Pool ZFS: `stripe`
  * Root Hermes: `/mnt/stripe/hermesAgent` (permessi standard homelab `777` o `775`, owner `olindo:k8s`)
  * Istanza Principale: `/mnt/stripe/hermesAgent/HermesMain`
  * Cartella Comune: `/mnt/stripe/hermesAgent/common/prj`
  * Binario Web Shell: `/mnt/stripe/truenas-docker/hermes/bin/ttyd` (architettura `x86_64`)

### 3.2 Mount Dichiarativi all'Interno del Container `hermes-main`
* `/opt/data`: mount dell'istanza (`HermesMain`). Costituisce la `HERMES_HOME` e la root di sicurezza `HERMES_WRITE_SAFE_ROOT`.
* `/opt/data/common`: mount del blocco comune (`common/`), contenente `prj/`.
* `/usr/local/bin/ttyd`: mount `:ro` del binario statico compilato di `ttyd`.
* Symlink interno: `/hermesAgent/common -> /opt/data/common` (o `/hermesAgent -> /opt/data`) per risolvere qualsiasi chiamata a percorso assoluto.

---

## 4. Vincoli Architetturali e Golden Rules Applicabili (da `GEMINI.md`)

1. **Configurazione Dichiarativa Immutabile**:
   * Qualsiasi modifica ai container Docker deve essere espressa esclusivamente all'interno dei file Compose versionati: `docker/orbstack/docker-compose.yaml` e `docker/truenas/docker-compose.yaml`.
   * Vietate modifiche manuali a caldo o container non dichiarati.
2. **Schema Permessi ZFS / NFS Homelab**:
   * Tutti i dati residenti sul pool `stripe` destinati ai workload devono tassativamente rispettare l'ownership `olindo:k8s` con permessi `chmod 775` o `777`, garantendo compatibilità universale con init-container root (UID 0) e processi unprivileged (UID 1000 `hermes`).
3. **Autenticazione Passwordless SSH**:
   * Qualsiasi comando di sincronizzazione o automazione verso TrueNAS (`10.10.20.50`) deve basarsi esclusivamente su scambio di chiavi pubbliche (`ssh -o BatchMode=yes`).
4. **Zero Data Loss & Safe Additive Sync**:
   * La sincronizzazione dello stato di Hermes non deve mai cancellare arbitrariamente file di lavoro (`rsync -auz` senza `--delete` automatico distruttivo).
5. **Protocollo Test-Driven (§12)**:
   * Ogni singolo step di modifica deve essere seguito da un test di verifica reale oggettivo (ispezione curl, validazione permessi, test di binding porta, esecuzione del comando dentro il container).

---

## 5. Aree di Attenzione Critica & Quesiti Specifici per la Revisione

1. **Iniezione del Tab "Terminale" nella WebGUI di Hermes**:
   * Il frontend di Hermes Agent v0.22.5 è un bundle SPA compilato servito da FastAPI (`HERMES_WEB_DIST=/opt/hermes/hermes_cli/web_dist`).
   * Qual è il meccanismo più robusto, pulito e mantenibile per integrare la voce "Terminale" nella UI e garantire che le connessioni WebSocket di `ttyd` (`127.0.0.1:7681`) vengano veicolate senza conflitti con i router WebSocket nativi di Hermes (`/api/chat/ws`)?
2. **Ciclo di Vita del Processo `ttyd` e Supervisore s6**:
   * Il container Hermes utilizza `s6-overlay`. È preferibile avviare `ttyd` come servizio s6 dedicato (`/run/service` o `/etc/s6-overlay/s6-rc.d`), oppure tramite un wrapper di entrypoint trasparente?
3. **Flush e Coerenza dei Database SQLite durante il Sync TrueNAS → Mac**:
   * L'arresto preventivo di `hermes-main` prima dell'rsync su TrueNAS azzera i rischi di corruzione WAL di SQLite. È necessario prevedere un timeout di sicurezza o un fallback nel caso in cui `docker stop` impieghi più tempo del previsto?
4. **Gestione Conflitti e Risoluzione Permessi su Mac**:
   * Su macOS, i file in `/Users/olindo/hermesAgent/common/prj` appartengono all'utente `olindo` (UID 501). Quando vengono sincronizzati su TrueNAS (dove `olindo` è tipicamente UID 1000 e `k8s` è GID 1000), il comando di normalizzazione `chown -R olindo:k8s` in `orbstack_failover.sh` è sufficiente a prevenire discrepanze di accesso?

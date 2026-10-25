---
title: "Piano: Migrazione Hermes Agent e LiteLLM da Kubernetes a Docker su TrueNAS SCALE"
type: plan
status: active
certified_for_ai: true
created_at: 2026-10-22
updated_at: 2026-10-22
supersedes: "[[hermes-agent-deployment]], [[litellm-proxy-kubernetes-deployment]]"
tags:
  - "#plan"
  - "#hermes"
  - "#litellm"
  - "#docker"
  - "#truenas"
  - "#homepage"
---

# Piano: Migrazione Hermes Agent + LiteLLM da K8s a Docker su TrueNAS SCALE

> [!NOTE]
> Stato **draft** (revisionato e validato): solo pianificazione, nessun comando operativo eseguito. L'esecuzione richiede approvazione per singolo passo (Execution Protocol test-driven). Al via libera i due piani sostituiti verranno archiviati (`status: archived`, `superseded_by`) e questo promosso ad `active`.

## 1. Decisioni dell'utente (2026-10-22)

### 1.1 Decisioni architetturali di base
| # | Tema | Decisione |
| :--- | :--- | :--- |
| 1 | LiteLLM | **Migra anche LiteLLM** su Docker TrueNAS insieme a Hermes |
| 2 | Privilegi K8s di Hermes | **A**: stessi di oggi (`cluster-admin` equivalente), comportamento invariato |
| 3 | Esposizione | **Solo interna**: nessun accesso esterno / Cloudflare / OAuth2 |
| 4 | Dati Hermes | **Riuso as-is** di `/mnt/stripe/hermesAgent/HermesMain` (nessuna copia/pulizia) |
| 5 | Alias DNS | **Rimossi** (`hermes`, `hermes-internal`, `litellm-internal`): accesso solo IP:porta |
| 6 | Dati LiteLLM | **Database nuovo** (nessun dump/restore da CNPG) |

### 1.2 Decisioni tecniche di consolidamento (post-revisione Argon)
| # | Tema | Scelta adottata | Motivazione |
| :--- | :--- | :--- | :--- |
| 7 | Storage `litellm-postgres` | **Dataset ZFS dedicato** `stripe/truenas-docker/litellm-postgres` con `recordsize=8k` e `chown 999:999` (`chmod 700`) | Allinea il block size ZFS alle pagine da 8 KB di PostgreSQL evitando write amplification, garantisce i permessi per `UID 999` e consente snapshot ZFS atomici indipendenti. |
| 8 | Bootstrap Virtual Key Hermes | **Comando API one-shot in FASE 2** (`POST /key/generate`) | Mantiene lo stack Docker Compose snello (senza container init aggiuntivi) e importa deterministicamente nel nuovo DB la stessa chiave già cifrata in SOPS (`HERMES_LITELLM_KEY`). |
| 9 | Strategia `kubeconfig` fuori dal cluster | **Verifica in FASE 0 e passaggio a certificato client X.509 / admin statico su VIP `10.10.20.55` se necessario** | Evita che la cancellazione del namespace `hermes` e del relativo ServiceAccount in FASE 5 invalidi il token usato da Hermes su TrueNAS. |
| 10 | Rete Docker Compose | **Rete di default condivisa** dello stack `servarr/truenas-docker/docker-compose.yaml` (`litellm-postgres` senza `ports:` sull'host) | Si integra nel file Compose esistente con il minimo overhead; Hermes contatta `http://litellm:4000/v1` e LiteLLM contatta `litellm-postgres:5432` via DNS interno Docker. |
| 11 | Cutover Hermes e Decommissioning | **Scale-down dichiarativo (`replicas: 0`) in FASE 3 e rimozione completa in FASE 5** | Rispetta le Golden Rules (vietati `kubectl scale/patch` manuali non tracciati), evita il doppio gateway concorrente sullo stesso dataset e preserva i manifest K8s + DB CNPG come paracadute fino alla validazione finale. |
| 12 | Miglioramenti operativi inclusi | **Matrice di Rollback esplicita**, **estrazione SOPS → file runtime (`600`)**, **integrazione `Power_Sequence`/NUT e test con Ollama spenti** | Garantisce reversibilità immediata in ogni fase, protezione delle credenziali su disco e resilienza all'avvio a freddo dell'homelab. |

## 2. Stato attuale (verificato nel repo)

### Hermes
| Elemento | Stato |
| :--- | :--- |
| Deploy | Kustomize + Helm `jyje/hermes-agent-helm` 1.0.0 in `hermes-agent/` (ns `hermes`) |
| Immagine / comando | `nousresearch/hermes-agent` (`tag: ""` nel chart, da verificare sul pod), `hermes gateway run`, dashboard `9119` |
| Persistenza | PV NFS `10.10.20.50:/mnt/stripe/hermes-agent` (già su TrueNAS, `ReadWriteMany`, `Retain`) |
| Segreti | `secrets-sops/hermes-secrets.enc.yaml`, `secrets-sops/hermes-kubeconfig.enc.yaml` |
| RBAC | `hermes-rbac.yaml`: `cluster-admin` al ServiceAccount del pod |
| Sidecar | `mcp-kubernetes` = `sleep infinity` (placeholder, non migrato) |
| Ingress | `ingress.enabled: false`; alias DNS `hermes`, `hermes-internal` in `rete.json` r.1100-1101 |

### LiteLLM
| Elemento | Stato |
| :--- | :--- |
| Deploy | Chart `oci://ghcr.io/berriai/litellm-helm` 1.106.2, valori in `litellm/litellm-values.yaml` (ns `litellm`) |
| Immagine | `ghcr.io/berriai/litellm:1.106.2` (già pinnata) |
| Database | CNPG `postgres-main-rw.cnpg-system.svc.cluster.local:5432`, DB e ruolo `litellm` |
| Segreti | `secrets-sops/litellm-secrets.enc.yaml` (master key, salt, UI password, virtual key Hermes), `litellm-db-password.enc.yaml` |
| Config | 5 modelli (`big-chat`, `big-alt`, `vision`, `vision-light`, `embed`), Mac Studio order 1 e `lxc-ollama` order 2; `router_settings` con cooldown 60 s |
| Esposizione | IngressRoute `litellm-internal.pindaroli.org` (Traefik VIP `10.10.20.56`) |
| Job | `litellm-sync-hermes-key` (post-install/upgrade), sostituito da chiamata API one-shot in FASE 2 |
| Consumer noti | Solo Hermes. RAGFlow è escluso (diretto su Ollama). Da riverificare in FASE 0 |

### Homepage
- `homepage/homepage.yaml` r.433-437 e `homepage/homepage-local.yaml` r.409-413: card Hermes (`href` esterno/interno, `siteMonitor` su DNS K8s).
- `homepage/homepage-local.yaml` r.419-423: card LiteLLM (`href` `litellm-internal.../ui`, `siteMonitor` su DNS K8s).
- Da verificare in FASE 0: eventuale presenza di una card LiteLLM in `homepage.yaml` e percorso della sorgente di `services.yaml` di Homepage TrueNAS.

Destinazione: `servarr/truenas-docker/docker-compose.yaml` (TrueNAS `10.10.20.50`, root `/mnt/stripe/truenas-docker/`), stesso pattern di Dozzle e Bitmagnet ([[dozzle-truenas-docker-integration]], [[bitmagnet-truenas-docker-integration]]).

## 3. Architettura target

```mermaid
flowchart LR
  U[LAN] -->|"http 10.10.20.50:9119"| H[hermes-agent]
  U -->|"http 10.10.20.50:4000/ui"| L[litellm]
  H -->|"http://litellm:4000/v1 (rete compose default)"| L
  L -->|"5432 (rete compose default)"| P[(litellm-postgres)]
  L -->|"11434"| M[Mac Studio Ollama]
  L -->|"11434"| X[lxc-ollama]
  H -->|"kubeconfig / talosconfig (:ro)"| K[Talos K8s API 10.10.20.55:6443]
```

1. **LiteLLM** (`ghcr.io/berriai/litellm:1.106.2`, porta host `4000`, da verificare libera) con `config.yaml` derivato da `proxy_config` del values, versionato nel repo e montato `:ro`.
2. **`litellm-postgres`**: container PostgreSQL pinnato dedicato (`postgres:16-alpine`, pattern `bitmagnet-postgres`), dati sul dataset ZFS dedicato `/mnt/stripe/truenas-docker/litellm-postgres` (`recordsize=8k`, `999:999`), sulla rete compose di default, senza porte esposte sull'host. Sostituisce il database `litellm` su CNPG.
3. **Hermes** (`nousresearch/hermes-agent:<TAG_PINNATO>`, porta host `9119`) con bind mount diretto `/mnt/stripe/hermesAgent/HermesMain` montato in `/opt/data` (dataset già con permessi `777`, `olindo:k8s`) e mount `:ro` di `kubeconfig` e `talosconfig`.
4. **Indirizzamento**: Hermes → LiteLLM tramite nome servizio compose `http://litellm:4000/v1` sulla rete di default dello stack, senza IP hardcoded. Ordine di avvio governato da `depends_on` con `condition: service_healthy`.
5. **Segreti e credenziali runtime**: `.env` su TrueNAS e file `kubeconfig`/`talosconfig` estratti da SOPS con permessi `600` (directory `700`), mai committati in chiaro in git.
6. **Solo interno**: nessun Traefik / OAuth2 / Cloudflare. L'accesso avviene esclusivamente su `http://10.10.20.50:9119` e `http://10.10.20.50:4000`.

### 3.1 Specifica dichiarativa dei servizi (`servarr/truenas-docker/docker-compose.yaml`)

Frammento da integrare nella sezione `services:` del file `servarr/truenas-docker/docker-compose.yaml` (sulla rete di default dello stack):

```yaml
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
    # Nessun port mapping sull'host: raggiungibile come litellm-postgres:5432 nella rete compose default

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
    image: nousresearch/hermes-agent:REPLACE_WITH_PINNED_TAG
    container_name: hermes-agent
    restart: unless-stopped
    ports:
      - "9119:9119"
    environment:
      HERMES_DASHBOARD: "1"
      HERMES_AUTH_PROVIDER: "password"
      HERMES_DASHBOARD_PASSWORD: ${HERMES_DASHBOARD_PASSWORD}
      OPENAI_API_BASE: "http://litellm:4000/v1"
      OPENAI_API_KEY: ${HERMES_LITELLM_KEY}
      KUBECONFIG: "/root/.kube/config"
      TALOSCONFIG: "/root/.talos/config"
    volumes:
      - /mnt/stripe/hermesAgent/HermesMain:/opt/data
      - /mnt/stripe/truenas-docker/hermes/kubeconfig:/root/.kube/config:ro
      - /mnt/stripe/truenas-docker/hermes/talosconfig:/root/.talos/config:ro
    depends_on:
      litellm:
        condition: service_healthy
    healthcheck:
      test: ["CMD", "curl", "-fsS", "http://localhost:9119/api/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 30s
```

*(Nota: i path interni al container di Hermes — `/opt/data`, `/root/.kube/config`, `/root/.talos/config` e i nomi esatti delle variabili d'ambiente — verranno confermati in FASE 0 ispezionando il Deployment K8s attuale prima del commit).*

## 4. Decisioni risolte e conseguenze

### 4.1 Alias DNS: rimossi
- Rimozione di `hermes`, `hermes-internal` e `litellm-internal` da `rete.json` (r.1100-1101 e r.1119) e dai relativi host override Unbound su OPNsense. Verifica preventiva in FASE 0 che non esistano record Cloudflare o altri riferimenti.
- Gli IngressRoute K8s di LiteLLM e il certificato dedicato vengono rimossi insieme alla release K8s in FASE 5.

### 4.2 Privilegi Kubernetes di Hermes: A (invariati e indipendenti dal namespace `hermes`)
- Hermes mantiene accesso completo al cluster (`cluster-admin`) e ai nodi Talos tramite `kubeconfig` e `talosconfig` montati `:ro` da `/mnt/stripe/truenas-docker/hermes/` (directory `700`, file `600`).
- **Salvaguardia post-decommissioning**: in FASE 0 si controlla il contenuto di `secrets-sops/hermes-kubeconfig.enc.yaml`:
  - Deve puntare al VIP API `https://10.10.20.55:6443`.
  - Se utilizza un token legato al ServiceAccount del namespace `hermes`, prima della FASE 5 viene sostituito in SOPS e su TrueNAS con un `kubeconfig` basato su certificato client X.509 statico (admin Talos), così che la rimozione del namespace `hermes` non revochi l'accesso di Hermes.

### 4.3 Dati LiteLLM: database nuovo e bootstrap deterministico
- Nessun `pg_dump`/restore: il dataset ZFS `stripe/truenas-docker/litellm-postgres` parte vuoto e le migrazioni Prisma creano lo schema al primo avvio.
- Si mantiene invariata la `LITELLM_SALT_KEY` proveniente da `secrets-sops/litellm-secrets.enc.yaml` per coerenza crittografica.
- La virtual key di Hermes (`HERMES_LITELLM_KEY`, già presente in SOPS) viene ricreata in modo deterministico in FASE 2 tramite chiamata API `POST /key/generate` autenticata con `LITELLM_MASTER_KEY`.
- Il database `litellm` su CNPG resta intatto fino alla FASE 5 come via di ritorno immediata.

### 4.4 Ordine di avvio (`Power_Sequence`), NUT e comportamento con Ollama spenti
- Con lo spostamento su TrueNAS (`10.10.20.50`), LiteLLM e Hermes si avviano automaticamente con il demone Docker di TrueNAS (`restart: unless-stopped`), prima ancora che il cluster Kubernetes Talos sia operativo.
- Se TrueNAS completa il boot prima di Mac Studio (`olindo-macstudio.pindaroli.org:11434`) o di `lxc-ollama` (`lxc-ollama.pindaroli.org:11434` su `pve3`), LiteLLM deve restare `healthy` (l'endpoint `/health/liveliness` verifica il proxy, non i modelli upstream) e mettere in cooldown temporaneo (`60 s`) i backend non raggiungibili finché non tornano online. Questo comportamento viene verificato esplicitamente in FASE 2.
- Nella documentazione `[[Power_Sequence]]` verrà registrato che la disponibilità dell'inferenza AI dipende da TrueNAS (gateway + agente) + almeno uno tra Mac Studio e `pve3`/`lxc-ollama`.
""
## 5. Modifiche Homepage (Homepage Operations Mandate)

Da eseguire rigorosamente tramite la skill `.agents/skills/homepage-manager/` (allineamento simmetrico, verifica icone a 7 livelli, rollout K8s, restart TrueNAS).

| File | Card | Modifica |
| :--- | :--- | :--- |
| `homepage/homepage.yaml` (K8s esterna) | Hermes | Rimozione della card: servizio solo interno, nessun accesso esterno |
| `homepage/homepage.yaml` | LiteLLM | Se presente, rimozione per lo stesso motivo |
| `homepage/homepage-local.yaml` (K8s interna) | Hermes | `href: http://10.10.20.50:9119`, `siteMonitor: http://10.10.20.50:9119/api/health`, descrizione `(TrueNAS Docker)` |
| `homepage/homepage-local.yaml` | LiteLLM | `href: http://10.10.20.50:4000/ui`, `siteMonitor: http://10.10.20.50:4000/health/liveliness`, descrizione `(TrueNAS Docker)` |
| Homepage TrueNAS (`/mnt/stripe/truenas-docker/homepage/services.yaml`) | Hermes e LiteLLM | Nuove card simmetriche con gli stessi URL e `siteMonitor` (sorgente repo verificata in FASE 0) |

Verifica icone `hermes.png` e `sh-litellm` con i 7 livelli della skill. Gli `href` usano esclusivamente IP e porta, senza hostname.
""
## 6. Fasi operative

Ogni singolo passo prevede spiegazione preventiva, approvazione esplicita dell'utente e test di verifica reale prima di procedere al passo successivo. **Ordine tassativo: prima LiteLLM, poi Hermes.**

### FASE 0: Raccolta dati e pre-check (sola lettura)

1. **Verifica immagine pinnata, env e mount path di Hermes su K8s**:
   ```bash
   kubectl get pod -n hermes -l app.kubernetes.io/name=hermes-agent -o jsonpath='{.items[0].spec.containers[0].image}{"\n"}'
   ```
   ```bash
   kubectl get deployment -n hermes -o yaml
   ```

2. **Ispezione segreti SOPS e verifica natura del `kubeconfig`**:
   ```bash
   sops -d secrets-sops/hermes-kubeconfig.enc.yaml | grep -E "server:|client-certificate-data:|token:"
   ```
   ```bash
   sops -d secrets-sops/litellm-secrets.enc.yaml | grep -E "^(  |stringData:|data:)"
   ```
   ```bash
   sops -d secrets-sops/hermes-secrets.enc.yaml | grep -E "^(  |stringData:|data:)"
   ```
   *(Criterio di superamento: confermare che il server sia `https://10.10.20.55:6443` e rilevare se il kubeconfig usa `token:` legato al ServiceAccount del namespace `hermes` o certificato client statico).*

3. **Verifica porte `4000` e `9119` libere su TrueNAS e stato dataset `/mnt/stripe/hermes-agent`**:
   ```bash
   ssh root@10.10.20.50 "ss -tulpn | grep -E ':(4000|9119)' || echo 'Porte 4000 e 9119 libere'"
   ```
   ```bash
   ssh root@10.10.20.50 "ls -ld /mnt/stripe/hermes-agent && ls -la /mnt/stripe/hermes-agent"
   ```

4. **Verifica raggiungibilità DNS e HTTP degli endpoint Ollama da TrueNAS (VLAN 20)**:
   ```bash
   ssh root@10.10.20.50 "curl -sf -m 5 http://olindo-macstudio.pindaroli.org:11434/api/version && echo ' - Mac Studio OK'"
   ```
   ```bash
   ssh root@10.10.20.50 "curl -sf -m 5 http://lxc-ollama.pindaroli.org:11434/api/version && echo ' - lxc-ollama OK'"
   ```

5. **Verifica assenza di altri consumer di LiteLLM e riferimenti DNS residui**:
   ```bash
   grep -rnE "litellm|hermes-internal|litellm-internal" . --exclude-dir=.git --exclude-dir=wiki
   ```

6. **Individuazione sorgente `services.yaml` di Homepage TrueNAS**:
   ```bash
   find . -maxdepth 4 -name "services.yaml"
   ```

---

### FASE 1: Backup ZFS, creazione dataset Postgres ed estrazione segreti SOPS

1. **Snapshot ZFS di sicurezza del dataset `stripe/hermes-agent`**:
   ```bash
   ssh root@10.10.20.50 "zfs snapshot stripe/hermes-agent@pre-docker-migration-20261022 && zfs list -t snapshot -r stripe/hermes-agent"
   ```

2. **Creazione del dataset ZFS dedicato `stripe/truenas-docker/litellm-postgres` (`recordsize=8k`) e permessi `999:999`**:
   ```bash
   ssh root@10.10.20.50 "zfs create -o recordsize=8k stripe/truenas-docker/litellm-postgres"
   ```
   ```bash
   ssh root@10.10.20.50 "chown -R 999:999 /mnt/stripe/truenas-docker/litellm-postgres && chmod 700 /mnt/stripe/truenas-docker/litellm-postgres"
   ```
   *Test di verifica*:
   ```bash
   ssh root@10.10.20.50 "zfs get recordsize,mountpoint stripe/truenas-docker/litellm-postgres && stat -c '%a %u:%g %n' /mnt/stripe/truenas-docker/litellm-postgres"
   ```

3. **Creazione directory runtime per LiteLLM e Hermes su TrueNAS**:
   ```bash
   ssh root@10.10.20.50 "mkdir -p /mnt/stripe/truenas-docker/litellm /mnt/stripe/truenas-docker/hermes && chmod 700 /mnt/stripe/truenas-docker/hermes"
   ```

4. **Procedura SOPS → file runtime su TrueNAS (permessi `600`, mai su git)**:
   - Estrazione controllata dei valori da `secrets-sops/litellm-secrets.enc.yaml`, `secrets-sops/litellm-db-password.enc.yaml` e `secrets-sops/hermes-secrets.enc.yaml` nel file `/mnt/stripe/truenas-docker/.env` (preservando le variabili già esistenti come `HOMEPAGE_MCP_TOKEN`).
   - Estrazione del `kubeconfig` (statico su VIP `10.10.20.55`) e del `talosconfig` in `/mnt/stripe/truenas-docker/hermes/kubeconfig` e `/mnt/stripe/truenas-docker/hermes/talosconfig`.
   - *Applicazione e verifica permessi*:
     ```bash
     ssh root@10.10.20.50 "chmod 600 /mnt/stripe/truenas-docker/.env /mnt/stripe/truenas-docker/hermes/kubeconfig /mnt/stripe/truenas-docker/hermes/talosconfig && stat -c '%a %u:%g %n' /mnt/stripe/truenas-docker/.env /mnt/stripe/truenas-docker/hermes/*"
     ```

---

### FASE 2: Deploy LiteLLM e Postgres su Docker TrueNAS

1. **Preparazione di `servarr/truenas-docker/litellm/config.yaml` e aggiornamento `docker-compose.yaml` (solo `litellm-postgres` e `litellm`)**:
   - Copia di `config.yaml` in `/mnt/stripe/truenas-docker/litellm/config.yaml`.
   - *Test di validazione sintattica del Compose*:
     ```bash
     ssh root@10.10.20.50 "cd /mnt/stripe/truenas-docker && docker compose config -q && echo 'Compose syntax OK'"
     ```

2. **Avvio di `litellm-postgres` e verifica prontezza DB**:
   ```bash
   ssh root@10.10.20.50 "cd /mnt/stripe/truenas-docker && docker compose up -d litellm-postgres"
   ```
   *Test di verifica*:
   ```bash
   ssh root@10.10.20.50 "docker exec litellm-postgres pg_isready -U litellm -d litellm"
   ```

3. **Avvio di `litellm` e verifica migrazioni Prisma e stato `healthy`**:
   ```bash
   ssh root@10.10.20.50 "cd /mnt/stripe/truenas-docker && docker compose up -d litellm"
   ```
   *Test di verifica tabelle Prisma e health endpoint*:
   ```bash
   ssh root@10.10.20.50 "docker exec litellm-postgres psql -U litellm -d litellm -c '\dt'"
   ```
   ```bash
   curl -sf http://10.10.20.50:4000/health/liveliness && echo "LiteLLM Liveliness OK"
   ```

4. **Bootstrap deterministico della Virtual Key di Hermes (API one-shot)**:
   Eseguito da TrueNAS leggendo `LITELLM_MASTER_KEY` e `HERMES_LITELLM_KEY` da `.env`:
   ```bash
   ssh root@10.10.20.50 'set -a && source /mnt/stripe/truenas-docker/.env && set +a && curl -sf -X POST "http://127.0.0.1:4000/key/generate" \
     -H "Authorization: Bearer ${LITELLM_MASTER_KEY}" \
     -H "Content-Type: application/json" \
     -d "{\"key\": \"${HERMES_LITELLM_KEY}\", \"user_id\": \"hermes-agent\", \"models\": [\"big-chat\", \"big-alt\", \"vision\", \"vision-light\", \"embed\"], \"aliases\": {\"default\": \"big-chat\"}}"'
   ```
   *Test di verifica della chiave e di chiamata inferenza su `big-chat`*:
   ```bash
   ssh root@10.10.20.50 'set -a && source /mnt/stripe/truenas-docker/.env && set +a && curl -sf "http://127.0.0.1:4000/key/info" -H "Authorization: Bearer ${HERMES_LITELLM_KEY}"'
   ```
   ```bash
   ssh root@10.10.20.50 'set -a && source /mnt/stripe/truenas-docker/.env && set +a && curl -sf -X POST "http://127.0.0.1:4000/v1/chat/completions" \
     -H "Authorization: Bearer ${HERMES_LITELLM_KEY}" \
     -H "Content-Type: application/json" \
     -d "{\"model\": \"big-chat\", \"messages\": [{\"role\": \"user\", \"content\": \"Rispondi solo OK\"}], \"max_tokens\": 10}"'
   ```

5. **Test di resilienza / fallback verso `lxc-ollama` e comportamento con backend non raggiungibile**:
   - Verifica che LiteLLM risponda sempre `200 OK` su `/health/liveliness` anche in caso di indisponibilità temporanea di un backend Ollama e che il router passi correttamente da Mac Studio (order 1) a `lxc-ollama` (order 2).

---

### FASE 3: Cutover dichiarativo di Hermes su Docker TrueNAS

1. **Arresto dichiarativo del pod K8s di Hermes (nessun doppio gateway sul dataset)**:
   - Modifica dichiarativa in `hermes-agent/` impostando `replicas: 0` (o `replicaCount: 0` nel values), applicazione e verifica che nessun pod Hermes sia in esecuzione nel namespace `hermes`:
     ```bash
     kubectl get pods -n hermes
     ```
     *(Risultato atteso: `No resources found in hermes namespace`)*

2. **Aggiunta e avvio di `hermes-agent` in `servarr/truenas-docker/docker-compose.yaml`**:
   ```bash
   ssh root@10.10.20.50 "cd /mnt/stripe/truenas-docker && docker compose up -d hermes-agent"
   ```

3. **Test di verifica completi di Hermes su Docker**:
   - *Verifica stato `healthy` e HTTP dashboard*:
     ```bash
     curl -sf http://10.10.20.50:9119/api/health && echo "Hermes Health OK"
     ```
   - *Verifica comunicazione interna Docker `hermes-agent` → `http://litellm:4000/v1`*:
     ```bash
     ssh root@10.10.20.50 "docker exec hermes-agent curl -sf http://litellm:4000/health/liveliness"
     ```
   - *Verifica accesso al cluster Kubernetes e ai nodi Talos dall'interno del container Hermes*:
     ```bash
     ssh root@10.10.20.50 "docker exec hermes-agent kubectl get nodes -o wide"
     ```
     ```bash
     ssh root@10.10.20.50 "docker exec hermes-agent talosctl -n 10.10.10.11 version --short"
     ```
   - *Verifica interazione end-to-end con l'agente (prompt di test verso `big-chat` tramite LiteLLM)*.

---

### FASE 4: Homepage e pulizia DNS

1. **Aggiornamento delle 3 istanze Homepage tramite la skill `homepage-manager`**:
   - Rimozione di Hermes (e LiteLLM se presente) da `homepage/homepage.yaml` (esterna).
   - Aggiornamento di `homepage/homepage-local.yaml` (interna) e del `services.yaml` di TrueNAS con:
     - Hermes: `href: http://10.10.20.50:9119`, `siteMonitor: http://10.10.20.50:9119/api/health`
     - LiteLLM: `href: http://10.10.20.50:4000/ui`, `siteMonitor: http://10.10.20.50:4000/health/liveliness`
   - Verifica dei 7 livelli icone (`hermes.png`, `sh-litellm`), rollout K8s e restart Homepage TrueNAS.

2. **Rimozione degli alias DNS (`hermes`, `hermes-internal`, `litellm-internal`)**:
   - Rimozione da `rete.json` (r.1100-1101 e r.1119) e dagli host override di Unbound su OPNsense.
   - *Test di verifica*:
     ```bash
     python3 scripts/network/validate_network.py
     ```
     ```bash
     dig +short hermes-internal.pindaroli.org && dig +short litellm-internal.pindaroli.org
     ```
     *(Risultato atteso: output vuoto per entrambi i domini e widget Homepage verdi).*

---

### FASE 5: Decommissioning K8s (solo dopo validazione esplicita dell'utente)

> [!IMPORTANT]
> Da avviare **esclusivamente** dopo che l'utente ha confermato il funzionamento stabile di Hermes e LiteLLM su TrueNAS e verificato in FASE 0/1 che il `kubeconfig` di Hermes non dipenda dal ServiceAccount del namespace `hermes`.

1. **Rimozione dichiarativa delle release e delle risorse K8s di Hermes e LiteLLM**:
   - Disinstallazione delle release Helm `hermes` (ns `hermes`) e `litellm` (ns `litellm`), inclusi `IngressRoute` e Certificate `cert-manager`.
   - Rimozione del `ClusterRoleBinding` `hermes-rbac.yaml` (se il `kubeconfig` su TrueNAS utilizza il certificato client statico e non il ServiceAccount).
   - Rimozione del PersistentVolume `hermes-agent-pv` (`persistentVolumeReclaimPolicy: Retain` — la rimozione dell'oggetto PV su K8s **non** tocca i file su `/mnt/stripe/hermes-agent`).
   - Rimozione dei namespace `hermes` e `litellm`.
   - *Test di verifica*:
     ```bash
     kubectl get all,pv,pvc,ingressroute -A | grep -E "hermes|litellm" || echo "Pulizia K8s completata"
     ```
     ```bash
     ssh root@10.10.20.50 "docker exec hermes-agent kubectl get nodes"
     ```

2. **Rimozione database e ruolo `litellm` su CloudNativePG (`postgres-main`)**:
   - Aggiornamento dichiarativo di `postgres/cluster.yaml` (e rimozione della relativa `Database` / `Role` entry) + eventuale drop pulito sul cluster `postgres-main` secondo la scelta dell'utente.
   - Rimozione dei segreti K8s non più referenziati e archiviazione/pulizia delle directory `hermes-agent/` e `litellm/`.

---

### FASE 6: Documentazione, `Power_Sequence` e chiusura

1. Aggiornamento delle entità wiki:
   - `[[LiteLLM]]` e `[[MCP_Platform]]` (architettura Docker su TrueNAS `10.10.20.50`, porte `4000` e `9119`, DB dedicato `litellm-postgres`).
   - `[[Secret_Registry]]` (mappatura da SOPS a `/mnt/stripe/truenas-docker/.env` e `/mnt/stripe/truenas-docker/hermes/`).
   - `[[Homepage]]` (rimozione da istanza esterna, puntamento IP:porta su istanze interne).
   - `[[Power_Sequence]]` (avvio automatico di LiteLLM e Hermes con TrueNAS; dipendenza funzionale da Mac Studio / `lxc-ollama` per l'inferenza; consapevolezza della dipendenza circolare Hermes su TrueNAS ↔ K8s con storage NFS su TrueNAS).
   - `rete.json`, `storage.json` (nuovo dataset `stripe/truenas-docker/litellm-postgres`), `todo.md`, `GEMINI.md`.
2. Archiviazione dei due piani sostituiti (`[[hermes-agent-deployment]]`, `[[litellm-proxy-kubernetes-deployment]]` → `status: archived`, `superseded_by: "[[hermes-agent-truenas-docker-migration]]"`).
3. Validazione finale del repository:
   ```bash
   python3 scripts/network/validate_network.py && python3 scripts/wiki/build_wiki_context.py
   ```

## 7. Matrice di Rollback (per fase)

Poiché il decommissioning K8s (FASE 5) avviene solo dopo la validazione finale, le fasi 1–4 dispongono di una via di ritorno immediata e senza perdita di dati:

| Fase | Scenario di fallimento | Procedura di Rollback | Tempo stimato |
| :--- | :--- | :--- | :--- |
| **FASE 2 (LiteLLM Docker)** | Migrazioni Prisma fallite, conflitto porta `4000`, problemi di connessione a Ollama da TrueNAS | 1. `ssh root@10.10.20.50 "cd /mnt/stripe/truenas-docker && docker compose stop litellm litellm-postgres && docker compose rm -f litellm litellm-postgres"`<br>2. Ripristinare `docker-compose.yaml`.<br>*(Impatto zero: Hermes e LiteLLM su K8s non sono ancora stati toccati).* | < 2 min |
| **FASE 3 (Hermes Docker)** | Hermes su Docker non parte, fallisce l'autenticazione K8s o corrompe lo stato locale | 1. Fermare subito il container: `ssh root@10.10.20.50 "cd /mnt/stripe/truenas-docker && docker compose stop hermes-agent"`<br>2. Se il dataset `/mnt/stripe/hermes-agent` ha subito scritture anomale: `zfs rollback stripe/hermes-agent@pre-docker-migration-20261022`<br>3. Ripristinare `replicas: 1` nel manifest K8s di Hermes (che punta ancora al LiteLLM K8s e al DB CNPG intatti). | < 3 min |
| **FASE 4 (Homepage / DNS)** | Monitor Homepage in errore o regressione sulla validazione di rete | 1. `git revert` della modifica su `homepage/` e `rete.json`.<br>2. Ripristinare gli host override in Unbound su OPNsense.<br>3. Rieseguire la skill `homepage-manager`. | < 5 min |

## 8. Rischi residui e mitigazioni adottate

1. **Dipendenza da TrueNAS e sequenza di avvio (`Power_Sequence`)**: LiteLLM e Hermes dipendono ora dal boot di TrueNAS anziché dal cluster K8s. *Mitigazione*: `restart: unless-stopped`, verifica in FASE 2 che LiteLLM gestisca senza crash l'assenza temporanea di entrambi gli Ollama, aggiornamento di `[[Power_Sequence]]`.
2. **Dipendenza circolare (Hermes su TrueNAS gestisce un cluster K8s i cui PV NFS risiedono su TrueNAS)**: se TrueNAS è offline, sono offline sia i PV NFS del cluster sia Hermes. *Mitigazione*: rischio accettato poiché già intrinseco nell'architettura attuale (il PV di Hermes era già su NFS TrueNAS); spostare Hermes direttamente su TrueNAS elimina anzi il livello intermedio K8s/NFS per l'agente stesso, rendendolo operativo anche quando il control plane K8s è degradato.
3. **Credenziali K8s/Talos su filesystem TrueNAS e traffico HTTP interno su VLAN 20**: *Mitigazione*: file `kubeconfig`, `talosconfig` e `.env` protetti con permessi `600` (directory `700`), montati in sola lettura (`:ro`) nel container; esposizione limitata alla sola rete interna fidata senza Ingress esterni.
4. **Ripartenza da zero del database LiteLLM**: perdita dello storico di spesa e delle chiavi create manualmente da UI. *Mitigazione*: bootstrap deterministico della virtual key di Hermes in FASE 2 e conservazione del DB `litellm` su CNPG fino alla FASE 5.

## 💾 Stato di Ripristino (AI Save-State)
- **Fase Attiva**: Migrazione Completata con Successo (Fasi 0, 1, 2, 3, 4, 6 completate; Fase 5 pronta al riavvio cluster K8s)
- **Ultima Azione Completata**: LiteLLM (con DB PostgreSQL ZFS 8k dedicato) e Hermes Agent (v2026.7.20 con binari statici kubectl e talosctl montati) sono 100% attivi, healthy e verificati su TrueNAS Docker (`10.10.20.50:4000` e `10.10.20.50:9119`). Inference test su big-chat eseguita con successo via Mac Studio Ollama. Homepage K8s e TrueNAS riallineate. Alias DNS rimossi da rete.json e Unbound OPNsense.
- **Prossimo Passo Operativo**: Al prossimo avvio del cluster compute (PVE1/2/3), esecuzione di FASE 5 (decommissioning dichiarativo delle vecchie release K8s e pulizia DB su postgres-main).
- **Blocchi/Decisioni Pendenti**: Nessun blocco. Workload perfettamente operativi su TrueNAS SCALE.

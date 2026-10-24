---
title: "Piano: Migrazione Garage S3 e Scrutiny da TrueNAS Apps a Docker Compose"
type: plan
status: completed
certified_for_ai: true
created_at: 2026-10-24
completed_at: 2026-10-24
tags:
  - "#plan"
  - "#truenas"
  - "#docker"
  - "#garage"
  - "#scrutiny"
  - "#storage"
  - "#homepage"
---

# Piano Operativo: Migrazione Garage S3 e Scrutiny da TrueNAS Apps a Docker Compose

> **Percorso Canonico Wiki**: `wiki/plans/garage-scrutiny-truenas-docker-migration.md` (alias: `[[garage-scrutiny-truenas-docker-migration]]`)
> **Comando di Attivazione**: `/resume [[garage-scrutiny-truenas-docker-migration]]`
> **Governance Collegata**: [[TrueNAS]], [[Homepage]], [[servarr-truenas-permanent-migration]], [[dozzle-truenas-docker-integration]], [[SCHEMA]].

---

## 1. Contesto, Obiettivo e Decisioni Architetturali (`/grill-me`)

Su **TrueNAS SCALE (`10.10.20.50`)** erano rimaste attive le ultime due applicazioni gestite tramite il catalogo nativo TrueNAS Apps (`ix-apps`):
1. **`garage`** (`ix-garage-garage-1`, basata sul template `ix-app` v1.4.4 $\rightarrow$ v1.4.7): Object Storage S3 (`dxflrs/garage:v2.3.0`) utilizzato da CloudNativePG (`postgres-main` WAL archiving), Velero e RAGFlow (`10.10.20.50:3900` / `:3903`).
2. **`scrutiny`** (`ix-scrutiny-scrutiny-1`, chart community v1.3.14 $\rightarrow$ v1.3.17): Monitoraggio S.M.A.R.T. e serie storiche InfluxDB (`ghcr.io/analogj/scrutiny:v0.9.5-omnibus`) esposto sulle porte `31054` (WebUI/API) e `31055` (InfluxDB).

L'obiettivo di questo piano è **migrare entrambi i servizi direttamente nello stack dichiarativo principale `/mnt/stripe/truenas-docker/docker-compose.yaml` (`docker/truenas/docker-compose.yaml`)**, mantenendo invariati tutti i puntamenti di rete (porte e IP), preservando integralmente i dati e lo storico, allineando la dashboard Homepage di TrueNAS (modalità `ECO`) ed eliminando definitivamente le due app dal catalogo TrueNAS.

### 1.1 Matrice delle Decisioni Approvate dall'Utente

| # | Ambito | Decisione Approvata | Specifica Tecnica Vincolante |
| :- | :--- | :--- | :--- |
| **1** | **Persistenza Dati & Volumi** | **Copia storico Scrutiny in `/mnt/stripe/truenas-docker/scrutiny` + Mantenimento `/mnt/oliraid/garage-data`** | Prima di fermare/eliminare l'app TrueNAS `scrutiny`, i volumi `/mnt/.ix-apps/app_mounts/scrutiny/{config,influxdb}` (`36 KB` `scrutiny.db` + `2.2 MB` InfluxDB) vengono copiati in `/mnt/stripe/truenas-docker/scrutiny/{config,influxdb}` (entrando così nel perimetro di snapshot e replica ZFS di `truenas-docker`). `garage` mantiene il bind mount diretto su `/mnt/oliraid/garage-data:/var/lib/garage` (`3.3 GB`). |
| **2** | **Versionamento Immagini** | **Tag stabili validati (`v2.3.0` e `v0.9.5-omnibus`)** | Si mantiene `dxflrs/garage:v2.3.0` durante il cutover (zero variabili sul formato DB SQLite/S3, con eventuale upgrade a `v2.4.1` in un passo dedicato successivo) e `ghcr.io/analogj/scrutiny:v0.9.5-omnibus` (già ultima release stabile upstream). |
| **3** | **Rete Garage & `garage.toml`** | **`network_mode: host` + Riallineamento `rpc_public_addr`** | `garage` gira con `network_mode: host` (zero overhead NAT per S3 `:3900`, RPC `:3901`, Web `:3902`, Admin `:3903`) e `group_add: ["568"]`. In `/mnt/oliraid/garage-data/garage.toml` viene aggiornato `rpc_public_addr` dal vecchio IP VLAN 10 (`10.10.10.50:3901`) a `10.10.20.50:3901`. |
| **4** | **Runtime Scrutiny** | **`privileged: true` + `/dev:/dev:ro` + Porte `31054`/`31055` + `TZ=Europe/Rome`** | `scrutiny` mantiene `/dev:/dev:ro` e `/run/udev:/run/udev:ro` con `privileged: true` (discovery automatica di tutti i dischi SATA/NVMe senza dipendere dalle lettere `/dev/sdX`), porte `31054:8080` e `31055:8086`, e timezone allineata a `TZ=Europe/Rome`. |
| **5** | **Allineamento Homepage** | **Aggiunta in Homepage TrueNAS (`ECO`) + Invarianza Homepage K8s (`FULL`)** | `homepage/homepage.yaml` e `homepage/homepage-local.yaml` su K8s puntano già a `http://10.10.20.50:3903/health` e `http://10.10.20.50:31054` e non richiedono modifiche. Le due card `Garage` e `Scrutiny` vengono aggiunte sotto `"Infrastructure Hosts"` in `/mnt/stripe/truenas-docker/homepage/services.yaml` (attiva in modalità `ECO`). |
| **6** | **Decommissioning TrueNAS Apps & Gate Ansible** | **Rimozione definitiva da TrueNAS Apps + Gate 3 in `ensure_storage_on.yml`** | Dopo il cutover e la validazione dei container Compose, le app `garage` e `scrutiny` vengono eliminate dal catalogo TrueNAS (`midclt call app.delete`), lasciando 0 app nel catalogo (mantenendo attivo il pool Apps per `docker.service`). Le porte `3900` (Garage S3) e `31054` (Scrutiny) vengono aggiunte al `Gate 3` di `ansible/playbooks/infrastructure/ensure_storage_on.yml`. |

---

## 2. Specifica Dichiarativa dei Servizi (`docker/truenas/docker-compose.yaml`)

Blocco da aggiungere in coda a `docker/truenas/docker-compose.yaml` (e sincronizzare in `/mnt/stripe/truenas-docker/docker-compose.yaml`):

```yaml
  # --- Garage S3 Object Storage ---
  garage:
    image: dxflrs/garage:v2.3.0
    container_name: garage
    network_mode: host
    restart: unless-stopped
    group_add:
      - "568"
    environment:
      - TZ=Europe/Rome
      - GARAGE_CONFIG_FILE=/var/lib/garage/garage.toml
    volumes:
      - /mnt/oliraid/garage-data:/var/lib/garage
    healthcheck:
      test: ["CMD", "/garage", "status"]
      interval: 30s
      timeout: 5s
      retries: 3

  # --- Scrutiny S.M.A.R.T. Disk Health & InfluxDB ---
  scrutiny:
    image: ghcr.io/analogj/scrutiny:v0.9.5-omnibus
    container_name: scrutiny
    restart: unless-stopped
    privileged: true
    user: "0:0"
    group_add:
      - "568"
    ports:
      - "31054:8080"
      - "31055:8086"
    environment:
      - TZ=Europe/Rome
      - UMASK=002
      - UMASK_SET=002
      - SCRUTINY_WEB_LISTEN_HOST=0.0.0.0
      - SCRUTINY_WEB_LISTEN_PORT=8080
      - SCRUTINY_WEB_DATABASE_LOCATION=/opt/scrutiny/config/scrutiny.db
      - SCRUTINY_WEB_INFLUXDB_HOST=127.0.0.1
      - SCRUTINY_WEB_INFLUXDB_PORT=8086
      - COLLECTOR_API_ENDPOINT=http://127.0.0.1:8080
    volumes:
      - /mnt/stripe/truenas-docker/scrutiny/config:/opt/scrutiny/config
      - /mnt/stripe/truenas-docker/scrutiny/influxdb:/opt/scrutiny/influxdb
      - /dev:/dev:ro
      - /run/udev:/run/udev:ro
    healthcheck:
      test: ["CMD", "curl", "--request", "GET", "--silent", "--output", "/dev/null", "--show-error", "--fail", "http://127.0.0.1:8080/api/health"]
      interval: 30s
      timeout: 5s
      retries: 5
      start_period: 15s
```

---

## 3. Mappa Completa dei File da Modificare

| Azione | Percorso File | Descrizione |
| :--- | :--- | :--- |
| **MODIFICA** | `docker/truenas/docker-compose.yaml` | Aggiunta dei servizi `garage` (`dxflrs/garage:v2.3.0`, `network_mode: host`) e `scrutiny` (`ghcr.io/analogj/scrutiny:v0.9.5-omnibus`, porte `31054:8080` e `31055:8086`). |
| **MODIFICA** | `/mnt/oliraid/garage-data/garage.toml` *(su TrueNAS)* | Aggiornamento di `rpc_public_addr` da `"10.10.10.50:3901"` a `"10.10.20.50:3901"`. |
| **MODIFICA** | `/mnt/stripe/truenas-docker/homepage/services.yaml` *(su TrueNAS)* | Aggiunta delle card `Garage` (`http://10.10.20.50:3903/health`) e `Scrutiny` (`http://10.10.20.50:31054`) nella sezione `"Infrastructure Hosts"`. |
| **MODIFICA** | `ansible/playbooks/infrastructure/ensure_storage_on.yml` | Aggiunta di `{ name: "Garage S3 API", port: 3900 }` e `{ name: "Scrutiny WebUI", port: 31054 }` nel `Gate 3`. |
| **MODIFICA** | `storage.json` | Aggiornamento della nota di `garage_data` per riflettere la gestione tramite `docker-compose.yaml` su TrueNAS anziché Custom App. |

---

## 4. Fasi Operative di Implementazione (Protocollo Test-Driven §12)

> [!IMPORTANT]
> **PROTOCOLLO D'ESECUZIONE**: Ogni singolo passo deve essere preceduto da spiegazione ed esplicita approvazione dell'utente, seguito dal relativo test di verifica reale prima di procedere al passo successivo.

### FASE 1: Preparazione Volumi Scrutiny, Aggiornamento `garage.toml` e File Dichiarativi
1. Creare le directory di destinazione `/mnt/stripe/truenas-docker/scrutiny/{config,influxdb}` su TrueNAS e copiare preventivamente (`cp -a`) i dati attuali da `/mnt/.ix-apps/app_mounts/scrutiny/`:
   ```bash
   ssh -o BatchMode=yes olindo@10.10.20.50 "sudo mkdir -p /mnt/stripe/truenas-docker/scrutiny && sudo cp -a /mnt/.ix-apps/app_mounts/scrutiny/config /mnt/stripe/truenas-docker/scrutiny/ && sudo cp -a /mnt/.ix-apps/app_mounts/scrutiny/influxdb /mnt/stripe/truenas-docker/scrutiny/"
   ```
2. Aggiornare `rpc_public_addr` in `/mnt/oliraid/garage-data/garage.toml` da `10.10.10.50:3901` a `10.10.20.50:3901`:
   ```bash
   ssh -o BatchMode=yes olindo@10.10.20.50 "sudo sed -i 's/10.10.10.50:3901/10.10.20.50:3901/g' /mnt/oliraid/garage-data/garage.toml"
   ```
3. Aggiornare `docker/truenas/docker-compose.yaml`, `ansible/playbooks/infrastructure/ensure_storage_on.yml` e `storage.json` nel repository Git, e sincronizzare `docker-compose.yaml` in `/mnt/stripe/truenas-docker/docker-compose.yaml`.
4. **Test di Verifica Fase 1**:
   ```bash
   ssh -o BatchMode=yes olindo@10.10.20.50 "sudo ls -la /mnt/stripe/truenas-docker/scrutiny/config/scrutiny.db && sudo grep rpc_public_addr /mnt/oliraid/garage-data/garage.toml && cd /mnt/stripe/truenas-docker && sudo docker compose config -q" && echo "Fase 1 OK"
   ```

---

### FASE 2: Cutover da TrueNAS Apps a Docker Compose (`garage` e `scrutiny`)
1. Fermare le due app nel catalogo TrueNAS (`garage` e `scrutiny`) ed eseguire un ultimo sync incrementale di `scrutiny` a container fermo per garantire consistenza SQLite/InfluxDB:
   ```bash
   ssh -o BatchMode=yes olindo@10.10.20.50 "sudo midclt call -j app.stop garage && sudo midclt call -j app.stop scrutiny && sudo cp -a /mnt/.ix-apps/app_mounts/scrutiny/config/. /mnt/stripe/truenas-docker/scrutiny/config/ && sudo cp -a /mnt/.ix-apps/app_mounts/scrutiny/influxdb/. /mnt/stripe/truenas-docker/scrutiny/influxdb/"
   ```
2. Avviare i nuovi container `garage` e `scrutiny` tramite `/mnt/stripe/truenas-docker/docker-compose.yaml`:
   ```bash
   ssh -o BatchMode=yes olindo@10.10.20.50 "cd /mnt/stripe/truenas-docker && sudo docker compose up -d garage scrutiny"
   ```
3. **Test di Verifica Fase 2**:
   - Verifica stato container, healthcheck HTTP di Garage (`:3903/health`), porta S3 (`:3900`), API/WebUI di Scrutiny (`:31054/api/health` e `:31054/api/summary` per confermare la presenza di tutti i dischi storici) e visibilità in Dozzle (`:8888`):
   ```bash
   curl -sfI http://10.10.20.50:3903/health | head -n 5
   curl -sf http://10.10.20.50:31054/api/health
   ssh -o BatchMode=yes olindo@10.10.20.50 "sudo docker exec garage /garage status && curl -sf http://127.0.0.1:31054/api/summary | jq '.data.summary | keys | length'"
   ```

---

### FASE 3: Eliminazione Definitiva dal Catalogo Apps di TrueNAS
1. Una volta certificato il funzionamento dei due container nello stack Compose, eliminare definitivamente le app `garage` e `scrutiny` dal catalogo TrueNAS:
   ```bash
   ssh -o BatchMode=yes olindo@10.10.20.50 "sudo midclt call -j app.delete garage && sudo midclt call -j app.delete scrutiny"
   ```
2. **Test di Verifica Fase 3**:
   - Verificare che `midclt call app.query` restituisca un array vuoto `[]` e che i container `garage` e `scrutiny` dello stack Compose siano ancora `Up` e rispondano regolarmente:
   ```bash
   ssh -o BatchMode=yes olindo@10.10.20.50 "sudo midclt call app.query | jq . && sudo docker ps --filter name=garage --filter name=scrutiny"
   ```

---

### FASE 4: Allineamento Homepage TrueNAS (Modalità `ECO`) e Validazione Finale
1. Aggiornare `/mnt/stripe/truenas-docker/homepage/services.yaml` su TrueNAS aggiungendo `Garage` e `Scrutiny` nella sezione `"Infrastructure Hosts"` e riavviare il container `homepage`:
   ```yaml
       - Garage:
           href: http://10.10.20.50:3903/health
           description: S3 Object Storage (TrueNAS Docker)
           icon: garage.png
           siteMonitor: http://10.10.20.50:3903/health
       - Scrutiny:
           href: http://10.10.20.50:31054
           description: Hard Drive Health & S.M.A.R.T. Monitoring
           icon: scrutiny.png
           siteMonitor: http://10.10.20.50:31054
   ```
2. **Test di Verifica Fase 4**:
   - Verifica presenza e rendering delle card `Garage` e `Scrutiny` su `https://home-internal.pindaroli.org/` e validazione sintattica di `ensure_storage_on.yml` e `validate_network.py`:
   ```bash
   curl -sk https://home-internal.pindaroli.org/ | grep -E "Garage|Scrutiny"
   ansible-playbook ansible/playbooks/infrastructure/ensure_storage_on.yml --syntax-check
   python3 scripts/network/validate_network.py && python3 scripts/wiki/build_wiki_context.py
   ```

---

## 💾 Stato di Ripristino (AI Save-State)
- **Fase Attiva**: Piano Completato con Successo ✅
- **Ultima Azione Completata**: Fase 1 (preparazione volumi e configurazioni), Fase 2 (cutover e avvio container healthy), Fase 3 (decommissioning catalogo TrueNAS Apps, `midclt call app.query` = `[]`), Fase 4 (allineamento card Homepage TrueNAS ECO, validazione sintattica Ansible e rete).
- **Prossimo Passo Operativo**: Nessuno (piano completato al 100%).
- **Blocchi/Decisioni Pendenti**: Nessuno.

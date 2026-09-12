---
title: "Stack Docker Compose Failover su TrueNAS (qBittorrent, Jellyfin, Prowlarr)"
type: plan
status: active
certified_for_ai: true
created_at: 2026-09-10
tags:
  - "#arr"
  - "#truenas"
  - "#failover"
  - "#storage"
  - "#jellyfin"
  - "#qbittorrent"
  - "#prowlarr"
---

# Piano: Stack Docker Compose Failover su TrueNAS (ZFS Nativo, SQLite & Init Container)

## 1. Obiettivo e Scenario Operativo
Questo piano definisce l'architettura e l'implementazione di uno stack **Docker Compose autonomo e auto-inizializzante su TrueNAS SCALE** contenente **qBittorrent**, **Jellyfin** e **Prowlarr**.

### Scenario d'uso: Disaster Recovery & Manutenzione Programmata
Lo stack entra in funzione **esclusivamente quando il cluster Kubernetes (Talos) è SPENTO**:
- Finestre di manutenzione hardware sui nodi Proxmox (`pve1`, `pve2`, `pve3`).
- Aggiornamenti del sistema operativo Talos o Proxmox VE.
- Situazioni di emergenza energetica o blackout prolungato (nodi Talos spenti per preservare l'autonomia dell'UPS, mantenendo attivo solo il NAS).
- Manutenzioni del cluster database CloudNativePG `postgres-main`.

---

## 2. Decisioni Architetturali Consolidate

### A. Zero Dipendenze da Database Esterni (Prowlarr con SQLite Isolato)
- Su Kubernetes, Prowlarr utilizza il cluster CloudNativePG `postgres-main`. A cluster spento, `postgres-main` non è raggiungibile.
- In Docker Compose, Prowlarr opera con il motore nativo **SQLite**, **isolato in una sottodirectory dedicata**:
  ```text
  /mnt/stripe/k8s-arr/servarr-prowlarr/sqlite:/config
  ```
- **Vantaggi dell'isolamento**:
  1. I file generati da SQLite (`prowlarr.db`, `prowlarr.db-shm`, `prowlarr.db-wal`, `config.xml` locale) restano confinati in `sqlite/`.
  2. Nessun rischio di corruzione o sovrascrittura della configurazione del cluster (`/mnt/stripe/k8s-arr/servarr-prowlarr/config.xml`), garantendo un rientro trasparente su K8s.
  3. Gli indexer configurati durante la manutenzione rimangono salvati per le future sessioni di failover.

### B. qBittorrent: Nessun Database, Continuità Assoluta
- qBittorrent non fa uso di alcun database SQL (né SQLite né Postgres); memorizza lo stato nei file di configurazione (`qBittorrent.conf`) e nei file `.fastresume` in `BT_backup/`.
- Sia K8s sia Docker Compose montano **la stessa identica cartella fisica ZFS**:
  `/mnt/stripe/k8s-arr/servarr-qbittorrent:/config`
- I download temporanei usano l'NVMe ultra-veloce (`/mnt/stripe/qb_temp:/data/incomplete`).
- I download completati finiscono sul pool di massa (`/mnt/oliraid/arrdata/media:/media`).
- **Esito**: Quando il cluster K8s si riaccende, qBittorrent ritrova tutti i torrent attivi e lo stato di avanzamento al 100% allineato.

### C. Jellyfin 12.0: Database Unificato EF Core, Segregazione Storage e VA-API AMD Vega
- **Jellyfin 12.0 Core**: Adotta il database relazionale unificato `jellyfin.db` gestito da Entity Framework Core sotto `data/` (`library.db` è formalmente dismesso).
- **Segregazione Percorsi (Zero Rischi di Contesa)**: L'istanza Docker su TrueNAS opera esclusivamente su percorsi isolati usa-e-getta:
  - `/mnt/stripe/k8s-arr/servarr-jellyfin-config-truenas:/config`
  - `/mnt/stripe/k8s-arr/servarr-jellyfin-db-truenas:/config/data`
- **Tuning Hardware Silicio AMD Vega**: La CPU Ryzen 5 PRO 5650G (Cezanne APU) integra grafica Radeon Vega 8 (VCN 2.2). Supporta decodifica/codifica H.264, HEVC 10-bit, VP9 e Tone Mapping HDR, ma **NON supporta AV1**. Il file `encoding.xml` viene generato specificamente con VA-API `/dev/dri/renderD128` e AV1 disabilitato.
- **Risoluzione Blocco 403 Forbidden su Subnet L3**: Il file `network.xml` viene pre-configurato con `<EnableRemoteAccess>true</EnableRemoteAccess>` e `<LocalNetworkSubnets>10.10.0.0/16</LocalNetworkSubnets>`, abilitando la navigazione trasparente dai client su VLAN 20 verso TrueNAS (VLAN 10).
- **Nessuna Retro-Copia al Rientro**: Le cartelle `-truenas` sono usa-e-getta. Al ripristino di Proxmox, Jellyfin su LXC 2200 esegue un Cold Start dal proprio disco locale NVMe (`rpool/data/jellyfin-db/`), preservando l'integrità assoluta dell'ambiente di produzione Intel QSV.

### D. Pattern Init Container in Docker Compose
Per garantire l'avvio idempotente e sicuro senza dover eseguire comandi manuali da shell TrueNAS, lo stack integra un **Init Container** (`init-arr-bootstrap`):
1. Esegue il probe pre-flight degli endpoint Traefik di Kubernetes (`prowlarr`, `qbittorrent`, `jellyfin`) e nodi PVE/LXC (`10.10.10.11`, `10.10.10.21`, `10.10.10.31`, `10.10.20.32`) e abortisce l'avvio se il cluster è ancora attivo.
2. Crea automaticamente la sottocartella `/mnt/stripe/k8s-arr/servarr-prowlarr/sqlite` e ne pre-popola il file `config.xml` estraendo l'ApiKey dalla configurazione di produzione Kubernetes (evitando token casuali o race-condition al primo avvio) con permessi `1000:1000` (chmod 775).
3. Applica la patch di sicurezza su `qBittorrent.conf` (whitelist subnet LAN `10.0.0.0/8`, `192.168.0.0/16` e bypass CSRF/HostHeader), replicando fedelmente l'initContainer K8s.
4. Prepara le directory segregate `/mnt/stripe/k8s-arr/servarr-jellyfin-*-truenas` assicurando ownership `1000:1000` e permessi `0775`.
5. Utilizza `restart: "no"` e la direttiva `depends_on: { init-arr-bootstrap: { condition: service_completed_successfully } }` su tutti i servizi principali.

### E. Anti-Split-Brain Guardrail & Pre-Flight Probe Traefik
Per scongiurare categoricamente corruzioni di dati o accessi concorrenti non coordinati sullo storage ZFS condiviso (`stripe` e `oliraid`), l'`init-arr-bootstrap` implementa una sonda pre-flight attiva:
- Esegue il probe HTTPS/HTTP verso gli ingress Traefik:
  * `https://prowlarr-internal.pindaroli.org`
  * `https://qbittorrent-internal.pindaroli.org`
  * `https://jellyfin-internal.pindaroli.org`
- Se **almeno uno degli endpoint risponde** (ricevendo risposta HTTP/HTTPS da Traefik o dai pod K8s), l'init container termina immediatamente con `exit 1`.
- Docker Compose, vincolato dalla dipendenza `condition: service_completed_successfully`, blocca istantaneamente l'avvio di tutti i carichi applicativi (`qbittorrent`, `jellyfin`, `prowlarr`), evitando qualsiasi collisione con Kubernetes.

### F. Sincronizzazione & Caricamento Automatico Indexer da Dump JSON
Poiché su Kubernetes Prowlarr risiede su PostgreSQL (`postgres-main`), la sua istanza di failover su TrueNAS viene inizializzata con un database SQLite pulito. Per garantire che tutti gli indexer/tracker rimangano operativi senza doverli riconfigurare a mano:
- Lo stack integra un'azione dedicata (`prowlarr-indexers-loader` / script `load_indexers.py`).
- **Sorgente Dati**: Legge il file dump degli indexer posizionato sotto la share SMB `smb://olindo@truenas/k8s-arr/servarr-prowlarr` (path host TrueNAS: `/mnt/stripe/k8s-arr/servarr-prowlarr/indexerrs_dump.json`, con fallback automatico a `indexers_dump.json`).
- **Autenticazione Dinamica**: Estrae automaticamente l'ApiKey dal `config.xml` di Prowlarr e attende che il servizio WebUI/API sia pronto (`/api/v1/system/status`).
- **Caricamento Idempotente**:
  1. Interroga `GET /api/v1/indexer` per rilevare gli indexer già registrati ed evitare duplicazioni.
  2. Per ciascun indexer del dump non presente, azzera l'`id` a `0`, sanitizza i tag non ancora censiti e invia una chiamata `POST /api/v1/indexer`.
  3. L'azione opera come container one-shot avviato in automatico dopo Prowlarr (`prowlarr-indexers-loader`), ma è anche invocabile on-demand in qualsiasi momento via CLI.

### G. Dashboard Failover Centralizzata Homepage su TrueNAS (Porta 3000)
- Durante il failover K8s, i container Homepage ordinari (`homepage` e `homepage-local` su Talos) sono spenti.
- Viene integrata un'istanza dedicata di Homepage (`ghcr.io/gethomepage/homepage:v1.4.5`) esposta su `http://10.10.10.50:3000`.
- **Configurazione Segregata**: Residente in `servarr/compose/homepage-config-truenas/` e sincronizzata su `/mnt/stripe/compose/arr/homepage-config-truenas/`.
- **Perimetro di Monitoraggio Esclusivo**: Mostra esclusivamente gli endpoint fisici statici del lab (Switch Extreme `192.168.2.1`, switch 2.5G, AP, OPNsense `10.10.20.1`, PBS `10.10.10.100:8007`, host PVE) e i servizi attivi su TrueNAS (Jellyfin 12, qBittorrent, Prowlarr, TrueNAS UI). Tutte le entità K8s e i widget cluster sono esclusi.

---

## 3. Matrice Storage: ZFS Nativo su TrueNAS

| Servizio | Path Fisico su TrueNAS | Mount Container | Pool ZFS | Note |
| :--- | :--- | :--- | :--- | :--- |
| **Homepage** | `./homepage-config-truenas` | `/app/config` | `stripe` (NVMe) | File YAML dashboard failover |
| **qBittorrent** | `/mnt/stripe/k8s-arr/servarr-qbittorrent` | `/config` | `stripe` (NVMe) | Configurazione e `.fastresume` |
| | `/mnt/stripe/qb_temp` | `/data/incomplete` | `stripe` (NVMe) | Temp download NVMe |
| | `/mnt/oliraid/arrdata/media` | `/media` | `oliraid` (HDD) | Mass storage libreria (`downloads/`, `movies/`, ecc.) |
| **Jellyfin 12** | `/mnt/stripe/k8s-arr/servarr-jellyfin-config-truenas` | `/config` | `stripe` (NVMe) | **Segregato usa-e-getta**: `encoding.xml` Vega, `network.xml` LAN |
| | `/mnt/stripe/k8s-arr/servarr-jellyfin-db-truenas` | `/config/data` | `stripe` (NVMe) | **Segregato usa-e-getta**: `jellyfin.db` SQLite unificato EF Core |
| | `/mnt/oliraid/arrdata/media` | `/mnt/media` e `/media` | `oliraid` (HDD) | Doppia mappatura per parità assoluta path DB EF Core |
| | `/dev/dri` | `/dev/dri` | Host | Driver VAAPI AMD Radeon Vega (`renderD128`) |
| **Prowlarr** | `/mnt/stripe/k8s-arr/servarr-prowlarr/sqlite` | `/config` | `stripe` (NVMe) | **Subdirectory ad-hoc**: DB SQLite locale e config isolata |
| | `/mnt/oliraid/arrdata/media` | `/media` | `oliraid` (HDD) | Cartella media condivisa |

---

## 4. Specifiche di Networking e Porte (TrueNAS `10.10.10.50`)

Durante il failover, Traefik e MetalLB sono inattivi. L'accesso avviene direttamente sull'IP del NAS o tramite il record DNS `truenas.pindaroli.org`:

* **Homepage Failover Dashboard**: `http://10.10.10.50:3000`
* **qBittorrent WebUI**: `http://10.10.10.50:8080`
* **qBittorrent BitTorrent Port**: `30661` (TCP e UDP, allineata al port-forward OPNsense)
* **Jellyfin WebUI / Smart TV App**: `http://10.10.10.50:8096`
* **Prowlarr WebUI**: `http://10.10.10.50:9696`
* **Inter-container networking**: Prowlarr comunica con qBittorrent via rete Docker bridge `arr_net` (`http://qbittorrent:8080`).

---

## 5. Manifesto Dichiarativo `docker-compose.yml` (Consolidato)

```yaml
services:
  # ==========================================
  # INIT CONTAINER (One-shot Bootstrap, Security & K8s Guardrail)
  # ==========================================
  init-arr-bootstrap:
    image: busybox:latest
    container_name: init-arr-bootstrap
    restart: "no"
    command:
      - sh
      - -c
      - |
        echo "[INIT] 0. Guardrail di sicurezza: verifica stato cluster Kubernetes (Traefik Ingress)..."
        K8S_ACTIVE=0
        ENDPOINTS="https://prowlarr-internal.pindaroli.org https://qbittorrent-internal.pindaroli.org https://jellyfin-internal.pindaroli.org"

        for ep in $$ENDPOINTS; do
          echo "[INIT] Probing $$ep ..."
          OUTPUT=$$(wget -S --spider --no-check-certificate -T 2 "$$ep" 2>&1)
          if echo "$$OUTPUT" | grep -qE "HTTP/[0-9]"; then
            echo "[ABORT] Endpoint Kubernetes $$ep è ATTIVO e RISPONDE!"
            echo "$$OUTPUT" | grep "HTTP/" | head -n 1
            K8S_ACTIVE=1
          fi
        done

        if [ "$$K8S_ACTIVE" -eq 1 ]; then
          echo "======================================================================"
          echo "[FATAL ERROR] Cluster Kubernetes o Traefik Ingress ancora ATTIVO!"
          echo "Lo stack Docker Compose NON può avviarsi per evitare split-brain e"
          echo "conflitti di scrittura simultanea su storage ZFS (/mnt/stripe e /mnt/oliraid)."
          echo "Arrestare i pod Kubernetes o spegnere i nodi Talos prima del failover."
          echo "======================================================================"
          exit 1
        fi
        echo "[INIT] 0b. Guardrail di sicurezza: verifica stato nodi Proxmox e LXC Jellyfin..."
        PVE_NODES="10.10.10.11 10.10.10.21 10.10.10.31 10.10.20.32"
        for ip in $$PVE_NODES; do
          echo "[INIT] Probing PVE/LXC $$ip ..."
          if ping -c 1 -W 1 "$$ip" >/dev/null 2>&1; then
            echo "======================================================================"
            echo "[FATAL ERROR] L'host $$ip è ATTIVO e RISPONDE al ping!"
            echo "Lo stack Failover NON può avviarsi se il cluster Proxmox o l'LXC sono attivi."
            echo "Altrimenti corromperesti il DB SQLite di Jellyfin con doppie scritture su ZFS/NFS."
            echo "======================================================================"
            exit 1
          fi
        done
        echo "[INIT] Nessun endpoint Kubernetes attivo. Procedo con la preparazione dello storage..."

        echo "[INIT] 1. Preparazione sottocartella SQLite per Prowlarr e pre-seeding API Key..."
        mkdir -p /mnt/prowlarr-root/sqlite
        if [ ! -f "/mnt/prowlarr-root/sqlite/config.xml" ]; then
          APIKEY=""
          if [ -f "/mnt/prowlarr-root/config.xml" ]; then
            APIKEY=$$(sed -n 's/.*<ApiKey>\(.*\)<\/ApiKey>.*/\1/p' /mnt/prowlarr-root/config.xml)
          fi
          if [ -z "$$APIKEY" ]; then
            APIKEY="fad287a6fe814e1b885f1ba0a8f95179"
          fi
          printf '<Config>\n  <Port>9696</Port>\n  <UrlBase></UrlBase>\n  <BindAddress>*</BindAddress>\n  <ApiKey>%s</ApiKey>\n  <AuthenticationMethod>None</AuthenticationMethod>\n  <LogLevel>info</LogLevel>\n  <Branch>master</Branch>\n  <LaunchBrowser>False</LaunchBrowser>\n  <UpdateMechanism>BuiltIn</UpdateMechanism>\n</Config>\n' "$$APIKEY" > /mnt/prowlarr-root/sqlite/config.xml
          echo "[INIT] sqlite/config.xml pre-popolato con successo (ApiKey allineata a Kubernetes)."
        fi
        chown -R 1000:1000 /mnt/prowlarr-root/sqlite
        chmod 775 /mnt/prowlarr-root/sqlite
        chmod 664 /mnt/prowlarr-root/sqlite/config.xml

        echo "[INIT] 2. Patch di sicurezza qBittorrent per accesso LAN diretto..."
        CONF="/mnt/qbittorrent-config/qBittorrent/qBittorrent.conf"
        if [ -f "$$CONF" ]; then
          sed -i '/WebUI\\CSRFProtection/d; /WebUI\\HostHeaderValidation/d; /WebUI\\AuthSubnetWhitelist/d' "$$CONF"
          sed -i '/\[Preferences\]/a WebUI\\AuthSubnetWhitelist=10.0.0.0/8, 172.16.0.0/12, 192.168.0.0/16, 127.0.0.0/8\nWebUI\\AuthSubnetWhitelistEnabled=true\nWebUI\\CSRFProtection=false\nWebUI\\HostHeaderValidation=false' "$$CONF"
          chown 1000:1000 "$$CONF"
          echo "[INIT] qBittorrent.conf patchato con successo."
        fi
        echo "[INIT] 3. Preparazione directory Jellyfin TrueNAS Failover..."
        mkdir -p /mnt/jellyfin-config /mnt/jellyfin-db
        chown -R 1000:1000 /mnt/jellyfin-config /mnt/jellyfin-db
        chmod -R 775 /mnt/jellyfin-config /mnt/jellyfin-db
        echo "[INIT] Bootstrap completato con successo."
    volumes:
      - /mnt/stripe/k8s-arr/servarr-prowlarr:/mnt/prowlarr-root
      - /mnt/stripe/k8s-arr/servarr-qbittorrent:/mnt/qbittorrent-config
      - /mnt/stripe/k8s-arr/servarr-jellyfin-config-truenas:/mnt/jellyfin-config
      - /mnt/stripe/k8s-arr/servarr-jellyfin-db-truenas:/mnt/jellyfin-db

  # ==========================================
  # QBITTORRENT
  # ==========================================
  qbittorrent:
    image: lscr.io/linuxserver/qbittorrent:5.2.3_v2.0.13-ls468
    container_name: qbittorrent
    restart: unless-stopped
    depends_on:
      init-arr-bootstrap:
        condition: service_completed_successfully
    environment:
      - PUID=1000
      - PGID=1000
      - TZ=Europe/Rome
      - WEBUI_BYPASS_AUTH_SUBNET_WHITELIST_ENABLED=true
      - WEBUI_AUTH_SUBNET_WHITELIST=10.0.0.0/8,172.16.0.0/12,192.168.0.0/16,127.0.0.0/8
      - TELEGRAM_BOT_TOKEN=${TELEGRAM_BOT_TOKEN:-}
      - TELEGRAM_CHAT_ID=${TELEGRAM_CHAT_ID:-}
    volumes:
      - /mnt/stripe/k8s-arr/servarr-qbittorrent:/config
      - /mnt/stripe/qb_temp:/data/incomplete
      - /mnt/oliraid/arrdata/media:/media
    ports:
      - "8080:8080"
      - "30661:30661"
      - "30661:30661/udp"
    networks:
      - arr_net

  # ==========================================
  # JELLYFIN
  # ==========================================
  jellyfin:
    image: lscr.io/linuxserver/jellyfin:12.0ubu2604-ls48
    container_name: jellyfin
    restart: unless-stopped
    depends_on:
      init-arr-bootstrap:
        condition: service_completed_successfully
    environment:
      - PUID=1000
      - PGID=1000
      - TZ=Europe/Rome
    devices:
      - /dev/dri:/dev/dri
    group_add:
      - "video"
      - "render"
    volumes:
      - /mnt/stripe/k8s-arr/servarr-jellyfin-config-truenas:/config
      - /mnt/stripe/k8s-arr/servarr-jellyfin-db-truenas:/config/data
      - /mnt/oliraid/arrdata/media:/mnt/media
      - /mnt/oliraid/arrdata/media:/media
    ports:
      - "8096:8096"
      - "7359:7359/udp"
    networks:
      - arr_net

  # ==========================================
  # PROWLARR (SQLite Failover)
  # ==========================================
  prowlarr:
    image: ghcr.io/hotio/prowlarr:release-2.5.2.5491
    container_name: prowlarr
    restart: unless-stopped
    depends_on:
      init-arr-bootstrap:
        condition: service_completed_successfully
    environment:
      - PUID=1000
      - PGID=1000
      - TZ=Europe/Rome
    volumes:
      - /mnt/stripe/k8s-arr/servarr-prowlarr/sqlite:/config
      - /mnt/stripe/k8s-arr/servarr-prowlarr:/backup:ro
      - /mnt/oliraid/arrdata/media:/media
    ports:
      - "9696:9696"
    networks:
      - arr_net

  # ==========================================
  # PROWLARR INDEXERS LOADER (One-shot Sync from JSON dump)
  # ==========================================
  prowlarr-indexers-loader:
    image: python:3.12-alpine
    container_name: prowlarr-indexers-loader
    restart: "no"
    depends_on:
      prowlarr:
        condition: service_started
    volumes:
      - /mnt/stripe/k8s-arr/servarr-prowlarr:/backup:ro
      - /mnt/stripe/k8s-arr/servarr-prowlarr/sqlite:/config:ro
      - ./load_indexers.py:/app/load_indexers.py:ro
    environment:
      - PROWLARR_URL=http://prowlarr:9696
      - CONFIG_XML=/config/config.xml
      - DUMP_FILE=/backup/indexerrs_dump.json
    command: ["python3", "/app/load_indexers.py"]
    networks:
      - arr_net

  # ==========================================
  # HOMEPAGE (Failover Dashboard)
  # ==========================================
  homepage:
    image: ghcr.io/gethomepage/homepage:v1.4.5
    container_name: homepage
    restart: unless-stopped
    depends_on:
      init-arr-bootstrap:
        condition: service_completed_successfully
    environment:
      - PUID=1000
      - PGID=1000
      - TZ=Europe/Rome
    volumes:
      - ./homepage-config-truenas:/app/config
    ports:
      - "3000:3000"
    networks:
      - arr_net

networks:
  arr_net:
    name: arr_net
    driver: bridge
```

### 5.1 Script di Sincronizzazione Indexer: `load_indexers.py`

```python
#!/usr/bin/env python3
"""
Prowlarr Indexer Loader for TrueNAS Failover Stack.
Imports indexers from indexerrs_dump.json (or indexers_dump.json) into Prowlarr via REST API.
"""
import os
import sys
import time
import json
import urllib.request
import urllib.error
import urllib.parse
import xml.etree.ElementTree as ET

PROWLARR_URL = os.getenv("PROWLARR_URL", "http://prowlarr:9696")
CONFIG_XML = os.getenv("CONFIG_XML", "/config/config.xml")
DUMP_FILES = [
    os.getenv("DUMP_FILE", ""),
    "/backup/indexerrs_dump.json",
    "/backup/indexers_dump.json",
    "/mnt/stripe/k8s-arr/servarr-prowlarr/indexerrs_dump.json",
    "/mnt/stripe/k8s-arr/servarr-prowlarr/indexers_dump.json"
]

def get_api_key():
    key = os.getenv("PROWLARR_API_KEY")
    if key:
        return key
    config_paths = [
        CONFIG_XML,
        "/config/config.xml",
        "/mnt/stripe/k8s-arr/servarr-prowlarr/sqlite/config.xml",
        "/mnt/stripe/k8s-arr/servarr-prowlarr/config.xml"
    ]
    for cp in config_paths:
        if os.path.isfile(cp):
            try:
                tree = ET.parse(cp)
                api_elem = tree.find("ApiKey")
                if api_elem is not None and api_elem.text:
                    return api_elem.text.strip()
            except Exception as e:
                print(f"[WARN] Errore lettura {cp}: {e}")
    return None

def wait_for_prowlarr(url, api_key, timeout=60):
    print(f"[INIT] Attesa che Prowlarr a {url} sia online...")
    start = time.time()
    while time.time() - start < timeout:
        try:
            req = urllib.request.Request(f"{url}/api/v1/system/status", headers={"X-Api-Key": api_key})
            with urllib.request.urlopen(req, timeout=3) as resp:
                if resp.status == 200:
                    print("[INIT] Prowlarr ONLINE e pronto a ricevere richieste!")
                    return True
        except Exception:
            time.sleep(2)
    print("[ERROR] Timeout attesa avvio di Prowlarr.")
    return False

def main():
    api_key = get_api_key()
    if not api_key:
        print("[ERROR] Impossibile rilevare ApiKey di Prowlarr. Abort.")
        sys.exit(1)

    # Identificazione file dump
    dump_path = None
    for path in DUMP_FILES:
        if path and os.path.isfile(path):
            dump_path = path
            break

    if not dump_path:
        print("[WARN] Nessun file dump indexer trovato nei percorsi monitorati. Nessun import eseguito.")
        sys.exit(0)

    print(f"[INIT] Rilevato file dump indexer: {dump_path}")
    with open(dump_path, "r", encoding="utf-8") as f:
        dumped_indexers = json.load(f)

    if not wait_for_prowlarr(PROWLARR_URL, api_key):
        sys.exit(1)

    # Elenco indexer esistenti
    req = urllib.request.Request(f"{PROWLARR_URL}/api/v1/indexer", headers={"X-Api-Key": api_key})
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            existing = json.load(resp)
        existing_names = {idx.get("name") for idx in existing}
    except Exception as e:
        print(f"[WARN] Impossibile recuperare indexer esistenti: {e}")
        existing_names = set()

    # Rilevamento tag validi nel nuovo DB
    valid_tag_ids = set()
    try:
        req_tags = urllib.request.Request(f"{PROWLARR_URL}/api/v1/tag", headers={"X-Api-Key": api_key})
        with urllib.request.urlopen(req_tags, timeout=5) as resp:
            tags = json.load(resp)
            valid_tag_ids = {t.get("id") for t in tags}
    except Exception:
        pass

    added_count = 0
    for idx in dumped_indexers:
        name = idx.get("name")
        if name in existing_names:
            print(f"[SKIP] Indexer '{name}' già presente nel database.")
            continue

        payload = dict(idx)
        payload["id"] = 0  # Cruciale per generare nuovo record
        if "tags" in payload:
            payload["tags"] = [t for t in payload["tags"] if t in valid_tag_ids]

        data = json.dumps(payload).encode("utf-8")
        post_req = urllib.request.Request(
            f"{PROWLARR_URL}/api/v1/indexer",
            data=data,
            headers={"X-Api-Key": api_key, "Content-Type": "application/json"},
            method="POST"
        )
        try:
            with urllib.request.urlopen(post_req, timeout=10) as post_resp:
                if post_resp.status in (200, 201):
                    print(f"[OK] Aggiunto indexer '{name}'.")
                    added_count += 1
        except urllib.error.HTTPError as e:
            err_body = e.read().decode("utf-8", errors="ignore")
            print(f"[FAIL] Errore aggiunta '{name}': HTTP {e.code} - {err_body}")

    print(f"[DONE] Importazione completata con successo: {added_count} indexer registrati su Prowlarr.")

if __name__ == "__main__":
    main()
```

---

## 6. Procedura Operativa di Attivazione e Switch-Back

### Fase 1: Creazione e Deposito File (Local & TrueNAS)
1. Salvare i file nel repository in `servarr/compose/` (`docker-compose.yml`, `load_indexers.py`, `.env.example`, `README.md`).
2. Copiare la cartella su TrueNAS in `/mnt/stripe/compose/arr/`.

### Fase 2: Attivazione Failover (K8s Spento)
1. Verificare che i pod K8s siano arrestati o che i nodi Talos siano offline.
2. Avviare lo stack su TrueNAS:
   ```bash
   cd /mnt/stripe/compose/arr && docker compose up -d
   ```
3. L'init container `init-arr-bootstrap` esegue automaticamente il controllo pre-flight:
   - **Guardrail anti-split-brain**: Esegue il probe HTTPS degli endpoint Traefik (`prowlarr-internal`, `qbittorrent-internal`, `jellyfin-internal`). Se anche uno solo risponde, `init-arr-bootstrap` fallisce con exit code 1 e Docker Compose arresta l'avvio prima di toccare i file ZFS.
   - **Bootstrap & Security**: Se il cluster è spento (nessuna risposta), crea la sottocartella `sqlite/`, pre-popola `sqlite/config.xml` estraendo l'ApiKey dalla configurazione di produzione Kubernetes (eliminando race-condition e allineando le credenziali a quelle note), applica la patch di sicurezza su `qBittorrent.conf` e termina con successo, sbloccando l'avvio in background dei 3 container applicativi.
4. **Caricamento Automatico Indexer Prowlarr**:
   - Il container `prowlarr-indexers-loader` si attiva non appena Prowlarr è partito (`service_started`).
   - Attende che l'API sia pronta su `http://prowlarr:9696`, legge `/backup/indexerrs_dump.json` (proveniente dalla share SMB `/mnt/stripe/k8s-arr/servarr-prowlarr`) e registra tutti gli indexer mancanti via `POST /api/v1/indexer`.
5. **Esecuzione Manuale On-Demand (Opzionale)**:
   - In caso di necessità o per forzare un re-import a caldo:
     ```bash
     cd /mnt/stripe/compose/arr && docker compose run --rm prowlarr-indexers-loader
     ```
     oppure direttamente dall'host TrueNAS tramite l'interprete Python nativo:
     ```bash
     cd /mnt/stripe/compose/arr && python3 load_indexers.py
     ```
6. Accesso da browser: `http://10.10.10.50:8080` (qBittorrent), `8096` (Jellyfin), `9696` (Prowlarr).

### Fase 3: Rientro su Kubernetes (Cluster Riattivato)
1. Arrestare lo stack Docker su TrueNAS **prima** di avviare o sbloccare i carichi su K8s per evitare contese sui file:
   ```bash
   cd /mnt/stripe/compose/arr && docker compose down
   ```
2. Riaccendere o ripristinare il cluster Kubernetes: le applicazioni riprenderanno il controllo dei dataset ZFS senza conflitti.

---

## 💾 Stato di Ripristino (AI Save-State)
- **Fase Attiva**: File Materializzati in `servarr/compose/` (Pronto al Deposito su TrueNAS)
- **Ultima Azione Completata**: Materializzati con successo i file dichiarativi nel repository in `servarr/compose/` (`docker-compose.yml`, `load_indexers.py`, `indexers_dump.json`, `.env.example`, `README.md`) e aggiornato `GEMINI.md`.
- **Prossimo Passo Operativo**: Deposito della directory su TrueNAS tramite rsync: `rsync -avz servarr/compose/ root@10.10.10.50:/mnt/stripe/compose/arr/`.
- **Blocchi/Decisioni Pendenti**: Nessuno. Stack pronto per l'avvio in failover su TrueNAS.

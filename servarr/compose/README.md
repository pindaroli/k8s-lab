# Stack Docker Compose Failover su TrueNAS SCALE Bare Metal

Stack Docker Compose autonomo e auto-inizializzante per **qBittorrent**, **Jellyfin** e **Prowlarr**, progettato per subentrare istantaneamente a **cluster Kubernetes (Talos) spento** durante manutenzioni programmata o emergenze energetiche.

- **Riferimento Piano Wiki**: [`wiki/plans/docker-compose-arr-truenas-failover.md`](file:///Users/olindo/prj/k8s-lab/wiki/plans/docker-compose-arr-truenas-failover.md)
- **Host di Esecuzione**: TrueNAS SCALE Bare Metal (`10.10.10.50`)
- **Directory su TrueNAS**: `/mnt/stripe/compose/arr/`

---

## 🛡️ Guardrail Pre-Flight & Protezione Split-Brain

Prima di avviare qualsiasi servizio, l'init container `init-arr-bootstrap`:
1. **Probe Traefik HTTPS**: Interroga `https://prowlarr-internal.pindaroli.org`, `https://qbittorrent-internal.pindaroli.org` e `https://jellyfin-internal.pindaroli.org`. Se **anche uno solo risponde**, l'avvio viene bloccato immediatamente con `exit 1` per scongiurare scritture concorrenti su ZFS.
2. **Pre-seeding ApiKey Prowlarr**: Clona la stringa `<ApiKey>` dal file di Kubernetes `/mnt/stripe/k8s-arr/servarr-prowlarr/config.xml` verso `/mnt/stripe/k8s-arr/servarr-prowlarr/sqlite/config.xml`, garantendo zero race condition e la stessa identica chiave di produzione.
3. **Patch qBittorrent**: Applica a `qBittorrent.conf` il bypass per CSRF e whitelist subnet locali (`10.0.0.0/8`, `172.16.0.0/12`, `192.168.0.0/16`).

---

## 🚀 Avvio Rapido su TrueNAS

### 1. Copia dei File su TrueNAS
```bash
# Eseguibile da Mac/Workstation:
rsync -avz servarr/compose/ root@10.10.10.50:/mnt/stripe/compose/arr/
```

### 2. Attivazione Failover (K8s Spento)
```bash
ssh root@10.10.10.50
cd /mnt/stripe/compose/arr
docker compose up -d
```
All'avvio:
- `init-arr-bootstrap` verifica che K8s sia spento e prepara le cartelle e i permessi.
- `qbittorrent`, `jellyfin` e `prowlarr` partono in background.
- `prowlarr-indexers-loader` parte subito dopo Prowlarr, si collega via REST API e carica automaticamente tutti gli indexer da `indexerrs_dump.json`.

### 3. URL di Accesso Diretto
* **qBittorrent WebUI**: `http://10.10.10.50:8080` (Porta BT: `30661`)
* **Jellyfin WebUI / Smart TV**: `http://10.10.10.50:8096`
* **Prowlarr WebUI**: `http://10.10.10.50:9696`

---

## 🔄 Ricaricamento On-Demand degli Indexer

Se aggiungi nuovi tracker al dump o vuoi forzare un re-import:
```bash
# Tramite container Docker Compose:
docker compose run --rm prowlarr-indexers-loader

# Oppure direttamente con Python nativo su TrueNAS:
python3 /mnt/stripe/compose/arr/load_indexers.py
```

---

## 🛑 Rientro su Kubernetes (Switch-Back)

Prima di riaccendere i nodi Talos o sbloccare i carichi su Kubernetes:
```bash
cd /mnt/stripe/compose/arr
docker compose down
```
Tutti i dati e lo stato di download restano perfettamente allineati e salvati sui dataset ZFS nativi (`stripe` e `oliraid`).

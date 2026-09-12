# Stack Docker Compose Failover su TrueNAS SCALE Bare Metal

Stack Docker Compose autonomo e auto-inizializzante per **Homepage**, **qBittorrent**, **Jellyfin 12** e **Prowlarr**, progettato per subentrare istantaneamente a **cluster Kubernetes (Talos) spento** durante manutenzioni programmate o emergenze energetiche.

- **Riferimento Piani Wiki**:
  - [`wiki/plans/docker-compose-arr-truenas-failover.md`](file:///Users/olindo/prj/k8s-lab/wiki/plans/docker-compose-arr-truenas-failover.md)
  - [`wiki/plans/truenas-only-migration-failover.md`](file:///Users/olindo/prj/k8s-lab/wiki/plans/truenas-only-migration-failover.md)
- **Host di Esecuzione**: TrueNAS SCALE Bare Metal (`10.10.10.50`)
- **Directory su TrueNAS**: `/mnt/stripe/compose/arr/`

---

## 🛡️ Guardrail Pre-Flight & Protezione Split-Brain

Prima di avviare qualsiasi servizio applicativo, l'init container `init-arr-bootstrap`:
1. **Probe Traefik HTTPS**: Interroga `https://prowlarr-internal.pindaroli.org`, `https://qbittorrent-internal.pindaroli.org` e `https://jellyfin-internal.pindaroli.org`. Se **anche uno solo risponde**, l'avvio viene bloccato immediatamente con `exit 1` per scongiurare scritture concorrenti su ZFS.
2. **Probe PVE & LXC**: Verifica via ICMP l'assenza di `10.10.10.11`, `10.10.10.21`, `10.10.10.31` e `10.10.20.32` per impedire doppie istanze Jellyfin attive.
3. **Pre-seeding ApiKey Prowlarr**: Clona la stringa `<ApiKey>` dal file di Kubernetes `/mnt/stripe/k8s-arr/servarr-prowlarr/config.xml` verso `/mnt/stripe/k8s-arr/servarr-prowlarr/sqlite/config.xml`, garantendo zero race condition e la stessa identica chiave di produzione.
4. **Patch qBittorrent**: Applica a `qBittorrent.conf` il bypass per CSRF e whitelist subnet locali (`10.0.0.0/8`, `172.16.0.0/12`, `192.168.0.0/16`).
5. **Preparazione Storage Segregato Jellyfin**: Garantisce l'esistenza e i permessi `1000:1000` (chmod 775) per le directory temporanee isolate `/mnt/stripe/k8s-arr/servarr-jellyfin-*-truenas`.

---

## 🎬 Jellyfin 12.0 e Segregazione Storage

- **Database Unificato EF Core**: Jellyfin 12.0 utilizza un unico file relazionale `jellyfin.db` nella sottodirectory `data/`.
- **Segregazione Percorsi (Zero Rischi di Contesa)**: L'istanza Docker su TrueNAS non scrive mai sulle cartelle di produzione (`servarr-jellyfin-config` e `servarr-jellyfin-db`), bensì su copie usa-e-getta:
  - Config: `/mnt/stripe/k8s-arr/servarr-jellyfin-config-truenas` montato in `/config`
  - Database: `/mnt/stripe/k8s-arr/servarr-jellyfin-db-truenas` montato in `/config/data`
- **Accelerazione Hardware AMD Vega**: Il descrittore Compose esegue il passthrough `/dev/dri:/dev/dri` con `group_add: ["video", "render"]`. `encoding.xml` viene pre-configurato con VA-API (`/dev/dri/renderD128`), AV1 hardware disabilitato (non supportato da AMD Cezanne Vega 8), HEVC/VP9 abilitati e HDR tone mapping attivo.
- **Risoluzione Blocco 403 Forbidden**: `network.xml` abilita `<EnableRemoteAccess>true</EnableRemoteAccess>` e definisce `<LocalNetworkSubnets>10.10.0.0/16</LocalNetworkSubnets>`, consentendo l'accesso trasparente da client su VLAN 20 verso TrueNAS (VLAN 10).
- **Parità Percorsi Media**: I media sono montati sia su `/mnt/media` sia su `/media` per garantire perfetta corrispondenza dei path del database EF Core generato su LXC.

---

## 🚀 Avvio Rapido su TrueNAS

### 1. Copia dei File su TrueNAS
```bash
# Eseguibile da Mac/Workstation:
rsync -avz servarr/compose/ root@10.10.10.50:/mnt/stripe/compose/arr/
```

### 2. Attivazione Failover (Tramite Playbook Ansible)
```bash
ansible-playbook -i ansible/inventory.ini ansible/playbooks/infrastructure/migrate_to_truenas_only.yml
```

### 3. URL di Accesso Diretto (VLAN 10 / IP 10.10.10.50)
* **Homepage Failover Dashboard**: `http://10.10.10.50:3000` (Pannello centrale LAN con dispositivi fissi e app TrueNAS)
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

Il rientro viene orchestrato in sicurezza dal playbook Ansible:
```bash
ansible-playbook -i ansible/inventory.ini ansible/playbooks/infrastructure/restore_from_truenas_only.yml
```
1. Lo stack Docker viene arrestato (`docker compose down`).
2. Nessuna retro-copia Jellyfin: le cartelle `-truenas` vengono abbandonate; Jellyfin su LXC 2200 esegue un Cold Start dal proprio disco locale NVMe incontaminato.
3. Vengono attesi i nodi fisici Proxmox VE e avviate le VM Talos.
4. Al ripristino del quorum etcd, i nodi K8s vengono automaticamente uncordoned.

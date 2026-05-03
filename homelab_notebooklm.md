# Project GEMINI: Homelab Infrastructure Documentation
> **Document Status**: Active / Source of Truth for LLM Context
> **Last Updated**: 2026-05-02 (Traefik & 10G Optimization)

## 1. Executive Summary
Project GEMINI represents the migration and modernization of a personal homelab environment. The core objective is to move from legacy standalone deployments to a fully declarative, high-availability Kubernetes cluster running on **Talos Linux**, hosted on a 3-node **Proxmox VE** cluster. Major components include **TrueNAS Scale** for storage, **OPNsense** for routing/firewalling, and a **Servarr** media stack backed by **PostgreSQL**.

---

## 2. Network Topology & Security
The network is segmented into VLANs to separate management traffic from client/iot traffic, strictly controlled by OPNsense.

### VLAN Structure
| Name | VLAN ID | Subnet | Role | Access Policy |
|---|---|---|---|---|
| **Server** | `10` | `10.10.10.0/24` | Management, Storage (TrueNAS), Hypervisors | Strictly Restricted. Admin access only. |
| **Client** | `20` | `10.10.20.0/24` | Talos Nodes, Personal Computers, WiFi | Trusted Network. Access to Services. |
| **IoT** | `30` | `10.10.30.0/24` | *DEPRECATED / UNUSED* | Currently inactive. |
| **Transit**| `-` | `192.168.2.0/24`| Switch Interconnects | L3 Routing backbone. |

### Access Strategy (Split-DNS)
The lab uses a Split-DNS architecture to ensure optimal routing and security.
*   **External Access**: Users accessing services from the internet are routed through **Cloudflare Tunnel**. We are migrating from wildcard `*` to specific hostnames for security. All requests MUST pass through **Google OAuth2** (Traefik).
*   **Internal Access**: Users inside the LAN (VLAN 20) resolve specific service names (e.g., `tdarr-internal`, `nas`) directly to the internal Traefik VIP (`10.10.20.56`). **Wildcards are prohibited in internal DNS** to avoid Kubernetes routing loops (ndots issue).

---

## 3. Infrastructure Layer (Hypervisors & Storage)
The foundation runs on **Proxmox VE 9.1** (Debian 13 Trixie).

### Compute Nodes
*   **PVE (10.10.10.11)**: Host for TrueNAS (Storage) and PBS (Backup).
*   **PVE2 (10.10.10.21)**: Compute Node. Runs Talos CP.
*   **PVE3 (10.10.10.31)**: Compute Node. Runs Media Server (LXC) and Talos CP.

### Storage (TrueNAS Scale)
*   **Role**: Central NAS providing NFS shares to Kubernetes and VM backups.
*   **IPs**: `10.10.10.50` (Storage & Routing via L3 Switch).
*   **Startup Logic**: Critical dependency. All other VMs wait for TrueNAS to be pingable via a custom hook script (`wait-for-truenas.sh`) before booting.

### Backup Strategy
*   **Proxmox Backup Server (PBS)**: LXC Container (`10.10.10.100`) saving snapshots to NFS.
*   **Velero**: Kubernetes disaster recovery tool, backing up cluster resources and PVCs to MinIO/S3.

---

## 4. Kubernetes Cluster (Talos Linux)
The application layer runs on a **Talos Linux** cluster (Version 1.12.0), treating the OS as immutable infrastructure.

### Cluster Nodes
*   **Control Plane 01** (`talos-cp-01`): `10.10.20.141` — VM 2100 on PVE1. ✅ Ready.
*   **Control Plane 02** (`talos-cp-02`): `10.10.20.142` — VM 2300 on PVE2. ⚠️ **In manutenzione** (PVE2 offline). Da reinstallare via fresh ISO Talos quando PVE2 torna.
*   **Control Plane 03** (`talos-cp-03`): `10.10.20.143` — VM 3200 on PVE3. ✅ Ready.
*   **Virtual IP (VIP)**: `10.10.20.55` (HA Endpoint per API)

> **Architettura**: Tutti i nodi sono **iper-convergenti** (Master + Worker). Non esistono nodi worker dedicati. Il file `worker.yaml` è un residuo da rimuovere.

### Management
*   **Source of Truth**: `talos-config/` directory.
    *   `controlplane.yaml` → CP01 (`.141`)
    *   `controlplane-3200.yaml` → CP03 (`.143`)
    *   `controlplane-cp02.yaml` → Da creare quando PVE2 torna online.
*   **DNS**: Tutti i nodi CP usano `10.10.20.1` (OPNsense) come nameserver primario per risoluzione interna.
*   **Operations**: Managed via `talosctl`. No SSH access (API only).

### Procedura Rientro CP02 (quando PVE2 torna)
1. Boot VM 2300 da ISO Talos v1.12.0.
2. `sed 's/10.10.20.141/10.10.20.142/g' talos-config/controlplane.yaml > talos-config/controlplane-cp02.yaml`
3. `talosctl apply-config -n <IP_DHCP> --file talos-config/controlplane-cp02.yaml --insecure`
4. CNPG ricostruisce automaticamente `postgres-main-2` replica.
5. Pulire i PV orfani: `kubectl delete pv pvc-052584c6-... pvc-ebe1187c-...`

---

## 5. Services & Workloads
Major applications deployed via Helm and Flux (planned/in-progress).

### Media Stack (Namespace: `arr`)
*   **Apps**: Radarr, Lidarr, Prowlarr, qBittorrent.
*   **Readarr**: Cancelled due to instability.
*   **Database**: Migrated from SQLite to **CloudNativePG** (PostgreSQL) cluster (`10.10.20.57`).
*   **Privacy**: 
    *   **qBittorrent**: Migrated to a dedicated **MetalLB LoadBalancer IP (10.10.20.60)** for direct, high-performance P2P traffic. Zero Trust isolation handles security via OPNsense.
    *   **Prowlarr**: Now uses direct networking for improved scraping reliability and reduced latency. No Xray sidecar is currently deployed for this service.

### Ingress & Connectivity
*   **Traefik**: Main Ingress Controller (`10.10.20.56`). Gestisce SSL termination e routing. Usa solo **IngressRoute CRD** (no standard Ingress K8s).
*   **MetalLB**: LoadBalancer IPs assegnati:
    *   `10.10.20.56` → Traefik VIP
    *   `10.10.20.57` → PostgreSQL CNPG (postgres-main)
    *   `10.10.20.60` → qBittorrent (dedicato)
    *   `10.10.20.61` → Tdarr Server API
*   **Cert-Manager**: Rinnovo automatico wildcard `*.pindaroli.org` via Cloudflare DNS-01. **NOTA**: Il secret TLS va propagato manualmente in ogni namespace che ne ha bisogno (`arr`, `monitoring`, `oauth2-proxy`, `kasmweb`). Cert-manager crea il secret solo nei namespace dove esiste la risorsa `Certificate`.

### Ottimizzazioni Connettività & Rete 10G (2026-05-02)
Per risolvere problemi di `ERR_CONNECTION_REFUSED` su Chrome e stabilizzare il routing asimmetrico causato dallo switch L3 Xikestor, sono state applicate le seguenti configurazioni:
*   **Traefik Timeout Alignment**: Impostato `idleTimeout: 3600s` e `readTimeout: 0s` nei `values.yaml` di Traefik. Questo impedisce al proxy di chiudere le connessioni prima del browser Chromium (che mantiene i socket aperti a lungo).
*   **Talos TCP Stack Tuning**: Applicati `sysctls` avanzati a tutti i nodi Talos per massimizzare il throughput sui 10G:
    *   `net.core.rmem_max/wmem_max`: Portati a 128MB.
    *   `net.ipv4.tcp_rmem/wmem`: Finestre di ricezione/invio ottimizzate fino a 64MB.
*   **OPNsense Asymmetric Routing Mitigation**: 
    *   **Firewall Optimization**: Impostata su **Conservative** per allungare la vita degli stati TCP idle.
    *   **Sloppy State Tracking**: Abilitato sulle regole VLAN 20 -> VLAN 10 per permettere il passaggio di pacchetti TCP di cui il firewall non vede l'intero handshake (causato dal bypass parziale del traffico via switch L3).

### Nuovi Servizi Deployati (2026-04-27)
*   **Prefect** (namespace `prefect`): Orchestratore di workflow. Server + Kubernetes Worker deployati via Helm. Database su `postgres-main` (CNPG). Accessibile su `https://prefect-internal.pindaroli.org`.
*   **Tdarr** (namespace `tdarr`): Media transcoding. Architettura ibrida:
    *   **Server**: Da deployare in K8s (in sospeso).
    *   **Node**: Gira su **Mac Studio** (`10.10.20.100`) per accelerazione hardware Apple VideoToolbox.
    *   **LB IP**: `10.10.20.61` (MetalLB pool `tdarr-api-pool`).
    *   **IngressRoute**: `tdarr-internal.pindaroli.org` → port 8267.
*   **Kasmweb** (namespace `kasmweb`): Desktop remoto containerizzato. Immagine custom `olindo/almalinux-9-oli-desktop:latest`. Accessibile su `https://kasmweb.pindaroli.org` (OAuth2) e `https://kasmweb-internal.pindaroli.org`.

### Local & Complementary Services (Off-Cluster)
While the core workloads run on Kubernetes, specialized services are hosted on dedicated nodes for performance:
*   **Jellyfin Media Server**: Runs as a privileged LXC on **PVE3** for hardware transcoding.
*   **Ollama AI**: Hosted locally on **Mac Studio M2 Ultra** to leverage the 64GB Unified Memory for high-performance LLM inference.
    -   **Endpoints**: Engine on `11434`, Metrics Exporter (Proxy) on `11435`.
    -   **Monitoring**: Gold Standard implementation using `ollama-metrics` (Go) and `VMStaticScrape` in VictoriaMetrics. Captures Token/Sec, Metal GPU saturation, and VRAM pressure.
    - **Persistence**: Managed via LaunchAgents (`homebrew.mxcl.ollama.plist` and `org.norskhelsenett.ollama-metrics.plist`). Optimized for Apple Silicon (`OLLAMA_NUM_GPU=1`) and persistent model loading (`OLLAMA_KEEP_ALIVE=-1`).


---

## 6. Automation & Maintenance
*   **Ansible**: `ansible/` contains playbooks for Day-2 operations:
    *   `shutdown_lab.yml`: Orchestrates safe shutdown (Kubernetes -> DB -> Storage -> Hypervisors).
    *   `dhcp_reservations.yml`: Syncs inventory IPs to OPNsense via Kea DHCP API.
    *   `opnsense_sync_dns.yml`: Updates Unbound DNS config based on `rete.json`.
*   **Source of Truth**: The `rete.json` file is the master record for all IP addresses, MAC addresses, and VLAN assignments.

## 7. Known Issues & Pending Tasks

### Critici
*   **CP02 / PVE2**: Nodo offline per manutenzione hardware. `postgres-main-2` (replica CNPG) in stato `Pending` in attesa del rientro del nodo. Il cluster funziona normalmente con 2/3 CP e 1 replica PostgreSQL.
*   **Tdarr Server**: Il Deployment K8s del server non è stato ancora creato. Solo MetalLB pool e IngressRoute sono attivi. Il node sul Mac non può connettersi finché il server non è deployato.

### Da Pulire
*   `talos-config/worker.yaml`: File residuo, non applicabile (architettura iper-convergente, nessun nodo worker dedicato).
*   PV orfani su PVE2 (quando torna): `pvc-052584c6-*` (postgres-main-2, 100Gi), `pvc-ebe1187c-*` (postgres-main-2-wal, 4Gi).

### Rete & DNS (OPNsense)
*   **Kubernetes Split DNS**: I pod K8s (`10.244.0.0/16`) ricevono un "Connection Refused" quando interrogano il DNS di OPNsense (`10.10.20.1`), causando fallback su `1.1.1.1` e risoluzione di domini interni a `0.0.0.0`.
    *   *Azione Richiesta*: In OPNsense, andare su `Services -> Unbound DNS -> Access Lists` e aggiungere una regola in "Allow" per la subnet `10.244.0.0/16`.
*   **OPNsense WebGUI Rebind Check**: L'accesso via `firewall-direct.pindaroli.org` è bloccato dall'anti-DNS-rebind.
    *   *Azione Richiesta*: Accedere via IP (`https://10.10.20.1`), andare in `System -> Settings -> Administration` e aggiungere `firewall-direct.pindaroli.org` nel campo "Alternate Hostnames".

### Monitoraggio
*   **Certificati TLS**: Rinnovati il 2026-04-27. Prossima scadenza ~90 giorni. Monitorare che cert-manager rinnovi automaticamente nel namespace `arr` (l'ultimo rimasto `False`).
*   **Traffic Traversal**: Monitoraggio continuo del routing asimmetrico tra OPNsense e L3 Switch.

---

## 8. Cronologia Incidenti Maggiori

### 2026-05-03: DNS Split-Horizon Resolution Failure
**Causa**: Conflito tra record "Black Hole" (0.0.0.0) su Cloudflare, ACL mancanti su OPNsense e IP DNS errato in Talos.
**Risoluzione**:
1. Autorizzato subnet Pod (`10.244.0.0/16`) nelle Access List di Unbound.
2. Corretto IP DNS in `controlplane.yaml` da `.1` a `.254`.
3. Rimossi record `0.0.0.0` da Cloudflare e disabilitata automazione Ansible relativa.
4. Ottimizzato Unbound (`transparent`) e DHCP Option 15 (`pindaroli.org`).
**Dettagli**: Vedere [2026-05-03-dns-split-horizon-conflict.md](file:///Users/olindo/prj/k8s-lab/incidents/2026-05-03-dns-split-horizon-conflict.md).

### 2026-04-27: Ripristino Cluster Post-Crash
**Causa**: Crash/corruzione Etcd su tutti e 3 i nodi dopo problemi hardware su PVE2.
**Risoluzione**:
1. Forzato bootstrap Etcd su CP01 (`.141`).
2. Risolto conflitto IP tra nodi tramite config statica via `talosctl apply-config`.
3. Aggiunto DNS OPNsense (`10.10.20.1`) ai file `controlplane.yaml` e `controlplane-3200.yaml`.
4. Rimosso nodo fantasma `talos-cp-02` con `kubectl delete node`.
5. Forzato rinnovo certificati TLS scaduti (Cloudflare DNS challenge).
6. Corrette IngressRoute n8n spostate erroneamente nel namespace `default`.
**Stato Post-Incidente**: Cluster stabile, 2/3 nodi Ready, tutti i workload operativi.

---
*Created for ingestion by NotebookLM to provide full context on the Project GEMINI architecture.*

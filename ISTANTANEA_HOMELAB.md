# Snapshot Configurazione Homelab - Progetto GEMINI

Questo documento fornisce una panoramica completa dello stato attuale, dell'architettura di rete e dello stack software dell'Homelab "pindaroli", aggiornato a Febbraio 2026. È strutturato per fornire contesto a modelli AI e per documentazione tecnica.

## 1. Panoramica Infrastrutturale
L'infrastruttura è ibrida, basata su virtualizzazione **Proxmox VE** che ospita un cluster **Kubernetes (Talos Linux)** e servizi legacy/storage su VM dedicate.

### Hardware & Nodi
| Nodo | IP Mgmt (VLAN 10) | Ruolo | OS | Stato | Note |
|---|---|---|---|---|---|
| **pve** | `10.10.10.11` | Primary Hypervisor | Proxmox VE 9.1 (Debian 13) | Online | Ospita TrueNAS (pass-through controller) |
| **pve2** | `10.10.10.21` | Compute Node | Proxmox VE 9.1 (Debian 13) | Online | Ospita Jellyfin LXC, Talos CP |
| **pve3** | `10.10.10.31` | Compute Node | Proxmox VE 9.1 (Debian 13) | **OFFLINE** | In attesa di manutenzione/recovery |
| **TrueNAS** | `10.10.10.50` | NAS Storage | TrueNAS SCALE | Online | VM ID 1100 su pve. Multihomed (VLAN 10/20) |
| **PBS** | `10.10.10.100` | Backup Server | Proxmox Backup Server | Online | LXC ID 1400 su pve |

---

## 2. Architettura di Rete

### Segmentazione VLAN
La rete è gestita da **OPNsense** e switch gestiti L3/L2.

*   **VLAN 10 (Server)**: `10.10.10.0/24`. Management Proxmox, TrueNAS, IPMI.
*   **VLAN 20 (Client)**: `10.10.20.0/24`. Talos Cluster Services, Client personali (PC/Mac), WiFi "Eternal".
*   **VLAN 30 (IoT)**: `10.10.30.0/24`. *DEPRECATA / NON IN USO* (Ex-dispositivi isolati).
*   **Transit**: `192.168.2.0/24`. Interconnessione Switch <-> Firewall.

### Strategia DNS (Split-DNS)
Il dominio autoritativo è `pindaroli.org`.
1.  **Interno (LAN)**: Risolto da OPNsense Unbound. Punta ai VIP interni (es. `10.10.20.56`). Assicura traffico diretto locale.
2.  **Esterno (WAN)**: Gestito da Cloudflare. Punta al Tunnel Cloudflare.

### Accesso & Sicurezza
*   **Ingress Esterno**: Cloudflare Tunnel -> Traefik.
*   **Autenticazione**: OBBLIGATORIA **OAuth2 (Google)** per tutti i servizi esposti esternamente. Implementata via Traefik Middleware (`oauth2-auth`).
*   **Ingress Interno**: Traefik LoadBalancer VIP (`10.10.20.56`). Accesso libero o BasicAuth per subnet fidate.

---

## 3. Cluster Kubernetes (Talos)

### Specifiche
*   **Distribuzione**: Talos Linux v1.12.0.
*   **Control Plane**: 3 Nodi (VM su Proxmox).
    *   `talos-cp-01`: 10.10.20.141
    *   `talos-cp-02`: 10.10.20.142
    *   `talos-cp-03`: 10.10.20.143
*   **VIP Cluster**: `10.10.20.55`.

### Componenti Core
*   **CNI**: Flannel (Default Talos).
*   **Ingress Controller**: Traefik (con CRD IngressRoute).
*   **Load Balancer**: MetalLB (Layer 2).
*   **Certificate Management**: Cert-Manager (DNS-01 Challenge via Cloudflare).
*   **Storage**:
    *   `OpenEBS/LocalPath`: Per storage veloce/effimero sui nodi.
    *   `NFS-Subdir-External-Provisioner`: Per volumi persistenti su TrueNAS (`/mnt/stripe/k8s-arr`).

---

## 4. Organizzazione dello Storage

### TrueNAS Scale (VM ID 1100)
Cuore dello storage centrale, gestito come VM su PVE1 con controller HBA in pass-through.
*   **Pool `oliraid`**: Storage primario (HDD). Contiene i media server (`arrdata/media`), documenti e backup generali.
*   **Pool `stripe`**: Storage veloce (SSD/NVMe). Dedicato ai volumi persistenti Kubernetes (`k8s-arr`) per performance I/O superiori.

### Integrazione Kubernetes
*   **NFS CSI Driver**:
    *   Utilizzato per i Persistent Volume Claims (PVC) standard.
    *   Punta a `/mnt/stripe/k8s-arr` su TrueNAS.
*   **Local Path Provisioner**:
    *   Utilizzato per workload effimeri o che richiedono IOPS elevate locali al nodo.

### Backup Target
*   **MinIO (S3)**: Istanza su TrueNAS, funge da repository per **Velero** (backup cluster K8s).
*   **NFS Backup**: Share dedicata (`/mnt/pbs-store`) montata da Proxmox Backup Server.

---

## 5. Software Stack & Applicazioni

### Servarr & Media (Namespace: `arr`)
Gestione automatizzata dei media, migrata interamente su Database Relazionale.
*   **Applicazioni**: Radarr, Lidarr, Prowlarr. (Readarr deprecato).
*   **Database**: **PostgreSQL** (CloudNativePG operator).
    *   Cluster PGIP: `10.10.20.57` (MetalLB).
    *   Vantaggio: Performance superiori e integrità dati rispetto a SQLite su NFS.
*   **Download**: qBittorrent.
    *   **Networking**: Traffico instradato via Sidecar Container **Xray** (VPN/Tunnel) per privacy.
*   **Player**: Jellyfin (Standalone LXC su PVE2 per accesso diretto iGPU/HW Transcoding, montato via NFS).

### Automation & Dashboard
*   **Homepage**: Dashboard principale (`home.pindaroli.org` / `home-internal`). Configurazione splittata per link interni/esterni.
*   **n8n**: Workflow automation.
*   **Gitea/Forgejo**: (Se presente/pianificato) Self-hosted git.

### Backup & Disaster Recovery
*   **Velero**: Backup delle risorse Kubernetes e dei PVC verso MinIO (S3 on TrueNAS).
*   **Proxmox Backup Server (PBS)**: Backup snapshot completi delle VM e dei container LXC.

---

## 6. Automazione & Ansible
La gestione dell'infrastruttura adotta l'approccio *Infrastructure as Code* (IaC).

### Repository & Source of Truth
*   **`ansible/`**: Contiene tutti i playbook di automazione.
*   **`rete.json`**: File JSON centrale che definisce l'intera topologia di rete (IP, MAC, VLAN, DNS). È la fonte di verità per la configurazione dei servizi di rete.

### Playbook Critici
1.  **Shutdown Lab** (`ansible/playbooks/shutdown_lab.yml`):
    *   Orchestra lo spegnimento sequenziale dell'intero rack.
    *   Flusso: Talos Nodes -> Database -> Storage -> Hypervisors.
    *   Salvaguardia l'integrità dei dati (ZFS/Postgres) prevenendo spegnimenti bruschi.
2.  **Network Sync**:
    *   `dhcp_reservations.yml`: Applica le prenotazioni DHCP su OPNsense (utilizzando l'API di Kea DHCP) leggendo da `rete.json`.
    *   `opnsense_sync_dns.yml`: Configura gli override DNS su Unbound (OPNsense) per la risoluzione interna locali.

### Gestione Segreti
*   **Ansible Vault**: Cifra tutte le credenziali sensibili (token API, chiavi SSH, password DB) nel file `ansible/vars/secrets.yml`.
*   **Scripts**: Script ausiliari in `scripts/` e `secrets/` per la gestione dell'ambiente.

---

## 7. Stato Attuale e Manutenzione

### Completati Recenti
*   ✅ Migrazione Database Servarr da SQLite a PostgreSQL.
*   ✅ Implementazione OAuth2 globale su Cloudflare Tunnel.
*   ✅ Configurazione Networking Split-DNS.
*   ✅ Setup Sidecar VPN (Xray) per qBittorrent.

### Criticità Aperte / Next Steps
*   ⚠️ **Recovery Nodo PVE3**: Il nodo fisico è offline. Necessario ripristino per ridondanza completa (Quorum Proxmox e Talos).
*   ⚠️ **Upgrade Hardware**: Sostituzione pianificata di PVE3 con nuovo hardware (Ryzen 9).
*   🔄 **Maintenance**: Monitoraggio log Velero e verifica consistenza backup Postgres.

---
title: "Piano: Integrazione Operativa ServiceNow & CMDB Homelab"
type: plan
status: active
certified_for_ai: true
created_at: 2026-07-27
tags:
  - "#plan"
  - "#servicenow"
  - "#cmdb"
  - "#itom"
  - "#proxmox"
  - "#talos"
  - "#opnsense"
  - "#truenas"
---

# Piano: Integrazione Operativa ServiceNow & CMDB Homelab

**Target**: Homelab Infrastructure & ServiceNow PDI · **Data**: 2026-07-27
**Autore**: Antigravity AI Engineering

> [!IMPORTANT]
> **Obiettivo Operativo**: Portare l'intera infrastruttura del Homelab (**Proxmox PVE1/PVE2/PVE3**, **TrueNAS Scale**, **Cluster K8s GEMINI su Talos**, **OPNsense**, **Switch ONTi / Extreme X620 / Horaco / GoodTop**, **n8n**, **Prefect**) sotto piena gestione e governance ServiceNow (CMDB, CSDM 4.0, ITOM Discovery, ITSM Operativo, HAM Pro, IntegrationHub e Sviluppo Custom App Engine).
>
> Questo piano si concentra esclusivamente sull'**esecuzione tecnica e architetturale**, eliminando le stime d'ore umane e i percorsi di formazione/certificazione.

---

## Architecture & Integration Layout

```
                               ┌──────────────────────────────────────────────┐
                               │            ServiceNow PDI (Cloud)            │
                               │  - CMDB (CSDM 4.0) & Service Graph          │
                               │  - ITSM (Incident/Problem/Change/SLA)        │
                               │  - HAM Pro & Asset Workspace                 │
                               │  - IntegrationHub & Flow Designer            │
                               │  - App Engine ("HomeLab CMDB Enhancer")      │
                               └──────────────────────▲───────────────────────┘
                                                      │ (Outbound HTTPS 443)
                                                      │
                                   ┌──────────────────┴──────────────────┐
                                   │   OPNsense Firewall (VLAN 10 Out)   │
                                   └──────────────────▲──────────────────┘
                                                      │
 ┌────────────────────────────────────────────────────┴────────────────────────────────────────────────────┐
 │  Homelab Private Network (VLAN 10 Server / VLAN 20 K8s / VLAN 99 OOB)                                   │
 │                                                                                                         │
 │   ┌──────────────────────────┐     ┌──────────────────────────┐     ┌───────────────────────────────┐   │
 │   │  Proxmox MID Server VM   │     │  Proxmox Cluster         │     │  TrueNAS Scale                │   │
 │   │  - ITOM MID Agent        │────►│  - PVE1, PVE2, PVE3    │────►│  - ZFS Storage & NFS Shares   │   │
 │   │  - Discovery Engine      │     │  - VMs & LXC Containers  │     │  - REST API & SSH             │   │
 │   │  - IntegrationHub Proxy  │     └──────────────────────────┘     └───────────────────────────────┘   │
 │   └────────────┬─────────────┘                                                                          │
 │                │                   ┌──────────────────────────┐     ┌───────────────────────────────┐   │
 │                ├──────────────────►│  K8s Cluster GEMINI      │     │  Network Infrastructure       │   │
 │                │                   │  - Talos Control Plane   │────►│  - Extreme X620 (10G Switch) │   │
 │                │                   │  - Traefik Ingress VIP   │     │  - ONTi 8-port 10G Switch     │   │
 │                │                   └──────────────────────────┘     └───────────────────────────────┘   │
 │                │                                                                                        │
 │                └──────────────────► Automation Bridge: n8n Webhooks & Prefect Orchestration             │
 └─────────────────────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## Fase 1: Foundation & Struttura Dati Fondazionale (Piattaforma)

### Sotto-piano 1.1: Struttura Organizzativa Fittizia
- [ ] Creazione Company `HomeLab Corp`.
- [ ] Creazione Dipartimenti: `IT Ops`, `NetOps`, `DevOps`, `Security`.
- [ ] Creazione Location: `Home Server Room`.
- [ ] Configurazione Gerarchia aziendale su `User Administration > Companies / Departments`.

### Sotto-piano 1.2: Utenti, Gruppi e Governance RBAC
- [ ] Creazione account utente tecnici: `admin`, `itil`, `asset_manager`, `discovery_admin`, `developer`.
- [ ] Creazione gruppi di lavoro per ogni team (`IT Ops HomeLab`, `NetOps HomeLab`, `DevOps HomeLab`).
- [ ] Assegnazione ruoli RBAC ai gruppi e verifica ereditarietà sui singoli utenti.

### Sotto-piano 1.3: Attivazione Moduli & Plugin
- [ ] Attivazione plugin `ITOM Visibility` (`sn_itom_pattern`).
- [ ] Attivazione e configurazione `ITSM Guided Setup`.
- [ ] Attivazione `Hardware Asset Management Professional`.

### Sotto-piano 1.4: CSDM Foundation Stage
- [ ] Popolamento tabelle fondazionali del modello CSDM 4.0:
  - `Business Process`: Processi operativi del lab.
  - `Contract`: Contratti di manutenzione fittizi/hardware.
  - `Product Model`: Modelli per hardware in uso (Intel X710, AMD Ryzen AI Strix, ONTi 8G SFP+, Extreme X620-10x).

### Sotto-piano 1.5: Processi ITSM & Service Catalog
- [ ] Configurazione ITSM Guided Setup per Incident, Problem e Change Management.
- [ ] Configurazione categorie Incident coerenti con il lab: `Storage`, `Network`, `Compute`, `Kubernetes`, `Security`.
- [ ] Definizione Change Models: `Standard`, `Normal`, `Emergency`.
- [ ] Creazione Catalog Items nel Service Catalog:
  - *"Provisioning VM su Proxmox"*
  - *"Aggiunta VLAN OPNsense"*
  - *"Deploy Namespace Kubernetes"*
- [ ] Impostazione variabili e workflow di approvazione in Workflow Studio.

---

## Fase 2: MID Server, Connettività & ITOM Discovery

### Sotto-piano 2.1: Provisioning VM MID Server su Proxmox
- [ ] Creazione VM Linux (Debian 12 o Ubuntu 22.04 LTS) su PVE2/PVE3:
  - Subnet: VLAN 10 Server (`10.10.10.x`).
  - Sizing: 4 vCPU, 4GB RAM, 40GB Disk, Java 11+.
  - IP Statico e configurazione DNS.
- [ ] Configurazione regola firewall OPNsense: abilitare traffico outbound dal MID Server verso il PDI ServiceNow (porta `443/SSL`).
- [ ] Creazione utente MID Server sull'istanza ServiceNow (`Discovery > Platform foundations > MID Server user`).

### Sotto-piano 2.2: Installazione & Validazione MID Server
- [ ] Download pacchetto MID Server per Linux dal PDI.
- [ ] Configurazione `config.xml` con URL istanza e credenziali MID user.
- [ ] Avvio daemon MID Server e verifica comparsa in `Discovery > MID Servers`.
- [ ] Esecuzione procedura di validazione (`Validate MID Server`).
- [ ] Assegnazione `Application = ALL` e configurazione IP Ranges (`10.10.10.0/24`, `10.10.20.0/24`).

### Sotto-piano 2.3: Configurazione Credenziali di Discovery
- [ ] Creazione credenziali SSH per i nodi Proxmox PVE1/PVE2/PVE3 e TrueNAS (`Unix Credentials`).
- [ ] Creazione credenziali SNMP v3 per gli switch ONTi ed Extreme Networks X620.
- [ ] Creazione credenziali per TrueNAS (API Key o SSH).
- [ ] Test di credential affinity automatica tramite MID Server.

### Sotto-piano 2.4: Esecuzione Schedule di Discovery
- [ ] **Subnet Discovery:** Esecuzione Subnet Discovery via OPNsense SNMP per identificare le subnet `10.10.10.0/24` e `10.10.20.0/24` e popolare `cmdb_ci_ip_network`.
- [ ] **Discovery Schedule VLAN 10 (Server):** Scansione range `10.10.10.0/24` (SSH Linux per PVE1/2/3, TrueNAS; SNMP per switch).
- [ ] **Discovery Schedule VLAN 20 (Client/K8s):** Scansione range `10.10.20.0/24` (Nodi Control Plane Talos `talos-cp-01`, `-02`, `-03` e tracciamento VIPs `10.10.20.55`, `10.10.20.56`, `10.10.20.60`).
- [ ] **Discovery Schedule Network:** Scansione OPNsense, ONTi 8-port 10G, Extreme X620 per popolamento `cmdb_ci_netgear` e topologia Layer 3.

### Sotto-piano 2.5: Gap Analysis e Schedulazione Ricorrente
- [ ] Analisi Discovery Log ed ECC Queue.
- [ ] Identificazione CI non scoperti da agentless (es. VM Proxmox senza agent, workloads Kubernetes).
- [ ] Schedulazione automatica ricorsiva (giornaliera per VLAN 10, settimanale per VLAN 20).

---

## Fase 3: CMDB Design, CSDM Implementation & Governance

### Sotto-piano 3.1: Mapping CI Classes alla Gerarchia CMDB
- [ ] Definizione e costruzione matrice di mapping per l'Homelab:
  - `PVE1, PVE2, PVE3` ➔ `cmdb_ci_unix_server`
  - `TrueNAS Scale VM` ➔ `cmdb_ci_storage_server`
  - `OPNsense` ➔ `cmdb_ci_firewall`
  - Switch `ONTi / Extreme X620 / Horaco / GoodTop` ➔ `cmdb_ci_netgear`
  - `VM Proxmox (generiche)` ➔ `cmdb_ci_virtual_machine_instance`
  - `Nodi Talos (talos-cp-01, -02, -03)` ➔ `cmdb_ci_kubernetes_node`
  - `Cluster GEMINI` ➔ `cmdb_ci_kubernetes_cluster`
  - `postgres-main (CloudNativePG)` ➔ `cmdb_ci_db_postgresql_instance`
  - `Traefik / n8n / Prefect / Sonarr / Radarr / Jellyfin` ➔ `cmdb_ci_appl`

### Sotto-piano 3.2: Population Manuale / Import Set per CI Non Scoperti
- [ ] Importazione o inserimento manuale CI non raggiungibili via Discovery standard:
  - VM Proxmox tramite Import Set via Proxmox REST API.
  - Nodi Talos con attributi estratti via `talosctl`.
  - LXC Containers (Jellyfin LXC, PBS LXC).
- [ ] Compilazione attributi chiave: Serial Number, Asset Tag, IP Address, OS, Location, Support Group.
- [ ] Validazione tramite IRE (*Identification and Reconciliation Engine*) per evitare duplicati.

### Sotto-piano 3.3: Modellazione Relazioni CI (`cmdb_rel_ci`)
- [ ] Creazione relazioni fondazionali:
  - `"Runs on"`: VM Proxmox ➔ Host Fisico PVE.
  - `"Hosted on"`: K8s Pods / Workloads ➔ Nodi K8s Talos.
  - `"Connected to"`: Server / Host ➔ Switch ONTi / Extreme X620.
  - `"Depends on"`: n8n / Application Services ➔ DB postgres-main.
- [ ] Validazione relazioni tramite Dependency Views e CMDB Query Builder.

### Sotto-piano 3.4: Modellazione Technical & Application Services (CSDM)
- [ ] Creazione Technical Service: `"Kubernetes Cluster GEMINI"` (Business Criticality = 1).
- [ ] Creazione Application Service: `"Media Stack"` (Jellyfin + Sonarr + Radarr + TrueNAS).
- [ ] Creazione Application Service: `"Automation Platform"` (n8n + Prefect + postgres-main).
- [ ] Associazione CI agli Application Services tramite `svc_ci_associ`.

### Sotto-piano 3.5: Service Mapping Top-Down (Kubernetes Ingress)
- [ ] Installazione Service Mapping Plus.
- [ ] Configurazione Entry Point per il servizio Traefik (`VIP 10.10.20.56`).
- [ ] Esecuzione Service Mapping top-down per ricostruire la mappa di servizio *"Kubernetes Ingress"*.

### Sotto-piano 3.6: CMDB Health & Governance
- [ ] Impostazione Principal Classes in CI Class Manager (`Server`, `Network Device`, `Firewall`, `Kubernetes Cluster`).
- [ ] Accesso a CMDB Workspace e configurazione KPI di Completeness, Correctness, Compliance (Target >80%).
- [ ] Configurazione Data Manager Policy: Attestazione semestrale per CI Server, Data Purge per CI stale (>90 giorni).

---

## Fase 4: ITSM Operativo, HAM & Event Management

### Sotto-piano 4.1: ITSM Operations Workflow
- [ ] **Incident Management:** Apertura e gestione ciclo completo (New ➔ In Progress ➔ Resolved ➔ Closed) per eventi reali:
  - *"Disco ZFS degraded su TrueNAS"*
  - *"Nodo K8s irraggiungibile"*
  - *"OPNsense update failure"*
- [ ] **Change Management:**
  - Normal Change per *"Upgrade Proxmox VE da 8.x a 9.2 su PVE1"* (Risk Assessment, Test Plan, Rollback Plan).
  - Standard Change per *"Aggiunta VLAN Kubernetes"*.
- [ ] **Problem Management:** Problem Record per *"Intermittent K8s pod scheduling failures"*, collegato agli incident correlati, Problem Task e generazione Known Error.
- [ ] **Service Level Management (SLA):** Definizione SLA Agreement per Technical Services (es. K8s Cluster: 99.5% uptime, RTO 4h), associazione agli incident e monitoraggio dei breach.

### Sotto-piano 4.2: Hardware Asset Management (HAM Pro)
- [ ] Attivazione Hardware Asset Workspace.
- [ ] Creazione Asset Records per: 3x Mini PC PVE, Switch ONTi, Switch Extreme X620, Switch Horaco, Switch GoodTop, AP Cudy, Mini PC OPNsense.
- [ ] Compilazione campi: Asset Tag, Serial Number, Model, Location, Purchase Cost, Warranty Expiry.
- [ ] Collegamento di ogni Asset Record al corrispettivo CI CMDB.
- [ ] Gestione del ciclo di vita (`In Stock` ➔ `Deployed` ➔ `In Maintenance` ➔ `Retired`).

### Sotto-piano 4.3: Rete OOB & VLAN 99 in CMDB
- [ ] Modellazione rete OOB (`192.168.100.0/24`, VLAN 99) come `Management Network` separata nel CMDB.
- [ ] Creazione CI per le interfacce OOB di PVE1/PVE2/PVE3 e porta ADMIN di OPNsense (`Management Interface`).

### Sotto-piano 4.4: Event Management & AIOps
- [ ] Configurazione plugin Event Management.
- [ ] Invio eventi via REST API al MID Server per simulare alert da Prometheus / Alertmanager (K8s).
- [ ] Configurazione Alert Rules per la correlazione automatica `Eventi` ➔ `Incident`.

---

## Fase 5: Integrazioni REST, IntegrationHub & Workflow Automation

### Sotto-piano 5.1: REST Table API & Script Homelab
- [ ] Utilizzo Table API (GET, POST, PUT, PATCH) con curl/Postman per lettura e scrittura CMDB.
- [ ] Creazione script Python/Ansible nell'Homelab che legge le metriche/API Proxmox e scrive/aggiorna i CI su ServiceNow.

### Sotto-piano 5.2: IntegrationHub Spokes & Connection Aliases
- [ ] Attivazione IntegrationHub su PDI e configurazione Connections Dashboard.
- [ ] Creazione Connection Alias per Proxmox VE API (REST via MID Server).
- [ ] Creazione REST Action Custom in Workflow Studio per interrogare le API Proxmox e ritornare la lista delle VM.

### Sotto-piano 5.3: Flow Designer Workflows
- [ ] Creazione Flow scatenato su `Incident Created` con `Category = Storage`:
  1. Cerca il CI coinvolto nel CMDB.
  2. Verifica se il CI è un nodo TrueNAS.
  3. Invia chiamata REST API via MID Server a TrueNAS per leggere lo stato del pool ZFS.
  4. Scrive il risultato nelle Work Notes dell'incident.

### Sotto-piano 5.4: IntegrationHub SSH Step su Proxmox
- [ ] Configurazione SSH Step in IntegrationHub con MID Server come proxy.
- [ ] Creazione Action *"Proxmox Node Status"* che esegue SSH su PVE1/PVE2/PVE3 con comando `pvesh get /nodes`.
- [ ] Integrazione dell'action in un Flow scatenato da Change Request.

### Sotto-piano 5.5: Integrazione Inbound n8n / Alertmanager ➔ ServiceNow
- [ ] Configurazione n8n per inviare Webhook a ServiceNow al verificarsi di un alert (es. *"Disco K8s PVC Full"*).
- [ ] Creazione Inbound Webhook Trigger in Workflow Studio per parsificare il JSON e creare automaticamente un Incident con CI correlato.

### Sotto-piano 5.6: DNS Split-Horizon OPNsense
- [ ] Configurazione Unbound DNS su OPNsense per risolvere internamente i domini `*-internal.pindaroli.org` verso i servizi del cluster K8s.
- [ ] Verifica che il MID Server risolva correttamente gli hostname interni.

### Sotto-piano 5.7: Automazione Ansible Orchestrata da ServiceNow
- [ ] Creazione Action IntegrationHub che esegue un playbook Ansible sull'Homelab tramite SSH Step verso un Ansible Controller / MID Server.
- [ ] Use Case: *"Change Approved ➔ esegui playbook Ansible per configurare OPNsense"*.

### Sotto-piano 5.8: Playbooks Operativi in Workflow Studio
- [ ] Creazione Playbook ITSM per il processo *"Nodo K8s Irraggiungibile"*:
  `Check` ➔ `Cordon node` ➔ `Drain pods` ➔ `Reboot via Proxmox API` ➔ `Wait` ➔ `Uncordon` ➔ `Verify`.
- [ ] Implementazione Decision Tables per logica condizionale senza codice.

---

## Fase 6: Sviluppo Custom App Engine "HomeLab CMDB Enhancer"

### Sotto-piano 6.1: Scripting Server-Side (GlideRecord & Business Rules)
- [ ] Scrittura script GlideRecord per operazioni CRUD su tabelle CMDB.
- [ ] Scrittura Business Rules (`before`, `after`, `async`) per auto-assegnazione incident in base al CI colpito.
- [ ] Creazione Script Include per logica riusabile.

### Sotto-piano 6.2: Client Scripts & UI Policies
- [ ] Scrittura UI Policy per mostrare/nascondere campi del form CI in base alla classe.
- [ ] Scrittura Client Scripts (`onLoad`, `onChange`) usando `GlideForm` e `GlideAjax` per chiamate server asincrone.

### Sotto-piano 6.3: Scoped Application "HomeLab CMDB Enhancer"
- [ ] Creazione Scoped Application in App Engine Studio:
  1. Tabella custom `Proxmox Cluster Node` estesa da `cmdb_ci_server` con attributi specifici (ZFS pool status, CPU pinning, PCI passthrough).
  2. Widget Service Portal per mostrare lo stato real-time dei nodi PVE.
  3. Scheduled Job che invoca l'API Proxmox via IntegrationHub ogni ora e aggiorna i CI.

### Sotto-piano 6.4: Scripted REST API Custom
- [ ] Creazione Scripted REST API esponendo l'endpoint GET `/api/homelab/infra/summary`.
- [ ] Output JSON: conteggio CI per tipo, stato CMDB Health, incident aperti per servizio.
- [ ] Consumo dell'endpoint da n8n per la dashboard interna con autenticazione OAuth2.

### Sotto-piano 6.5: Automated Test Framework (ATF)
- [ ] Creazione Test Suite con ATF per validare la Scoped Application.
- [ ] Scrittura test automatizzati per Business Rules, Client Scripts e Scripted REST API.

---

## 📋 Appendice Operativa: Matrice di Mapping Homelab ➔ CMDB

| Componente Homelab | Classe CMDB | Tabella ServiceNow | Metodo di Popolamento | Priorità |
| :--- | :--- | :--- | :--- | :--- |
| **PVE1, PVE2, PVE3** | UNIX Server | `cmdb_ci_unix_server` | Discovery SSH | ALTA |
| **TrueNAS Scale VM** | Storage Server | `cmdb_ci_storage_server` | Discovery SSH + Manuale (Pool ZFS) | ALTA |
| **OPNsense Mini PC** | Firewall | `cmdb_ci_firewall` | Discovery SNMP + Manuale | ALTA |
| **ONTi 10G, Extreme X620** | Network Gear (Switch) | `cmdb_ci_netgear` | Discovery SNMP | ALTA |
| **Horaco 2.5G, GoodTop 2.5G** | Network Gear (Switch) | `cmdb_ci_netgear` | Manuale (no SNMP v3) | MEDIA |
| **Cudy AP11000** | Wireless Access Point | `cmdb_ci_wap_network` | Manuale | MEDIA |
| **VM Proxmox (generiche)** | Virtual Machine Instance | `cmdb_ci_vmware_instance` | Import Set via Proxmox API + REST | ALTA |
| **talos-cp-01, -02, -03** | Kubernetes Node | `cmdb_ci_kubernetes_node` | Manuale + API `talosctl` | ALTA |
| **Cluster GEMINI (VIP 10.10.20.55)** | Kubernetes Cluster | `cmdb_ci_kubernetes_cluster` | Manuale | ALTA |
| **postgres-main (CloudNativePG)** | PostgreSQL Database | `cmdb_ci_db_postgresql_instance` | Discovery Pattern / Manuale | ALTA |
| **Traefik (VIP 10.10.20.56)** | Application | `cmdb_ci_appl` | Service Mapping Top-Down | MEDIA |
| **n8n, Prefect, Homepage** | Application | `cmdb_ci_appl` | Manuale + Service Mapping | MEDIA |
| **Jellyfin (LXC su PVE3)** | Application / Server | `cmdb_ci_appl` / `cmdb_ci_linux_server` | Discovery SSH (LXC) + Manuale | MEDIA |
| **PBS (Proxmox Backup Server LXC)**| Application Server | `cmdb_ci_app_server` | Discovery SSH / Manuale | MEDIA |
| **VLAN 10, 20, 99, 1** | IP Network | `cmdb_ci_ip_network` | Discovery Network Schedule | ALTA |

---

## 💾 Stato di Ripristino (AI Save-State)
- **Fase Attiva**: Fase 1 / Foundation & Struttura Dati Fondazionale
- **Ultima Azione Completata**: Stesura e materializzazione del piano esecutivo nel Wiki (`wiki/plans/plan-servicenow-homelab-integration.md`)
- **Prossimo Passo Operativo**: Avvio attività Fase 1.1 (Creazione Company `HomeLab Corp`, Dipartimenti e Location su ServiceNow PDI)
- **Blocchi/Decisioni Pendenti**: Nessuno.

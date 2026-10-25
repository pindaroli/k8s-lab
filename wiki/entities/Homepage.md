---
title: "Homepage Dashboard"
last_updated: "2026-10-25"
confidence: "High"
tags:
  - "#app"
  - "#dashboard"
  - "#ui"
  - "#mcp"
provenance:
  - "homepage/kustomization.yaml"
  - "wiki/plans/homepage-four-modes-reorganization.md"
  - "wiki/plans/homepage-upgrade-v2.4.0.md"
---

# Homepage Dashboard

Homepage è la dashboard centrale del lab, che fornisce una vista aggregata di tutti i servizi, lo stato del cluster Kubernetes e le metriche in tempo reale. Tutte le istanze sono allineate alla versione **v2.4.0** (`ghcr.io/gethomepage/homepage:v2.4.0`) e riorganizzate sotto l'unica directory canonica `homepage/` a seguito del piano [[homepage-four-modes-reorganization]].

## 1. Accesso & Le 4 Modalità Unificate in `homepage/`
Tutte e 4 le varianti di Homepage sono versionate su Git in sottocartelle omogenee di `homepage/` contenenti i file nativi YAML/CSS/JS (`services.yaml`, `widgets.yaml`, `settings.yaml`, `bookmarks.yaml`, `custom.css`, `custom.js`):
- **1. Esterna (`homepage/external/`)**: `https://home.pindaroli.org` (Kubernetes, protetta da [[OAuth2_Proxy]] e [[Traefik]]). MCP disabilitato (`HOMEPAGE_MCP_ENABLED: "false"`).
- **2. Interna `FULL` (`homepage/lab_mode_full/`)**: `https://home-internal.pindaroli.org` (Kubernetes, accesso diretto LAN/VPN senza OAuth2). MCP abilitato con Bearer token.
- **3. Interna `ECO` (`homepage/lab_mode_eco/`)**: `https://home-internal.pindaroli.org` / `http://10.10.20.50:3000` (Docker TrueNAS in `docker/truenas/docker-compose.yaml`, sincronizzata automaticamente via `rsync` verso `/mnt/stripe/truenas-docker/homepage/`). MCP abilitato con Bearer token.
- **4. Interna `OFF` (`homepage/lab_mode_off/`)**: `https://home-internal.pindaroli.org` / `http://10.10.20.100:3000` (Docker Mac Studio OrbStack in `docker/orbstack/docker-compose.yaml`, montata direttamente in bind-mount).
- **Manifesti Infrastrutturali Kubernetes (`homepage/k8s/` + `homepage/kustomization.yaml`)**: Deployment, Service, RBAC, IngressRoute e Middleware Steam sono separati dai contenuti e applicati tramite **`kubectl apply -k homepage/`** (`configMapGenerator` con hash suffix automatico).

## 2. Model Context Protocol (MCP Endpoint)
Homepage espone nativamente un endpoint MCP su `POST /api/mcp` abilitato sui canali interni fidati:
- **Token di Sicurezza**: `HOMEPAGE_MCP_TOKEN` iniettato via Secret Kubernetes `homepage-mcp-secret` in `default` e via docker-compose su TrueNAS.
- **Autenticazione**: Header `Authorization: Bearer <HOMEPAGE_MCP_TOKEN>` o `X-Homepage-MCP-Token: <token>`.
- **Tool Esposti**: `list_config_files`, `read_config_file`, `validate_config_file`, `write_config_file`, `add_service`, `add_info_widget`, `homepage_docs`.

## 3. Permessi RBAC (Critico K8s)
Per visualizzare i dati del cluster (nodi, pod, ingress), Homepage utilizza un **ServiceAccount** dedicato (`homepage` / `homepage-local`) nel namespace `default`.
- **ClusterRole**: Possiede permessi di `get` e `list` su namespaces, pods, nodes e ingressroutes.
- **Troubleshooting**: Se i widget dei nodi appaiono vuoti, verificare che il `ClusterRoleBinding` sia attivo:
  ```bash
  kubectl describe clusterrolebinding homepage
  ```

## 4. Widget e Integrazioni
- **Kubernetes**: Mostra CPU/Memory del [[Talos_Cluster]].
- **Servizi Arrs**: Integrazione API con Sonarr/Radarr per mostrare le code di download.
- **Monitoring**: Visualizza grafici provenienti da [[Monitoring]] (VictoriaMetrics).

## 5. Controllo Workload On-Demand (LXC Steam Host)
Homepage include un controllo interattivo per la gestione del container gaming `lxc-steam` (`CT 301` su PVE3):
- **Architettura API**: Utilizza le API REST native di Proxmox VE (`/api2/json/nodes/pve3/lxc/301/status/...`) instradate via Traefik con middleware di riscrittura (`steam-api-rewrite`) e iniezione credenziali server-side (`steam-api-headers`).
- **Sicurezza**: Utente dedicato `steam-ui@pve` con ruolo ristretto `SteamOperator` (`VM.PowerMgmt`, `VM.Audit`) vincolato all'oggetto `/vms/301`. Nessuna credenziale esposta nel client browser.
- **Frontend**: Pillola nativa glassmorphism posizionata in basso a destra nella casella "Steam Host" (`custom.js` e `custom.css`):
  - 🟢 **Spegni**: quando il container è online (cliccando arresta il container e avvia Ollama).
  - 🔴 **Avvia**: quando il container è spento (cliccando avvia il container e arresta Ollama).
  - 🟡 **Avvio... / Stop...**: stato transitorio con spinner.
- Piano di riferimento: [[homepage-steam-lxc-control-button]].

## 6. Standard Icone Servizi & Skill Operativa
La gestione dei servizi, la risoluzione delle icone e il rollout delle dashboard sono governati tassativamente dalla skill [homepage-manager](file:///.agents/skills/homepage-manager/SKILL.md).
Prima dell'inserimento, ogni icona è soggetta al protocollo di verifica preventiva a 7 livelli (Dashboard Icons, varianti SVG/alt, selfh.st, web asset interni dell'app `/apple-touch-icon.png` e `/logo.svg`, Simple Icons, Lobe/CNCF e Chart.yaml upstream), con fallback standard MDI solo se tutti i tentativi falliscono.

## Relazioni
- Autenticazione via: [[OAuth2_Proxy]].
- Esposta via: [[Traefik]].
- Monitora: [[Talos_Cluster]], [[Servarr]], [[Tdarr]].
- Controlla on-demand: `lxc-steam` (`CT 301` su PVE3).

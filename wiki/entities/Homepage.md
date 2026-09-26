---
title: "Homepage Dashboard"
last_updated: "2026-09-26"
confidence: "High"
tags:
  - "#app"
  - "#dashboard"
  - "#ui"
  - "#mcp"
provenance:
  - "homepage/README.md"
  - "wiki/plans/homepage-upgrade-v2.4.0.md"
---

# Homepage Dashboard

Homepage è la dashboard centrale del lab, che fornisce una vista aggregata di tutti i servizi, lo stato del cluster Kubernetes e le metriche in tempo reale. Tutte le istanze sono allineate alla versione **v2.4.0** (`ghcr.io/gethomepage/homepage:v2.4.0`) a seguito del piano [[homepage-upgrade-v2.4.0]].

## 1. Accesso & Istanze
- **K8s Esterno**: `https://home.pindaroli.org` (Protetto da [[OAuth2_Proxy]] e [[Traefik]]). MCP disabilitato (`HOMEPAGE_MCP_ENABLED: "false"`).
- **K8s Interno**: `https://home-internal.pindaroli.org` (Accesso diretto LAN/VPN senza OAuth2). MCP abilitato con Bearer token.
- **Docker TrueNAS**: `http://10.10.20.50:3000` (Stack nativo bare-metal in `servarr/truenas-docker/docker-compose.yaml`). MCP abilitato con Bearer token.

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

## Relazioni
- Autenticazione via: [[OAuth2_Proxy]].
- Esposta via: [[Traefik]].
- Monitora: [[Talos_Cluster]], [[Servarr]], [[Tdarr]].

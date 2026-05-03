---
title: "Homepage Dashboard"
last_updated: "2026-05-03"
confidence: "High"
tags:
  - "#app"
  - "#dashboard"
  - "#ui"
provenance:
  - "homepage/README.md"
---

# Homepage Dashboard

Homepage è la dashboard centrale del lab, che fornisce una vista aggregata di tutti i servizi, lo stato del cluster Kubernetes e le metriche in tempo reale.

## 1. Accesso
- **URL Esterno**: `https://home.pindaroli.org` (Protetto da [[OAuth2_Proxy]]).
- **URL Interno**: `https://home-internal.pindaroli.org` (Accesso diretto LAN).

## 2. Permessi RBAC (Critico)
Per visualizzare i dati del cluster (nodi, pod, ingress), Homepage utilizza un **ServiceAccount** dedicato (`homepage`) nel namespace `default`.
- **ClusterRole**: Possiede permessi di `get` e `list` su namespaces, pods, nodes e ingressroutes.
- **Troubleshooting**: Se i widget dei nodi appaiono vuoti, verificare che il `ClusterRoleBinding` sia attivo:
  ```bash
  kubectl describe clusterrolebinding homepage
  ```

## 3. Widget e Integrazioni
- **Kubernetes**: Mostra CPU/Memory del [[Talos_Cluster]].
- **Servizi Arrs**: Integrazione API con Sonarr/Radarr per mostrare le code di download.
- **Monitoring**: Visualizza grafici provenienti da [[Monitoring]] (VictoriaMetrics).

## Relazioni
- Autenticazione via: [[OAuth2_Proxy]].
- Esposta via: [[Traefik]].
- Monitora: [[Talos_Cluster]], [[Servarr]], [[Tdarr]].

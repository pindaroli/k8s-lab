---
title: "Monitoring Stack (VictoriaMetrics)"
last_updated: "2026-05-03"
confidence: "High"
tags:
  - "#observability"
  - "#monitoring"
  - "#grafana"
provenance:
  - "monitoring/README.md"
  - "ollama/README.md"
---

# VictoriaMetrics & Grafana

La stack di observability è basata sull'operatore di **VictoriaMetrics**, distribuito nel namespace `monitoring` (etichettato come `privileged` per il node-exporter).

## 1. Accesso (Grafana)
- **URL Esterno**: `grafana.pindaroli.org` (OAuth2 Protected).
- **URL Interno**: `grafana-internal.pindaroli.org` (No-Auth LAN).
- **Password**: Gestita dal secret Kubernetes `grafana-admin-secret`.

## 2. Scraping Strategy
Tutti i target interni sono gestiti tramite Custom Resources dell'Operatore:
- **Traefik, CNPG, Velero, Servarr**: Utilizzano `VMServiceScrape`.
- **Ollama (Mac Studio)**: Utilizza un `VMStaticScrape` (`ollama-static-scrape.yaml`). Punta all'IP del Mac (`10.10.20.100:11435`) dove un Exporter Proxy (avviato via `launchd`) intercetta le chiamate API per estrarre i "Token per Secondo" dal chip M2 Ultra.

## 3. Maintenance (Helm)
Per aggiornare la stack:
```bash
helm upgrade --install victoria-monitoring vm/victoria-metrics-k8s-stack \
  --namespace monitoring --version 0.72.5 -f monitoring/vm-stack-values.yaml
```

## Relazioni
- Dashboard integrata in: [[Homepage]].
- Accesso esterno via: [[Traefik]] e [[OAuth2_Proxy]].
- Scraping nodi fornito da: [[Talos_Cluster]] (Privileged Mode).

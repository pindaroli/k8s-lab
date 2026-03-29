# VictoriaMetrics Stack — Monitoring

Stack di observability basato su **VictoriaMetrics** per il cluster Kubernetes homelab `pindaroli`.

## Struttura directory

```
monitoring/
├── README.md                        # Questo file
├── vm-stack-values.yaml             # Helm values (source of truth del deploy)
├── ingress.yaml                     # Traefik IngressRoute per Grafana
├── grafana-admin-secret.yaml.example # Template secret Grafana
├── scrapes/                         # VMServiceScrape per le app
│   ├── traefik-scrape.yaml          # Traefik Metrics
│   ├── cnpg-scrape.yaml             # PostgreSQL CloudNativePG
│   ├── velero-scrape.yaml           # Backup Monitor
│   ├── servarr-exporters.yaml       # Radarr/Lidarr/Lidarr/qBit
│   └── blackbox-exporter.yaml       # Uptime Probes
└── rules/                           # VMRule per alerting (Fase 4)
```

---

## 🚀 Stato del Deploy — ✅ OPERATIVO (7/7 Fasi)

La migrazione a VictoriaMetrics è stata completata con successo seguendo queste fasi:

### Phase 1: Core Stack
- **Namespace**: `monitoring` (Etichettato come `privileged` per node-exporter).
- **Storage**: `local-postgres` (local-path) su `talos-cp-03`.

### Phase 2: Kubernetes System Scrapes
- Monitoraggio core (Kubelet, API, Scheduler) e hardware nodi attivo.

### Phase 3: Application Scrapes
- **Scrapers**: Traefik, PostgreSQL (postgres-main), Velero, Blackbox.
- **n8n**: Database metrics consolidated in `postgres-main` (cnpg-system).
- **Servarr**: Exporters dedicati per Radarr, Lidarr, Prowlarr e qBittorrent nel namespace `arr`.

### Phase 4: Alerting (Telegram)
- Alertmanager configurato con integrazione Bot Telegram (Token salvato nel vault).

### Phase 5: Ingress & Accesso Remoto
- **URL Pubblico**: [grafana.pindaroli.org](https://grafana.pindaroli.org) (OAuth2 Protected).
- **URL Locale**: [grafana-internal.pindaroli.org](https://grafana-internal.pindaroli.org) (No-Auth LAN).
- **SSL**: Certificato wildcard locale copiato nel namespace `monitoring`.

### Phase 6: Networking & DNS
- Host registrati in `rete.json` e sincronizzati su OPNsense Unbound via Ansible.

### Phase 7: Visualizzazione (Homepage)
- Widget Grafana integrato nelle dashboard `home` e `home-internal`.

---

## 🛠️ Manutenzione e Gestione

### Password Grafana
La password di amministrazione admin è gestita dal secret `grafana-admin-secret`.

### Rollback / Upgrade
```bash
export KUBECONFIG=talos-config/kubeconfig
# Upgrade
helm upgrade --install victoria-monitoring vm/victoria-metrics-k8s-stack \
  --namespace monitoring \
  --version 0.72.5 \
  --values monitoring/vm-stack-values.yaml
```

### Note di Sicurezza
Il namespace `monitoring` richiede permessi `privileged` per il corretto funzionamento del node-exporter su Talos Linux.

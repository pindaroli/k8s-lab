# Walkthrough: VictoriaMetrics Homelab Migration

Abbiamo completato con successo la migrazione dell'intero stack di monitoraggio del laboratorio a **VictoriaMetrics**, consolidando l'osservabilità e l'alerting.

## ✅ Obiettivi Raggiunti

### 1. VictoriaMetrics Core Stack (Phase 1)
- Installato `victoria-metrics-k8s-stack` (v0.72.5) nel namespace `monitoring`.
- Configurato `vmsingle` per storage persistente su `talos-cp-03` (20GB Retention 30d).
- Risolti i problemi di permessi (`privileged`) e sicurezza di Grafana (`fsGroup: 472`).

### 2. Scraping Universale (Phase 2 & 3)
Lo stack ora monitora automaticamente:
- **Core Kube**: Kubelet, API Server, Scheduler, Controller Manager, CoreDNS.
- **Node Exporter**: Metriche hardware per tutti i nodi Talos.
- **Infrastruttura**: Traefik (porta 9100), PostgreSQL (porta 9187), Velero (porta 8085).
- **App Stack (Servarr)**: Exporters dedicati per Radarr, Lidarr, Prowlarr e qBittorrent.
- **Blackbox**: Probe uptime per domini esterni e interni.

### 3. Alerting Telegram (Phase 4)
- Integrato **Alertmanager** con il Bot Telegram del lab recuperando le credenziali dal vault Ansible.
- Creato `alertmanager-telegram-secret` per la gestione sicura del token.

### 4. Ingress & Accesso Sicuro (Phase 5 & 6)
- **IngressRoute**: Configurato accesso LAN (`grafana-internal`) e WAN (`grafana.pindaroli.org`).
- **OAuth2**: Accesso esterno protetto dal middleware `oauth2-auth` di Traefik (Google Login).
- **DNS Sync**: Alias aggiunti a `rete.json` e sincronizzati su OPNsense Unbound via Ansible.

### 5. Homepage Dashboard (Phase 7)
- Integrato il widget di Grafana sia nella Homepage interna che in quella esterna per un accesso immediato allo stato del laboratorio.

---

## 🛠️ Note Tecniche Importanti

> [!IMPORTANT]
> **Privileged Namespace**
> Il namespace `monitoring` deve mantenere l'etichetta `pod-security.kubernetes.io/enforce=privileged` per consentire l'esecuzione di componenti di sistema come il node-exporter su Talos Linux.

> [!TIP]
> **Manutenzione Scrape**
> Se aggiungi nuove app, crea un file `VMServiceScrape` in `monitoring/scrapes/` e applicalo per attivare automaticamente il monitoraggio.

---

## 🚀 Verifica Finale

- **Status Pod**: Tutti i componenti (`vmagent`, `vmsingle`, `grafana`) sono in `Running`.
- **Targets**: `vmagent` mostra tutti i target attivi e verdi su `http://localhost:8429/targets`.
- **Dashboard**: Grafana ricarica correttamente le dashboard di sistema predefinite.
- **DNS**: `nslookup grafana-internal.pindaroli.org` risolve correttamente verso il Traefik VIP (`10.10.20.56`).

Il progetto è ora in stato **OPERATIONAL**.

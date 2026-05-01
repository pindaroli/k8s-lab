# PostgreSQL Post-Recovery Tasks

## Critical Actions

### [x] Restore PVE2 Replication (In attesa del rientro dell'hardware)
### [x] Tdarr NFS & Node Connectivity
- [x] Risolto `Permission denied` su TrueNAS (10.10.10.50).
- [x] Nodo Mac Studio (10.10.20.100) connesso e operativo.
- [x] Libreria `/Volumes/arrdata/media` montata correttamente.

## Network Architecture Optimization (Premium Approach)
- [x] **Punto A: Migrazione DNS Esterno (Cloudflare Dashboard)**
  - Sostituire il CNAME wildcard `*` con record CNAME puntuali per ogni servizio.
  - *Perché*: Impedisce l'enumerazione dei sottodomini e aumenta la sicurezza del tunnel.
- [ ] **Punto B: Rafforzamento Configurazione Tunnel (Cloudflared ConfigMap)**
  - Elencare esplicitamente gli hostname nell'Ingress del tunnel invece di usare `*.pindaroli.org`.
  - *Perché*: Evita che il traffico DNS "sporco" venga dirottato a Traefik, risolvendo alla radice i problemi di Black Hole Routing.
- [x] **Documentazione Script Ansible (In Corso)**
  - Rinominato `README.md` in `ansible-scripts-doc.md`.
  - [ ] Completare la descrizione dettagliata di tutti gli script nella cartella `ansible/playbooks/`.
- [x] **Infrastructure Consistency**
  - [x] Trasformare il nome host fisico del nodo Proxmox principale da `pve` a `pve1` (Verificato).

## Network & Control Plane Stabilization (COMPLETED 2026-05-01)
- [x] **Risoluzione Asimmetria di Rete (ERR_CONNECTION_REFUSED)**
  - Migrato Traefik da Deployment a DaemonSet per distribuzione simmetrica.
  - Impostata `externalTrafficPolicy: Local` per eliminare inter-node SNAT.
  - Validata stabilità socket TCP con suite di test dedicata.
- [x] **Ripristino Service Discovery VictoriaMetrics**
  - Rimosso formalmente `talos-cp-02` da etcd per sbloccare KubePrism.
  - Verificato ripristino target in `vmagent` (32 target attivi).
- [x] **Documentazione Incidente**
  - Creato `traefik/INCIDENT_REPORT_20260501.md`.

## PVE2 Recovery (Pending Hardware)
- [ ] Applicare configurazione Talos `bind-address=0.0.0.0` a `talos-cp-02` (10.10.20.142).
  - *Nota*: Il nodo è stato rimosso da etcd il 01/05 per stabilizzare il cluster. Al rientro dovrà essere aggiunto come nuovo membro.
  - Comando: `talosctl apply-config -n 10.10.20.142 -f talos-config/controlplane.yaml`

### [ ] Consolidate n8n Database
Migrate `n8n` from local SQLite storage to a dedicated database within the `postgres-main` cluster.
- **Current Status**: `n8n` is using SQLite in `n8n-config-pvc`.
- **Goal**: Create user/db in `postgres-main` and update n8n deployment.

## Maintenance & Monitoring

### [ ] Monitor Disk Usage on talos-cp-01
The disk `/var/mnt/postgres` was recently at 100%. Ensure the usage stays below 80%.
- Command: `talosctl -n 10.10.20.141 usage /var/mnt/postgres`

### [ ] Clean Up Emergency Scripts
- [ ] Delete `force-cleanup.yaml`
- [ ] Delete `force-cleanup-n8n` job (if not already deleted)

### [ ] Grafana Session Duration
Estendere la durata della sessione di login per evitare disconnessioni frequenti.
- Configurazione in `monitoring/vm-stack-values.yaml` (sezione `grafana.ini`).
- Parametri: `login_maximum_inactive_lifetime_duration` e `login_maximum_lifetime_duration`.

## Log Management (Future Phase)

### [ ] Centrale Log (VictoriaLogs)
Implementare un sistema di aggregazione log centralizzato nel cluster per:
- **Ollama**: Tailing di `/opt/homebrew/var/log/ollama.log` via Promtail.
- **Suite ARR**: Raccolta log dai pod Radarr, Lidarr, Prowlarr e qBittorrent.
- **Configurazione**: Aggiunta log source in Grafana.

## Ollama & Client Integration

### [ ] Installazione AIChat su Nodi Lab
Installare e configurare **AIChat** per interrogare Ollama (Mac Studio) direttamente dai terminali dei nodi senza `curl`.
- [ ] Installazione binario su `pve1`, `pve2`, `pve3`.
- [ ] Installazione binario su `truenas` (SCALE).
- [ ] Configurazione endpoint: `http://10.10.20.100:11434`.

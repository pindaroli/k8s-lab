# PostgreSQL Post-Recovery Tasks

## Critical Actions

### [ ] Restore PVE2 Replication
When PVE2 is back online and the Talos node `talos-cp-02` is `Ready`, perform the following:
1. **Remove Fencing**:
   ```bash
   kubectl cnpg fencing off postgres-main "postgres-main-2" -n cnpg-system
   ```
2. **Verify Replication Slot**:
   Lo slot `_cnpg_postgres_main_2` è stato rimosso manualmente per sbloccare lo spazio disco sul nodo 3. Verificare che venga ricreato automaticamente dall'operatore dopo aver tolto il fencing. In caso contrario, riavviare il Primary `postgres-main-3`.

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
- [ ] **Infrastructure Consistency**
  - [ ] Trasformare il nome host fisico del nodo Proxmox principale da `pve` a `pve1` (incluso `/etc/hosts`, `/etc/hostname` e configurazione cluster PVE).

## PVE2 Recovery (Pending Hardware)
- [ ] Applicare configurazione Talos `bind-address=0.0.0.0` a `talos-cp-02` (10.10.20.142).
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

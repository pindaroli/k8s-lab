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


### [ ] Consolidate n8n Database
Migrate `n8n` from local SQLite storage to a dedicated database within the `postgres-main` cluster to follow the project's consolidation strategy.
- Current Status: `n8n` is using SQLite in `n8n-config-pvc`.
- Goal: Create user/db in `postgres-main` and update n8n deployment.

## Maintenance & Monitoring

### [ ] Monitor Disk Usage on talos-cp-01
The disk `/var/mnt/postgres` was recently at 100%. Ensure the usage stays below 80%.
- Command: `talosctl -n 10.10.20.141 usage /var/mnt/postgres`

### [ ] Clean Up Emergency Scripts
- [ ] Delete `force-cleanup.yaml`
- [ ] Delete `force-cleanup-n8n` job (if not already deleted)

## Log Management (Future Phase)

### [ ] Centrale Log (VictoriaLogs)
Implementare un sistema di aggregazione log centralizzato nel cluster per:
- **Ollama**: Tailing di `/opt/homebrew/var/log/ollama.log` via Promtail.
- **Suite ARR**: Raccolta log dai pod Radarr, Lidarr, Prowlarr e qBittorrent.
- **Configurazione**: Aggiunta log source in Grafana.

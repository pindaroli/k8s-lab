# Disaster Recovery con Velero 🛡️

Velero è installato nel cluster e configurato per eseguire il backup di **tutta la configurazione Kubernetes** (Deployments, Services, ConfigMaps, Secrets) su MinIO.

## 1. Architettura
- **Namespace**: `velero`
- **Storage**: MinIO Bucket `s3://velero` (Hostata su TrueNAS)
- **Schedule**: Backup automatico ogni notte alle 03:00 (`daily-backup`)
- **Retention**: 30 Giorni

## 2. Cheatsheet Comandi (Velero CLI)

Assicurati di aver installato la CLI:
```bash
brew install velero
```

### Backup Manuale
Esegui un backup on-demand (utile prima di fare modifiche rischiose):
```bash
velero backup create backup-manuale-$(date +%F) --wait
```

### Lista Backup
Vedi tutti i backup disponibili (sia manuali che schedulati):
```bash
velero backup get
```

### Ripristino (Restore)
Se cancelli per sbaglio un namespace (es. `arr`) o fai danni alla config:

**Scenario A: Ripristino Totale di un Namespace**
```bash
velero restore create --from-backup <NOME_BACKUP> --include-namespaces arr --wait
```

**Scenario B: Ripristino Intero Cluster**
```bash
velero restore create --from-backup <NOME_BACKUP> --wait
```

## 3. Manutenzione
I backup vecchi vengono cancellati automaticamente dopo 30 giorni (TTL).
Il bucket MinIO `velero` è mappato sul dataset ZFS `oliraid/velero`, quindi è protetto anche dagli snapshot di TrueNAS.

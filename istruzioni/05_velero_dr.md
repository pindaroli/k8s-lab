# Guida Operativa Velero 🛡️

Velero è il tuo "Time Machine" per Kubernetes. Salva lo stato del cluster (Deployment, Service, ConfigMap, Secret) sotto forma di file compressi su MinIO.

## 1. I Tre Pilastri di Velero
1.  **Backup**: Una "foto" istantanea del cluster o di un namespace.
2.  **Schedule**: Un backup automatico ricorrente (es. "ogni notte alle 3").
3.  **Restore**: L'atto di prendere una "foto" e riapplicarla al cluster.

---

## 2. Lezione Pratica: Comandi CLI

### A. La Routine (Backup)
Prima di fare una modifica pericolosa (es. aggiornare un'app), fai sempre un backup manuale.

**Sintassi Base:**
```bash
velero backup create <NOME> --include-namespaces <NAMESPACE> --wait
```

**Esempi:**
1.  **Backup di tutto il namespace `arr`:**
    ```bash
    velero backup create backup-arr-pre-upgrade --include-namespaces arr --wait
    ```
2.  **Backup di TUTTO il cluster (Tutti i namespace):**
    ```bash
    velero backup create backup-totale-$(date +%F) --wait
    ```

### B. L'Ispezione (Check)
Hai fatto il backup? È andato a buon fine? Cosa c'è dentro?

1.  **Lista dei Backup:**
    ```bash
    velero backup get
    ```
    *Cerca la colonna STATUS. Deve essere `Completed`.*

2.  **Dettagli di un Backup (Il microscopio):**
    ```bash
    velero backup describe <NOME_BACKUP>
    ```
    *Ti dice quanti oggetti ha salvato, se ci sono stati errori, e quanto è grande.*

3.  **Vedere i Logs (Se qualcosa va male):**
    ```bash
    velero backup logs <NOME_BACKUP>
    ```

### C. Il Disastro (Restore) 🚑
Hai cancellato un namespace per sbaglio? Un deployment è rotto? È ora del Restore.

> [!IMPORTANT]
> Velero, per default, **NON sovrascrive** le risorse che esistono già.
> Se vuoi ripristinare un namespace corrotto, spesso conviene prima cancellare quello rotto (se esiste ancora) e poi lanciare il restore.

**Esempio di Restore:**
```bash
velero restore create --from-backup backup-arr-pre-upgrade --wait
```

### D. La Pulizia
I backup scadono da soli (dopo 30 giorni). Ma se vuoi cancellarne uno subito (e liberare spazio su MinIO):

```bash
velero backup delete <NOME_BACKUP>
```
*(Ti chiederà conferma. Questo cancella sia il record in Velero che i file su MinIO).*

---

## 3. Setup Attuale
- **Bucket**: `s3://velero` (su TrueNAS)
- **Schedule**: `daily-backup` (Ogni notte alle 03:00)
- **Plugin**: AWS (compatibile S3 MinIO)

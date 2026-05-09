# Wiki Plan: Recyclarr Anti-Spam Automation

> [!NOTE]
> **Status**: Ready for Execution
> **Goal**: Eliminate fake/spam torrents (e.g., "Anal Teen") and automate quality filtering.

## 🎯 Obiettivo
Implementare un sistema di filtraggio euristico e proattivo basato su **TRaSH Guides** per lo stack Servarr. L'obiettivo è spostare il carico di lavoro dal "blacklistare parole" al "validare la qualità" in modo automatico e dichiarativo.

## 🛠️ Componenti
1.  **Configurazione**: [recyclarr.yaml](file:///Users/olindo/prj/k8s-lab/servarr/recyclarr.yaml)
2.  **Deployment**: [recyclarr-cronjob.yaml](file:///Users/olindo/prj/k8s-lab/servarr/recyclarr-cronjob.yaml)
3.  **Sync Logic**: Sincronizzazione periodica (12h) dei Custom Formats via API.

## 🚀 Step di Esecuzione

### 1. Preparazione Segreti
Assicurarsi che le API Key di Radarr e Sonarr siano presenti nel secret `servarr-api-keys`.
- `radarr-api-key`
- `sonarr-api-key`

### 2. Deployment
Applicare i manifesti nel cluster:
```bash
kubectl apply -f servarr/recyclarr-cronjob.yaml
```

### 3. Sincronizzazione Iniziale
Forzare il primo sync per popolare i Custom Formats:
```bash
kubectl create job --from=cronjob/recyclarr -n servarr recyclarr-init-sync
```

### 4. Validazione
- Entrare nella UI di **Radarr** -> **Settings** -> **Custom Formats**.
- Verificare la presenza di formati come `Bad Groups`, `Fake`, `Honeypot`.
- Controllare che il punteggio assegnato sia `-10000`.

## 📈 Manutenzione
Il sistema si aggiorna automaticamente. Eventuali nuovi pattern di spam scoperti dalla community verranno iniettati nel cluster al prossimo ciclo del CronJob.

---
**Riferimenti**:
- [TRaSH Guides](https://trash-guides.info/)
- [Recyclarr Documentation](https://recyclarr.dev/)

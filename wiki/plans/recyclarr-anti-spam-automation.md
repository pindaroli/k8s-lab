# Wiki Plan: Recyclarr Anti-Spam Automation

> [!NOTE]
> **Status**: ✅ **APPROVATO — Pronto per Esecuzione**
> **Goal**: Integrare Recyclarr **nativamente nel chart `pindaroli-arr-helm`** per eliminare fake/spam torrent in modo automatico e dichiarativo.

## 🎯 Obiettivo
Implementare un sistema di filtraggio euristico e proattivo basato su **TRaSH Guides** per lo stack Servarr. L'obiettivo è spostare il carico di lavoro dal "blacklistare parole" al "validare la qualità", integrandolo come **componente Helm opzionale** nel chart `servarr` del progetto `pindaroli-arr-helm`.

---

## 🏗️ Architettura

| Parametro | Valore |
|---|---|
| **Progetto** | `/Users/olindo/prj/pindaroli-arr-helm` |
| **Chart** | `charts/servarr/` |
| **Pattern** | Sottocomponente opzionale (`enabled: false` di default) |
| **Release Name** | `servarr` (verificato sul cluster) |
| **Namespace** | `arr` (verificato sul cluster) |

### Struttura File da Creare
```
charts/servarr/templates/recyclarr/
  ├── cronjob.yaml      # CronJob K8s (Helm-templated)
  └── configmap.yaml    # ConfigMap con recyclarr.yaml (Helm-templated)
```

### Sezione `values.yaml` da Aggiungere
```yaml
## @section Recyclarr parameters
## @param recyclarr.enabled Whether to enable Recyclarr.
## @param recyclarr.image.repository Docker image repository.
## @param recyclarr.image.tag Docker image tag.
## @param recyclarr.schedule Cron schedule for the sync job.
## @param recyclarr.apiKeys.existingSecret Existing K8s secret with API keys (recommended).
## @param recyclarr.apiKeys.existingSecretKeyRadarr Key name for Radarr API key in the secret.
## @param recyclarr.apiKeys.existingSecretKeySonarr Key name for Sonarr API key in the secret.
## @param recyclarr.apiKeys.radarrApiKey Radarr API key (fallback, NOT for production).
## @param recyclarr.apiKeys.sonarrApiKey Sonarr API key (fallback, NOT for production).
## @param recyclarr.radarr.enabled Whether to sync Radarr.
## @param recyclarr.radarr.url Radarr internal service URL.
## @param recyclarr.sonarr.enabled Whether to sync Sonarr.
## @param recyclarr.sonarr.url Sonarr internal service URL.
##
recyclarr:
  enabled: false
  image:
    repository: ghcr.io/recyclarr/recyclarr
    tag: "6.0"
    pullPolicy: IfNotPresent
  schedule: "0 */12 * * *"

  # API Key management (hybrid pattern)
  apiKeys:
    existingSecret: ""                         # Prioritario: nome del Secret K8s
    existingSecretKeyRadarr: "radarr-api-key"  # Chiave nel Secret per Radarr
    existingSecretKeySonarr: "sonarr-api-key"  # Chiave nel Secret per Sonarr
    radarrApiKey: ""                           # Fallback diretto (NON produzione)
    sonarrApiKey: ""                           # Fallback diretto (NON produzione)

  radarr:
    enabled: true
    url: "http://servarr-radarr.arr.svc.cluster.local:7878"  # Default verificato
  sonarr:
    enabled: false  # Disabilitato di default, attivare se si usa Sonarr
    url: "http://servarr-sonarr.arr.svc.cluster.local:8989"
```

> [!TIP]
> Gli URL di default sono costruiti sui service name verificati sul cluster (`servarr-radarr`, `servarr-sonarr` nel namespace `arr`). Se si cambia Release Name o Namespace, vanno aggiornati.

### Override in `oli-arr-values.yaml` (k8s-lab — produzione)
```yaml
recyclarr:
  enabled: true
  apiKeys:
    existingSecret: "servarr-api-keys"  # Secret già presente nel cluster
  radarr:
    enabled: true
    # url: default OK (servarr-radarr.arr.svc.cluster.local)
```

---

## ✅ Decisioni Approvate

| # | Decisione | Scelta |
|---|---|---|
| 1 | **API Keys** | Pattern ibrido: `existingSecret` prioritario, fallback a valori diretti. |
| 2 | **Service URL** | Opzione B — URL esplicito configurabile in `values.yaml`. Default pre-compilati con i valori verificati sul cluster. |
| 3 | **Service Naming** | Verificato sul cluster: `servarr-radarr`, `servarr-sonarr` nel namespace `arr`. Usati come default. |
| 4 | **Chart Metadata** | Sì — version bump in `Chart.yaml` + keyword `recyclarr` + `README.md` aggiornato. |
| 5 | **Sonarr Support** | Incluso nel chart con `sonarr.enabled: false` di default. Si attiva semplicemente settando `recyclarr.sonarr.enabled: true` nei values quando Sonarr verrà deployato. |

---

## 🚀 Step di Esecuzione (Post-Approvazione)

1. [x] **Implementazione Helm** (`pindaroli-arr-helm`):
    - [x] `values.yaml` — Aggiungere sezione `recyclarr` completa con i default verificati.
    - [x] `templates/recyclarr/configmap.yaml` — Template Helm per `recyclarr.yaml`.
    - [x] `templates/recyclarr/cronjob.yaml` — Template Helm per il CronJob.
    - [x] `Chart.yaml` — Version bump (`1.2.2` → `1.2.3`) + keyword `recyclarr`.
    - [x] `README.md` — Documentare la nuova sezione `recyclarr`.
2. [x] **Pubblicazione Chart**:
    - [x] Commit & Push su `pindaroli-arr-helm` (trigger GitHub Release/Registry).
    - [x] Versione pubblicata: **`1.2.3`**.
3. [x] **Configurazione Produzione** (`k8s-lab`):
    - [x] `arr-values.yaml` (k8s-lab) — Override di produzione con `existingSecret: servarr-api-keys`.
    - [x] `oli-arr-values.yaml` (helm repo) — Sync configurazione.
    - [x] **Cleanup**: Rimozione vecchi manifesti statici `recyclarr.yaml` e `recyclarr-cronjob.yaml`.
4. [ ] **Deployment**:
    - [ ] Eseguire `helm repo update` per scaricare la versione `1.2.3`.
    - [ ] Eseguire `helm upgrade servarr kubitodev/servarr --version 1.2.3 -n arr -f servarr/arr-values.yaml`.
5. [ ] **Verifica**:
    - [ ] Creazione Job di test: `kubectl create job --from=cronjob/servarr-recyclarr recyclarr-test-sync -n arr`.
    - [ ] Controllo log e validazione Custom Formats in Radarr UI.

---

## 📋 Riferimenti
- [pindaroli-arr-helm](https://github.com/pindaroli/pindaroli-arr-helm) — Repository sorgente del chart.
- [TRaSH Guides](https://trash-guides.info/)
- [Recyclarr Documentation](https://recyclarr.dev/)

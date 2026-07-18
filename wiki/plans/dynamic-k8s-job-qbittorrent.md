---
title: "Piano: Orchestrazione Dinamica K8s Job da qBittorrent"
last_updated: "2026-07-18"
status: "in_progress"
type: "plan"
tags:
  - "#plan"
  - "#kubernetes"
  - "#qbittorrent"
  - "#servarr"
---

# Piano: Orchestrazione Dinamica K8s Job da qBittorrent

Questo piano definisce le modifiche architetturali necessarie per innescare dinamicamente un Job Kubernetes (utilizzando l'immagine `custom-normalizer`) dalla fine di un download in qBittorrent.

Il design scelto utilizza **l'Opzione A (Raw API Call tramite curl)**, supportata dall'uso di **`jq`** per costruire in modo sicuro il JSON. Questo approccio è ottimale in quanto:
1. Mantiene l'immagine leggera (solo `curl` e `jq` richiesti).
2. Isola la logica di chiamata in uno script Bash montato via ConfigMap.
3. Risolve completamente il rischio di _injection_ (caratteri speciali, virgolette o newline nei nomi dei torrent) delegando la generazione dell'oggetto JSON direttamente al parser di `jq`.
4. Mantiene la sicurezza prelevando le credenziali Telegram direttamente dal secret via `valueFrom.secretKeyRef`.
5. **Permette il ritorno all'immagine "vanilla" (originale non modificata) di qBittorrent**, svincolando la logica di normalizzazione dal downloader.

---

## Modifiche Architetturali (Helm)

### 1. `k8s-lab/servarr/arr-values.yaml`
Ripristino dell'immagine upstream ufficiale di qBittorrent:
```yaml
qbittorrent:
  image:
    repository: lscr.io/linuxserver/qbittorrent
    tag: "5.2.3_v2.0.13-ls468"
```

### 2. `charts/servarr/templates/qbittorrent/rbac.yaml`
Creazione delle risorse RBAC affinché qBittorrent possa interfacciarsi in sicurezza con l'API Kubernetes per il solo spawn di Job:
- `Role`: Permesso per le azioni `create`, `list`, `get` sulle risorse `jobs` nell'API `batch`.
- `RoleBinding`: Associazione tra questo Role e il `ServiceAccount` esistente di qBittorrent (`{{ .Release.Name }}-qbittorrent`).

### 3. `charts/servarr/templates/qbittorrent/trigger-job-configmap.yaml`
Definizione di un `ConfigMap` contenente lo script bash `trigger-job.sh`. Questo disaccoppia definitivamente il trigger code dall'immagine Docker.

### 4. `charts/servarr/templates/qbittorrent/deployment.yaml`
- Mount della nuova `ConfigMap` (`trigger-job-configmap`) all'interno del Pod qBittorrent in `/scripts/trigger-job.sh`.
- Iniezione di `KUBERNETES_SERVICE_HOST` e `KUBERNETES_SERVICE_PORT`.

---

## Implementazione: Lo script `trigger-job.sh`

```bash
#!/usr/bin/env bash
# USO: trigger-job.sh "<CONTENT_PATH>"
set -euo pipefail

CONTENT_PATH="$1"

K8S_TOKEN="$(cat /var/run/secrets/kubernetes.io/serviceaccount/token)"
K8S_CA="/var/run/secrets/kubernetes.io/serviceaccount/ca.crt"
K8S_API="https://${KUBERNETES_SERVICE_HOST}:${KUBERNETES_SERVICE_PORT}"
NAMESPACE="$(cat /var/run/secrets/kubernetes.io/serviceaccount/namespace)"

JSON_PAYLOAD=$(jq -n \
  --arg path "$CONTENT_PATH" \
  '{
    "apiVersion": "batch/v1",
    "kind": "Job",
    "metadata": {
      "generateName": "audio-normalizer-",
      "namespace": "arr"
    },
    "spec": {
      "ttlSecondsAfterFinished": 600,
      "backoffLimit": 0,
      "template": {
        "metadata": {
          "labels": {
            "app.kubernetes.io/name": "audio-normalizer"
          }
        },
        "spec": {
          "restartPolicy": "Never",
          "affinity": {
            "podAntiAffinity": {
              "requiredDuringSchedulingIgnoredDuringExecution": [
                {
                  "labelSelector": {
                    "matchExpressions": [
                      { "key": "app.kubernetes.io/name", "operator": "In", "values": ["qbittorrent"] }
                    ]
                  },
                  "topologyKey": "kubernetes.io/hostname"
                }
              ]
            }
          },
          "containers": [
            {
              "name": "normalizer",
              "image": "ghcr.io/pindaroli/custom-normalizer:1.0.1",
              "args": [$path, "", "/media/downloads"],
              "env": [
                {
                  "name": "TELEGRAM_BOT_TOKEN",
                  "valueFrom": { "secretKeyRef": { "name": "servarr-api-keys", "key": "telegram-token" } }
                },
                {
                  "name": "TELEGRAM_CHAT_ID",
                  "valueFrom": { "secretKeyRef": { "name": "servarr-api-keys", "key": "telegram-chat-id" } }
                }
              ],
              "volumeMounts": [
                { "name": "media-data", "mountPath": "/media/downloads" }
              ]
            }
          ],
          "volumes": [
            {
              "name": "media-data",
              "persistentVolumeClaim": { "claimName": "servarr-jellyfin-media" }
            }
          ]
        }
      }
    }
  }'
)

HTTP_CODE=$(curl -sS -o /dev/null -w "%{http_code}" --cacert "$K8S_CA" \
  -H "Authorization: Bearer $K8S_TOKEN" \
  -H "Content-Type: application/json" \
  -X POST -d "$JSON_PAYLOAD" "${K8S_API}/apis/batch/v1/namespaces/${NAMESPACE}/jobs")

if [ "$HTTP_CODE" -eq 201 ]; then
    echo "Job creato con successo per: $CONTENT_PATH"
else
    echo "Errore nella creazione del Job. Codice HTTP: $HTTP_CODE"
    exit 1
fi
```

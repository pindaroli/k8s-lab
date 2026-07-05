---
title: "Piano: Provisioning Automatico Categorie qBittorrent e Rimozione jellyfin-classic"
type: plan
status: archived
certified_for_ai: false
created_at: 2026-07-05
tags:
  - "#plan"
  - "#torrent"
  - "#helm"
---

# Piano: Provisioning Automatico Categorie qBittorrent e Rimozione jellyfin-classic

**Target**: Cluster GEMINI (`pindaroli.org`) · **Data**: 2026-07-05
**Autore**: Antigravity AI Engineering

> [!IMPORTANT]
> Questo piano introduce una variabile dichiarativa `categories` in `values.yaml` che innesca un Job di post-deploy Helm per auto-configurare in modo dinamico e parametrizzato (usando il path delle preferenze di qBittorrent `/media/{{ .Values.qbittorrent.persistence.path }}`) le categorie in qBittorrent. Inoltre, rimuove completamente il servizio deprecato `jellyfin-classic`.

---

## Struttura del Job Post-Deploy (`post-deploy-job.yaml`)

```yaml
{{- if and .Values.qbittorrent.enabled .Values.qbittorrent.categories }}
apiVersion: batch/v1
kind: Job
metadata:
  name: {{ .Release.Name }}-qb-setup
  namespace: {{ .Release.Namespace }}
  labels:
    app.kubernetes.io/name: qbittorrent-setup
    app.kubernetes.io/instance: {{ .Release.Name }}
  annotations:
    "helm.sh/hook": post-install,post-upgrade
    "helm.sh/hook-delete-policy": hook-succeeded
spec:
  template:
    metadata:
      labels:
        app.kubernetes.io/name: qbittorrent-setup
        app.kubernetes.io/instance: {{ .Release.Name }}
    spec:
      restartPolicy: OnFailure
      containers:
        - name: qb-configurator
          image: alpine:latest
          env:
            - name: QBITTORRENT_USER
              valueFrom:
                secretKeyRef:
                  name: {{ .Values.recyclarr.apiKeys.existingSecret | default "servarr-api-keys" }}
                  key: qbittorrent-user
            - name: QBITTORRENT_PASS
              valueFrom:
                secretKeyRef:
                  name: {{ .Values.recyclarr.apiKeys.existingSecret | default "servarr-api-keys" }}
                  key: qbittorrent-pass
          command:
            - /bin/sh
            - -c
            - |
              apk add --no-cache curl jq
              
              QB_URL="http://{{ .Release.Name }}-qbittorrent-web:8080"
              echo "Waiting for qBittorrent WebUI at $QB_URL..."
              until curl -s -o /dev/null -w "%{http_code}" "$QB_URL/api/v2/app/version" | grep -q "403\|200"; do
                sleep 2
              done
              echo "qBittorrent is up!"
              
              echo "Logging in..."
              COOKIE=$(curl -s -i -X POST -d "username=$QBITTORRENT_USER&password=$QBITTORRENT_PASS" "$QB_URL/api/v2/auth/login" | grep -i "set-cookie:" | awk '{print $2}' | cut -d';' -f1)
              
              if [ -z "$COOKIE" ]; then
                echo "Error: Failed to authenticate with qBittorrent API."
                exit 1
              fi
              echo "Authentication successful!"
              
              echo "Retrieving existing categories..."
              EXISTING_CATEGORIES=$(curl -s -H "Cookie: $COOKIE" "$QB_URL/api/v2/torrents/categories")
              echo "Existing categories: $EXISTING_CATEGORIES"
              
              BASE_PATH="/media/{{ .Values.qbittorrent.persistence.path | default "downloads" }}"
              CATEGORIES="{{ join " " .Values.qbittorrent.categories }}"
              
              for CAT in $CATEGORIES; do
                if echo "$EXISTING_CATEGORIES" | jq -e "has(\"$CAT\")" >/dev/null 2>&1; then
                  echo "Category '$CAT' already exists. Updating save path to $BASE_PATH/$CAT..."
                  curl -s -H "Cookie: $COOKIE" -X POST \
                    -d "category=$CAT" \
                    -d "savePath=$BASE_PATH/$CAT" \
                    "$QB_URL/api/v2/torrents/editCategory"
                else
                  echo "Creating category '$CAT' with path $BASE_PATH/$CAT..."
                  curl -s -H "Cookie: $COOKIE" -X POST \
                    -d "category=$CAT" \
                    -d "savePath=$BASE_PATH/$CAT" \
                    "$QB_URL/api/v2/torrents/createCategory"
                fi
              done
              echo "qBittorrent categories provisioning completed successfully!"
{{- end }}
```

---

## Modifiche Architetturali

1. **Helm Chart (`pindaroli-arr-helm`)**:
   * Rimozione totale di `charts/servarr/templates/jellyfin-classic`.
   * Rimozione dei valori di default per `jellyfin-classic` in `values.yaml`.
   * Nuovo template `post-deploy-job.yaml` sotto `templates/qbittorrent/`.
2. **Cluster Config (`k8s-lab`)**:
   * Rimozione della configurazione di `jellyfin-classic` in `servarr/arr-values.yaml`.
   * Aggiunta delle categorie in `servarr/arr-values.yaml`:
     ```yaml
     categories:
       - radarr
       - lidarr
       - readarr
       - classical
     ```

---

## Ordine di Esecuzione

- [x] **Fase 1: Approvazione**
  - Ottenere approvazione del piano dall'utente.
- [x] **Fase 2: Rimozione jellyfin-classic**
  - Cancellare la directory `jellyfin-classic` e rimuoverlo da `values.yaml`.
- [x] **Fase 3: Implementazione Job Hook**
  - Creare il file `post-deploy-job.yaml` in `pindaroli-arr-helm`.
  - Dichiarare la variabile `categories` in `values.yaml`.
- [x] **Fase 4: Configurazione k8s-lab**
  - Aggiornare `servarr/arr-values.yaml` per rimuovere `jellyfin-classic` e inserire le categorie.
- [x] **Fase 5: Deploy & Verifica**
  - Eseguire l'upgrade di `servarr`.
  - Verificare l'esecuzione del Job e l'avvenuta creazione delle categorie nella Web UI di qBittorrent.

---

## 💾 Stato di Ripristino (AI Save-State)
- **Fase Attiva**: Completato
- **Ultima Azione Completata**: Correzione del Job, deploy ed effettiva verifica delle categorie create in qBittorrent via chiamata API autenticata.
- **Prossimo Passo Operativo**: Nessuno, l'automazione è completata ed integrata.
- **Blocchi/Decisioni Pendenti**: Nessuno.

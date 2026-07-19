---
status: active
certified_for_ai: true
---
# Implementation Plan: Programmable Post-Download Job Filtering in qBittorrent

Questo piano consente di configurare in modo dinamico e dichiarativo in `arr-values.yaml` destinazioni personalizzate per il job `audio-normalizer` basate sulla categoria del torrent in qBittorrent.

Se una categoria non è elencata nei filtri (o è vuota), il filtro "non fa nulla" (non applica una destinazione personalizzata) ma **non blocca l'esecuzione originale**, procedendo all'innesco del Job con la destinazione di default (comportamento originario).

## Proposed Changes

### Component: servarr Helm Chart (pindaroli-arr-helm)

---

#### [MODIFY] `values.yaml`
Aggiunta del blocco di configurazione per il triggerJob sotto `qbittorrent`:
```yaml
  triggerJob:
    enabled: false
    filters: {}
```

#### [MODIFY] `Chart.yaml`
Incremento versione patch del chart (es. `1.7.3` -> `1.7.4`).

#### [MODIFY] `trigger-job-configmap.yaml`
Modifica dello script `trigger-job.sh` per:
1. Accettare `$2` come `CATEGORY`.
2. Verificare la categoria impostando `TARGET_OUTPUT` ma procedendo comunque all'innesco in caso di mancata corrispondenza:
   ```bash
   TARGET_OUTPUT=""
   
   {{- if .Values.qbittorrent.triggerJob.filters }}
   case "$CATEGORY" in
     {{- range $cat, $dest := .Values.qbittorrent.triggerJob.filters }}
     "{{ $cat }}")
       TARGET_OUTPUT="{{ $dest }}"
       echo "ℹ️ Applicato filtro categoria '$CATEGORY'. Destinazione: $TARGET_OUTPUT"
       ;;
     {{- end }}
     *)
       echo "ℹ️ Categoria '$CATEGORY' non presente nei filtri. Si procede con la destinazione di default."
       ;;
   esac
   {{- else }}
   echo "ℹ️ Nessun filtro configurato per le categorie. Si procede con la destinazione di default."
   {{- end }}
   ```
3. Passare `$TARGET_OUTPUT` come secondo parametro (`target_output`) a `jq` per la creazione del Job.

#### [MODIFY] `post-deploy-job.yaml`
Aggiunta del blocco per configurare l'autorun via API qBittorrent:
```bash
              {{- if .Values.qbittorrent.triggerJob.enabled }}
              echo "Configuring post-download trigger program..."
              curl -s -H "Cookie: $COOKIE" -X POST \
                --data-urlencode 'json={"autorun_enabled": true, "autorun_program": "/scripts/trigger-job.sh \"%F\" \"%L\""}' \
                "$QB_URL/api/v2/app/setPreferences"
              {{- else }}
              echo "Disabling post-download trigger program..."
              curl -s -H "Cookie: $COOKIE" -X POST \
                --data-urlencode 'json={"autorun_enabled": false, "autorun_program": ""}' \
                "$QB_URL/api/v2/app/setPreferences"
              {{- end }}
```

---

### Component: Homelab Configuration (k8s-lab)

---

#### [MODIFY] `arr-values.yaml`
Configurazione del filtro in `qbittorrent` con le modifiche richieste (spostando la musica classica da `autobrr-classical` e `lidarr-classical` su `classical`):
```yaml
  categories:
    - radarr
    - lidarr
    - readarr
    - autobrr-classical
    - lidarr-classical

  triggerJob:
    enabled: true
    filters:
      autobrr-classical: "classical"
      lidarr-classical: "classical"
```

## 💾 Stato di Ripristino (AI Save-State)
- **Fase Attiva**: Esecuzione modifiche del piano.
- **Ultima Azione Completata**: Salvataggio piano nel Wiki.
- **Prossimo Passo Operativo**: Implementazione modifiche sui template Helm in `pindaroli-arr-helm`.
- **Blocchi/Decisioni Pendenti**: Nessuno.

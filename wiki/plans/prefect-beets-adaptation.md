---
title: "Wiki Plan: Adattamento Routine Beets per Orchestrazione Prefect (Standalone)"
last_updated: "2026-06-07"
confidence: "Medium"
status: "Pianificato"
tags:
  - "#app"
  - "#beets"
  - "#prefect"
  - "#classica"
  - "#k8s"
provenance:
  - "wiki/plans/classical-music-strategy.md"
  - "wiki/plans/classical-ingestion-routing.md"
---

# Wiki Plan: Adattamento Routine Beets per Orchestrazione Prefect

> [!NOTE]
> **Status**: 🟡 **PIANIFICATO**
> **Obiettivo**: Ristrutturare gli attuali script Python isolati di Beets in Flussi e Task di Prefect,
> testandoli localmente (fuori dal cluster) prima di iniettarli nel worker `prefect-kubernetes`.
>
> ### 🔗 Relazioni & Tracciabilità
> - Dipende da: [[classical-music-strategy]] (pipeline attuale, ambiente Python 3.12)
> - Dipende da: [[classical-ingestion-routing]] (topologia storage e qBittorrent)
> - Fa parte di: [[dual-pipeline-gitops-integration]]
> - Workload target: `prefect-kubernetes` worker pool

---

## 🏗️ Architettura Target (Riepilogo)

Questo piano implementa il **Ciclo di Vita Stateless** definito nel Piano Architetturale Globale:

```
[qBittorrent Webhook]
        │
        ▼
[Prefect Work Queue] ── concorrenza = 1 ──► [Prefect Worker K8s]
        │
        ├── initContainer: pull_state_from_s3  ← MinIO: scarica classical_musiclibrary.db
        │
        ├── Main Container: run_beets_import   ← Beets tagger + copy to library
        │
        ├── Main Container: sync_media_servers ← Lidarr silence + Jellyfin + Navidrome rescan
        │
        └── finally: push_state_to_s3          ← MinIO: ricarica DB (anche in caso di errore)
```

**Storage per lo stato (DB Beets):**
- Il file `classical_musiclibrary.db` è archiviato su **MinIO (S3)** su TrueNAS.
- Durante l'esecuzione, viene copiato in un volume `emptyDir` K8s (iper-veloce, sul nodo).
- Il Pod muore al termine — nessuno stato locale persiste nel cluster.

---

## 📋 Fase 1: Refactoring del Codice (Task Prefect)

Gli script attuali in `import_music/import_classical/` vengono wrappati nei decoratori `@task` e `@flow` di Prefect.

### Struttura del Flusso Principale

```python
# classical_ingestion_flow.py

from prefect import flow, task

@flow(name="Classical_Ingestion_Flow")
def classical_ingestion_flow(staging_path: str):
    db_local_path = pull_state_from_s3()
    beets_result  = run_beets_import(staging_path, db_local_path)
    sync_media_servers(beets_result)
    push_state_to_s3(db_local_path)  # sempre eseguito (try...finally nel flow)
```

### Task 1: `pull_state_from_s3`

```python
@task(name="pull_state_from_s3", retries=3, retry_delay_seconds=10)
def pull_state_from_s3() -> str:
    """Scarica classical_musiclibrary.db da MinIO in /tmp/beets/ (emptyDir su K8s)."""
    import boto3
    s3 = boto3.client("s3", endpoint_url=MINIO_ENDPOINT, ...)
    local_path = "/tmp/beets/classical_musiclibrary.db"
    s3.download_file(BUCKET, "classical_musiclibrary.db", local_path)
    return local_path
```

**Dipendenze**: `boto3`, credenziali MinIO da Secret K8s (`minio-creds`).

### Task 2: `run_beets_import`

```python
@task(name="run_beets_import", timeout_seconds=1800)
def run_beets_import(staging_path: str, db_path: str) -> dict:
    """Esegue beets import con il DB scaricato in emptyDir."""
    import subprocess
    result = subprocess.run([
        "beet", "--config", "/app/beets_classical_config.yaml",
        "import", "-q", staging_path
    ], capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"Beets import fallito: {result.stderr}")
    return {"status": "ok", "stdout": result.stdout}
```

> [!IMPORTANT]
> Il `beets_classical_config.yaml` deve essere montato nel Pod come ConfigMap.
> Il parametro `directory` e `library` nel config devono puntare ai path dell'`emptyDir`.

### Task 3: `sync_media_servers`

```python
@task(name="sync_media_servers", retries=2)
def sync_media_servers(beets_result: dict):
    """
    1. Silenzia l'album su lidarr-classic (rimuove il monitoring).
    2. Forza il rescan della libreria su jellyfin-classic.
    3. Forza il rescan della libreria su Navidrome (API Subsonic-compatibile).
    """
    import httpx
    # Lidarr: PUT /api/v1/album/{id} con monitored=false
    httpx.put(f"{LIDARR_URL}/api/v1/album/{album_id}", ...)
    # Jellyfin: POST /Library/Refresh
    httpx.post(f"{JELLYFIN_URL}/Library/Refresh", headers={"X-Emby-Token": JELLYFIN_TOKEN})
    # Navidrome: GET /rest/startScan (Subsonic API)
    httpx.get(f"{NAVIDROME_URL}/rest/startScan", params={"u": USER, "p": PASS, ...})
```

**API Navidrome**: usa l'API Subsonic-compatibile (`/rest/startScan.view`).
**Dipendenze**: URL e token dei servizi da Secret K8s o Prefect Blocks.

### Task 4: `push_state_to_s3`

```python
@task(name="push_state_to_s3", retries=3, retry_delay_seconds=15)
def push_state_to_s3(db_path: str):
    """Ricarica il DB aggiornato su MinIO. Garantito da try...finally nel flow."""
    import boto3
    s3 = boto3.client("s3", endpoint_url=MINIO_ENDPOINT, ...)
    s3.upload_file(db_path, BUCKET, "classical_musiclibrary.db")
```

> [!CAUTION]
> Questo task **deve sempre girare**, anche in caso di errore dei task precedenti.
> Implementare con `try...finally` nel `@flow`:
> ```python
> try:
>     beets_result = run_beets_import(...)
>     sync_media_servers(beets_result)
> finally:
>     push_state_to_s3(db_local_path)
> ```

---

## 🧪 Fase 2: Test Locale Standalone (Mocking)

Prima di toccare Kubernetes, il codice viene testato sul **Mac Studio** con Prefect in modalità locale.

### Setup Ambiente di Test

```bash
# Crea bucket di test su MinIO
mc alias set local http://10.10.10.50:9000 ACCESS_KEY SECRET_KEY
mc mb local/beets-state-test

# Copia il DB attuale nel bucket di test
mc cp import_music/import_classical/classical_musiclibrary.db local/beets-state-test/

# Installa dipendenze nel venv 3.12
source import_music/import_classical/venv/bin/activate
pip install prefect boto3 httpx
```

### Esecuzione Test Locale

```bash
# Lancia il flow localmente con Prefect in modalità "ephemeral" (no server richiesto)
python classical_ingestion_flow.py \
  --staging-path /Volumes/classical/staging/TestAlbum \
  --minio-endpoint http://10.10.10.50:9000 \
  --bucket beets-state-test
```

### Checklist di Validazione

- [ ] Il DB viene scaricato da MinIO in `/tmp/beets/`
- [ ] Beets sposta fisicamente i file in `/Volumes/classical/library/`
- [ ] L'upload finale del DB su MinIO avviene (verificare con `mc ls local/beets-state-test/`)
- [ ] In caso di errore simulato nel Task 2, il Task 4 (push) viene comunque eseguito

---

## 🐳 Fase 3: Dockerizzazione

Una volta validato localmente, creare un `Dockerfile` dedicato per il worker Prefect.

```dockerfile
# Dockerfile.beets-worker
FROM python:3.12-slim

# Installa chromaprint per fingerprinting AcoustID
RUN apt-get update && apt-get install -y libchromaprint-tools ffmpeg && rm -rf /var/lib/apt/lists/*

# Installa dipendenze Python
COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

# Copia il codice e la config beets
COPY classical_ingestion_flow.py /app/
COPY beets_classical_config.yaml /app/

WORKDIR /app
```

**`requirements.txt`**:
```
beets==2.11.0
musicbrainzngs
prefect
boto3
httpx
```

> [!NOTE]
> Base Python 3.12 (stesso ambiente che ha risolto i `KeyError` di MusicBrainz su `musicbrainzngs`).
> **NON usare Python 3.14** — causa eccezioni bloccanti nelle API MusicBrainz.

---

## ☸️ Fase 4: Configurazione K8s Work Pool

Una volta validato il Docker in locale, configurare il **Kubernetes Work Pool** in Prefect.

### Base Job Template (emptyDir + initContainer)

```yaml
# Aggiunta al base_job_template del Work Pool Prefect
variables:
  minio_secret_name:
    type: string
    default: "minio-creds"
  beets_config_configmap:
    type: string
    default: "beets-classical-config"

job_configuration:
  job_manifest:
    spec:
      template:
        spec:
          initContainers:
            - name: pull-beets-db
              image: amazon/aws-cli
              command: ["aws", "s3", "cp", "s3://beets-state/classical_musiclibrary.db", "/tmp/beets/classical_musiclibrary.db"]
              env:
                - name: AWS_ACCESS_KEY_ID
                  valueFrom:
                    secretKeyRef:
                      name: "{{ minio_secret_name }}"
                      key: ACCESS_KEY_ID
              volumeMounts:
                - name: beets-state
                  mountPath: /tmp/beets
          containers:
            - name: prefect-worker
              volumeMounts:
                - name: beets-state
                  mountPath: /tmp/beets
                - name: beets-config
                  mountPath: /app/beets_classical_config.yaml
                  subPath: beets_classical_config.yaml
          volumes:
            - name: beets-state
              emptyDir: {}
            - name: beets-config
              configMap:
                name: "{{ beets_config_configmap }}"
```

> [!CAUTION]
> **Regola Fondamentale Prefect-Kubernetes**: Tutte le variabili personalizzate definite
> nella sezione `variables` del template **DEVONO** essere richiamate esplicitamente nella sezione
> `job_configuration` usando la sintassi `{{ variable_name }}`.
> Se omesso, le variabili non vengono passate al worker e il Pod fallisce per mancanza di volumi/secret.

### Concorrenza della Work Queue

```python
# Impostare nel Prefect UI o via CLI
prefect work-queue create classical-ingestion --concurrency-limit 1
```

**Motivo**: concorrenza = 1 evita race conditions sul DB SQLite condiviso su MinIO e rispetta il rate limiting delle API MusicBrainz.

---

## 📊 Dipendenze & Relazioni

| Componente | Tipo | Note |
|---|---|---|
| `classical_musiclibrary.db` | Storage (MinIO) | Stato persistente della pipeline |
| `beets_classical_config.yaml` | ConfigMap K8s | Mountato nel Pod |
| `minio-creds` | Secret K8s | Credenziali S3 per pull/push DB |
| `jellyfin-classic` | Workload K8s | Rescan via API REST |
| `navidrome` | Workload K8s | Rescan via Subsonic API `/rest/startScan` |
| `lidarr-classic` | Workload K8s | Silenzio album via API REST |
| `prefect-kubernetes` | Worker Pool | Esecuzione effimera dei Job |

---

## 💾 Stato di Ripristino (AI Save-State)

- **Fase Attiva**: Fase 1 — Refactoring del Codice (Task Prefect)
- **Ultima Azione Completata**: Piano documentato e struttura task definita
- **Prossimo Passo Operativo**: Scrivere il codice Python dei 4 task (`pull_state_from_s3`, `run_beets_import`, `sync_media_servers`, `push_state_to_s3`) in un file `classical_ingestion_flow.py`
- **Blocchi/Decisioni Pendenti**:
  - Percorso del file di flow nel repo (sotto `import_music/import_classical/` o directory Prefect dedicata?)
  - Conferma endpoint e credenziali Navidrome per l'API Subsonic

---

*Piano redatto da Antigravity AI Engineering — 2026-06-07*
*Ref: [[classical-music-strategy]], [[classical-ingestion-routing]], [[dual-pipeline-gitops-integration]]*

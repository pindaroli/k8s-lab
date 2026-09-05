---
title: "Piano: Integrazione Sidecar qBittorrent Exporter & Monitoring"
type: plan
status: active
certified_for_ai: true
created_at: 2026-09-05
tags:
  - "#plan"
  - "#servarr"
  - "#qbittorrent"
  - "#monitoring"
  - "#victoriametrics"
  - "#helm"
---

# Piano: Integrazione Sidecar qBittorrent Exporter & Monitoring

**Target**: Cluster GEMINI (`pindaroli.org`) · Namespace `arr` · **Data**: 2026-09-05  
**Autore**: Antigravity AI Engineering

> [!IMPORTANT]
> Questo piano formalizza l'integrazione, la configurazione e il collaudo del container sidecar `qbittorrent-exporter` all'interno del pod `servarr-qbittorrent`, garantendo il corretto scraping delle metriche verso VictoriaMetrics (`VMServiceScrape`).
> Il piano affronta e risolve in via prioritaria il bug di autenticazione introdotto con **qBittorrent 5.2.x** (ritorno di `HTTP 204 No Content` su `/api/v2/auth/login`).

---

## 1. Analisi dello Stato Attuale & Root Cause

Nel deployment attuale di qBittorrent su Kubernetes:
- Nel file `servarr/arr-values.yaml` (righe 116-142) è configurato un container secondario sotto `extraContainers`:
  ```yaml
  extraContainers:
    - name: qbittorrent-exporter
      image: ghcr.io/martabal/qbittorrent-exporter:v1.12.1
      env:
        - name: QBITTORRENT_BASE_URL
          value: "http://127.0.0.1:8080"
        - name: QBITTORRENT_COOKIE_NAME
          value: "QBT_SID_8080"
  ```
- **Sintomo di Errore**: I log del container riportano continuamente:
  ```
  [ERROR] authentication failed, status code: 204
  ```
- **Causa Tecnica**: Come tracciato nell'incidente storico [[2026-09-02-qbittorrent-5.2-auth-cookie-breaking-change]], qBittorrent versione 5.2.x non risponde più con `HTTP 200 OK` ("Ok.") al login, ma restituisce `HTTP 204 No Content` impostando il cookie di sessione `QBT_SID_<PORT>` (nello specifico `QBT_SID_8080`). L'immagine upstream `martabal/qbittorrent-exporter:v1.12.1` tratta qualsiasi status code diverso da 200 come fallimento dell'autenticazione.

---

## 2. Decisioni Architetturali

| Componente | Scelta | Motivazione |
| :--- | :--- | :--- |
| **Topologia Pod** | Sidecar Container in `servarr-qbittorrent` | Stesso Network Namespace del demone torrent (`http://127.0.0.1:8080`), latenza zero ed esclusione dal traffico instradato esternamente. |
| **Immagine Exporter** | Fork patchato o container compatibile con HTTP 204 | Supporto ai codici 2xx/204 e gestione del cookie `QBT_SID_8080`. |
| **Service & Porte** | Porta 8090 TCP (`name: metrics`) | Esposta sul Service `servarr-qbittorrent-web` già predisposto nel chart `pindaroli-arr-helm`. |
| **Metrics Collector** | Custom Resource `VMServiceScrape` | Conforme alla strategia di osservabilità documentata in [[Monitoring]]. |
| **Credenziali** | Secret SOPS `servarr-api-keys` | Utilizzo delle chiavi `qbittorrent-user` e `qbittorrent-pass`. |

---

## 3. Fasi Operative

### Fase 1: Analisi e Selezione Immagine Exporter
- Testare immagini/fork alternativi o container personalizzato con gestione di `HTTP 204` e `QBT_SID_8080`.
- Validare l'autenticazione tramite curl e verifica del token.

### Fase 2: Standardizzazione nel Chart Helm (`pindaroli-arr-helm`)
- Verificare i template in `charts/servarr/templates/qbittorrent/` (`service.yaml`, `deployment.yaml`, `monitoring.yaml`).
- Assicurare che il blocco `monitoring` generi il corretto `VMServiceScrape` e che la porta `metrics` sia aperta.
- Incrementare la versione patch/minor in `Chart.yaml`.

### Fase 3: Configurazione Cluster & GitOps (`k8s-lab`)
- Aggiornare `servarr/arr-values.yaml` con l'immagine selezionata e le risorse (CPU: 10m requests, 32Mi RAM).
- Validare la conformità del secret `servarr-api-keys`.

### Fase 4: Deploy & Test-Driven Verification
- Eseguire il deploy:
  ```bash
  helm upgrade --install servarr charts/servarr -f ../k8s-lab/servarr/arr-values.yaml -n arr
  ```
- Verificare lo stato del container:
  ```bash
  kubectl logs -n arr -l app.kubernetes.io/name=qbittorrent -c qbittorrent-exporter --tail=50
  ```
- Verificare lo scraping dell'endpoint `/metrics` sulla porta 8090.
- Verificare la comparsa dei target attivi in VictoriaMetrics (`vmagent`) e delle metriche torrent su Grafana.

---

## 💾 Stato di Ripristino (AI Save-State)
- **Fase Attiva**: Fase 1 / Analisi e Selezione Immagine Exporter
- **Ultima Azione Completata**: Redazione del piano architetturale nel Wiki e aggiornamento di `todo.md`
- **Prossimo Passo Operativo**: Identificazione/costruzione dell'immagine Docker con fix 204 per qbittorrent-exporter
- **Blocchi/Decisioni Pendenti**: Scelta tra fork community o container custom nel monorepo

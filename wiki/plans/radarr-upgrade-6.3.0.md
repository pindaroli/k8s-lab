---
title: "Piano: Upgrade Radarr a v6.3.0.10514"
type: plan
status: archived
certified_for_ai: false
created_at: 2026-07-14
completed_at: 2026-09-10
tags:
  - "#plan"
  - "#talos"
  - "#database"
---

# Piano: Upgrade Radarr a v6.3.0.10514

**Target**: Cluster GEMINI (`pindaroli.org`) · **Data**: 2026-07-14
**Autore**: Antigravity AI Engineering

> [!IMPORTANT]
> **Stato Operativo: COMPLETATO CON SUCCESSO ✅**
> L'aggiornamento dell'immagine di Radarr all'interno del namespace `arr` alla versione stabile `v6.3.0.10514` è stato completato e verificato in produzione. Il pod `servarr-radarr-76bf8fbfc4-q968p` è attivo e Running (2/2 Ready) su `ghcr.io/hotio/radarr:release-6.3.0.10514`.

---

## Dettagli dell'Aggiornamento

| Componente | Versione Precedente | Nuova Versione Attiva | Registro Immagine |
| :--- | :--- | :--- | :--- |
| **Radarr** | `release-6.2.1.10461` | `release-6.3.0.10514` | `ghcr.io/hotio/radarr` |

---

## Ordine di Esecuzione

- [x] **Fase 1: Backup Preventivo**
  - Eseguito backup manuale del namespace `arr` tramite Velero.
- [x] **Fase 2: Modifica Configurazione**
  - Aggiornato il tag dell'immagine in `servarr/arr-values.yaml`.
- [x] **Fase 3: Deploy & Verifiche**
  - Eseguito l'aggiornamento della release Helm.
  - Verificato rollout: Pod `servarr-radarr-76bf8fbfc4-q968p` in stato Running (2/2 Ready) con tag `release-6.3.0.10514`.
  - Verificate migrazioni schema database PostgreSQL (`postgres-main-rw`).

---

## Verifica Eseguita

```bash
$ kubectl get pod -n arr -l app.kubernetes.io/name=radarr -o jsonpath='{.items[0].spec.containers[0].image}'
ghcr.io/hotio/radarr:release-6.3.0.10514

$ kubectl get pod -n arr -l app.kubernetes.io/name=radarr
NAME                              READY   STATUS    RESTARTS   AGE
servarr-radarr-76bf8fbfc4-q968p   2/2     Running   0          10d
```

---

## 💾 Stato di Ripristino (AI Save-State)
- **Fase Attiva**: Completato (Archiviato)
- **Ultima Azione Completata**: Validazione versione in produzione e archiviazione piano.
- **Prossimo Passo Operativo**: Nessuno.
- **Blocchi/Decisioni Pendenti**: Nessuno.

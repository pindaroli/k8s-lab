---
title: "Piano: Upgrade Radarr a v6.3.0.10514"
type: plan
status: active
certified_for_ai: true
created_at: 2026-07-14
tags:
  - "#plan"
  - "#talos"
  - "#database"
---

# Piano: Upgrade Radarr a v6.3.0.10514

**Target**: Cluster GEMINI (`pindaroli.org`) · **Data**: 2026-07-14
**Autore**: Antigravity AI Engineering

> [!IMPORTANT]
> Questo piano definisce l'aggiornamento dell'immagine di Radarr all'interno del namespace `arr` alla versione stabile `v6.3.0.10514`.
> Radarr utilizza PostgreSQL (`postgres-main-rw`), pertanto le migrazioni dello schema del database verranno applicate automaticamente all'avvio del nuovo container.

---

## Dettagli dell'Aggiornamento

| Componente | Versione Attuale | Nuova Versione | Registro Immagine |
| :--- | :--- | :--- | :--- |
| **Radarr** | `release-6.2.1.10461` | `release-6.3.0.10514` | `ghcr.io/hotio/radarr` |

---

## Ordine di Esecuzione

- [ ] **Fase 1: Backup Preventivo**
  - Eseguire un backup manuale del namespace `arr` tramite Velero.
- [ ] **Fase 2: Modifica Configurazione**
  - Aggiornare il tag dell'immagine in `servarr/arr-values.yaml`.
- [ ] **Fase 3: Deploy & Verifiche**
  - Eseguire l'aggiornamento della release Helm.
  - Monitorare il rollout dei Pod e i log di avvio per verificarlo.

---

## Verifica

```bash
# Controlla lo stato del Pod
kubectl get pods -n arr -l app.kubernetes.io/name=radarr

# Controlla i log di avvio del container
kubectl logs -n arr -l app.kubernetes.io/name=radarr -c radarr --tail=100
```

---

## 💾 Stato di Ripristino (AI Save-State)
- **Fase Attiva**: Fase 1: Backup Preventivo
- **Ultima Azione Completata**: Inizializzazione della documentazione del piano.
- **Prossimo Passo Operativo**: Modificare la configurazione dell'immagine in `servarr/arr-values.yaml`.
- **Blocchi/Decisioni Pendenti**: Nessuno.

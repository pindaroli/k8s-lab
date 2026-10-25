---
title: "Piano: Riorganizzazione Unificata Homepage nelle 4 Modalità (external, lab_mode_full, lab_mode_eco, lab_mode_off) via Kustomize"
type: plan
status: completed
certified_for_ai: true
created_at: 2026-10-25
completed_at: 2026-10-25
tags:
  - "#homepage"
  - "#dashboard"
  - "#kustomize"
  - "#kubernetes"
  - "#truenas"
  - "#orbstack"
  - "#gitops"
---

# Piano Operativo: Riorganizzazione Unificata Homepage nelle 4 Modalità (`external`, `lab_mode_full`, `lab_mode_eco`, `lab_mode_off`)

> **Percorso Canonico Wiki**: `wiki/plans/homepage-four-modes-reorganization.md` (alias: `[[homepage-four-modes-reorganization]]`)  
> **Comando di Attivazione per l'Agente Locale**: `/resume [[homepage-four-modes-reorganization]]`  
> **Governance Collegata**: [[Homepage]], [[homepage-lab-mode-status-widget]], [[home-internal-dns-failover-and-https-ingress]], [[orbstack-failover-truenas-services]], [[SCHEMA]].

---

## 1. Contesto e Motivazione

Fino ad oggi le definizioni delle **4 dashboard Homepage** dell'homelab erano distribuite in 3 posizioni distinte e con 2 formati incompatibili tra loro:
1. **Esterna (`home.pindaroli.org`)**: incorporata come stringhe YAML multi-linea dentro la `ConfigMap` di `homepage/homepage.yaml` (insieme a RBAC, Deployment, Service e IngressRoute).
2. **Interna `lab_mode_full` (`home-internal.pindaroli.org` su K8s)**: incorporata come stringhe YAML multi-linea dentro la `ConfigMap` di `homepage/homepage-local.yaml`.
3. **Interna `lab_mode_eco` (`home-internal.pindaroli.org` su TrueNAS Docker)**: salvata esclusivamente sul filesystem remoto di TrueNAS (`/mnt/stripe/truenas-docker/homepage/`) e **non versionata su Git**.
4. **Interna `lab_mode_off` (`home-internal.pindaroli.org` su Mac Studio OrbStack)**: salvata fuori dalla directory `homepage/`, in `docker/orbstack/homepage-config/`.

### Obiettivo del Piano
Riorganizzare l'intera configurazione sotto l'unica directory canonica `homepage/`, suddivisa nelle **4 sottocartelle omogenee** con file YAML nativi puri (`services.yaml`, `widgets.yaml`, `settings.yaml`, `bookmarks.yaml`, `docker.yaml`, `kubernetes.yaml`, `proxmox.yaml`, `custom.css`, `custom.js`), separando nettamente i **contenuti delle pagine** dall'**infrastruttura Kubernetes** gestita tramite **Kustomize (`kubectl apply -k homepage/k8s`)**.

---

## 2. Architettura Target della Directory `homepage/`

```text
homepage/
├── external/                 # 1. Funzionamento esterno (home.pindaroli.org - K8s con OAuth2)
│   ├── bookmarks.yaml
│   ├── custom.css
│   ├── custom.js
│   ├── docker.yaml
│   ├── kubernetes.yaml
│   ├── services.yaml
│   ├── settings.yaml
│   └── widgets.yaml
├── lab_mode_full/            # 2. Versione lab_mode_full interna (home-internal.pindaroli.org - K8s)
│   ├── bookmarks.yaml
│   ├── custom.css
│   ├── custom.js
│   ├── docker.yaml
│   ├── kubernetes.yaml
│   ├── services.yaml
│   ├── settings.yaml
│   └── widgets.yaml
├── lab_mode_eco/             # 3. Versione lab_mode_eco interna (TrueNAS 10.10.20.50:3000)
│   ├── bookmarks.yaml
│   ├── custom.css
│   ├── custom.js
│   ├── docker.yaml
│   ├── kubernetes.yaml
│   ├── proxmox.yaml
│   ├── services.yaml
│   ├── settings.yaml
│   └── widgets.yaml
├── lab_mode_off/             # 4. Versione lab_mode_off interna (Mac OrbStack 10.10.20.100:3000)
│   ├── bookmarks.yaml
│   ├── custom.css
│   ├── custom.js
│   ├── docker.yaml
│   ├── kubernetes.yaml
│   ├── proxmox.yaml
│   ├── services.yaml
│   ├── settings.yaml
│   └── widgets.yaml
└── k8s/                      # Infrastruttura Kubernetes pura (Kustomize)
    ├── kustomization.yaml    # configMapGenerator da ../external e ../lab_mode_full
    ├── rbac.yaml             # ServiceAccount, ClusterRole, ClusterRoleBinding (homepage & homepage-local)
    ├── external-deploy.yaml  # Deployment, Service, IngressRoute per home.pindaroli.org
    ├── internal-deploy.yaml  # Deployment, Service, IngressRoute per home-internal.pindaroli.org
    └── steam-proxy.yaml      # Service/EndpointSlice proxmox-pve3, ServersTransport skip-verify, Middleware Steam
```

---

## 3. Confronto Architetturale: `kubectl apply -k` (Kustomize) vs Helm Chart

| Criterio | `kubectl apply -k` (Kustomize — **Scelto**) | Helm Project Chart (`helm-charts/homepage/`) |
| :--- | :--- | :--- |
| **Semplicità e Leggibilità** | **Massima**: i file in `homepage/external/` e `homepage/lab_mode_full/` restano YAML puri senza sintassi di templating (`{{ ... }}`). | Richiede `Chart.yaml`, `values.yaml` e template Go in `helm-charts/homepage/templates/`. |
| **Riavvio Automatico Pod al cambio config** | **Nativo**: `configMapGenerator` calcola l'hash SHA dei file (es. `homepage-local-9f8b2c4d`) e aggiorna automaticamente il riferimento nel `Deployment`, innescando il RollingUpdate senza bisogno di `kubectl rollout restart`. | Richiede l'annotazione manuale `checksum/config: {{ include ... | sha256sum }}` nel template del Deployment. |
| **Struttura Unificata in `homepage/`** | Tutte e 4 le modalità risiedono fisicamente sotto `homepage/`. | Sposterebbe la logica K8s sotto `helm-charts/homepage/` separandola dalle cartelle Docker (`lab_mode_eco`, `lab_mode_off`). |
| **Rollback & Release History** | Gestito direttamente tramite Git (`git revert` + `kubectl apply -k`). | Gestito nel cluster tramite revisioni Helm (`helm rollback homepage`). |

> [!NOTE]
> **Dettaglio tecnico Kustomize (`files` relative path)**: poiché per sicurezza Kustomize non consente a `configMapGenerator` di leggere file fuori dalla propria root (`../`) senza il flag `--load-restrictor=LoadRestrictionsNone`, posizioneremo `kustomization.yaml` direttamente nella root `homepage/kustomization.yaml` (che punta a `k8s/*.yaml` per le risorse e a `external/*` e `lab_mode_full/*` per i `configMapGenerator`). In questo modo il comando standard **`kubectl apply -k homepage/`** funziona nativamente senza flag extra!

---

## 4. Mappa dei File Coinvolti

| Azione | Percorso File | Descrizione |
| :--- | :--- | :--- |
| **CREAZIONE** | `homepage/external/*.{yaml,css,js}` | Estrazione 1:1 dei file di configurazione dalla ConfigMap di `homepage/homepage.yaml`. |
| **CREAZIONE** | `homepage/lab_mode_full/*.{yaml,css,js}` | Estrazione 1:1 dei file di configurazione dalla ConfigMap di `homepage/homepage-local.yaml`. |
| **CREAZIONE** | `homepage/lab_mode_eco/*.{yaml,css,js}` | Versionamento su Git dei file di configurazione di TrueNAS (`/mnt/stripe/truenas-docker/homepage/`). |
| **SPOSTAMENTO** | `docker/orbstack/homepage-config/*` $\rightarrow$ `homepage/lab_mode_off/` | Spostamento 1:1 dei file di configurazione di OrbStack dentro `homepage/lab_mode_off/`. |
| **CREAZIONE** | `homepage/k8s/{rbac,external-deploy,internal-deploy,steam-proxy}.yaml` | Separazione pulita dei manifesti infrastrutturali Kubernetes. |
| **CREAZIONE** | `homepage/kustomization.yaml` | Generatore automatico delle ConfigMap `homepage` e `homepage-local` con hash suffix per auto-rollout. |
| **RIMOZIONE** | `homepage/homepage.yaml`, `homepage/homepage-local.yaml`, `homepage/skip-verify.yaml` | Rimozione dei vecchi monoliti dopo validazione completa di `kubectl kustomize homepage/`. |
| **MODIFICA** | `docker/orbstack/docker-compose.yaml` | Aggiornamento volume mount di `homepage-mac` verso `${ROOT_DIR}/homepage/lab_mode_off:/app/config`. |
| **MODIFICA** | `scripts/infrastructure/orbstack_failover.sh` | Aggiunta sync automatico (`rsync`) di `homepage/lab_mode_eco/` verso TrueNAS `/mnt/stripe/truenas-docker/homepage/` durante il failback/avvio di TrueNAS. |
| **MODIFICA** | `.agents/skills/homepage-manager/SKILL.md` e `wiki/entities/Homepage.md` | Aggiornamento documentazione e skill operativa ai nuovi 4 percorsi e a `kubectl apply -k homepage/`. |

---

## 5. Fasi Operative di Implementazione (Protocollo Test-Driven §12)

### FASE 1: Estrazione delle 4 Cartelle di Configurazione (`external`, `lab_mode_full`, `lab_mode_eco`, `lab_mode_off`)
1. Estrarre programmaticamente da `homepage/homepage.yaml` (chiave `data:` della ConfigMap `homepage`) gli 8 file dentro `homepage/external/`.
2. Estrarre programmaticamente da `homepage/homepage-local.yaml` (chiave `data:` della ConfigMap `homepage-local`) gli 8 file dentro `homepage/lab_mode_full/`.
3. Popolare `homepage/lab_mode_eco/` con i file correnti dell'istanza TrueNAS (`/mnt/stripe/truenas-docker/homepage/`, inclusi Garage, Scrutiny, Hermes `/api/health` e widget `🟡 Stato: ECO`).
4. Spostare i file di configurazione da `docker/orbstack/homepage-config/` a `homepage/lab_mode_off/` (escludendo la cartella runtime `logs/`).
5. **Verifica Test-Driven (Fase 1)**:
   - Controllo presenza ed equivalenza byte-per-byte dei file estratti rispetto alle ConfigMap originali.
   - Validazione sintattica YAML (`yq` / `python3 -c 'import yaml'`) su tutti i file `.yaml` delle 4 cartelle (`external`, `lab_mode_full`, `lab_mode_eco`, `lab_mode_off`).

---

### FASE 2: Creazione Struttura Kubernetes Kustomize (`homepage/kustomization.yaml` e `homepage/k8s/`)
1. Creare in `homepage/k8s/`:
   - `rbac.yaml`: `ServiceAccount`, `Secret` token, `ClusterRole` e `ClusterRoleBinding` per `homepage` e `homepage-local`.
   - `steam-proxy.yaml`: `ServersTransport` (`skip-verify`), `Service` ed `EndpointSlice` (`proxmox-pve3`), `Middleware` (`steam-api-rewrite`, `steam-api-headers`, `homepage-local-cache-control`).
   - `external-deploy.yaml`: `Service`, `Deployment` e `IngressRoute` per `homepage` (`home.pindaroli.org`).
   - `internal-deploy.yaml`: `Service`, `Deployment` e `IngressRoute` per `homepage-local` (`home-internal.pindaroli.org`).
2. Creare `homepage/kustomization.yaml` con `configMapGenerator` per generare `homepage` (da `external/*`) e `homepage-local` (da `lab_mode_full/*`).
3. Rimuovere i vecchi file monolitici `homepage/homepage.yaml`, `homepage/homepage-local.yaml`, `homepage/skip-verify.yaml` e la vecchia directory `docker/orbstack/homepage-config/`.
4. **Verifica Test-Driven (Fase 2)**:
   - Eseguire `kubectl kustomize homepage/` e verificare che l'output YAML renderizzato sia completo, valido e contenga tutte le risorse K8s attese e le 2 ConfigMap generate con hash suffix.

---

### FASE 3: Aggiornamento Stack OrbStack (`lab_mode_off`) e Script di Sync TrueNAS (`lab_mode_eco`)
1. Aggiornare in `docker/orbstack/docker-compose.yaml` il bind mount del servizio `homepage`:
   - Da: `- ${ROOT_DIR:-/Users/olindo/prj/k8s-lab}/docker/orbstack/homepage-config:/app/config`
   - A: `- ${ROOT_DIR:-/Users/olindo/prj/k8s-lab}/homepage/lab_mode_off:/app/config`
2. Aggiornare `scripts/infrastructure/orbstack_failover.sh` (nella funzione `deactivate_orbstack_failover_to_truenas`) per sincronizzare automaticamente via `rsync` i file da `homepage/lab_mode_eco/` a `/mnt/stripe/truenas-docker/homepage/` su TrueNAS quando TrueNAS è online.
3. **Verifica Test-Driven (Fase 3)**:
   - Ricreare il container `homepage-mac` su OrbStack (attualmente attivo in `lab_mode_off`):
     `docker compose --env-file ~/.homelab-failover/.env -f docker/orbstack/docker-compose.yaml up -d --force-recreate homepage`
   - Verificare che `homepage-mac` sia `Up` e risponda con `HTTP 200 OK` su `http://127.0.0.1:3000` e `https://home-internal.pindaroli.org/`, servendo correttamente i file da `homepage/lab_mode_off/`.
   - Verificare la sintassi bash di `scripts/infrastructure/orbstack_failover.sh` con `bash -n`.

---

### FASE 4: Allineamento Skill `homepage-manager`, Entità Wiki e Contesto Globale
1. Aggiornare `.agents/skills/homepage-manager/SKILL.md` sostituendo i riferimenti ai vecchi file monolitici con le 4 cartelle (`homepage/external/`, `homepage/lab_mode_full/`, `homepage/lab_mode_eco/`, `homepage/lab_mode_off/`) e aggiornando il comando di rollout K8s a `kubectl apply -k homepage/`.
2. Aggiornare `wiki/entities/Homepage.md`, `GEMINI.md` e `todo.md`.
3. **Verifica Test-Driven (Fase 4)**:
   - Eseguire `python3 scripts/network/validate_network.py && python3 scripts/wiki/build_wiki_context.py` verificando `exit code 0`.

---

## 💾 Stato di Ripristino (AI Save-State)
- **Fase Attiva**: COMPLETATO ✅ (Fasi 1-4 eseguite e validate con esito positivo al 100%)
- **Ultima Azione Completata**: Estrazione delle 4 cartelle `homepage/{external,lab_mode_full,lab_mode_eco,lab_mode_off}`, separazione manifesti K8s in `homepage/k8s/` + `homepage/kustomization.yaml` (48 risorse verificate con `kubectl kustomize homepage/`), bind-mount aggiornato e testato live su `homepage-mac` (`HTTP 200 OK` su `https://home-internal.pindaroli.org/`), allineamento skill `homepage-manager` e rigenerazione `wiki_context.md`.
- **Prossimo Passo Operativo**: Nessuno. Piano concluso.
- **Blocchi/Decisioni Pendenti**: Nessuno.

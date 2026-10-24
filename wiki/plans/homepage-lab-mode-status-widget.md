---
title: "Piano: Widget di Stato Homelab (FULL/ECO/OFF) su Tutte le Istanze Homepage"
type: plan
status: completed
certified_for_ai: true
created_at: 2026-10-24
completed_at: 2026-10-24
tags:
  - "#homepage"
  - "#dashboard"
  - "#widget"
  - "#homelab-status"
  - "#kubernetes"
  - "#truenas"
  - "#orbstack"
---

# Piano: Widget di Stato Homelab (FULL/ECO/OFF) su Tutte le Istanze Homepage

Il presente piano definisce l'integrazione dichiarativa e nativa di un **Information Widget** (`greeting`) nella barra superiore (`widgets.yaml`) di tutte le istanze Homepage del laboratorio, per mostrare in modo immediato, trasparente e privo di latenza o dipendenze di rete la modalità operativa attiva dell'homelab:
- **`FULL`**: Compute Kubernetes (Talos + Proxmox VE) e Storage TrueNAS Bare Metal attivi.
- **`ECO`**: Solo Storage TrueNAS Bare Metal attivo (K8s cluster e hypervisor PVE spenti per risparmio energetico).
- **`OFF`**: Rack dark (K8s, PVE e TrueNAS spenti) con failover locale su Mac Studio (OrbStack).

---

## 🎯 Obiettivi e Scelte Architetturali

1. **Info Widget Nativo (`widgets.yaml`)**:
   - Inserimento del widget informativo nativo `greeting` nella sezione superiore (`widgets.yaml`) di ciascuna dashboard Homepage.
   - Posizionamento in testa ai widget di sistema (sopra o accanto a `kubernetes`, `resources` e `search`), garantendo visibilità immediata sia su desktop che su mobile.
2. **Architettura Dichiarativa per Istanza (Zero Overhead & Zero Latenza)**:
   - Poiché le tre istanze di Homepage sono fisicamente e logicamente vincolate alla modalità di esecuzione:
     - **Kubernetes (`homepage.yaml` e `homepage-local.yaml`)**: è attivo esclusivamente in `FULL LAB` $\rightarrow$ `🟢 Stato: FULL (Compute K8s & Storage TrueNAS Online)`.
     - **TrueNAS Bare Metal (`/mnt/stripe/truenas-docker/homepage/widgets.yaml`)**: è l'endpoint attivo su `home-internal.pindaroli.org` in `ECO LAB` $\rightarrow$ `🟡 Stato: ECO (Storage TrueNAS Online — K8s Dark)`.
     - **Mac Studio OrbStack (`docker/orbstack/homepage-config/widgets.yaml`)**: è l'endpoint attivo su `home-internal.pindaroli.org` in `OFF / RACK DARK` $\rightarrow$ `⚫ Stato: OFF (Rack Dark — Mac Studio Failover)`.
   - Nessuna chiamata API esterna bloccante, nessun rischio di timeout HTTP o disallineamento durante le fasi di transizione energetica.
3. **Piena Conformità alla Governance Homepage (`homepage-manager` Skill)**:
   - Allineamento rigorosamente simmetrico tra `homepage.yaml` (accesso esterno) e `homepage-local.yaml` (accesso interno).
   - Validazione preventiva dei manifesti YAML.
   - Rollout atomico su TrueNAS e predisposizione per Kubernetes.

---

## 🗺️ Mappa dei File Coinvolti

| File | Destinazione / Istanza | Modifica Prevista |
| :--- | :--- | :--- |
| `homepage/homepage.yaml` | K8s Esterno (`home.pindaroli.org`) | Aggiunta `greeting` in `widgets.yaml` (`🟢 FULL`) |
| `homepage/homepage-local.yaml` | K8s Interno (`home-internal.pindaroli.org`) | Aggiunta `greeting` in `widgets.yaml` (`🟢 FULL`) |
| `/mnt/stripe/truenas-docker/homepage/widgets.yaml` | TrueNAS Bare Metal (`10.10.20.50:3000`) | Aggiunta `greeting` in `widgets.yaml` (`🟡 ECO`) |
| `docker/orbstack/homepage-config/widgets.yaml` | Mac Studio OrbStack (`10.10.20.100:3000`) | Aggiunta `greeting` in `widgets.yaml` (`⚫ OFF`) |

---

## 📋 Fasi Operative di Implementazione (Protocollo Test-Driven §12)

### FASE 1: Aggiornamento Dashboard TrueNAS Bare Metal (Modalità ECO - Attualmente Live) [COMPLETATA ✅]
1. [x] Eseguire backup preventivo di `/mnt/stripe/truenas-docker/homepage/widgets.yaml` su TrueNAS (`widgets.yaml.bak_20261024_144222`).
2. [x] Inserire il widget `greeting` dichiarativo (sanitizzato senza termine "Storage"):
   ```yaml
   - greeting:
       text_size: md
       text: "🟡 Stato: ECO (TrueNAS Online — K8s Dark)"
   ```
3. [x] Riavviare il container `homepage` su TrueNAS (`sudo docker restart homepage`).
4. [x] **Verifica Test-Driven**:
   - Container `homepage` tornato `running (healthy: healthy)`.
   - Query HTTP/2 su `https://home-internal.pindaroli.org/`: HTTP 200 con stringa `"Stato: ECO (TrueNAS Online — K8s Dark)"` renderizzata con successo.

### FASE 2: Aggiornamento Dashboard Mac Studio OrbStack (Modalità OFF / Failover) [COMPLETATA ✅]
1. [x] Modificare `docker/orbstack/homepage-config/widgets.yaml`:
   ```yaml
   - greeting:
       text_size: md
       text: "⚫ Stato: OFF (Rack Dark — Mac Studio Failover)"
   ```
2. [x] **Verifica Test-Driven**:
   - Validazione sintattica YAML con `yq` superata con successo (`exit code 0`).

### FASE 3: Aggiornamento Manifesti Kubernetes (Modalità FULL) [COMPLETATA ✅]
1. [x] Modificare simmetricamente `homepage/homepage.yaml` e `homepage/homepage-local.yaml` aggiungendo in `widgets.yaml`:
   ```yaml
       - greeting:
           text_size: md
           text: "🟢 Stato: FULL (K8s & TrueNAS Online)"
   ```
2. [x] **Verifica Test-Driven**:
   - Validazione sintattica manifesti YAML con `yq` superata con successo (`exit code 0`).
   - Sincronizzazione automatica al prossimo boot del cluster Talos in `lab_mode_full.sh`.

---

## 💾 Stato di Ripristino (AI Save-State)
- **Fase Attiva**: COMPLETATO ✅
- **Ultima Azione Completata**: Tutte e tre le dashboard Homepage (TrueNAS Live, OrbStack Failover, Kubernetes Full) aggiornate con il widget di stato sanitizzato senza termine "Storage" e validate.
- **Prossimo Passo Operativo**: Nessuno. Piano concluso e documentato nel Wiki.
- **Blocchi/Decisioni Pendenti**: Nessuno.

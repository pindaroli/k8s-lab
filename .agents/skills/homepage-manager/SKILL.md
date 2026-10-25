---
name: homepage-manager
type: skill
description: "Gestione e manutenzione dashboard Homepage nelle 4 modalità (homepage/external, homepage/lab_mode_full, homepage/lab_mode_eco, homepage/lab_mode_off): aggiunta e modifica servizi, correzione, aggiornamento o sostituzione di icone rotte, mancanti o invisibili, risoluzione icone con verifica preventiva di raggiungibilità a 7 livelli, fallback standard MDI e rollout automatico Kustomize/Docker."
when_to_use: "Quando l'utente richiede di aggiungere, rimuovere, aggiornare o modificare servizi, correggere o sostituire icone rotte o mancanti, sistemare link o widget nelle dashboard Homepage (homepage/external, homepage/lab_mode_full, homepage/lab_mode_eco, homepage/lab_mode_off, home.pindaroli.org, home-internal.pindaroli.org)."
status: active
tags:
  - homepage
  - dashboard
  - icons
  - kubernetes
  - kustomize
---

# Homepage Manager Skill (`homepage-manager`)

## 🗣️ Trigger Phrases Riconosciute (Pattern di Attivazione)
La skill si attiva automaticamente quando l'utente scrive o richiede comandi come:
- `correggi / sistema icona di <servizio>`
- `cambia / aggiorna / sostituisci icona di <servizio>`
- `l'icona di <servizio> non funziona / non si vede / è vuota su homepage`
- `icona rotta per <servizio>`
- `aggiungi <servizio> su homepage`
- `rimuovi / modifica <servizio> su homepage`
- `aggiorna dashboard homepage`

---

## 🎯 Obiettivo
Governare in modo deterministico e impeccabile l'intero ciclo di vita delle **4 dashboard Homepage** del lab, tutte centralizzate in `homepage/`:
1. **Allineamento Simmetrico Multi-Modalità**:
   - **Esterna (`home.pindaroli.org`)**: [homepage/external/services.yaml](file:///Users/olindo/prj/k8s-lab/homepage/external/services.yaml) (K8s protetto da OAuth2).
   - **Interna `FULL` (`home-internal.pindaroli.org` su K8s)**: [homepage/lab_mode_full/services.yaml](file:///Users/olindo/prj/k8s-lab/homepage/lab_mode_full/services.yaml).
   - **Interna `ECO` (`home-internal.pindaroli.org` su TrueNAS Docker)**: [homepage/lab_mode_eco/services.yaml](file:///Users/olindo/prj/k8s-lab/homepage/lab_mode_eco/services.yaml) (sincronizzata via `rsync` su `/mnt/stripe/truenas-docker/homepage/`).
   - **Interna `OFF` (`home-internal.pindaroli.org` su Mac OrbStack)**: [homepage/lab_mode_off/services.yaml](file:///Users/olindo/prj/k8s-lab/homepage/lab_mode_off/services.yaml).
2. **Risoluzione Icone con Verifica Preventiva (7 Livelli)**: Prima di salvare qualsiasi configurazione, testare preventivamente la reale raggiungibilità HTTP 200 dell'asset, evitando icone rotte o invisibili.
3. **Rollout e Verifica Automatica K8s (`kubectl apply -k homepage/`)**: Applicare tramite Kustomize (`configMapGenerator` con hash suffix automatico) e verificare lo stato `1/1 Running`.

---

## 🔍 Protocollo Risoluzione Icone (Verifica Preventiva a 7 Livelli)

> [!IMPORTANT]
> È severamente vietato inserire un nome di file icona o un URL senza aver prima verificato che la risorsa sia effettivamente raggiungibile (HTTP 200). L'agente DEVE eseguire i test prima di modificare i manifesti.

L'agente deve testare la reperibilità dell'icona seguendo rigorosamente questa gerarchia sequenziale (fino a 7 tentativi):

### 1. Livello 1: Dashboard Icons Primario (`<servizio>.png`)
Verificare nel repository `homarr-labs/dashboard-icons`:
`https://cdn.jsdelivr.net/gh/homarr-labs/dashboard-icons/png/<servizio>.png`  
*Sintassi in Homepage:* `icon: <servizio>.png`

### 2. Livello 2: Dashboard Icons Varianti (`.svg`, `-alt`, `-light`, no-hyphen)
Verificare se l'icona è censita con estensione SVG, con suffisso o senza trattini:
- `https://cdn.jsdelivr.net/gh/homarr-labs/dashboard-icons/svg/<servizio>.svg`
- `https://cdn.jsdelivr.net/gh/homarr-labs/dashboard-icons/png/<servizio>-alt.png`
- Forma normalizzata (es. `calibreweb` invece di `calibre-web`, `homeassistant` invece di `home-assistant`).  
*Sintassi in Homepage:* `icon: <slug-risultato>.png` o `icon: <slug-risultato>.svg`

### 3. Livello 3: Selfh.st Icons (`sh-<servizio>`)
Verificare il catalogo ufficiale `selfh.st/icons`:
- CDN: `https://cdn.jsdelivr.net/gh/selfhst/icons/png/<servizio>.png`  
*Sintassi in Homepage:* `icon: sh-<servizio>`

### 4. Livello 4: Web Asset dell'Applicazione in Esecuzione
Verificare se il pod o il container web dell'applicazione serve direttamente nella sua root o cartella statica asset grafici ad alta risoluzione:
- `http://<service>.<namespace>.svc.cluster.local:<port>/apple-touch-icon.png` (PNG quadrata ad alta risoluzione 180×180/192×192)
- `http://<service>.<namespace>.svc.cluster.local:<port>/logo.svg`
- `http://<service>.<namespace>.svc.cluster.local:<port>/favicon.png`  
*Sintassi in Homepage:* `icon: https://<servizio>-internal.pindaroli.org/<asset>` (o URL pubblico Cloudflare se protetto).

### 5. Livello 5: Simple Icons Nativo (`si-<servizio>`)
Verificare se il brand/progetto è censito nella libreria ufficiale Simple Icons (`https://simpleicons.org/`):  
*Sintassi in Homepage:* `icon: si-<slug>` (es. `si-kubernetes`, `si-traefik`, `si-grafana`). È opzionale aggiungere il codice esadecimale del brand: `si-<slug>-#<hex>`.

### 6. Livello 6: Lobe Icons / CNCF Icons
Verificare se l'icona è presente nelle collection specializzate cloud-native o AI:
- CNCF Icons: `https://cncf-icons.com/artwork/projects/<servizio>/icon/color/<servizio>-icon-color.svg`
- Lobe Icons (per stack AI/LLM): `https://cdn.jsdelivr.net/gh/lobehub/lobe-icons/packages/<servizio>/...`  
*Sintassi in Homepage:* `icon: https://<url-completo-svg>`

### 7. Livello 7: Asset Ufficiale Upstream (`Chart.yaml` o GitHub Repo)
Ispezionare il manifesto `Chart.yaml` della Helm Chart installata nel cluster o il README/assets del repository GitHub ufficiale dell'applicazione (es. `https://raw.githubusercontent.com/<owner>/<repo>/main/assets/logo.svg`).  
*Sintassi in Homepage:* `icon: https://<url-completo>`

---

### 🛑 Fallback Standard (dopo 7 tentativi falliti)
Qualora tutti i 7 livelli di ricerca preventiva abbiano dato esito negativo (nessun asset dedicato raggiungibile con HTTP 200), l'agente adotta l'approccio standard approvato:
- Utilizzo di un'icona semantica da **Material Design Icons**:  
  `icon: mdi-<categoria>` (es. `mdi-server`, `mdi-database`, `mdi-robot-outline`, `mdi-lan`, `mdi-wifi`, `mdi-chip`).

---

## 🛠️ Procedura Operativa di Rollout e Verifica

1. **In modalità `FULL` (Kubernetes — `homepage/external/` e `homepage/lab_mode_full/`)**:
   Il `configMapGenerator` di Kustomize calcola automaticamente il nuovo hash della ConfigMap e aggiorna i Deployment innescando il RollingUpdate:
   ```bash
   kubectl apply -k homepage/
   kubectl rollout status deployment/homepage -n default && kubectl rollout status deployment/homepage-local -n default
   kubectl get pods -n default -l 'app.kubernetes.io/name in (homepage,homepage-local)'
   ```

2. **In modalità `ECO` (TrueNAS Docker — `homepage/lab_mode_eco/`)**:
   Sincronizzare i file verso TrueNAS e riavviare il container `homepage`:
   ```bash
   rsync -az --no-owner --no-group -e "ssh -o BatchMode=yes" --rsync-path="sudo -n rsync" --exclude='.DS_Store' --exclude='logs/' homepage/lab_mode_eco/ olindo@10.10.20.50:/mnt/stripe/truenas-docker/homepage/ && ssh -o BatchMode=yes olindo@10.10.20.50 "sudo -n docker restart homepage"
   ```

3. **In modalità `OFF` (Mac Studio OrbStack — `homepage/lab_mode_off/`)**:
   Il bind mount `${ROOT_DIR}/homepage/lab_mode_off:/app/config` è diretto; riavviare il container locale se necessario:
   ```bash
   docker restart homepage-mac
   ```

Al termine, eseguire la congruenza di rete e la rigenerazione del wiki:
```bash
python3 scripts/network/validate_network.py && python3 scripts/wiki/build_wiki_context.py
```

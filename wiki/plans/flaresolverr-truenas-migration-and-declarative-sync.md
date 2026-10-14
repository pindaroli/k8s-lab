---
title: "Piano: Migrazione FlareSolverr su TrueNAS Docker & Riconciliazione Dichiarativa K8s/Prowlarr"
type: plan
status: active
certified_for_ai: true
created_at: 2026-10-14
tags:
  - "#flaresolverr"
  - "#truenas"
  - "#docker"
  - "#servarr"
  - "#prowlarr"
  - "#helm"
---

# Piano: Migrazione FlareSolverr su TrueNAS Docker & Riconciliazione Dichiarativa K8s/Prowlarr

Questo piano operativo definisce l'installazione e l'integrazione di **FlareSolverr** nello stack Docker Compose su TrueNAS SCALE bare-metal (`10.10.20.50`), la configurazione dichiarativa dei servizi TrueNAS (in particolare **Prowlarr** per il bypass della Cloudflare Turnstile Challenge su indexer protetti come **FileMood**), e il reindirizzamento dichiarativo senza cablaggio hardcoded dei carichi di lavoro Kubernetes verso l'endpoint TrueNAS tramite il file `values.yaml` della Helm Chart `servarr`.

---

## 🗺️ Mappe Concettuali e Relazioni
- [[SCHEMA]] (Regole del Wiki, Governance e Protocollo Test-Driven)
- [[Servarr]] (Architettura dello stack multimediale convergente)
- [[servarr-truenas-permanent-migration]] (Piano di migrazione carichi core su TrueNAS bare-metal)
- [[MCP_Platform]] (Integrazione `arrstack-mcp` per il controllo dell'infrastruttura media)
- [[Network_Registry]] (Censimento IP TrueNAS VLAN 20: `10.10.20.50`)

---

## 🎯 Obiettivi Architetturali

1. **Deploy FlareSolverr su TrueNAS (`10.10.20.50`)**:
   - Integrare il container `flaresolverr` (`ghcr.io/flaresolverr/flaresolverr:v3.4.6`) in `servarr/truenas-docker/docker-compose.yaml`.
   - Esporre la porta `8191:8191` sulla rete host di TrueNAS.
   - Consentire la comunicazione container-to-container nativa sulla rete Docker bridge di TrueNAS tramite hostname `http://flaresolverr:8191`.
2. **Collegamento Dichiarativo di Prowlarr a FlareSolverr**:
   - Configurare in modo dichiarativo e idempotente in Prowlarr il tag `flaresolverr`, il proxy `FlareSolverr` (`http://flaresolverr:8191`) e l'associazione del tag all'indexer `FileMood`.
   - Risolvere definitivamente l'errore di blocco Cloudflare Turnstile su FileMood senza degradare le performance degli altri indexer non protetti.
3. **Decoupling Dichiarativo K8s (Oggetto `external` con `ip` e `port`)**:
   - Aggiornare la Project Chart `charts/servarr` (`templates/external-services.yaml`) adottando l'oggetto standard `external:` contenente i campi `ip` e `port`.
   - Nessun riferimento a "TrueNAS" né IP di fallback cablati nel codice del chart Helm (chart 100% generico e agnostico).
   - Nel file di override dell'ambiente (`k8s-lab/servarr/arr-values.yaml`), dichiarare l'oggetto strutturato:
     ```yaml
     flaresolverr:
       enabled: false
       external:
         ip: "10.10.20.50"
         port: 8191
     ```
   - Incrementare la versione semantica della chart in `Chart.yaml` a `1.10.2`.
   - Dismettere il Pod locale `flaresolverr` su Kubernetes liberando risorse di calcolo sul nodo `talos-cp-01`.

---

## 🏗️ Fasi Operative

### 🐳 FASE 1: Installazione FlareSolverr nello Stack Docker TrueNAS
In questa fase si arricchisce la definizione dello stack Docker su TrueNAS e si avvia il container FlareSolverr.

#### Azioni
1. **Aggiornamento Dichiarativo `docker-compose.yaml`**:
   Nel file `servarr/truenas-docker/docker-compose.yaml`, aggiungere il blocco del servizio:
   ```yaml
     flaresolverr:
       image: ghcr.io/flaresolverr/flaresolverr:v3.4.6
       container_name: flaresolverr
       environment:
         - LOG_LEVEL=info
         - LOG_HTML=false
         - CAPTCHA_SOLVER=none
         - TZ=Europe/Rome
       ports:
         - 8191:8191
       restart: unless-stopped
   ```
2. **Sincronizzazione su TrueNAS**:
   Trasferire il file aggiornato su TrueNAS bare-metal (`10.10.20.50`) nella cartella `/mnt/stripe/truenas-docker/docker-compose.yaml`:
   ```bash
   scp servarr/truenas-docker/docker-compose.yaml olindo@10.10.20.50:/mnt/stripe/truenas-docker/docker-compose.yaml
   ```
3. **Avvio Container**:
   Eseguire il pull dell'immagine e il rollout del container via SSH passwordless:
   ```bash
   ssh -o BatchMode=yes olindo@10.10.20.50 "docker compose -f /mnt/stripe/truenas-docker/docker-compose.yaml up -d flaresolverr"
   ```

#### 🛑 CHECKPOINT FASE 1 (Test di Verifica)
- [x] Il container `flaresolverr` è nello stato `Up` su TrueNAS (`docker ps | grep flaresolverr`).
- [x] La porta `8191` risponde sulla LAN con codice 200:
  ```bash
  curl -s http://10.10.20.50:8191/ | grep -i "FlareSolverr is ready"
  ```
- [x] *(Completato)* Container attivo, `version: 3.4.6` e porta `8191` pienamente responsive.

---

### ⚙️ FASE 2: Configurazione Dichiarativa di Prowlarr verso FlareSolverr
In conformità con le raccomandazioni ufficiali TRaSH Guides, FlareSolverr in Prowlarr deve essere agganciato tramite tag dedicato (`flaresolverr`), in modo da attivarsi esclusivamente per le richieste dirette a indexer protetti da Cloudflare (es. `FileMood`), senza rallentare le query degli altri indexer standard.

#### Azioni
1. **Definizione File Dichiarativo (`servarr/truenas-docker/prowlarr-flaresolverr-config.yaml`)**:
   Creare la specifica dichiarativa dei proxy e delle associazioni indexer:
   ```yaml
   prowlarr:
     tags:
       - name: "flaresolverr"
     proxies:
       - name: "FlareSolverr"
         implementation: "FlareSolverr"
         configContract: "FlareSolverrSettings"
         host: "http://flaresolverr:8191"
         requestTimeout: 60
         tags:
           - "flaresolverr"
     indexers:
       - name: "FileMood"
         tags:
           - "flaresolverr"
   ```
2. **Sviluppo Script di Riconciliazione Idempotente (`scripts/servarr/sync_prowlarr_flaresolverr.py`)**:
   Implementare uno script Python autonomo che:
   - Estrae la chiave API di Prowlarr direttamente dal file locale o dall'ambiente (`/mnt/stripe/truenas-docker/prowlarr/config.xml` o secret SOPS).
   - Verifica se il tag `flaresolverr` esiste in `GET /api/v1/tag`; se assente, lo crea via `POST /api/v1/tag`.
   - Verifica se il proxy `FlareSolverr` esiste in `GET /api/v1/indexerproxy`; se assente o disallineato, lo crea o aggiorna impostando `host: http://flaresolverr:8191` e collegando il tag `flaresolverr`.
   - Recupera l'indexer `FileMood` da `GET /api/v1/indexer` e aggiunge il tag `flaresolverr` preservando i parametri esistenti.
   - Lancia il test dell'indexer `FileMood` per verificare il superamento della challenge.
3. **Esecuzione dello Script**:
   Eseguire lo script di riconciliazione per allineare Prowlarr.

#### 🛑 CHECKPOINT FASE 2 (Test di Verifica)
- [x] Il proxy `FlareSolverr` compare tra i proxy attivi di Prowlarr (`GET /api/v1/indexerproxy`).
- [x] L'indexer `FileMood` ha il tag `flaresolverr` assegnato.
- [x] Il test dell'indexer `FileMood` ha esito positivo (HTTP 200, challenge Turnstile superata e ricerca release operativa).
- [x] *(Completato)* Tag `flaresolverr` (ID 1) e Proxy `FlareSolverr` associati a FileMood; test di ricerca con esito 100% positivo (restituiti torrent con 973 seeders).

---

### ☸️ FASE 3: Reindirizzamento K8s via Helm Chart (`pindaroli-arr-helm`)
In questa fase si adegua la Project Chart Helm `charts/servarr` secondo il **Rasoio di Occam**: eliminando qualsiasi riferimento infrastrutturale specifico (nessuna menzione di "TrueNAS" né IP di fallback cablati nel template), introducendo un pattern Kubernetes generico e universale basato sull'oggetto strutturato **`external: { ip: "...", port: ... }`** per componente.

#### Schema Architetturale (Occam's Razor)
- **`enabled: true`** $\rightarrow$ Deployment + Service convenzionale in-cluster.
- **`enabled: false` + `external.ip`** $\rightarrow$ Service + Endpoints verso l'indirizzo e porta esterni (zero pod in K8s, risoluzione interna trasparente via DNS `servarr-<component>`).
- **`enabled: false` (senza `external`)** $\rightarrow$ Nessuna risorsa creata.

#### Azioni
1. **Aggiornamento Template Generico (`charts/servarr/templates/external-services.yaml`)**:
   Rifattorizzare il template eliminando la variabile accoppiata `$trueNasIp` e il fallback hardcoded `10.10.10.50`, adottando la direttiva generica per componente:
   ```yaml
   {{- if and .Values.flaresolverr (not .Values.flaresolverr.enabled) .Values.flaresolverr.external .Values.flaresolverr.external.ip }}
   {{- $port := .Values.flaresolverr.external.port | default .Values.flaresolverr.service.port | default 8191 }}
   apiVersion: v1
   kind: Service
   metadata:
     name: {{ .Release.Name }}-flaresolverr
     labels:
       app.kubernetes.io/name: flaresolverr
       app.kubernetes.io/instance: {{ .Release.Name | quote }}
   spec:
     ports:
       - port: {{ $port }}
         targetPort: {{ $port }}
         protocol: TCP
         name: http
   ---
   apiVersion: v1
   kind: Endpoints
   metadata:
     name: {{ .Release.Name }}-flaresolverr
     labels:
       app.kubernetes.io/name: flaresolverr
       app.kubernetes.io/instance: {{ .Release.Name | quote }}
   subsets:
     - addresses:
         - ip: {{ .Values.flaresolverr.external.ip | quote }}
       ports:
         - port: {{ $port }}
           name: http
   {{- end }}
   ```
   *(Uniformando con lo stesso pattern pulito anche `qbittorrent.external` e `prowlarr.external`)*.

2. **Incremento Semantico Versione Chart**:
   In `charts/servarr/Chart.yaml`, aggiornare:
   ```yaml
   version: 1.10.2
   ```

3. **Configurazione Dichiarativa nel file di valori (`k8s-lab/servarr/arr-values.yaml`)**:
   Dichiarare semplicemente l'oggetto strutturato per il componente:
   ```yaml
   flaresolverr:
     enabled: false
     external:
       ip: "10.10.20.50"
       port: 8191
   ```
   *(Nessuna variabile globale `externalTrueNasIp` o logica oscura: IP e porta risiedono nello stesso oggetto logico chiaro e auto-esplicativo)*.
4. **Validazione e Rollout Helm**:
   - Eseguire `helm lint charts/servarr`.
   - Eseguire `helm template servarr charts/servarr -f ../k8s-lab/servarr/arr-values.yaml -s templates/external-services.yaml` per confermare la corretta generazione del Service ed Endpoints `servarr-flaresolverr` puntanti a `10.10.20.50:8191`.
   - Applicare il deploy con enforced namespace `-n arr`:
     ```bash
     helm upgrade --install servarr charts/servarr -f ../k8s-lab/servarr/arr-values.yaml -n arr
     ```

#### 🛑 CHECKPOINT FASE 3 (Test di Verifica)
- [x] Il Service `servarr-flaresolverr` e gli Endpoints `servarr-flaresolverr` puntano all'IP `10.10.20.50:8191`:
  ```bash
  kubectl get endpoints servarr-flaresolverr -n arr
  ```
- [x] Il vecchio Pod `servarr-flaresolverr-*` nel namespace `arr` è stato terminato e non consuma più CPU/RAM su K8s.

---

### 🧪 FASE 4: Validazione Test-Driven End-to-End
Verifica complessiva della catena di chiamate sia dal cluster K8s sia dallo stack TrueNAS.

#### Azioni di Test
1. **Test Connettività K8s -> TrueNAS via K8s Service DNS**:
   Da uno dei pod attivi nel namespace `arr` (es. `servarr-radarr` o `servarr-bazarr`), verificare la risoluzione e raggiungibilità del proxy FlareSolverr:
   ```bash
   kubectl exec -it deployment/servarr-radarr -c radarr -n arr -- wget -qO- http://servarr-flaresolverr:8191/
   ```
   *Esito atteso*: Ricezione del payload JSON `{"msg": "FlareSolverr is ready!", "version": "v3.4.6"}`.
2. **Test Scraping FileMood da Prowlarr**:
   Verificare tramite arrstack-mcp o WebUI di Prowlarr che la ricerca su FileMood restituisca release e non generi errori HTTP 403 / challenge timeout.
3. **Audit Log FlareSolverr**:
   Ispezionare i log del container FlareSolverr su TrueNAS per osservare la corretta ricezione ed evasione delle richieste:
   ```bash
   ssh -o BatchMode=yes olindo@10.10.20.50 "sudo docker logs --tail 30 flaresolverr"
   ```

#### 🛑 CHECKPOINT FASE 4
- [x] FlareSolverr risolve con successo la Turnstile Challenge per FileMood.
- [x] I Pod K8s comunicano con FlareSolverr trasparente tramite il Service ClusterIP interno (`http://servarr-flaresolverr:8191/`).
- [x] Nessun errore presente nei log di Prowlarr o FlareSolverr (log FlareSolverr conferma `GET http://servarr-flaresolverr:8191/ 200 OK`).

---

### 📚 FASE 5: Consolidamento Documentale & Knowledge Base
Allineamento del Wiki e dei file di governance.

#### Azioni
1. Aggiornamento dell'entità [[Servarr]] (`wiki/entities/Servarr.md`) con la nuova topologia FlareSolverr su TrueNAS.
2. Sincronizzazione dei task in `todo.md`.
3. Esecuzione degli script di validazione e rigenerazione:
   ```bash
   python3 scripts/network/validate_network.py && python3 scripts/wiki/build_wiki_context.py
   ```

---

## 💾 Stato di Ripristino (AI Save-State)
- **Fase Attiva**: Piano Completato con Successo ✅
- **Ultima Azione Completata**: Fase 3, 4 e 5 completate. FlareSolverr attivo su TrueNAS (`10.10.20.50:8191`), Prowlarr riconciliato dichiarativamente (proxy + tag su FileMood), Helm Project Chart `pindaroli-arr-helm` aggiornata a `1.10.2` con pattern generico `external: { ip, port }`, Pod K8s dismesso, test E2E da pod K8s superato al 100%, wiki e todo sincronizzati.
- **Prossimo Passo Operativo**: Nessuno, piano concluso.
- **Blocchi/Decisioni Pendenti**: Nessuno.


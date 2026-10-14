---
title: "Piano: Integrazione Headlamp Kubernetes Web UI via Helm in k8s-lab"
type: plan
status: completed
completed_at: 2026-10-14
certified_for_ai: true
created_at: 2026-10-14
tags:
  - "#headlamp"
  - "#kubernetes"
  - "#helm"
  - "#traefik"
  - "#ingress"
  - "#dashboard"
  - "#homepage"
---

# Piano: Integrazione Headlamp Kubernetes Web UI via Helm in k8s-lab

Questo piano operativo definisce la procedura per installare, configurare ed integrare **Headlamp** (l'interfaccia web e dashboard estendibile per Kubernetes sviluppata sotto l'egida di `kubernetes-sigs`) all'interno del cluster Talos `k8s-lab`. L'integrazione rispetta rigorosamente le policy architetturali del homelab: gestione 100% dichiarativa via Helm (Anti-Loose-YAML Guard), instradamento Split-Horizon via Traefik (con TLS wildcard e Google OAuth2 per l'accesso esterno), censimento di rete in `rete.json`, e visualizzazione centralizzata nelle dashboard Homepage.

---

## 🗺️ Mappe Concettuali e Relazioni
- [[SCHEMA]] (Regole del Wiki, Governance e Protocollo Test-Driven)
- [[Talos_Cluster]] (Cluster Kubernetes Talos Linux v1.12.0)
- [[Traefik]] (Edge Router, Ingress Controller e Terminazione TLS)
- [[OAuth2_Proxy]] (Autenticazione Google OAuth per esposizione esterna)
- [[Homepage]] (Dashboard unificata dei servizi interni ed esterni)
- [[Network_Registry]] (Censimento IP e domini: VIP Traefik `10.10.20.56`)

---

## 🎯 Obiettivi Architetturali

1. **Deployment Dichiarativo Helm Ufficiale**:
   - Utilizzare il repository Helm ufficiale `kubernetes-sigs`:
     `https://kubernetes-sigs.github.io/headlamp/`
   - Creare un file di valori centralizzato e versionato: [`headlamp/headlamp-values.yaml`](file:///Users/olindo/prj/k8s-lab/headlamp/headlamp-values.yaml).
   - Nessun manifesto YAML standalone o non versionato (Anti-Loose-YAML Guard).

2. **Routing Split-Horizon via Traefik**:
   - **Accesso Interno (LAN)**: `https://headlamp-internal.pindaroli.org` (e `headlamp`) diretto senza passaggio da OAuth2, per una gestione operativa rapida e fluida dalla LAN (`10.10.20.0/24`).
   - **Accesso Esterno (Internet)**: `https://headlamp.pindaroli.org` protetto obbligatoriamente dal middleware `oauth2-auth` (Google Login con whitelist admin).
   - Certificato TLS: Wildcard `pindaroli-wildcard-tls` gestito da `cert-manager`.
   - L'oggetto `IngressRoute` di Traefik viene integrato direttamente nel file `values.yaml` di Helm sfruttando la chiave ufficiale `extraManifests`, garantendo che l'intera configurazione di rete sia gestita dal ciclo di vita della release Helm.

3. **Strategia di Autenticazione RBAC (Confermata)**:
   - **In-Cluster Automatic Token (`config.unsafeUseServiceAccountToken: true`)**: Headlamp utilizza direttamente il proprio `ServiceAccount` (`cluster-admin`) montato in-cluster via `/var/run/secrets/kubernetes.io/serviceaccount/token`. L'accesso da LAN fidata (`headlamp-internal.pindaroli.org`) è immediato senza prompt di credenziali, mentre l'accesso pubblico WAN (`headlamp.pindaroli.org`) è subordinato all'autenticazione preventiva su Traefik con Google OAuth2 (`oauth2-auth`).

4. **Namespace Dedicato (Confermato)**:
   - Namespace **`headlamp`** (gestito atomicamente da Helm con `--create-namespace`) anziché `kube-system`, per rispettare le best practice CIS/Kubernetes di isolamento del blast radius, auditing pulito e Pod Security Standards.

5. **Integrazione Dashboard Homepage**:
   - Aggiungere il riquadro Headlamp nella categoria `Kubernetes Services` sia in `homepage/homepage.yaml` (link esterno) sia in `homepage/homepage-local.yaml` (link interno).
   - Includere `siteMonitor` per monitorare la salute del pod via K8s CoreDNS (`http://headlamp.headlamp.svc.cluster.local:80/`).

---

## 🧠 Approfondimento Architetturale: Logica di extraManifests, Traefik Watch e Golden Pattern

### 1. Perché Traefik NON legge la directory `traefik/` sul Mac
I file storici presenti in `traefik/` (`ragflow-ingress-routes.yaml`, `mcp-ui-ingress-route.yaml`, `hermes-ingress-routes.yaml`, `all-arr-ingress-routes.yaml`) non sono mai stati montati o letti dal pod Traefik sui nodi Talos. Venivano caricati manualmente nel cluster tramite comandi operativi `kubectl apply -f`.
Traefik non è un proxy tradizionale che legge file statici da disco: è un **controller Kubernetes nativo** che interroga costantemente l'API Server tramite il meccanismo `Watch/Informer` (`providers.kubernetesCRD: enabled: true`, `allowCrossNamespace: true`). Non gli importa da quale file o cartella locale provenga la risorsa: gli interessa solo che esista come oggetto `IngressRoute` dentro Kubernetes.

### 2. Il Meccanismo di `extraManifests` (Anti-Loose-YAML Guard)
La chart upstream di Headlamp include un template (`extra-manifests.yaml`) che itera sugli oggetti dichiarati nella chiave `extraManifests` del file `values.yaml` e li compila come manifest nativi della release.
- **Ciclo di vita atomico**: Helm comprime l'intero pacchetto generato (Deployment, Service, ServiceAccount, ClusterRoleBinding e IngressRoute) e lo memorizza nel Secret della release (`sh.helm.release.v1.headlamp.v1`).
- **Nessuna risorsa orfana**: In caso di aggiornamento (`helm upgrade`), rollback (`helm rollback`) o disinstallazione (`helm uninstall`), l'IngressRoute di Traefik segue atomicamente il ciclo di vita dell'applicazione.

### 3. Headlamp come Golden Pattern per il Lab
Headlamp stabilisce il pattern di riferimento pulito al 100%:
- Unico punto di configurazione: `headlamp/headlamp-values.yaml`.
- Nessun file YAML sciolto sparso in directory accessorie.
- Tracciabilità GitOps totale.
Questo standard costituirà il modello per il futuro piano di bonifica e sanatoria del debito tecnico sui vecchi servizi (`traefik/*.yaml`).

---

## 🏗️ Fasi Operative

### 📦 FASE 1: Scaffolding e Configurazione Dichiarativa (`headlamp/headlamp-values.yaml`)
In questa fase viene creata la cartella dedicata `headlamp/` e redatto il file di valori conforme agli standard del lab.

#### Azioni
1. Creare la directory di configurazione:
   ```bash
   mkdir -p headlamp
   ```
2. Creare il file [`headlamp/headlamp-values.yaml`](file:///Users/olindo/prj/k8s-lab/headlamp/headlamp-values.yaml) con la seguente configurazione:
   ```yaml
   # ============================================================
   # Headlamp — Kubernetes Web UI Dashboard Helm Values
   # Repo: https://kubernetes-sigs.github.io/headlamp/
   # Homelab: pindaroli / Talos Linux v1.12.0
   # ============================================================

   replicaCount: 1

   image:
     registry: ghcr.io
     repository: headlamp-k8s/headlamp
     pullPolicy: IfNotPresent
     # Tag lasciato vuoto per seguire appVersion della chart ufficiale

   service:
     type: ClusterIP
     port: 80

   serviceAccount:
     create: true
     name: headlamp

   clusterRoleBinding:
     create: true
     clusterRoleName: cluster-admin

   config:
     inCluster: true
     inClusterContextName: "talos-cluster"
     sessionTTL: 86400
     # Se true, autentica gli utenti via ServiceAccount in-cluster (perfetto dietro Traefik OAuth2 / LAN)
     unsafeUseServiceAccountToken: true

   resources:
     requests:
       cpu: 50m
       memory: 64Mi
     limits:
       cpu: 300m
       memory: 256Mi

   # Ingress nativo Kubernetes disabilitato a favore dell'IngressRoute Traefik nativo
   ingress:
     enabled: false

   # Definizione dichiarativa IngressRoute Traefik Split-Horizon gestita da Helm (Anti-Loose-YAML Guard)
   extraManifests:
     - |
       apiVersion: traefik.io/v1alpha1
       kind: IngressRoute
       metadata:
         name: headlamp-ingress-route
         namespace: headlamp
       spec:
         entryPoints:
           - websecure
         routes:
           # 1. Accesso Esterno: protetto da Google OAuth2 via Traefik Middleware
           - match: Host(`headlamp.pindaroli.org`)
             kind: Rule
             services:
               - name: headlamp
                 port: 80
             middlewares:
               - name: oauth2-auth
                 namespace: traefik
           # 2. Accesso Interno LAN: accesso fidato diretto senza OAuth2
           - match: Host(`headlamp`) || Host(`headlamp-internal.pindaroli.org`)
             kind: Rule
             services:
               - name: headlamp
                 port: 80
         tls:
           secretName: pindaroli-wildcard-tls
   ```

#### 🛑 CHECKPOINT FASE 1 (Test di Verifica)
- [ ] Validazione sintattica della chart e dei valori tramite Helm dry-run:
  ```bash
  helm template headlamp headlamp/headlamp --namespace headlamp -f headlamp/headlamp-values.yaml > /dev/null
  ```
  *(Esito atteso: exit code 0 e nessun errore di rendering)*.

---

### 🌐 FASE 2: Registrazione di Rete e DNS (`rete.json` & OPNsense Unbound)
Registrazione dichiarativa degli alias di dominio verso il VIP Traefik.

#### Azioni
1. **Aggiornamento `rete.json`**:
   Aggiungere `"headlamp"` e `"headlamp-internal"` agli `aliases` del VIP `traefik-lb` (`10.10.20.56`):
   ```json
   "aliases": [
     "headlamp",
     "headlamp-internal",
     ...
   ]
   ```
2. **Configurazione DNS su OPNsense Unbound**:
   Verificare o creare gli Host Override per:
   - `headlamp.pindaroli.org` -> `10.10.20.56`
   - `headlamp-internal.pindaroli.org` -> `10.10.20.56`

#### 🛑 CHECKPOINT FASE 2 (Test di Verifica)
- [ ] Convalida dello schema di rete tramite script:
  ```bash
  python3 scripts/network/validate_network.py
  ```
- [ ] Risoluzione DNS locale da terminale:
  ```bash
  dig +short headlamp-internal.pindaroli.org @10.10.20.1
  ```
  *(Esito atteso: `10.10.20.56`)*.

---

### 🚀 FASE 3: Deployment Helm della Release
Esecuzione del deployment dichiarativo nel namespace di destinazione (`headlamp`).

#### Azioni
1. Aggiungere e aggiornare il repository Helm:
   ```bash
   helm repo add headlamp https://kubernetes-sigs.github.io/headlamp/
   ```
   ```bash
   helm repo update headlamp
   ```
2. Eseguire l'installazione o upgrade dichiarativo:
   ```bash
   helm upgrade --install headlamp headlamp/headlamp --namespace headlamp --create-namespace -f headlamp/headlamp-values.yaml
   ```

#### 🛑 CHECKPOINT FASE 3 (Test di Verifica)
- [ ] Ispezione dello stato del deployment e pod:
  ```bash
  kubectl rollout status deployment/headlamp -n headlamp
  ```
- [ ] Ispezione del Service e dell'IngressRoute Traefik generati:
  ```bash
  kubectl get svc headlamp -n headlamp
  ```
  ```bash
  kubectl get ingressroute headlamp-ingress-route -n headlamp
  ```
  *(Esito atteso: Deployment in stato `successfully rolled out`, Service attivo su porta 80 e IngressRoute valido)*.

---

### 🧪 FASE 4: Validazione Test-Driven & Generazione Token di Accesso
Verifica funzionale end-to-end del servizio sia a livello HTTP interno sia di autorizzazioni RBAC.

#### Azioni
1. **Test Connettività HTTP Interna**:
   Effettuare una richiesta HTTP verso il Traefik VIP passando l'header host per `headlamp-internal.pindaroli.org`:
   ```bash
   curl -k -I -s --resolve headlamp-internal.pindaroli.org:443:10.10.20.56 https://headlamp-internal.pindaroli.org/ | head -n 5
   ```
   *(Esito atteso: HTTP 200 OK)*.
2. **Procedura Generazione Token Admin (Fallback / Token Mode)**:
   Nel caso in cui si volesse comunque generare un token esplicito:
   ```bash
   kubectl create token headlamp -n headlamp --duration=8760h
   ```
   *(Genera un token JWT valido per 1 anno per autenticarsi direttamente nell'interfaccia di Headlamp)*.

#### 🛑 CHECKPOINT FASE 4
- [ ] L'interfaccia web di Headlamp risponde correttamente con HTTP 200 via `headlamp-internal.pindaroli.org`.
- [ ] L'interfaccia visualizza automaticamente e senza prompt le risorse del cluster (nodi, pod, namespace, storage) grazie al token in-cluster.

---

### 📊 FASE 5: Integrazione Dashboard Homepage & Consolidamento Knowledge Base
Integrazione dell'icona e monitoraggio in Homepage e allineamento della documentazione.

#### Azioni
1. **Aggiornamento `homepage/homepage.yaml` (Esterno)**:
   Aggiungere in `Kubernetes Services`:
   ```yaml
   - Headlamp:
       href: https://headlamp.pindaroli.org
       description: Kubernetes cluster web UI & management dashboard
       icon: si-kubernetes
       siteMonitor: http://headlamp.headlamp.svc.cluster.local:80/
   ```
2. **Aggiornamento `homepage/homepage-local.yaml` (Interno)**:
   Aggiungere in `Kubernetes Services`:
   ```yaml
   - Headlamp:
       href: https://headlamp-internal.pindaroli.org
       description: Kubernetes cluster web UI (Internal)
       icon: si-kubernetes
       siteMonitor: http://headlamp.headlamp.svc.cluster.local:80/
   ```
3. **Rollout Homepage**:
   Applicare i manifesti e riavviare i deployment come da regola di progetto:
   ```bash
   kubectl apply -f homepage/homepage.yaml && kubectl apply -f homepage/homepage-local.yaml && kubectl rollout restart deployment/homepage deployment/homepage-local -n default
   ```
4. **Documentazione**:
   - Creare la scheda entità [`wiki/entities/Headlamp.md`](file:///Users/olindo/prj/k8s-lab/wiki/entities/Headlamp.md).
   - Eseguire i comandi di rigenerazione e compilazione del contesto wiki:
     ```bash
     python3 scripts/network/validate_network.py && python3 scripts/wiki/build_wiki_context.py
     ```

---

## 💾 Stato di Ripristino (AI Save-State)
- **Fase Attiva**: Piano Completato ✅
- **Ultima Azione Completata**: Fase 5 completata con successo. Servizio Headlamp registrato in Homepage esterna e interna, rollout restart dei deployment `homepage` e `homepage-local` completato con esito positivo, scheda entità `wiki/entities/Headlamp.md` creata e wiki context rigenerato.
- **Prossimo Passo Operativo**: Nessuno. Integrazione dichiarativa di Headlamp completata al 100%.
- **Blocchi/Decisioni Pendenti**: Nessuno.

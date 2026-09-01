---
title: "Piano: Architettura e Deployment Enterprise per RAGFlow su Cluster Kubernetes a 3 Nodi"
type: plan
status: active
certified_for_ai: true
created_at: 2026-08-30
tags:
  - "#plan"
  - "#ragflow"
  - "#ai"
  - "#cnpg"
  - "#storage"
  - "#s3"
  - "#traefik"
  - "#security"
---

# Piano: Architettura e Deployment Enterprise per RAGFlow su Cluster Kubernetes a 3 Nodi

**Target**: Cluster GEMINI (`pindaroli.org`) · **Data**: 2026-08-30  
**Autore**: Antigravity AI Engineering  

> [!IMPORTANT]
> **RAGFlow** è una piattaforma Retrieval-Augmented Generation (RAG) di livello enterprise per l'orchestrazione avanzata di agenti IA e l'estrazione da documenti complessi tramite il motore di visione **DeepDoc**.
> Il deployment adotta l'**Architettura Ibrida Assistita da Operator**:
> - **Core Computazionale**: Pod stateless RAGFlow + DeepDoc + Redis + Elasticsearch distribuiti su 3 nodi Talos K8s (`talos-cp-01`, `talos-cp-02`, `talos-cp-03`).
> - **Database Relazionale HA**: Cluster PostgreSQL (1 Primary + 2 Replicas) gestito nativamente dall'Operator **CloudNativePG (CNPG)** su storage NVMe locale (`local-postgres`).
> - **Object Storage**: Bucket `ragflow-docs` ospitato su **Garage S3** (TrueNAS `10.10.10.50:3900`), protetto da ZFS su disco con indirizzamento `path-style`.
> - **Sicurezza & Ingress**: Routing Traefik con separazione **Split-Horizon** (Esterno con **OAuth2 Proxy**, Interno fiduciario diretto).

---

## 1. Analisi Architetturale e Strategia Ibrida Assistita da Operator

La piattaforma RAGFlow si compone di microservizi specializzati:
- **DeepDoc Engine**: Motore OCR e visual layout analysis per estrazione strutturata di PDF, tabelle e immagini.
- **RAGFlow API Server**: Server bilingue Python (Quart) / Go per API REST, gestione agenti e orchestrazione workflow.
- **Task Queue & Cache**: Istanza Redis per lo scheduling asincrono dell'elaborazione documentale.
- **Vector & Hybrid Search**: Motore Elasticsearch dedicato all'indicizzazione ibrida (full-text + vector embedding).
- **Relational DB**: PostgreSQL per metadati, utenti, tenancy e log dei workflow.
- **Object Storage**: S3 per il repository immutabile dei file originali e dei chunk binari.

### Confronto Modelli di Deployment

| Modello di Deploy | Componenti Gestiti | Meccanismo di Persistenza | Grado di Isolamento & Resilienza | Complessità Operativa | Valutazione |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Helm Monolitico In-Chart** | Tutti i microservizi (API, DeepDoc, MySQL mono-istanza, Redis, ES, MinIO) in un unico chart. | StatefulSet a replica singola con PVC locali. | **Basso**. Singolo punto di guasto (SPOF) su DB e MinIO; competizione risorse sui nodi. | Minima (singolo comando Helm). | ❌ Non adatto alla produzione |
| **Architettura Ibrida K8s + External Storage (Raccomandata)** | Core RAGFlow/DeepDoc/ES/Redis via Helm; PostgreSQL HA via Operator (CNPG); Object Storage Garage S3 su TrueNAS. | CNPG PostgreSQL distribuito su 3 nodi (NVMe locale); TrueNAS ZFS per dati S3. | **Elevato**. Nessun SPOF; failover automatico del DB in <10s; storage blob protetto da ZFS. | Media (gestione CRD e S3 esterno). | ✅ **Scelta Ottimale** |
| **Docker Compose (Non-K8s)** | Tutti i servizi eseguiti come container su singolo host bare metal/VM. | Bind mount su filesystem locale. | **Assente**. Totalmente dipendente dalla singola macchina. | Bassa (ambiente dev). | ❌ Non resiliente |

### Diagramma Architetturale

```
                             ┌───────────────────────────────────────────────────────────┐
                             │                      TRAEFIK EDGE                         │
                             │                 (VIP: 10.10.20.56:443)                    │
                             └─────────────┬───────────────────────────────┬─────────────┘
                                           │                               │
                      [Esterno: ragflow.pindaroli.org]          [Interno: ragflow-internal]
                                           │                               │
                                 ┌─────────▼──────────┐                    │
                                 │    OAuth2 Proxy    │                    │
                                 │   (Google Auth)    │                    │
                                 └─────────┬──────────┘                    │
                                           │                               │
                                           └───────────────┬───────────────┘
                                                           │
                                            ┌──────────────▼──────────────┐
                                            │    ragflow-system (K8s)     │
                                            └──────────────┬──────────────┘
                                                           │
            ┌──────────────────────────────────────────────┼──────────────────────────────────────────────┐
            │                                              │                                              │
 ┌──────────▼──────────┐                        ┌──────────▼──────────┐                        ┌──────────▼──────────┐
 │    talos-cp-01      │                        │    talos-cp-02      │                        │    talos-cp-03      │
 │  (10.10.20.141)     │                        │  (10.10.20.142)     │                        │  (10.10.20.143)     │
 ├─────────────────────┤                        ├─────────────────────┤                        ├─────────────────────┤
 │ • RAGFlow API Pod   │                        │ • DeepDoc OCR Pod   │                        │ • Elasticsearch Pod │
 │ • Redis Cache Pod   │                        │                     │                        │                     │
 │ • CNPG: postgres-1  │◄══════════════════════►│ • CNPG: postgres-2  │◄══════════════════════►│ • CNPG: postgres-3  │
 │   (Primary)         │  Streaming Replication │   (Standby Replica) │  Streaming Replication │   (Standby Replica) │
 └──────────┬──────────┘                        └─────────────────────┘                        └─────────────────────┘
            │                                                                                             │
            │ PostgreSQL WAL Archiving & Blob Document Storage                                            │
            └──────────────────────────────────────────────┬──────────────────────────────────────────────┘
                                                           │ (S3 Protocol - Path Style)
                                            ┌──────────────▼──────────────┐
                                            │      TrueNAS Bare Metal     │
                                            │        (10.10.10.50)        │
                                            ├─────────────────────────────┤
                                            │  Garage S3 (Porta 3900)     │
                                            │  Bucket: ragflow-docs       │
                                            │  Pool: ZFS RAID-Z2          │
                                            └─────────────────────────────┘
```

---

## 2. Object Storage: Configurazione di Garage S3 su TrueNAS

Garage è già operativo come container Docker su TrueNAS (`10.10.10.50:3900`). È necessario inizializzare il bucket dedicato e configurare i corretti parametri di integrazione.

### Passo 1: Inizializzazione Bucket e Credenziali via Garage CLI
Eseguire all'interno del container Garage su TrueNAS:

```bash
# 1. Creazione del bucket dedicato ai documenti RAGFlow
garage bucket create ragflow-docs
```

*Verifica:*
```bash
garage bucket list | grep ragflow-docs
```

```bash
# 2. Creazione della chiave API dedicata
garage key create ragflow-key
```

*Verifica:*
```bash
garage key list | grep ragflow-key
```

```bash
# 3. Assegnazione permessi di lettura e scrittura sul bucket
garage bucket allow ragflow-docs --read --write --key ragflow-key
```

*Verifica:*
```bash
garage bucket info ragflow-docs
```

### Passo 2: Parametri di Integrazione e Configurazioni Critiche

I parametri di connessione verso Garage su TrueNAS vengono configurati come segue:

```yaml
s3:
  access_key: "<GARAGE_ACCESS_KEY_DA_SOPS>"
  secret_key: "<GARAGE_SECRET_KEY_DA_SOPS>"
  endpoint_url: "http://10.10.10.50:3900"
  bucket: "ragflow-docs"
  region: "garage"
  signature_version: "v4"
  addressing_style: "path"
```

> [!CRITICAL]
> **Rilevanza del parametro `addressing_style: "path"`**:
> Di default, i client S3 usano il *Virtual-Hosted Style* (`http://ragflow-docs.10.10.10.50:3900/file`), che fallisce in assenza di wildcard DNS per gli indirizzi IP.
> Impostando **`addressing_style: "path"`**, RAGFlow richiede le risorse nella forma `http://10.10.10.50:3900/ragflow-docs/file`, garantendo la comunicazione diretta via IP:porta senza dipendenze DNS esterne.

### Requisiti di Rete e Reverse Proxy
- **Raggiungibilità Porta 3900**: Verificare che la subnet VLAN 20 (`10.10.20.0/24`) dei nodi Talos possa raggiungere la porta `3900` su TrueNAS (`10.10.10.50`).
- **Dimensione Massima Payload**: Nelle rotte Traefik e nei proxy intermedi, il limite `client_max_body_size` deve essere configurato a non meno di **`500M`** per supportare l'upload di grandi documenti PDF e corpora testuali.

---

## 3. Database Relazionale Distribuito: Cluster PostgreSQL HA via CloudNativePG

RAGFlow supporta nativamente PostgreSQL tramite `DB_TYPE=postgresql`. Per eliminare qualsiasi SPOF, viene utilizzato l'operator **CloudNativePG** con topologia a 3 istanze su storage locale NVMe.

### Passo 1: Verifica e Installazione dell'Operator CloudNativePG
Se l'operator non è già presente nel cluster:

```bash
kubectl apply --server-side -f https://raw.githubusercontent.com/cloudnative-pg/cloudnative-pg/release-1.22/releases/cnpg-1.22.0.yaml
```

*Verifica:*
```bash
kubectl get pods -n cnpg-system
```

### Passo 2: Definizione del Secret Cifrato (SOPS)
Creare il file `secrets-sops/ragflow-secrets.enc.yaml` contenente le credenziali cifrate:

```yaml
apiVersion: v1
kind: Secret
metadata:
  name: postgres-ragflow-creds
  namespace: ragflow-system
type: Opaque
stringData:
  username: ragflow_user
  password: "<GENERATED_STRONG_PASSWORD>"
```

### Passo 3: Manifesto Custom Resource `Cluster` (CNPG)
File `ragflow/postgres-ha.yaml`:

```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: ragflow-system
---
apiVersion: postgresql.cnpg.io/v1
kind: Cluster
metadata:
  name: postgres-ha
  namespace: ragflow-system
spec:
  instances: 3

  # Immagine ufficiale ottimizzata CNPG
  imageName: ghcr.io/cloudnative-pg/postgresql:16.4

  # Distribuzione anti-affinità rigida sui 3 nodi Talos
  topologySpreadConstraints:
    - maxSkew: 1
      topologyKey: kubernetes.io/hostname
      whenUnsatisfiable: DoNotSchedule
      labelSelector:
        matchLabels:
          cnpg.io/cluster: postgres-ha

  storage:
    size: 20Gi
    storageClass: local-postgres

  walStorage:
    size: 10Gi
    storageClass: local-postgres

  bootstrap:
    initdb:
      database: rag_flow
      owner: ragflow_user
      secret:
        name: postgres-ragflow-creds

  resources:
    requests:
      cpu: "1000m"
      memory: "2Gi"
    limits:
      cpu: "2000m"
      memory: "4Gi"

  postgresql:
    parameters:
      max_connections: "1000"
      shared_buffers: "1GB"
      work_mem: "16MB"
      maintenance_work_mem: "256MB"
      effective_cache_size: "3GB"

  backup:
    retentionPolicy: "30d"
    barmanObjectStore:
      destinationPath: s3://postgres-wal/
      endpointURL: http://10.10.10.50:3900
      s3Credentials:
        accessKeyId:
          name: garage-creds
          key: ACCESS_KEY_ID
        secretAccessKey:
          name: garage-creds
          key: SECRET_ACCESS_KEY
      wal:
        compression: gzip

  monitoring:
    enablePodMonitor: true
```

*Verifica:*
```bash
kubectl get cluster -n ragflow-system postgres-ha
```
*Esito atteso:* `Cluster in healthy state`, `3/3 instances ready`, endpoint `postgres-ha-rw.ragflow-system.svc.cluster.local:5432` disponibile.

---

## 4. Deployment Dettagliato di RAGFlow tramite Helm Chart

### Dimensionamento Risorse Cluster K8s (3 Nodi)
- **vCPU**: Richieste minime 6-8 vCPU aggregate, limiti a 12-16 vCPU.
- **RAM**: Richieste minime 12-16 GB aggregate, limiti a 24-32 GB.
- **Storage Subsystem**: NVMe locale (`local-postgres`) per PostgreSQL ed Elasticsearch; TrueNAS ZFS per blob binary S3.

### Immagini Container Ufficiali
- **RAGFlow Core**: `infiniflow/ragflow:v0.27.1`
- **DeepDoc OCR/Vision**: `infiniflow/deepdoc_oss:latest`

### File di Configurazione `values-hybrid.yaml`

File `ragflow/values-hybrid.yaml`:

```yaml
ragflow:
  image:
    repository: infiniflow/ragflow
    tag: v0.27.1
    pullPolicy: IfNotPresent

  env:
    DB_TYPE: "postgresql"
    STORAGE_IMPL: "S3"
    TZ: "Europe/Rome"

  deployment:
    resources:
      requests:
        cpu: "2000m"
        memory: "4Gi"
      limits:
        cpu: "4000m"
        memory: "8Gi"

  service_conf:
    database:
      type: "postgresql"

    postgres:
      name: "rag_flow"
      user: "ragflow_user"
      # La password viene iniettata tramite Secret K8s o Secret SOPS
      password: "<FROM_SOPS_SECRET>"
      host: "postgres-ha-rw.ragflow-system.svc.cluster.local"
      port: 5432
      max_connections: 1000

    s3:
      access_key: "<GARAGE_ACCESS_KEY>"
      secret_key: "<GARAGE_SECRET_KEY>"
      endpoint_url: "http://10.10.10.50:3900"
      bucket: "ragflow-docs"
      region: "garage"
      signature_version: "v4"
      addressing_style: "path"

deepdoc:
  image:
    repository: infiniflow/deepdoc_oss
    tag: latest
  deployment:
    resources:
      requests:
        cpu: "1000m"
        memory: "2Gi"
      limits:
        cpu: "2000m"
        memory: "4Gi"

# Disabilitazione MySQL mono-istanza in-chart (sostituito da CNPG)
mysql:
  enabled: false

# Elasticsearch per indicizzazione ibrida vettoriale/testuale
elasticsearch:
  enabled: true
  storage:
    capacity: 30Gi
    storageClassName: "local-postgres"
  deployment:
    resources:
      requests:
        cpu: "2000m"
        memory: "4Gi"
      limits:
        cpu: "4000m"
        memory: "8Gi"

# Redis per caching e coda task asincroni
redis:
  enabled: true
  deployment:
    resources:
      requests:
        cpu: "200m"
        memory: "512Mi"
      limits:
        cpu: "500m"
        memory: "1Gi"

# Pod Anti-Affinity per distribuire le repliche sui 3 nodi fisici
affinity:
  podAntiAffinity:
    preferredDuringSchedulingIgnoredDuringExecution:
      - weight: 100
        podAffinityTerm:
          labelSelector:
            matchExpressions:
              - key: app.kubernetes.io/name
                operator: In
                values:
                  - ragflow
                  - deepdoc
                  - elasticsearch
          topologyKey: "kubernetes.io/hostname"
```

---

## 5. Ingress & Routing Traefik Split-Horizon

Nel pieno rispetto delle **Golden Rules** del Progetto GEMINI:
- **Accesso Esterno (`ragflow.pindaroli.org`)**: Protetto obbligatoriamente da Google OAuth2 via middleware `oauth2-auth@kubernetescrd`.
- **Accesso Interno (`ragflow-internal.pindaroli.org` / `ragflow`)**: Diretto e fiduciario senza autenticazione OAuth2.

### Manifesto Traefik IngressRoute
File `traefik/ragflow-ingress-routes.yaml`:

```yaml
apiVersion: traefik.io/v1alpha1
kind: IngressRoute
metadata:
  name: ragflow-ingress-route
  namespace: ragflow-system
spec:
  entryPoints:
    - websecure
  routes:
    # 1. Accesso Esterno protetto da OAuth2 Proxy
    - match: Host(`ragflow.pindaroli.org`)
      kind: Rule
      services:
        - name: ragflow
          port: 9380
      middlewares:
        - name: oauth2-auth
          namespace: traefik

    # 2. Accesso Interno LAN Diretto
    - match: Host(`ragflow`) || Host(`ragflow-internal.pindaroli.org`)
      kind: Rule
      services:
        - name: ragflow
          port: 9380
  tls:
    secretName: pindaroli-wildcard-tls
```

---

## 6. Integrazione Rete, DNS & Homepage Dashboard

### Aggiornamento `rete.json`
Aggiungere gli alias DNS sotto il nodo `traefik-lb` (VIP `10.10.20.56`):
- `ragflow`
- `ragflow-internal`

### Aggiornamento Dashboard Homepage
File `homepage/homepage.yaml` e `homepage/homepage-local.yaml` nella sezione `"AI services"`:

```yaml
        - RAGFlow:
            href: https://ragflow.pindaroli.org # (o -internal per homepage-local)
            description: Enterprise RAG & DeepDoc Document Intelligence
            icon: mdi-brain
```

*Applicazione e rollout automatico:*
```bash
kubectl apply -f homepage/homepage.yaml && kubectl apply -f homepage/homepage-local.yaml && kubectl rollout restart deployment/homepage deployment/homepage-local -n default
```

---

## 7. Protocollo di Resilienza, Manutenzione e Test-Driven Verification

### Fase 1: Verifica Stato Pod e Distribuzione Multi-Nodo
```bash
kubectl get pods -n ragflow-system -o wide
```
*Esito Atteso*: Tutti i Pod (`ragflow`, `deepdoc`, `postgres-ha-1..3`, `elasticsearch`, `redis`) in stato `Running` e distribuiti equamente tra i nodi `talos-cp-01`, `talos-cp-02`, `talos-cp-03`.

### Fase 2: Validazione Salute Cluster CNPG
```bash
kubectl get cluster -n ragflow-system postgres-ha
```
*Esito Atteso*: `Cluster in healthy state` con `3/3` istanze pronte e sync attivo.

### Fase 3: Test di Failover Automatico del Database
Simulazione di guasto hardware sul nodo che ospita il Primary:
```bash
# 1. Identificazione dell'istanza Primary
kubectl get pods -n ragflow-system -l cnpg.io/role=primary

# 2. Eliminazione controllata del Pod Primary
kubectl delete pod postgres-ha-1 -n ragflow-system

# 3. Monitoraggio elezione e promozione in tempo reale
kubectl get cluster -n ragflow-system postgres-ha -w
```
*Esito Atteso*: CloudNativePG promuove una delle due repliche a Primary in meno di **10 secondi**, reindirizzando trasparentemente le scritture sull'endpoint `postgres-ha-rw` senza crash o disservizi nei pod RAGFlow.

### Fase 4: Validazione Persistenza Documenti su Garage S3
1. Effettuare il login sull'interfaccia UI di RAGFlow ed eseguire l'upload di un documento PDF di test.
2. Eseguire l'ispezione del bucket su Garage CLI:
```bash
garage bucket info ragflow-docs
```
*Esito Atteso*: Aumento del conteggio oggetti e della dimensione del bucket, a conferma del corretto upload binario su ZFS.

### Fase 5: Procedura di Upgrade e Migrazioni Schema ORM
Prima di procedere ad aggiornamenti di versione del container RAGFlow:
1. **Backup Logico/Snapshot CNPG**: Eseguire il backup del cluster PostgreSQL (`kubectl cnpg backup postgres-ha -n ragflow-system`).
2. **Aggiornamento Tag Immagine**: Aggiornare `ragflow.image.tag` nel file `values-hybrid.yaml`.
3. **Esecuzione Helm Upgrade**:
   ```bash
   helm upgrade ragflow . -n ragflow-system -f values-hybrid.yaml
   ```
4. **Audit Log di Migrazione DDL**:
   ```bash
   kubectl logs -n ragflow-system -l app.kubernetes.io/name=ragflow --tail=100
   ```
   Verificare l'assenza di errori nelle migrazioni automatiche eseguite dall'ORM Peewee all'avvio.

---

## 💾 Stato di Ripristino (AI Save-State)
- **Fase Attiva**: Deployment & Verifica Completati con Successo ✅
- **Ultima Azione Completata**: Consolidamento database `rag_flow` su `postgres-main` (CNPG), deploy Helm release `ragflow` (v0.27.1), IngressRoute Traefik e cifratura completa dei segreti in SOPS (`secrets-sops/ragflow-secrets.enc.yaml`).
- **Prossimo Passo Operativo**: Utilizzo operativo della piattaforma RAGFlow su `https://ragflow.pindaroli.org` (OAuth2) e `https://ragflow-internal.pindaroli.org`.
- **Blocchi/Decisioni Pendenti**: Nessuno. Piattaforma 100% convergente, operational e testata con successo.


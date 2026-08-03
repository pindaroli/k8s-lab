---
title: Piano POC Minimale — Discovery Kubernetes su ServiceNow PDI
status: active
certified_for_ai: true
created_at: 2026-08-03
tags:
  - servicenow
  - kubernetes
  - discovery
  - itom
  - cmdb
---

# 🎯 Piano POC Minimale: Discovery Kubernetes su ServiceNow PDI (`dev395227`)

## 📌 Obiettivo del Test
Effettuare un test di fattibilità (Proof of Concept) essenziale per verificare che la PDI ServiceNow (`https://dev395227.service-now.com`) sia in grado di scansionare il cluster Kubernetes del lab e popolare automaticamente il CMDB con i relativi CI (`cmdb_ci_kubernetes_cluster`, `cmdb_ci_kubernetes_node`, `cmdb_ci_kubernetes_pod`).

---

## 🛠️ Elenco Configurazioni Minime (3 Step)

### Passo 1: Configurazione RBAC K8s (Lettura API Server)
Creazione di un `ServiceAccount` e `ClusterRole` di sola lettura sul cluster Kubernetes del lab per consentire la scansione.

1. **Manifest YAML minimale (`sn-rbac-minimal.yaml`)**:
   ```yaml
   apiVersion: v1
   kind: ServiceAccount
   metadata:
     name: sn-discovery-sa
     namespace: default
   ---
   apiVersion: rbac.authorization.k8s.io/v1
   kind: ClusterRole
   metadata:
     name: sn-discovery-read-role
   rules:
   - apiGroups: ["", "apps"]
     resources: ["nodes", "namespaces", "pods", "services", "deployments"]
     verbs: ["get", "list", "watch"]
   ---
   apiVersion: rbac.authorization.k8s.io/v1
   kind: ClusterRoleBinding
   metadata:
     name: sn-discovery-binding
   subjects:
   - kind: ServiceAccount
     name: sn-discovery-sa
     namespace: default
   roleRef:
     kind: ClusterRole
     name: sn-discovery-read-role
     apiGroup: rbac.authorization.k8s.io
   ```
2. **Generazione Bearer Token**:
   ```bash
   kubectl create token sn-discovery-sa --duration=8760h -n default
   ```

---

### Passo 2: Avvio e Validazione del MID Server (Pod K8s)
Deploy di un singolo Pod MID Server nel cluster K8s che fa da ponte outbound verso ServiceNow.

1. **Deployment K8s MID Server (`sn-mid-server.yaml`)**:
   ```yaml
   apiVersion: apps/v1
   kind: Deployment
   metadata:
     name: sn-mid-server
     namespace: default
   spec:
     replicas: 1
     selector:
       matchLabels:
         app: mid-server
     template:
       metadata:
         labels:
           app: mid-server
       spec:
         containers:
         - name: mid-server
           image: servicenow/mid-server:latest
           env:
           - name: YOUR_INSTANCE_URL
             value: "https://dev395227.service-now.com"
           - name: MID_INSTANCE_USERNAME
             value: "admin"
           - name: MID_INSTANCE_PASSWORD
             valueFrom:
               secretKeyRef:
                 name: servicenow-mid-creds
                 key: SN_PASSWD
           - name: MID_SERVER_NAME
             value: "K8s_Lab_MID_Server"
   ```
2. **Validazione in ServiceNow**:
   - Accedere alla PDI -> **MID Server -> Servers**.
   - Selezionare `K8s_Lab_MID_Server` e cliccare **Validate**.

---

### Passo 3: Inserimento Credenziali e Scansione Quick Discovery
Configurazione del token K8s ed esecuzione della prima scansione di prova.

1. **Inserimento Credenziale su ServiceNow**:
   - Navigare in **Discovery -> Credentials**.
   - Cliccare **New** -> Selezionare **Kubernetes Credentials**.
   - Inserire:
     - **Name**: `K8s-Lab-Token`
     - **Bearer Token**: Il token generato al Passo 1.
2. **Esecuzione Quick Discovery**:
   - Navigare in **Discovery -> Quick Discovery**.
   - Inserire:
     - **Target IP / Endpoint**: Endpoint dell'API Server K8s (es. `https://10.10.10.x:6443` o `https://kubernetes.default.svc:443`).
     - **MID Server**: `K8s_Lab_MID_Server`.
   - Cliccare **Run Discovery**.

---

## 🧪 Criterio di Successo e Verifica (CMDB Audit)
Il test si considera superato con successo quando, terminata la Discovery, interrogando le seguenti tabelle CMDB in ServiceNow compaiono i record reali del lab:

- `cmdb_ci_kubernetes_cluster.list` (Cluster K8s)
- `cmdb_ci_kubernetes_node.list` (Nodi Talos/PVE)
- `cmdb_ci_kubernetes_pod.list` (Pod in esecuzione)

---

## 💾 Stato di Ripristino (AI Save-State)
- **Fase Attiva**: [Fase 1 / Stesura Piano Minimale POC]
- **Ultima Azione Completata**: Redazione del piano di test minimale in `wiki/plans/poc-servicenow-k8s-discovery.md`.
- **Prossimo Passo Operativo**: Attendere conferma dell'utente prima di applicare i manifest YAML K8s o configurare il MID Server.
- **Blocchi/Decisioni Pendenti**: In attesa di via libera dell'utente per l'esecuzione.

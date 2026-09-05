---
title: "Piano: Migrazione Kubernetes di Kubernetes MCP Server"
type: plan
status: active
certified_for_ai: true
created_at: 2026-09-05
tags:
  - "#plan"
  - "#mcp"
  - "#kubernetes"
  - "#toolhive"
  - "#helm"
---

# Piano: Migrazione Kubernetes di Kubernetes MCP Server

Questo documento definisce l'analisi architetturale comparativa e il piano operativo per migrare il server MCP **`kubernetes`** (attualmente eseguito localmente su macOS tramite `npx -y kubernetes-mcp-server` con lettura di `~/.kube/config`) all'interno del cluster homelab GEMINI nel namespace `mcp-system`.

---

## 🗺️ Mappe Concettuali e Relazioni
- [[MCP_Platform]] (Piattaforma federata Kuadrant, ToolHive Operator e Traefik IngressRoute)
- [[mcp-secret-projection-pattern]] (Pattern di Proiezione Segreti & Immutabilità)
- [[Talos_Cluster]] (Cluster Kubernetes Talos target)
- [[SCHEMA]] (Regole del Wiki)

---

## 1. Analisi Architetturale & Risposta sul Pattern

### Possiamo usare lo stesso pattern già usato?
**Sì, assolutamente.** Il server `kubernetes` si inserisce naturalmente nella stessa architettura a micro-servizi standardizzata della flotta MCP:
1. **ToolHive Operator & Project Chart Helm**: il server viene gestito come CRD `MCPServer` in `mcp-system`, esposto su porta interna 8080.
2. **Traefik IngressRoute**: routing TLS standard con certificato wildcard su `kubernetes-mcp-internal.pindaroli.org`.
3. **OPNsense Unbound DNS**: Host Override per risoluzione LAN sul VIP Traefik `10.10.20.56`.
4. **Antigravity Client**: disaccoppiamento totale dal filesystem locale, rimuovendo `npx` e configurando `"serverUrl": "https://kubernetes-mcp-internal.pindaroli.org/mcp"`.

### Vantaggio Architetturale Unico: In-Cluster ServiceAccount vs Kubeconfig SOPS
A differenza dei server esterni (come GitHub, OPNsense o TrueNAS) e di Talos (che dialoga con le API Talos Linux porta 50000), il server Kubernetes opera **direttamente all'interno del cluster Kubernetes che deve gestire**.

Questo apre due opzioni architetturali per la sicurezza:

| Caratteristica | Opzione 1: Native In-Cluster RBAC (Consigliata) | Opzione 2: Kubelet Volume Secret Projection (Archetipo 2) |
| :--- | :--- | :--- |
| **Meccanismo** | ServiceAccount nativo K8s (`kubernetes-mcp-sa`) + `ClusterRoleBinding` | Secret SOPS con file `kubeconfig` proiettato in sola lettura |
| **Segreti SOPS** | **Nessuno** (0 segreti da gestire o cifrare) | 1 secret cifrato (`secrets-sops/kubernetes-mcp-credentials.enc.yaml`) |
| **Scadenza Credenziali** | **Nessuna** (token ruotati automaticamente dal Kubelet) | Dipendente dai certificati client del kubeconfig |
| **Filesystem Immutabile** | 100% nativo (`/var/run/secrets/kubernetes.io/serviceaccount`) | 100% nativo (Volume Secret montato su `/etc/kubernetes/admin.conf`) |
| **Conformità Cloud-Native** | Massima (best practice standard CNCF per pod interni a K8s) | Identico allo schema `talos-mcp` |

---

## 2. Fasi Operative

### Fase 1: Configurazione Permessi RBAC (o Secret SOPS)
- Configurare il `ClusterRoleBinding` per `kubernetes-mcp-sa` in `mcp-system` collegandolo al ruolo amministrativo (o view/edit in base alle preferenze).

### Fase 2: Integrazione Helm Project Chart (`mcp-gateway`)
1. Bump della versione del chart in `helm-charts/mcp-gateway/Chart.yaml` (`0.2.6` → `0.2.7`).
2. Aggiunta della stanza `kubernetes` in `mcp-gateway/mcp-gateway-values.yaml`:
   - ToolHive: `name: kubernetes-mcp`, immagine `ghcr.io/containers/kubernetes-mcp-server:latest`, transport `stdio`, porta `8080`.
   - IngressRoute: `host: kubernetes-mcp-internal.pindaroli.org`.
3. Esecuzione di `helm upgrade mcp-gateway`.
4. Verifica transizione pod a `1/1 Running`.

### Fase 3: Routing Traefik & DNS Unbound
1. Censimento alias `kubernetes-mcp-internal` in `rete.json` e validazione con `validate_network.py`.
2. Registrazione Host Override in OPNsense Unbound DNS via API REST:
   - `kubernetes-mcp-internal.pindaroli.org` $\rightarrow$ `10.10.20.56`.
3. Test risoluzione DNS (`dig`) e test HTTPS Traefik (`curl`).

### Fase 4: Configurazione Client Antigravity
1. Aggiornamento `~/.gemini/antigravity/mcp_config.json`:
   ```json
   "kubernetes": {
     "serverUrl": "https://kubernetes-mcp-internal.pindaroli.org/mcp"
   }
   ```
2. Rimozione di `npx` e della variabile locale `KUBECONFIG`.

### Fase 5: Validazione Test-Driven & Non-Regressione
1. Esecuzione query di test (`namespaces_list`, `pods_list_in_namespace`, `nodes_top`).
2. Test di non-regressione su tutti i 6 server MCP del cluster.

### Fase 6: Consolidamento Documentale
1. Aggiornamento `wiki/entities/MCP_Platform.md` e `todo.md`.
2. Rigenerazione contesto con `validate_network.py` e `build_wiki_context.py`.
3. Commit e push su `main`.

---

## 💾 Stato di Ripristino (AI Save-State)
- **Fase Attiva**: Fase 1: Configurazione RBAC e Template Helm
- **Ultima Azione Completata**: Approvazione utente delle scelte architetturali (Opzione 1 In-Cluster RBAC + Opzione A Immagine Upstream ghcr.io/containers/kubernetes-mcp-server:latest).
- **Prossimo Passo Operativo**: Implementazione template RBAC in `helm-charts/mcp-gateway/templates/rbac.yaml` e bump versione chart a `0.2.7`.
- **Blocchi/Decisioni Pendenti**: Nessuno.

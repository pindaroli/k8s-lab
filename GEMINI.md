# Project GEMINI: Kubernetes Homelab Migration

> [!IMPORTANT]
> **Current Status**: **DNS EXPLICIT MAPPING OPERATIONAL**
> 0.0.0.0 "Black Hole" records removed from Cloudflare; All internal services exclusively managed via OPNsense.
> **Active Goal**: Ingress & External Access (Phase 5).

### 1. Quick Reference & Entry Point
Benvenuti nel Progetto GEMINI. Questa repository utilizza il paradigma **Wiki LLM** per la gestione della conoscenza.

### 🗺️ Mappe Concettuali (Wiki)
- **Governance**: [[purpose]] (Principi Core), [[SCHEMA]] (Regole del Wiki).
- **Infrastruttura**: [[OPNsense]], [[Talos_Cluster]], [[TrueNAS]], [[Traefik]], [[OAuth2_Proxy]].
- **Monitoraggio**: [[Monitoring]], [[Homepage]].
- **Workloads**: [[Servarr]], [[Tdarr]], [[Xray]].
- **Data & Registry**: [[Network_Registry]], [[Storage_Registry]].
- **Procedure**: [[Power_Sequence]] (Shutdown/Startup), [[Certificate_Renewal]].
- **Incidenti**: [[2026-05-03-dns-split-horizon-conflict]], [[2026-05-03-dnsbl-filtering-failure]].

- **Grafi**: [Core Wiki k8s-lab](obsidian://graph?vault=k8s-lab&filter=path:wiki)


---

## 2. Status & Active Goals
- **Current Status**: **DATABASE INFRASTRUCTURE RESTORED** (Instance 3 online).
- **Active Goal**: Ingress & External Access (Phase 5).
- **PVE2 Status**: **OFFLINE** (Hardware Pending) - `postgres-main-2` is currently fenced.

---

## 3. Security & Operational Policies (The Golden Rules)
> [!CRITICAL]
> **EXTERNAL ACCESS**: TUTTI i servizi esposti via Cloudflare **DEVONO** avere OAuth2 abilitato.
> **INTERNAL ACCESS**: I servizi `-internal.pindaroli.org` sono considerati fidati (No OAuth2).
> **INFRASTRUCTURE**: Ogni modifica deve essere **DICHIARATIVA** (Helm/Talos). Vietati i `kubectl patch` manuali.
> **ADDRESSING**: Usare sempre **VIP (Identità Logica)** per Ingress/Accesso Esterno; usare sempre **K8s DNS** per traffico interno. Mai usare IP fisici o hardcoded.
> **EXECUTION PROTOCOL**: Durante l'esecuzione di un piano, per ogni singolo comando/azione: 1. Spiegare COSA sto facendo e PERCHÉ. 2. Aspettare approvazione esplicita. 3. Eseguire e testare il risultato. 4. Aspettare autorizzazione esplicita per il passo successivo. Senza eccezioni.

---

## 4. Operational Cheatsheet
- **Talos Config**: `export TALOSCONFIG=talos-config/talosconfig`
- **Kube Config**: `export KUBECONFIG=talos-config/kubeconfig`
- **Dashboard**: `talosctl dashboard`
- **Backup Manuale**: `velero backup create backup-pre-change-$(date +%F) --wait`

---

## 5. Reference Files
- **Network Source of Truth**: [rete.json](file:///Users/olindo/prj/k8s-lab/rete.json)
- **Ansible Inventory**: `ansible/inventory.ini`
- **Task List**: [todo.md](file:///Users/olindo/prj/k8s-lab/todo.md)

---
> [!NOTE]
> Per una visione completa dell'infrastruttura, aprire questa cartella in **Obsidian** e attivare la **Graph View** filtrando per `path:wiki`.
   ```
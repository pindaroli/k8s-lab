---
title: "Piano: Startup Homelab e Sincronizzazione Uncordon Nodi Talos"
type: plan
status: archived
certified_for_ai: false
archived_at: 2026-10-11
created_at: 2026-10-11
tags:
  - "#plan"
  - "#talos"
  - "#kubernetes"
  - "#ansible"
  - "#proxmox"
  - "#startup"
---

# Piano: Startup Homelab e Sincronizzazione Uncordon Nodi Talos

Questo piano definisce l'implementazione della procedura di avvio orchestrato e deterministico del cluster Kubernetes (Talos OS) e degli hypervisor Proxmox VE (`pve1`, `pve2`, `pve3`), speculare alla procedura di spegnimento a risparmio energetico [[shutdown_to_truenas_only]].

Il piano risolve il problema critico del **disallineamento di carico (thundering herd / valanga di scheduling)** all'avvio, garantendo che i nodi worker non vengano sbloccati singolarmente, ma solo a seguito del superamento di un **Gate di Sincronizzazione (Sync Barrier)**.

---

## 🎯 Obiettivo Architetturale

1. **Simmetria Operativa (Rack Management)**:
   - Fornire il playbook `ansible/playbooks/infrastructure/startup_from_truenas_only.yml` e il relativo wrapper `scripts/infrastructure/startup_from_truenas_only.sh` come controparte ufficiale di `shutdown_to_truenas_only.yml`.
2. **Barriera di Sincronizzazione (All-Ready Barrier Gate)**:
   - Evitare che il primo nodo worker ad avviarsi subisca l'assegnazione del 100% dei pod del cluster.
   - Trattenere lo stato di `cordon` finché **tutti i nodi worker attesi (`talos-cp-01` e `talos-cp-02`) e il control plane (`talos-cp-03`)** non raggiungono simultaneamente la condition `Ready: True`.
3. **Uncordon Atomico e Simultaneo**:
   - Eseguire l'apertura dello scheduling (`kubectl uncordon`) in un unico comando atomico su tutti i nodi contemporaneamente dopo una finestra di grazia di stabilizzazione CNI (Flannel/vxlan).
4. **Preservazione Ruolo Control Plane Puro (`talos-cp-03`)**:
   - Garantire che l'uncordon di `talos-cp-03` rispetti il taint permanente `node-role.kubernetes.io/control-plane:NoSchedule`, lasciando il nodo libero da carichi generici per preservare la convergenza bare-metal su PVE3 (LXC Ollama e LXC Steam).
5. **Riallineamento Immediato di `talos-cp-03`**:
   - Ripristinare lo stato di `talos-cp-03`, attualmente fermo in `SchedulingDisabled`.

---

## 🗺️ Topologia e Mappatura Risorse

| Nodo K8s | Host Proxmox | IP Nodo | VMID | Ruolo nel Cluster | Taint / Scheduling |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **`talos-cp-01`** | `pve1` (`10.10.10.11`) | `10.10.20.141` | `1300` | Worker + Etcd + CP | Schedulabile (Worker Principale) |
| **`talos-cp-02`** | `pve2` (`10.10.10.21`) | `10.10.20.142` | `2300` | Worker + Etcd + CP | Schedulabile (Worker Secondario) |
| **`talos-cp-03`** | `pve3` (`10.10.10.31`) | `10.10.20.143` | `3200` | Pure Control Plane | `control-plane:NoSchedule` (No Pod generici) |

- **Kubernetes VIP**: `10.10.20.55` (Porta API `6443`)
- **Traefik VIP**: `10.10.20.56` (Porte `80`, `443`)
- **Talos API**: Porta `50000`

---

## 📋 Fasi Operative

### FASE 1: Creazione Playbook Ansible di Startup Sincronizzato
- File: `ansible/playbooks/infrastructure/startup_from_truenas_only.yml`
- Task previsti:
  1. **Gate 1 (Hypervisor PVE)**: Verifica connettività SSH e WebUI porta 8006 su `pve1`, `pve2`, `pve3`.
  2. **Gate 2 (Talos API)**: Attesa disponibilità porta `50000` su `10.10.20.141`, `10.10.20.142`, `10.10.20.143`.
  3. **Gate 3 (Kubernetes API VIP)**: Attesa disponibilità API Server K8s `10.10.20.55:6443`.
  4. **Gate 4 (Sync Barrier Nodi Ready)**: Polling ciclico (`until` con timeout) affinché `talos-cp-01`, `talos-cp-02` e `talos-cp-03` risultino contemporaneamente nello stato `Ready`.
  5. **Gate 5 (Stabilizzazione CNI)**: Pause di 10 secondi per permettere la convergenza delle rotte vxlan Flannel e dei DaemonSet.
  6. **Azione Atomica Uncordon**: Esecuzione simultanea:
     ```bash
     kubectl uncordon talos-cp-01 talos-cp-02 talos-cp-03
     ```
  7. **Gate 6 (Health Check Finale)**: Verifica stato Ingress Traefik VIP `10.10.20.56:443` e stato cluster CloudNativePG.

### FASE 2: Creazione Script Wrapper di Esecuzione
- File: `scripts/infrastructure/startup_from_truenas_only.sh`
- Wrapper eseguibile con navigazione deterministica della CWD e invocazione di `ansible-playbook -i ansible/inventory.ini ansible/playbooks/infrastructure/startup_from_truenas_only.yml`.

### FASE 3: Riallineamento a Caldo `talos-cp-03`
- Esecuzione dell'uncordon immediato di `talos-cp-03` per rimuovere lo stato residuo `SchedulingDisabled`, verificando che il taint `node-role.kubernetes.io/control-plane:NoSchedule` rimanga regolarmente attivo.

### FASE 4: Validazione e Test-Driven Execution
- Esecuzione sintassi e check statico del playbook (`ansible-playbook --syntax-check`).
- Test di connettività verso i nodi e simulazione dei task di verifica nodi.

### FASE 5: Consolidamento Documentale & Knowledge Base
- Aggiornamento di `wiki/workflows/Power_Sequence.md` con il riferimento al nuovo script di startup.
- Sincronizzazione di `todo.md` e `GEMINI.md`.
- Rigenerazione contesto Wiki con `build_wiki_context.py`.

---

## 💾 Stato di Ripristino (AI Save-State)
- **Fase Attiva**: Completato (Archiviato)
- **Ultima Azione Completata**: Test end-to-end con esito positivo (15/15 task Ansible ok), uncordon simultaneo e riallineamento `talos-cp-03`, aggiornamento `Power_Sequence.md`, `todo.md` e `GEMINI.md`.
- **Prossimo Passo Operativo**: Nessuno. Procedura pienamente integrata nell'orchestrazione homelab.
- **Blocchi/Decisioni Pendenti**: Nessun blocco.

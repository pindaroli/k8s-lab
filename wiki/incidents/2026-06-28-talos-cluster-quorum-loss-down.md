---
title: "Talos Cluster Quorum Loss & API Server Down"
type: incident
status: active
certified_for_ai: true
date: 2026-06-28
severity: P1
resolved: false
tags:
  - "#incident"
  - "#talos"
  - "#kubernetes"
---

# Incident: Talos Cluster Quorum Loss & API Server Down

**Data**: 2026-06-28
**Status**: ACTIVE (Ongoing)
**Severity**: Critical / P1 (Control Plane down, no API access)

## 🔍 Diagnosi

Durante la verifica dei nuovi puntamenti delle variabili d'ambiente `KUBECONFIG` e `TALOSCONFIG`, l'esecuzione di `kubectl get nodes` è fallita con il seguente errore:

```
Unable to connect to the server: dial tcp 10.10.20.55:6443: connect: host is down
```

L'indirizzo `10.10.20.55` è il Virtual IP (VIP) associato al Control Plane di Kubernetes.

Un controllo dello stato dei servizi sui singoli nodi tramite `talosctl` ha rivelato la seguente situazione:
* **`10.10.20.141` (talos-cp-01)**: Raggiungibile, ma il servizio `etcd` fallisce l'health check:
  `Health check failed: context deadline exceeded`
* **`10.10.20.142` (talos-cp-02)**: Non raggiungibile (`no route to host`).
* **`10.10.20.143` (talos-cp-03)**: Non raggiungibile (`no route to host`).

### Causa Radice

I nodi `talos-cp-02` (ospitato su `pve2`) e `talos-cp-03` (ospitato su `pve3`) sono offline o non raggiungibili a livello di rete. Questo ha causato la perdita del quorum di `etcd` (è attivo solo 1 nodo su 3). 
Senza quorum `etcd`, il Kubernetes API Server sul nodo `talos-cp-01` non può avviarsi, portando al fallimento dell'intero Control Plane e alla disattivazione del VIP `10.10.20.55`.

## 🛠️ Risoluzione (Pianificata)

La risoluzione di questo incidente verrà gestita durante la procedura dedicata al ripristino del cluster Talos. I passi necessari prevedono:
1. Verificare lo stato di alimentazione e connettività dei server Proxmox (`pve2` e `pve3`).
2. Avviare le VM dei nodi `talos-cp-02` e `talos-cp-03`.
3. Verificare che `etcd` ristabilisca il quorum su tutti e tre i nodi.
4. Verificare che il VIP `10.10.20.55` sia di nuovo attivo e che `kubectl get nodes` risponda correttamente.

## 🔗 References
- [[Talos_Cluster]]
- [[opnsense-recovery-and-temporary-routing]]

---
title: "Talos Cluster (Kubernetes Control Plane)"
last_updated: "2026-05-03"
confidence: "High"
tags:
  - "#compute"
  - "#k8s"
  - "#talos"
provenance:
  - "talos-config/controlplane.yaml"
---

# Talos Cluster (Kubernetes)

Il cluster è basato su Talos OS, un sistema operativo immutabile e API-driven per Kubernetes.

## 1. Nodi e Architettura
Il cluster è composto da 3 nodi Control Plane (CP) per garantire l'Alta Affidabilità (HA).

| Nodo | IP | Ruolo | Stato |
| :--- | :--- | :--- | :--- |
| **talos-cp-01** | `10.10.20.141` | Leader / Etcd | **Online** |
| **talos-cp-02** | `10.10.20.142` | Member | **Pending Hardware** (PVE2 Offline) |
| **talos-cp-03** | `10.10.20.143` | Member | **Online** (PVE3) |

- **Virtual IP (VIP)**: `10.10.20.55` (Punto di ingresso per `kubectl`).

## 2. Configurazione DNS
I nodi sono configurati per utilizzare [[OPNsense]] (`10.10.20.254`) come resolver primario. 
- *Azione Storica*: Il 03/05/2026 abbiamo corretto l'IP DNS che puntava erroneamente allo switch L3 (Vedi [[2026-05-03-dns-split-horizon-conflict]]).

## 3. Gestione Etcd
In caso di crash di un nodo (come successo con PVE2), il quorum deve essere mantenuto.
- Se un nodo è offline per lungo tempo, va rimosso dal quorum via API Talos per permettere agli altri di operare.

## Relazioni
- Dipende da [[OPNsense]] per il DNS.
- Utilizza [[TrueNAS]] via NFS per i Persistent Volumes (PV).
- Espone i servizi tramite [[Traefik]].

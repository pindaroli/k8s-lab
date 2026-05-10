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
  - "talos-config/controlplane-cp-01.yaml"
  - "talos-config/controlplane-cp-02.yaml"
  - "talos-config/controlplane-cp-03.yaml"
---

# Talos Cluster (Kubernetes)

Il cluster è basato su Talos OS, un sistema operativo immutabile e API-driven per Kubernetes.

## 1. Nodi e Architettura
Il cluster è composto da 3 nodi Control Plane (CP) per garantire l'Alta Affidabilità (HA).
La configurazione base è `talos-config/controlplane.yaml`.

> [!IMPORTANT]
> **Gestione Identità Nodi (Infrastructure as Code)**
> Per evitare la perdita di identità al riavvio/reinstallazione (che bloccherebbe lo storage locale), l'hostname di ogni nodo è ora codificato in file specifici. **Non usare mai** il file `controlplane.yaml` generico per le installazioni.
>
> Ogni nodo ha il suo file dedicato:
> - **CP-01**: `talos-config/controlplane-cp-01.yaml`
> - **CP-02**: `talos-config/controlplane-cp-02.yaml`
> - **CP-03**: `talos-config/controlplane-cp-03.yaml`
>
> In caso di reinstallazione da zero, la procedura corretta è:
> `talosctl apply-config -n <IP> -f talos-config/controlplane-cp-<XX>.yaml`
>
> (Questo comando imposta correttamente sia l'IP statico che l'Hostname in un unico passaggio).

| Nodo | IP | Ruolo | Stato |
| :--- | :--- | :--- | :--- |
| **talos-cp-01** | `10.10.20.141` | Leader / Etcd | **NotReady** |
| **talos-cp-02** | `10.10.20.142` | Member | **OFFLINE** (PVE2 in manutenzione) |
| **talos-cp-03** | `10.10.20.143` | Member | **NotReady** |
| **talos-7ke-08g** | `...` | Nuovi Nodi | **Ready** |
| **talos-ate-kwz** | `...` | Nuovi Nodi | **Ready** |

> [!CRITICAL]
> **Dipendenza Storage Locale**: Il nodo `talos-cp-02` è ospitato fisicamente sull'hypervisor **PVE2**. Poiché PVE2 è completamente spento per manutenzione hardware, `talos-cp-02` è irraggiungibile. Questo nodo è **fondamentale** perché ospita i dischi di **Local Storage** per il cluster di database `postgres-main` (CloudNativePG). Fino a quando PVE2/talos-cp-02 non tornerà online, il database PostgreSQL non potrà essere schedulato e tutti i servizi dipendenti (es. Lidarr) andranno in CrashLoopBackOff ("Connection Refused").

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

---
title: "Talos Cluster (Kubernetes Control Plane)"
last_updated: "2026-06-06"
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
| **talos-cp-01** | `10.10.20.141` | Leader / Etcd | **Ready** |
| **talos-cp-02** | `10.10.20.142` | Member | **Ready** |
| **talos-cp-03** | `10.10.20.143` | Member | **Ready** |
| **talos-7ke-08g** | `...` | Nuovi Nodi | **Ready** |
| **talos-ate-kwz** | `...` | Nuovi Nodi | **Ready** |

- **Virtual IP (VIP)**: `10.10.20.55` (Punto di ingresso per `kubectl`).

## 2. Configurazione DNS
I nodi sono configurati per utilizzare [[OPNsense]] (`10.10.20.254`) come resolver primario.
- *Azione Storica*: Il 03/05/2026 abbiamo corretto l'IP DNS che puntava erroneamente allo switch L3 (Vedi [[2026-05-03-dns-split-horizon-conflict]]).

## 3. Gestione Etcd
In caso di crash di un nodo (come successo con PVE2), il quorum deve essere mantenuto.
- Se un nodo è offline per lungo tempo, va rimosso dal quorum via API Talos per permettere agli altri di operare.

## 4. Guardia Procedurale (Upgrade Talos)
> [!WARNING]
> **BLOCCO PRE-UPGRADE (CORE-DNS OVERRIDE ATTIVO)**: Prima di aggiornare Talos OS, controllare le Release Notes di Sidero Labs. Se la nuova versione di Talos aggiorna l'immagine di CoreDNS, è **OBBLIGATORIO** aggiornare manualmente il campo `image:` all'interno del blocco `inlineManifests` nei file `talos-config/controlplane-cp-0*.yaml` e fare un `talosctl apply-config` prima di riavviare i nodi.

## 5. Resilienza e Alta Affidabilità (HA)

> [!CAUTION]
> **ANTI-PATTERN: PROXMOX HA DISABILITATO**
> Le VM del Control Plane di Talos (`vm:1300`, `vm:2300`, `vm:3200`) **NON** devono mai essere configurate sotto l'HA Manager di Proxmox VE. 
> 
> *Motivazione*: I dischi virtuali OS e dati (`etcd`) di queste macchine risiedono su storage fisico locale (`local-lvm` / `local-zfs`). Se un host si guasta, Proxmox non può migrare i dischi, causando loop di errore, fallimenti del watchdog e potenziali split-brain.
> L'intera logica di High Availability e quorum è demandata **esclusivamente** a livello applicativo (Kubernetes/Talos "shared-nothing").

## Relazioni
- Dipende da [[OPNsense]] per il DNS.
- Utilizza [[TrueNAS]] via NFS per i Persistent Volumes (PV).
- Espone i servizi tramite [[Traefik]].

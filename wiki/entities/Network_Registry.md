---
title: "Network Registry (rete.json)"
last_updated: "2026-05-03"
confidence: "High"
tags:
  - "#network"
  - "#core"
  - "#dns"
provenance:
  - "rete.json"
---

# Network Registry

Questo nodo del Wiki definisce le **regole** e la **governance** dell'architettura di rete. 

> [!WARNING]
> **SOURCE OF TRUTH**: I dati effettivi risiedono in `rete.json` (nella root del progetto). L'agente IA e l'utente devono modificare `rete.json` per applicare cambiamenti reali. Questo documento serve per capire *come* e *perché* quei dati sono strutturati in quel modo.

## 1. Topologia VLAN
L'infrastruttura è segmentata tramite OPNsense e lo Switch L3 (Xikestor):
- **VLAN 10 (Server)**: `10.10.10.0/24`. Rete di management. Ospita [[TrueNAS]] e le interfacce di gestione di Proxmox. Gateway: `10.10.10.254`.
- **VLAN 20 (Client/K8s)**: `10.10.20.0/24`. Rete operativa. Ospita i nodi del [[Talos_Cluster]] e i dispositivi personali. Gateway: `10.10.20.1`.
- **Transit**: `192.168.2.0/24`. Rete di interconnessione tra OPNsense e Switch L3.

## 2. Regola d'Oro del DNS (Explicit Mapping)
Nel paradigma GEMINI, **non utilizziamo record wildcard (`*.pindaroli.org`) per il traffico interno**.
Ogni volta che si crea un nuovo servizio (es. `nuovo-servizio.pindaroli.org`) ed è gestito da [[Traefik]], DEVE essere aggiunto esplicitamente in `rete.json` sotto il nodo del load balancer.

### Flusso di Automazione (Ansible)
1. Si modifica `rete.json` aggiungendo l'alias.
2. Si esegue il playbook: `ansible-playbook ansible/playbooks/opnsense_sync_dns.yml`.
3. Ansible legge `rete.json` e istruisce **Unbound** su [[OPNsense]] a creare i record di tipo A per risolvere l'indirizzo localmente, evitando il routing su IP pubblici (Split-Horizon).

## Relazioni
- Governa: `rete.json`
- Letto da: Automazioni Ansible.
- Impatta: [[OPNsense]], [[Traefik]], [[Talos_Cluster]].

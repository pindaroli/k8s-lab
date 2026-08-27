---
title: "Network Registry (rete.json)"
last_updated: "2026-08-27"
confidence: "High"
tags:
  - "#network"
  - "#core"
  - "#dns"
provenance:
  - "rete.json"
  - "raw/zx310s-8t2xs/ZX310S-8T2XS.pdf"
  - "incidents/2026-08-22-vlan20-asymmetric-routing-l3-alignment.md"
---

# Network Registry

Questo nodo del Wiki definisce le **regole** e la **governance** dell'architettura di rete.

> [!WARNING]
> **SOURCE OF TRUTH**: I dati effettivi risiedono in `rete.json` (nella root del progetto). L'agente IA e l'utente devono modificare `rete.json` per applicare cambiamenti reali. Questo documento serve per capire *come* e *perché* quei dati sono strutturati in quel modo.

## 1. Topologia VLAN e Routing Simmetrico L3
L'infrastruttura è segmentata tramite lo Switch Core L3 Extreme Networks (X620-10X) e OPNsense (Symmetric Routing):
- **VLAN 10 (Server)**: `10.10.10.0/24`. Rete di management e server. Ospita [[TrueNAS]] e le interfacce di gestione di Proxmox. Gateway logico L3: `10.10.10.1` (Switch Extreme L3). Rotta statica su OPNsense via TRANSIT (`192.168.2.1`).
- **VLAN 20 (Client/K8s)**: `10.10.20.0/24`. Rete operativa. Ospita i nodi del [[Talos_Cluster]] e i dispositivi personali/client. Gateway logico L3: `10.10.20.1` (Switch Extreme L3). Rotta statica su OPNsense via TRANSIT (`192.168.2.1`). Servizio DHCP gestito da Kea su OPNsense tramite **Bootprelay / DHCP Relay**.
- **VLAN 40 (IP Streamer / KVM)**: `10.10.40.0/24`. Rete isolata a bassissima latenza per lo streaming video multicast KVM (AV Access 4KIP100).
- **VLAN 99 (OOB Management)**: `192.168.100.0/24`. Rete Out-of-Band di emergenza per PVE1, PVE2, PVE3 (`nic0`), OPNsense (`igc3` LAN) e TrueNAS.
- **Transit**: `192.168.2.0/24`. Rete punto-a-punto di interconnessione tra OPNsense (`192.168.2.254`), Switch L3 Extreme (`192.168.2.1`) e Switch 2.5G Horaco (`192.168.2.3`).
- **DNS Primario Lab**: `192.168.2.254` (Unbound su OPNsense Transit).

## 2. Regola d'Oro del DNS (Explicit Mapping)
Nel paradigma GEMINI, **non utilizziamo record wildcard (`*.pindaroli.org`) per il traffico interno**.
Ogni volta che si crea un nuovo servizio (es. `nuovo-servizio.pindaroli.org`) ed è gestito da [[Traefik]], DEVE essere aggiunto esplicitamente in `rete.json` sotto il nodo del load balancer.

### Flusso di Automazione (Ansible)
1. Si modifica `rete.json` aggiungendo l'alias.
2. Si esegue il playbook: `ansible-playbook ansible/playbooks/opnsense_sync_dns.yml`.
3. Ansible legge `rete.json` e istruisce **Unbound** su [[OPNsense]] a creare i record di tipo A per risolvere l'indirizzo localmente, evitando il routing su IP pubblici (Split-Horizon).

## 3. Filtraggio DNS (AdBlock / DNSBL)
Il Network Registry contiene anche la lista centralizzata dei domini di tracciamento e telemetria da bloccare in OPNsense tramite wildcard.
- **Percorso**: `opnsense.outbound.blocked-domain`
- **Gestione**: I domini vengono applicati tramite il playbook `ansible/playbooks/opnsense_adblock_automation.yml`.

## 4. Procedure di Backup Configurazione Dispositivi

Per garantire la resilienza e facilitare il disaster recovery, le configurazioni dei dispositivi di rete gestiti devono essere salvate prima di ogni manutenzione fisica in `/Users/olindo/devices-backup/`.

### A. Switch Core Extreme Networks (X620-X10)
*   **IP Gestione**: `192.168.2.1` (VLAN 1 Default / Transit)
*   **Accesso CLI / Automazione**: SSH porta `22` con autenticazione a chiavi (`~/.ssh/id_rsa_extreme`).
*   **Gestione Ansible**: Moduli `extreme.exos` (vedere [[Ansible_Extreme_EXOS]]).
*   **Backup Configurazione EXOS**: `save configuration primary` o esportazione automatizzata via Ansible.

### B. Switch Managed GoodTop (GT-ST024M) e Horaco (ZX-310S-8T2XS)
*   **IP Gestione**: `192.168.2.2` (GoodTop Letto) e `192.168.2.3` (Horaco Server - Sala Server) (VLAN 1).
    *   *Nota*: Lo switch Horaco ZX-310S-8T2XS (`192.168.2.3`) opera come switch principale per le interfacce OOB (Porte 1..5 in Access PBID 1 / VLAN 99), IP Streamer (Porta 8 in Access PBID 2 / VLAN 40), Uplink Trunk verso OPNsense `igc1` (Porta 7) e Downlink Trunk 10G SFP+ verso Extreme Switch (Porta 10).
*   **Architettura Switch Horaco**: Configurato tramite il sistema a Bridge ID (PBID: 1 per OOB, 2 per Streamer) e mapping 802.1Q Single Tag (`ST`) in `Tagged VLAN`.
*   **Procedura Web GUI**:
    1. Andare in `System Tools` -> `Backup/Restore Configuration`.
    2. Cliccare su **`Backup`** per scaricare il file di configurazione `.bin`.

### C. Access Point Cudy AP11000
*   **IP Gestione**: `10.10.20.103` (VLAN 20)
*   **Procedura Web GUI**:
    1. Andare in `System` (o `System Tools`) -> `Backup & Restore`.
    2. Cliccare su **`Backup`** per scaricare la configurazione.

## Relazioni
- Governa: `rete.json`
- Letto da: Automazioni Ansible.
- Impatta: [[OPNsense]], [[Traefik]], [[Talos_Cluster]], [[Ansible_Extreme_EXOS]].

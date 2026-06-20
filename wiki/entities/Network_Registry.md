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

## 3. Filtraggio DNS (AdBlock / DNSBL)
Il Network Registry contiene anche la lista centralizzata dei domini di tracciamento e telemetria da bloccare in OPNsense tramite wildcard.
- **Percorso**: `opnsense.outbound.blocked-domain`
- **Gestione**: I domini vengono applicati tramite il playbook `ansible/playbooks/opnsense_adblock_automation.yml`.

## 4. Procedure di Backup Configurazione Dispositivi

Per garantire la resilienza e facilitare il disaster recovery, le configurazioni dei dispositivi di rete gestiti devono essere salvate prima di ogni manutenzione fisica in `/Users/olindo/devices-backup/`.

### A. Switch Managed ONTi (XikeStor SKS8300-8X)
*   **IP Gestione**: `192.168.2.1` (VLAN 1)
*   **Accesso CLI**: Telnet porta `23` → `telnet 192.168.2.1`

> [!WARNING]
> **CLI Gotcha**: Il firmware ONTi/Realtek NON accetta `configure terminal` (sintassi Cisco standard).
> Il comando corretto per entrare in modalità configurazione è **`config`** (abbreviato).
> ```
> enable
> config          ← corretto
> # configure terminal  ← NON funziona su questo firmware
> ```

> [!IMPORTANT]
> **DHCP Relay & WebGUI Gotchas**:
> * Il comando CLI `no ip helper-address` fallisce con l'errore `failed to delete helper address on active port 67` se il relay è in esecuzione.
> * Per disattivare il DHCP Relay, accedere alla WebGUI (`http://192.168.2.1`), andare in **L3 Features ➔ DHCP Relay ➔ DHCP Relay Config** e impostare **`DHCP Relay Forwarding`** su **`Off`** (Apply). Questo permette ai broadcast DHCP di fluire liberamente a livello L2 verso il DHCP server di OPNsense.

*   **Procedura Web GUI (Config Backup)**:
    1. Andare in `System Config` -> `Management Config` -> `HTTP`.
    2. Impostare `Operation Type` su **`Download`**.
    3. Impostare `File Type` su **`Running Configuration`**.
    4. Cliccare su **`Apply`** per scaricare il file di configurazione.

### B. Switch Managed GoodTop (GT-ST024M) e Horaco (HC-SWTGW218ASHC)
*   **IP Gestione**: `192.168.2.2` (GoodTop Letto) e `192.168.2.3` (Horaco Server - Sala Server) (VLAN 1).
    *   *Nota*: Lo switch LIAGUO (`192.168.2.4`) è stato dismesso, spento e rimosso dalla rete. Lo switch Horaco a `192.168.2.3` (ex Studio) è stato spostato in Sala Server come switch principale per le interfacce OOB e il Trunk LAN.
*   **Nota Software**: Lo switch Horaco (`192.168.2.3`) utilizza attualmente il **firmware di default (OEM)**. Le specifiche dettagliate, la compilazione del firmware open-source alternativo `RTLPlayground` e le metriche di telemetria avanzate sono documentate esclusivamente in `wiki/raw/Specifiche Tecniche HC-SWTGW218AS.md`.
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
- Impatta: [[OPNsense]], [[Traefik]], [[Talos_Cluster]].

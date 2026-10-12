---
title: "Piano: Automazione Wake-on-LAN (WoL) e Accensione Remota dell'Homelab"
type: plan
status: completed
certified_for_ai: true
created_at: 2026-10-12
tags:
  - "#plan"
  - "#networking"
  - "#wol"
  - "#automation"
  - "#proxmox"
  - "#truenas"
  - "#power"
---

# Piano: Automazione Wake-on-LAN (WoL) e Accensione Remota dell'Homelab

Questo piano definisce l'inclusione dichiarativa e centralizzata del meccanismo di **Wake-on-LAN (WoL)** nel repository `k8s-lab`, permettendo l'accensione remota e programmata di tutti i nodi fisici dell'infrastruttura (`pve1`, `pve2`, `pve3`, `truenas`) via software e senza accesso fisico al rack.

Il piano consolida le verifiche empiriche e le configurazioni già applicate sui nodi live, formalizzandole all'interno della *Source of Truth* del progetto (`rete.json`, `wiki/workflows/Power_Sequence.md`, `scripts/network/`).

---

## 🎯 Obiettivo Architetturale

1. **Integrazione nella Procedura di Rack Startup**:
   - Integrare l'accensione via Magic Packet nel workflow canonico [[Power_Sequence]], superando la necessità di premere fisicamente i pulsanti di accensione sui mini PC / server.
2. **Script Centralizzato di Accensione (`scripts/network/wake_node.py`)**:
   - Fornire un'utilità CLI Python autonoma (zero dipendenze esterne, basata su standard library `socket`) che legga i MAC address direttamente da `rete.json` o da argomenti CLI, inviando pacchetti Magic UDP broadcast sulle subnet OOB/Client appropriate.
   - Supportare il risveglio mirato per nodo singolo (`./scripts/network/wake_node.py pve2`) o massivo (`--all`).
3. **Censimento Dichiarativo in `rete.json`**:
   - Registrare formalmente lo stato e le specifiche WoL all'interno della definizione dei nodi fisici in `rete.json` (porta designata, MAC, broadcast subnet).
4. **Allineamento dei Template di Rete**:
   - Aggiornare i file template in `istruzioni/interfaces_pve*.txt` per includere `post-up ethtool -s nic0 wol g`.

---

## 🔍 Stato Attuale e Verifiche Empiriche (Live Baseline)

Tutte le interfacce e i parametri ACPI sono stati ispezionati ed abilitati live sui rispettivi nodi:

| Nodo | Interfaccia Designata WoL | Controller / Driver | MAC Address Target | Subnet / VLAN | Stato Hardware & OS |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **`pve1`** | `nic0` (OOB) | Realtek RTL8125 (`r8169`) | `58:47:ca:7b:d9:3d` | VLAN 99 OOB (`192.168.100.0/24`) | **Abilitato** (`Wake-on: g`, ACPI `GLAN` enabled) |
| **`pve1`** | `nic1` (10G DAC) | Intel X710 (`i40e`) | `3c:fd:fe:05:5e:a0` | VLAN 10 Server | **Abilitato** (`Wake-on: g`, ACPI `GPP0/1` enabled) |
| **`pve2`** | `nic0` (OOB) | Realtek RTL8125 (`r8169`) | `58:47:ca:7c:55:32` | VLAN 99 OOB (`192.168.100.0/24`) | **Abilitato** (`Wake-on: g`, ACPI `GLAN` enabled) |
| **`pve3`** | `nic0` (OOB) | Intel I225/I226 (`igc`) | `c8:ff:bf:05:50:24` | VLAN 99 OOB (`192.168.100.0/24`) | **Abilitato** (`Wake-on: g`)\* |
| **`truenas`** | `enp1s0f0np0` (10G) | Intel X710 (`i40e`) | `8c:fd:18:f7:f5:92` | VLAN 20 Client (LACP bond0) | **Abilitato** (`Wake-on: g`, ACPI `X161` enabled) |
| **`truenas`** | `enp8s0` (2.5G) | Realtek RTL8125 (`r8169`) | `3c:7c:3f:d9:fd:73` | VLAN 99 OOB / Standalone | **Abilitato** (`Wake-on: g`, ACPI `RLAN` enabled) |

*\* Nota PVE3: Il controller 2.5G è abilitato a livello firmware/OS, ma la porta è attualmente scollegata (`NO-CARRIER`). Per utilizzare il WoL su PVE3 è necessario connettere il cavo RJ45 allo switch.*

### Persistenza già applicata sugli Host
- **PVE1, PVE2, PVE3**: Salvata in `/etc/network/interfaces`:
  ```text
  auto nic0
  iface nic0 inet static
      address 192.168.100.x/24
      post-up ethtool -s nic0 wol g
  ```
- **TrueNAS Scale**: Registrata nei task ufficiali di avvio via middlewared:
  ```text
  midclt call initshutdownscript.create '{"type": "COMMAND", "command": "ethtool -s enp8s0 wol g", "when": "POSTINIT", "enabled": true, "timeout": 10, "comment": "Enable WoL on 2.5G nic enp8s0"}'
  ```

---

## 📋 Fasi Operative del Piano

### FASE 1: Scaffolding dello Script Canonico `scripts/network/wake_node.py`
- Sviluppo di uno script autonomo Python (`scripts/network/wake_node.py`) eseguibile sia da Mac che da runner di rete.
- **Funzionalità**:
  - Costruzione ed emissione del payload Magic Packet standard (sincronizzazione `6x 0xFF` + `16x MAC Address`).
  - Broadcast UDP su porta 9 (e porta 7).
  - Selezione automatica o manuale dell'interfaccia/subnet di broadcast:
    - Default OOB VLAN 99: `192.168.100.255`
    - Subnet Client VLAN 20: `10.10.20.255`
  - CLI amichevole con flag `--all`, `--node <nome>`, `--dry-run`, `--list`.

### FASE 2: Censimento Dichiarativo in `rete.json`
- Estensione della struttura JSON in `rete.json` per ciascun nodo fisico:
  ```json
  "wol": {
    "supported": true,
    "enabled": true,
    "primary_interface": "nic0",
    "target_mac": "58:47:ca:7b:d9:3d",
    "broadcast_address": "192.168.100.255",
    "port": 9
  }
  ```
- Allineamento delle verifiche di consistenza in `scripts/network/validate_network.py`.

### FASE 3: Aggiornamento Template Documentali (`istruzioni/`)
- Aggiornamento dei file statici di riferimento per prevenire drift manuali futuri:
  - `istruzioni/interfaces_pve.txt`
  - `istruzioni/interfaces_pve2.txt`
  - `istruzioni/interfaces_pve3.txt`

### FASE 4: Aggiornamento Workflow di Startup nel Wiki ([[Power_Sequence]])
- Modifica del documento `wiki/workflows/Power_Sequence.md`:
  - Sostituzione del passaggio "Accensione Fisica: accendi gli host fisici Proxmox" con l'istruzione formale:
    ```bash
    ./scripts/network/wake_node.py --all
    ```
  - Inserimento dell'ordine di risveglio consigliato (TrueNAS -> attesa storage export -> PVE1/PVE2/PVE3 -> Sync Barrier Talos).

### FASE 5: Validazione Test-Driven & Prerequisiti Hardware
- Esecuzione di un test reale di invio Magic Packet in modalità di monitoraggio (es. `tcpdump -i <iface> port 9`).
- Promemoria di verifica impostazioni BIOS/UEFI sui singoli nodi fisici:
  - **Power On By PCI-E / Wake On LAN**: `Enabled`
  - **ErP / EuP Mode**: `Disabled` (garantisce l'alimentazione 3.3V standby a PC spento).

---

## 🔗 Relazioni & Riferimenti Wiki
- Gestito da: [[Power_Sequence]] (Workflow Safe Shutdown & Startup).
- Source of Truth: `rete.json` ([[Network_Registry]]).
- Dipendenze: Configurazione OOB ([[oob-hardening-validation]]), Switch Extreme EXOS ([[switch_configuration_guide]]).

---
title: "Validazione Ingegneristica e Design del Piano di Accesso Out-of-Band (OOB) (Pragmatic Homelab)"
type: plan
status: archived
certified_for_ai: false
created_at: 2026-06-27
archived_at: 2026-06-27
tags:
  - "#plan"
  - "#network"
  - "#network"
  - "#proxmox"
  - "#opnsense"
---

# Validazione Ingegneristica e Design del Piano di Accesso Out-of-Band (OOB) (Pragmatic Homelab)

> [!IMPORTANT]
> **Stato del Piano**: **VALIDATO ED APPROVATO (ANALISI DEEP SEARCH CONSOLIDATA)**
> Questo documento integra le evidenze emerse dall'analisi approfondita di sicurezza e ingegneria delle reti (Gemini Deep Search) per validare l'architettura **OOB Direct-Connect Fisica su VLAN 99**, consolidando le linee guida per la stabilità e la sicurezza.

**Correzione Fisica Topologia Reale (Source of Truth)**:
*   **Porte Principali 10G**: I tre nodi Proxmox (PVE1, PVE2, PVE3) sono collegati direttamente tramite cavi DAC (Direct Attach Copper) allo switch a 10G **switch10g (ONTi)**.
*   **Porte di Servizio (OOB)**: Le porte OOB fisiche di tutti e tre i nodi (`nic0` su PVE1, `nic0` su PVE2, e la porta OOB di PVE3) **saranno collegate allo switch a 2.5G switch-25g-server (LIAGUO)** in Access VLAN 99. Questa stesura fisica dei cavi fa parte del piano.
*   **Mac Studio**: Posizionato in camera da letto e collegato allo switch **switch-25g-letto (GoodTop)**.

---

## 1. Analisi di Semplificazione per Homelab Privato

L'analisi di validazione conferma che in un Homelab ad accesso privato esclusivo (dove la sicurezza fisica locale è assoluta), l'adozione di controlli di hardening enterprise pesanti (come *Dynamic ARP Inspection*, *DHCP Snooping* e *BPDU Guard*) è **tecnicamente superflua** e comporterebbe un sovraccarico di manutenzione ingiustificato.

Adottiamo quindi un approccio **semplice e robusto**, basato su due soli pilastri ingegneristici:

### A. VLAN 99 Isolata (OOB-Management) ed Immunità DHCP
*   **Segmentazione Layer 2 (IEEE 802.1Q)**: La subnet `192.168.100.0/24` risiede interamente sulla VLAN 99. Poiché tutti i server DHCP attivi (come Kea DHCP su OPNsense) risiedono su altre VLAN (es. VLAN 1 o VLAN 20), i broadcast DHCP (`DHCPDISCOVER`, `DHCPOFFER`) vengono terminati all'interno dei rispettivi segmenti.
*   **Assenza di Race Condition**: Essendo la VLAN 99 priva di server DHCP ed essendo tutti gli endpoint configurati con IP statico, il rischio di instabilità o conflitti di indirizzamento IP è **totalmente azzerato**.

### B. Split-Routing Fisico su macOS (Darwin)
*   **Longest Prefix Match**: Le interfacce VLAN virtuali `vlan0` (VLAN 99) e `vlan1` (VLAN 1) del Mac Studio vengono configurate con IP statici rispettivamente `192.168.100.99/24` e `192.168.2.99/24` lasciando i campi **default gateway (Router)** e **DNS** completamente vuoti.
*   La tabella di routing di macOS (verificabile con `netstat -rn`) presenterà:
    1.  La rotta di default (`default` o `0.0.0.0/0`) associata a `en0` per tutto il traffico internet e inter-VLAN.
    2.  La rotta locale (`192.168.100.0/24`) associata all'interfaccia virtuale `vlan0`.
    3.  La rotta locale (`192.168.2.0/24`) associata all'interfaccia virtuale `vlan1`.
*   Il kernel Darwin, applicando il principio del **Longest Prefix Match**, instraderà in modo deterministico e automatico tutte le richieste destinate a `192.168.100.x` e `192.168.2.x` tramite le interfacce virtuali dedicate, garantendo prestazioni 10G native e stabilità assoluta.
*   **Zero Leak di Broadcast**: Il kernel Darwin elabora e termina i pacchetti di broadcast internamente a livello di stack IP dell'interfaccia virtuale ricevente, **senza eseguire il bridging dei pacchetti** tra le due interfacce (in assenza di configurazioni esplicite di IP Forwarding o Internet Sharing).

---

## 2. Architettura Fisica Semplificata (Multi-Vano)

```text
  [Mac Studio (Camera)]
         │ (Cavo Rame 10G - en0: IP 10.10.20.100 Untagged | vlan99: IP 192.168.100.99 Tagged 99 | vlan1: IP 192.168.2.99 Tagged 1)
         ▼
 ┌──────────────────────┐
 │   switch-25g-letto   │ (Camera da Letto)
 └──────────┬───────────┘
            │
            │ Trunk Link (VLAN 99 Tagged)
            ▼
 ┌──────────────────────┐
 │      switch10g       │ (Core ONTi - Studio)
 └──────────┬───────────┘
            │
            │ Trunk Link (VLAN 99 Tagged)
            ▼
 ┌──────────────────────┐
 │  switch-25g-server   │ (LIAGUO - Sala Server)
 └──┬───┬───┬───┬───────┘
    │   │   │   │  (Access VLAN 99)
    ▼   ▼   ▼   ▼
  [PVE1][PVE2][PVE3][OPNsense igc3]
 (100.11)(100.200)(100.31)(100.1)
```

---

## 3. Le 5 Regole d'Oro per la Configurazione degli Switch

Per garantire il corretto funzionamento ed impedire vulnerabilità latenti, gli switch devono essere configurati seguendo questi 5 criteri minimi essenziali:

1.  **Dichiarazione Statica della VLAN**: La VLAN 99 deve essere creata esplicitamente nel database VLAN di tutti e tre gli switch (`switch10g`, `switch-25g-letto`, `switch-25g-server`). Non affidarsi a meccanismi di propagazione dinamica.
2.  **Configurazione Rigida dei Trunk (802.1Q)**: Sui link inter-switch, la VLAN 99 deve essere aggiunta esplicitamente come **Tagged (Allowed)**. Lasciamo la VLAN 1 nativa untagged per il traffico di gestione standard degli switch, mantenendo la VLAN 99 isolata ed etichettata per prevenire attacchi di *Double Tagging*.
3.  **Configurazione Rigida delle Porte di Accesso e Trunk degli Endpoint**: Le porte collegate alle interfacce OOB dei tre nodi Proxmox devono essere configurate staticamente in modalità **Access VLAN 99** (o PVID 99), mentre la porta del Mac Studio deve essere configurata come **Trunk** (Native 20, Tagged 1, 99).
4.  **Disabilitazione del Dynamic Trunking (DTP)**: Assicurarsi che le porte di accesso non tentino di negoziare dinamicamente i trunk (disabilitare opzioni come "Auto-Trunking" o "Dynamic Port"), forzando lo stato di "Access" puro o "Trunk" statico.
5.  **Isolamento IP degli Switch (NO SVI su VLAN 99 - CRITICO!)**:
    > [!IMPORTANT]
    > **Nessuno dei tre switch deve avere un indirizzo IP logico (SVI / VLAN Interface) configurato sulla VLAN 99**. La gestione degli switch deve rimanere legata ai loro IP attuali sulla VLAN 1 (`192.168.2.x`). Questo garantisce che, anche in caso di teorica compromissione del piano OOB, gli switch non siano in alcun modo attaccabili direttamente su quel segmento.

6.  **Disabilitazione DHCP su OPNsense `igc3` (CRITICO!)**:
    > [!IMPORTANT]
    > L'interfaccia `igc3` (`lan`) di OPNsense ha DHCP abilitato di default sulla subnet `192.168.100.0/24`.
    > **Prima del cablaggio fisico**, disabilitare il servizio DHCP su questa interfaccia dalla Web GUI OPNsense
    > (`Services → Kea DHCP → Interfaces`). Tutti gli endpoint OOB usano IP statici: il DHCP su VLAN 99
    > è indesiderato e potrebbe causare conflitti.

---

## 4. Convalida del Client macOS Sequoia

1.  **Stabilità del MAC address su Ethernet**: macOS Sequoia **non applica alcuna randomizzazione del MAC address** sulle interfacce Ethernet cablate (inclusi gli adattatori USB-to-Ethernet). L'adattatore utilizzerà sempre il suo MAC hardware reale, garantendo stabilità assoluta sulle tabelle CAM degli switch.
2.  **Verifica dello Split-Routing**:
    Lancia il comando sul Mac Studio:
    ```bash
    netstat -rn
    ```
    *Assicurati che la rotta `default` punti al gateway della VLAN 20 (`10.10.20.1`) e che la subnet `192.168.100.0/24` sia associata unicamente all'interfaccia dell'adattatore USB.*
3.  **Verifica dell'IP Forwarding Disabilitato (Anti-Leak)**:
    Esegui il comando sul Mac Studio per assicurarti che il forwarding dei pacchetti sia disattivato di default:
    ```bash
    sysctl net.inet.ip.forwarding
    ```
    *L'output deve essere strettamente:* `net.inet.ip.forwarding: 0`.

---

## 5. Modifica IP e Rete nei Nodi Proxmox (Procedura Corosync Sicura)

Quando si modifica l'IP di gestione o si configura la rete OOB in un cluster Proxmox esistente, la sequenza deve essere rigorosa per evitare il fencing dei nodi dovuto alla perdita di quorum Corosync.

### Procedura passo-passo per ciascun nodo:
1.  **Fermare i servizi del cluster** sul nodo prima di applicare modifiche:
    ```bash
    systemctl stop pve-cluster pvedaemon pveproxy corosync
    ```
2.  **Applicare la nuova configurazione di rete**:
    Edita `/etc/network/interfaces` e applica live senza riavviare tramite `ifupdown2`:
    ```bash
    ifreload -a
    ```
3.  **Aggiornare `/etc/hosts`**:
    Associa il nome host corretto al nuovo IP.
4.  **Allineare `/etc/pve/corosync.conf`**:
    Edita il file `/etc/pve/corosync.conf` su un nodo attivo, aggiorna il `ring0_addr` del nodo modificato con il nuovo IP OOB e **incrementa la direttiva `config_version`** di 1 per propagare la modifica a tutti i membri.
5.  **Riavviare i servizi del cluster**:
    ```bash
    systemctl start pve-cluster corosync pvedaemon pveproxy
    ```

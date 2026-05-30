# PROMPT PER GEMINI DEEP SEARCH (Copia e Incolla - Validazione OOB Fisica Finale)

```text
Valuta e valida dal punto di vista dell'ingegneria delle reti e della sicurezza informatica il seguente piano di accesso Out-of-Band (OOB) "Direct-Connect" per un Homelab basato su Proxmox e Kubernetes. L'homelab è ad uso privato esclusivo dell'amministratore (con accesso fisico protetto), pertanto abbiamo escluso tutti i criteri di hardening enterprise superflui (come DAI, DHCP Snooping, BPDU Guard), concentrandoci solo sull'isolamento L2 essenziale su VLAN 99 e sullo split-routing.

---

## 1. CONTESTO E SPECIFICHE DELL'INFRASTRUTTURA REALE

L'homelab è basato su Proxmox VE 9.1 e Kubernetes (Talos OS) con tre nodi hypervisor. L'obiettivo è configurare una rete OOB altamente disponibile e resiliente che possa funzionare anche in caso di avaria o spegnimento totale di tutti gli hypervisor e di tutte le macchine virtuali/container.

Per questo motivo, abbiamo ESCLUSO l'uso di Bastion Host virtuali su Proxmox, optando per un cablaggio fisico "Direct-Connect" tra il client amministrativo e le porte di servizio dei nodi.

### A. I Nodi Hypervisor (Proxmox VE 9.1)
- **Porte Principali 10G (Dati)**: I tre nodi Proxmox (PVE1, PVE2, PVE3) sono collegati direttamente tramite cavi DAC (Direct Attach Copper) allo switch a 10G **switch10g (ONTi)**.
- **Porte di Servizio (OOB - subnet `192.168.100.0/24`)**:
  - Le tre porte di servizio fisiche dei nodi (`eno3` su PVE1, `nic0` su PVE2, e la porta OOB di PVE3) **saranno collegate allo switch a 2.5G switch-25g-server (LIAGUO)** in sala server. Questo cablaggio fisico fa parte del piano.
  - IP statici dei nodi sulla rete OOB:
    - **PVE1**: `192.168.100.11/24` (Senza Gateway)
    - **PVE2**: `192.168.100.200/24` (Senza Gateway)
    - **PVE3**: `192.168.100.31/24` (Senza Gateway)

### B. I Nodi Client (Stazione di Lavoro)
- **Mac Studio M2 Ultra**: Posizionato fisicamente in camera da letto.
  - Interfaccia Primaria (`en0`): IP statico `10.10.20.100` (VLAN 20 - Client), collegato allo switch della camera **switch-25g-letto (GoodTop)**. Gateway di default: `10.10.20.1` (OPNsense).
  - Interfaccia Secondaria (OOB Dedicata): Un adattatore USB-to-Ethernet fisso da 1G, collegato permanentemente alla Porta 3 del switch della camera **switch-25g-letto**. IP Statico proposto: `192.168.100.99/24` (Senza Gateway e Senza DNS).

### C. La Topologia degli Switch (Multi-Switch Trunked L2/L3)
1. **switch-25g-server (LIAGUO - Sala Server)**:
   - IP Gestione Switch: `192.168.2.3/24` (VLAN 1)
   - Porta 6 (Uplink a switch10g): Trunk con Native VLAN 1, Allowed VLANs: `1, 10, 20, 30, 99 (OOB)`.
   - Porte collegate alle tre porte OOB dei nodi Proxmox: Configurate in **Access VLAN 99** (PVID 99).
2. **switch10g (Core L3 - Studio/Ufficio)**: ONTi ONT-S508cl-8S (XikeStor SKS8300-8X)
   - IP Gestione Switch: `192.168.2.1/24` (VLAN 1)
   - Porte 1 (Verso Switch Server LIAGUO) e 8 (Verso Switch Letto GoodTop) sono in Trunk: Native VLAN 1 (Untagged), Allowed VLANs: `1, 10, 20, 30, 99 (OOB)`.
3. **switch-25g-letto (GoodTop - Camera da letto)**:
   - IP Gestione Switch: `192.168.2.2/24` (VLAN 1)
   - Porta 5 (Uplink a switch10g): Trunk con Native VLAN 1, Allowed VLANs: `1, 10, 20, 30, 99 (OOB)`.
   - Porta 3 (Collegata all'adattatore USB del Mac Studio): Configurata in **Access VLAN 99** (PVID 99).

---

## 2. IL PIANO PROPOSTO (Physical OOB Direct-Connect Plan)

### Architettura L2:
- Utilizzare una VLAN isolata dedicata (**VLAN 99 - OOB-Management**) per trasportare il traffico della subnet `192.168.100.0/24`, escludendo qualsiasi coesistenza logica o SVI con la VLAN 1 nativa o con le VLAN di produzione degli switch.
- Collegare tutte le porte fisiche OOB dei tre nodi Proxmox al switch **switch-25g-server (LIAGUO)** su porte configurate staticamente come **Access VLAN 99 (PVID 99)**.
- Collegare l'adattatore USB Ethernet del Mac Studio a una porta configurata staticamente come **Access VLAN 99 (PVID 99)** sul switch della camera **switch-25g-letto**.
- Mantenere la VLAN 1 nativa standard sui link trunk, aggiungendo semplicemente la VLAN 99 come taggata (`802.1Q`) per connettere i tre switch attraverso la casa.

### Routing & Client (Mac Studio):
- Sul Mac Studio, l'interfaccia principale `en0` gestisce tutto il traffico ordinario e internet tramite gateway `10.10.20.1`.
- L'adattatore USB Ethernet secondario (`192.168.100.99/24`, senza gateway e senza DNS) gestisce lo split-routing a livello di kernel macOS: Sequoia invierà le richieste destinate a `192.168.100.x` localmente tramite l'adattatore USB sulla VLAN 99, garantendo l'accesso SSH/GUI Proxmox ai nodi anche se l'intera produzione o il firewall sono spenti.

---

## 3. DOMANDE PER LA VALIDAZIONE E L'ANALISI (DEEP SEARCH)

Chiedo un'analisi approfondita strutturata sui seguenti punti:

1. **Efficacia di VLAN 99 contro i Conflitti DHCP e Broadcast**:
   - Questo design a VLAN 99 isolata (senza DHCP attivo e con IP statici su tutti gli host) risolve efficacemente i rischi di DHCP broadcast conflicts ed instabilità legati alla coesistenza con VLAN 1 nativa (dove gira Kea DHCP per gli switch)?
   - C'è qualche criticità o rischio residuo di leak di broadcast tra le due interfacce del Mac Studio?

2. **Gestione del Dual-Homing Semplificato su macOS Sequoia/Sonoma**:
   - Qual è il comportamento del kernel Darwin nella gestione di due schede di rete cablate attive contemporaneamente (una in VLAN 20 con gateway e DNS, una in VLAN 99 senza gateway e senza DNS)?
   - macOS Sequoia potrebbe presentare instabilità di routing, routing asimmetrico o problemi di split-routing in questa specifica configurazione semplificata? La randomizzazione del MAC address ("Private Wi-Fi address") ha impatti su interfacce Ethernet USB collegate su porte fisse in Access VLAN 99?

3. **Valutazione della Semplicità rispetto alle Best Practice Homelab**:
   - In un contesto Homelab ad accesso privato esclusivo, la scelta di escludere l'hardening L2 pesante (come DAI, BPDU Guard, DHCP Snooping) in favore della sola segmentazione L2 minima (VLAN 99 isolata) rappresenta un corretto compromesso tra stabilità funzionale, manutenibilità e sicurezza pratica?
   - Quali sono i controlli minimi essenziali sugli switch L2/L3 per garantire la corretta propagazione di VLAN 99?
```

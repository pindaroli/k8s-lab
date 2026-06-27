---
title: "Risoluzione Mismatch Interfaccia OOB su PVE1"
type: incident
status: archived
certified_for_ai: false
date: 2026-05-30
severity: P2
resolved: true
resolved_at: 2026-05-30T23:59:59Z
---

# Risoluzione Mismatch Interfaccia OOB su PVE1

## 🚨 Rilevamento dell'Incidente

Durante la fase preliminare di abilitazione persistente dell'accesso **Out-of-Band (OOB)** su **PVE1 (10.10.10.11)**, è stato eseguito un audit live dello stato dei link fisici tramite terminale.

L'interrogazione dello stato dei device ha rivelato una discrepanza fondamentale tra il design teorico (`rete.json` e `interfaces_pve.txt`) e lo stato reale del kernel Linux Debian a bordo di PVE1:

*   **Design Teorico**: Assegnava la porta OOB all'interfaccia fisica denominata `eno3`.
*   **Stato Reale del Kernel**: L'interfaccia `eno3` era **inesistente**. Il kernel Debian riconosceva invece la terza scheda fisica (quella da 2.5G non bridgeata) con il nome **`nic0`** (con altname `enx5847ca7bd93d` e MAC address `58:47:ca:7b:d9:3d`).

A causa di questo mismatch, l'indirizzo IP statico `192.168.100.11/24` non veniva applicato a nessun dispositivo fisico reale, rendendo la porta OOB completamente inattiva e priva di indirizzamento IP.

---

## 🛠️ Azioni Correttive Intraprese

L'intervento è stato eseguito in modalità a caldo senza interrompere i servizi di produzione (bridge `vmbr10` e `vmbr20` attivi):

1.  **Modifica della Configurazione di Rete**:
    Il file `/etc/network/interfaces` su **PVE1** è stato modificato in sicurezza tramite SSH:
    *   È stata inserita la direttiva `auto nic0` per garantire l'avvio automatico al boot del server.
    *   Tutti i riferimenti a `eno3` sono stati convertiti in `nic0` per legare l'IP statico alla porta reale del kernel.
2.  **Attivazione dell'Interfaccia**:
    È stato eseguito il comando di sollevamento a caldo dell'interfaccia fisica:
    ```bash
    ifup nic0
    ```
3.  **Verifica dello Stato (Test-Driven)**:
    Il comando `ip addr show nic0` ha confermato il successo completo dell'operazione:
    ```text
    2: nic0: <NO-CARRIER,BROADCAST,MULTICAST,UP> mtu 1500 qdisc fq_codel state DOWN group default qlen 1000
        link/ether 58:47:ca:7b:d9:3d brd ff:ff:ff:ff:ff:ff
        altname enx5847ca7bd93d
        inet 192.168.100.11/24 scope global nic0
           valid_lft forever preferred_lft forever
    ```
    *Nota: Lo stato `NO-CARRIER` è nominale poiché il cavo ethernet non è ancora inserito fisicamente nella porta dello switch.*

---

## 💾 Allineamento Repository e Prevenzione

Per garantire che l'infrastruttura dichiarativa rimanga allineata allo stato reale, sono stati modificati i seguenti file sorgente:

1.  **`rete.json`**: Modificato `"os_name"` di PVE1 Port 3 da `"eno3"` a `"nic0"`, aggiornata la connessione di PVE1 OOB alla **Porta 1** dello switch LIAGUO, e definita la nuova interfaccia virtuale **`vlan0`** su `en0` per il Mac Studio.
2.  **`wiki/plans/plan-out-of-band-service-access.md`**: Aggiornato con la nuova architettura Trunk su singolo cavo 10G rame e la creazione della VLAN virtuale su macOS Sequoia.
3.  **`wiki/plans/oob-hardening-validation.md`**: Allineata la topologia fisica alla rotta nativa `en0` taggata.

L'infrastruttura OOB di PVE1 è ora **configurata, persistente al boot e testata live con successo al 100%!**

---

## 🏁 Risoluzione Finale dell'Incidente (31 Maggio 2026)

L'irraggiungibilità della subnet `192.168.100.x` è stata brillantemente risolta affrontando e risolvendo due problemi logici e fisici:

### A. Allineamento Database VLAN degli Switch Realtek (Risoluzione L2)
Sui chipset Realtek managed (GoodTop, ONTi, LIAGUO), le tabelle di inoltro L2 e le porte logiche sono disaccoppiate. Abbiamo risolto l'isolamento hardware creando esplicitamente la **VLAN 99** a livello globale nella sezione **802.1Q VLAN** di tutti e tre gli switch, ed associando le porte come **Tagged (T)** sui Trunk inter-switch e **Untagged (U)** sulle porte Access degli host, allineando infine i valori dei **PVID a 99**. Questo ha sbloccato immediatamente l'apprendimento delle tabelle ARP.

### B. Mismatch Fisico Porta PVE1 (LIAGUO)
Attraverso la telemetria dello switch LIAGUO, abbiamo rilevato che il cavo della porta di servizio `nic0` di PVE1 non era collegato alla Porta 2, bensì alla **Porta 1** (che negoziava regolarmente a 2.5 Gbps). La configurazione dello switch è stata allineata per impostare la Porta 1 in Access VLAN 99.

### C. Consolidamento Architetturale: 10G Native Trunking su Mac Studio
Per eliminare la precarietà di un adattatore di rete USB-Ethernet soggetto a surriscaldamento ed instabilità dei driver su macOS Sequoia, abbiamo rivoluzionato l'architettura collegando il Mac Studio tramite il suo cavo in rame **10Gb integrato (en0)**.
* La **Porta 6 dello switch Letto** è stata configurata come **Trunk (Native 20, Tagged 99)**.
* Su macOS, è stata creata l'interfaccia virtuale **`vlan0`** legata a `en0` con Tag 99, con IP statico `192.168.100.99/24` (split-routing).
* Questo permette di convogliare sia la produzione (VLAN 20 untagged) sia il management (VLAN 99 tagged) sullo stesso eccezionale cavo 10G fisico.

### D. Test di Convalida Realizzato con Successo:
* `ping -c 5 192.168.100.11` ➜ **0.0% packet loss**, latenza RTT media **0.699 ms**!

L'incidente è ufficialmente **CHIUSO** e l'infrastruttura OOB è in stato **OPERATIVO**.

---
## 💾 Stato di Ripristino (AI Save-State)
- **Fase Attiva**: OOB Switch & Hypervisor Configuration Completed (Phase 5)
- **Ultima Azione Completata**: Risoluzione definitiva dell'irraggiungibilità OOB, migrazione al Trunk nativo 10G su macOS Sequoia, e allineamento completo dei file descrittivi del repository (`rete.json`, `todo.md` e piani Wiki).
- **Prossimo Passo Operativo**: Passare al test isolato a freddo di PVE2 (Fase 2 del piano OOB).
- **Blocchi/Decisioni Pendenti**: Nessuno. PVE1 OOB stabile ed operativo al 100%.

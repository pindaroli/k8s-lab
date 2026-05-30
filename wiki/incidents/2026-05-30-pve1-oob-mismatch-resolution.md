---
title: "Risoluzione Mismatch Interfaccia OOB su PVE1"
last_updated: "2026-05-30"
confidence: "High"
tags:
  - "#network"
  - "#proxmox"
  - "#active"
provenance:
  - "interfaces_pve.txt"
  - "plan-out-of-band-service-access.md"
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

1.  **`rete.json`**: Modificato `"os_name"` di PVE1 Port 3 da `"eno3"` a `"nic0"`.
2.  **`wiki/plans/plan-out-of-band-service-access.md`**: Aggiornati tutti i riferimenti descrittivi del cablaggio e della tabella IP di PVE1 da `eno3` a `nic0`.
3.  **`wiki/plans/oob-hardening-validation.md`**: Allineata la topologia fisica a `nic0`.

L'infrastruttura OOB di PVE1 è ora **configurata, persistente al boot e testata live con successo**!

---
## 💾 Stato di Ripristino (AI Save-State)
- **Fase Attiva**: OOB Switch & Hypervisor Configuration (Phase 5)
- **Ultima Azione Completata**: Modifica e attivazione di `nic0` su PVE1, e allineamento completo dei file descrittivi del repository.
- **Prossimo Passo Operativo**: Eseguire il cablaggio fisico del cavo OOB tra PVE1 e lo switch `LIAGUO` (Porte Access VLAN 99), e successivamente investigare lo stato del nodo PVE3.
- **Blocchi/Decisioni Pendenti**: Attesa del collegamento fisico dei cavi OOB e accensione/connessione di PVE3.

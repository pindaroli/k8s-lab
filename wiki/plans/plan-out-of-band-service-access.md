# Piano Preliminare Semplificato: Accesso Out-of-Band (OOB) ed Isolamento di Rete (Pragmatic Homelab)

Questo piano preliminare ha l'obiettivo di configurare la tua rete locale e gli switch per darti un **accesso fisico, diretto e permanente** alle **Porte di Servizio (Out-of-Band - OOB)** di tutti i nodi Proxmox (subnet `192.168.100.0/24`).

**Allineamento Topologia Fisica Reale**:
*   **Porte Principali 10G**: I tre nodi Proxmox (PVE1, PVE2, PVE3) sono collegati direttamente tramite cavi DAC (Direct Attach Copper) allo switch a 10G **switch10g (ONTi)**.
*   **Porte di Servizio (OOB)**: Le porte OOB fisiche di tutti e tre i nodi (`nic0` su PVE1, `nic0` su PVE2, e la porta OOB di PVE3) **saranno collegate allo switch a 2.5G switch-25g-server (LIAGUO)**.
*   **Mac Studio**: Posizionato in camera da letto e collegato allo switch **switch-25g-letto (GoodTop)**.
*   **Cablaggio OOB**: Il collegamento fisico di queste tre porte di servizio al switch LIAGUO **non è ancora stato effettuato ed è parte integrante di questo piano**.

---

## 1. Architettura OOB Semplificata

1.  **VLAN 99 Isolata (OOB-Management)**: La subnet `192.168.100.0/24` risiede sulla VLAN 99. Questo isolamento L2 è essenziale per evitare conflitti di broadcast ed evitare che i client DHCP ordinari ricevano risposte o interferenze dalla rete di produzione.
2.  **No SVI su VLAN 99 (Sicurezza degli Switch)**: **Nessuno degli switch deve avere un indirizzo IP logico (SVI / VLAN Interface) configurato sulla VLAN 99**. La gestione degli switch deve rimanere legata ai loro IP attuali sulla VLAN 1 (`192.168.2.x`). Questo garantisce che gli switch non siano in alcun modo attaccabili direttamente su quel segmento.
3.  **Uplink Trunk Semplici**: La VLAN 99 viene aggiunta come taggata (`802.1Q`) sui cavi di uplink che collegano i tre switch. Non modificheremo la VLAN nativa (lasciamo la default VLAN 1).
4.  **Mac Studio USB Connection**: Il Mac Studio (in camera) si connette alla VLAN 99 tramite un adattatore USB-to-Ethernet economico da 1G, collegato alla **Porta 3** del switch **switch-25g-letto** configurata in **Access VLAN 99 (PVID 99)**.
5.  **Split-Routing macOS**: L'adattatore USB del Mac Studio ha IP statico `192.168.100.99/24` **senza default gateway e senza DNS**. macOS instraderà il traffico `192.168.100.x` localmente sulla porta USB, mentre internet e tutto il resto passeranno sull'interfaccia principale `en0` (VLAN 20).

---

## 2. Schema di Cablaggio ed IP Semplificato

```text
  [Mac Studio (Camera)]
         │ (USB Ethernet Dongle - IP 192.168.100.99 - Access VLAN 99)
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
 └─────┬──────────┬─────┘
       │          │ (Access VLAN 99 - Cavi da collegare in questo piano!)
       ▼          ▼
   [PVE1 OOB]  [PVE2 OOB]  [PVE3 OOB]
  (100.11)     (100.200)    (100.31)
```

| Dispositivo | Interfaccia Fisica | IP Statico OOB | Connessione Switch | Configurazione Porta Switch |
| :--- | :--- | :--- | :--- | :--- |
| **Mac Studio** (Camera) | Adattatore USB-Ethernet 1G | `192.168.100.99/24` | **switch-25g-letto** Porta 3 | **Access VLAN 99** (PVID 99) |
| **PVE1** (Sala Server) | Port 3 (`nic0`) | `192.168.100.11/24` | **switch-25g-server** Port Libera | **Access VLAN 99** (PVID 99) |
| **PVE2** (Sala Server) | Port 3 (`nic0`) | `192.168.100.200/24` | **switch-25g-server** Port Libera | **Access VLAN 99** (PVID 99) |
| **PVE3** (Sala Server) | Port 3 (`nic0`) | `192.168.100.31/24` | **switch-25g-server** Port Libera | **Access VLAN 99** (PVID 99) |

---

## 3. Guida Passo-Passo per l'Esecuzione

### Step 1: Configurazione degli Switch (Creazione VLAN 99)
1.  Entra nella Web GUI dei tuoi tre switch:
    *   `switch10g (ONTi)` -> `http://192.168.2.1` **[x] (VLAN 99 & TRUNK COMPLETATI - 2026-05-30)**
    *   `switch-25g-letto (GoodTop)` -> `http://192.168.2.2` **[x] (VLAN 99 & TRUNK COMPLETATI - 2026-05-30)**
    *   `switch-25g-server (LIAGUO)` -> `http://192.168.2.3` **[x] (VLAN 99 & TRUNK COMPLETATI - 2026-05-30)**
2.  Crea la **VLAN 99** (Nome: `OOB`) su tutti e tre gli switch.
3.  **Configura i Trunk**:
    *   Aggiungi **VLAN 99** come **VLAN taggata (Tagged)** sui link trunk di interconnessione:
        *   Porta 1 e 8 su **switch10g (ONTi)**.
        *   Porta 5 su **switch-25g-letto (GoodTop)**.
        *   Porta 6 su **switch-25g-server (LIAGUO)**.
4.  **Configura le Porte di Accesso**:
    *   Sullo switch della stanza da letto (`switch-25g-letto`):
        *   Imposta la **Porta 3** (adattatore USB Mac Studio) in modalità **Access VLAN 99** (PVID 99).
    *   Sullo switch della sala server (`switch-25g-server`):
        *   Associa **3 porte libere a tua scelta** in modalità **Access VLAN 99** (PVID 99). Queste saranno le porte dedicate a ricevere i cavi delle tre porte di servizio dei nodi.
5.  **Verifica Importante**: Assicurati che **nessuno** degli switch abbia configurato un IP virtuale sulla VLAN 99 (lascia vuoto/disabilitato l'interfaccia VLAN 99).

---

### Step 2: Cablaggio Fisico delle Porte OOB (Il Cuore del Piano)
Ora procediamo a stendere i cavi fisici per connettere le porte di servizio:

1.  **Cablaggio PVE1**: Collega un cavo ethernet dalla **Porta 3 (`nic0`)** di PVE1 ad una delle porte configurate su **Access VLAN 99** del switch **switch-25g-server (LIAGUO)**.
2.  **Cablaggio PVE2**: Collega un cavo ethernet dalla **Porta 3 (`nic0`)** di PVE2 ad un'altra porta configurata su **Access VLAN 99** del switch **switch-25g-server (LIAGUO)**.
3.  **Configurazione PVE3 (Stato OOB-Esclusivo - Bootstrap Mode)**:
    *   Applica la configurazione temporanea in `istruzioni/interfaces_pve3.txt` (che assegna le VLAN di produzione 10/20 alle schede fittizie `dac1`/`dac2` e la porta OOB `192.168.100.31/24` all'interfaccia fisica reale `nic0`).
    *   Collega un cavo ethernet dalla porta fisica **`nic0` (Porta 3)** di PVE3 ad una delle porte configurate su **Access VLAN 99** del switch **switch-25g-server (LIAGUO)**.
    *   *Perché*: Ti permette di avviare il nodo ed amministrarlo interamente via OOB, bypassando temporaneamente il cablaggio e i problemi delle porte 10G.

---

### Step 3: Configurazione dell'adattatore USB su Mac Studio e Convalida
1.  Inserisci l'adattatore USB-to-Ethernet nel Mac Studio e collegalo alla **Porta 3** dello switch **switch-25g-letto** in camera.
2.  Apri il terminale del Mac Studio ed individua il nome della scheda USB Ethernet (es. `en3` o `en4`):
    ```bash
    networksetup -listallhardwareports
    ```
3.  Configura l'IP statico split-routing senza gateway e senza server DNS:
    ```bash
    # Sostituisci "USB 10/100/1000 LAN" con il nome esatto rilevato al punto precedente se diverso

    # 1. Imposta IP statico (Gateway vuoto)
    sudo networksetup -setmanual "USB 10/100/1000 LAN" 192.168.100.99 255.255.255.0 ""

    # 2. Svuota i DNS
    sudo networksetup -setdnsservers "USB 10/100/1000 LAN" "Empty"
    ```
4.  **Audit e Verifica Ingegneristica (dal Mac Studio in Camera)**:
    *   **Verifica dello Split-Routing**:
        Lancia `netstat -rn` ed assicurati che la rotta `default` punti a `10.10.20.1` (en0) e che la subnet `192.168.100.0/24` sia associata all'interfaccia dell'adattatore USB.
    *   **Verifica dell'IP Forwarding Disabilitato (Anti-Leak)**:
        Esegui `sysctl net.inet.ip.forwarding`. L'output deve essere `0`.

---

### Step 4: Test Isolato di PVE2 (In Esecuzione Remota)
Poiché PVE2 si trova connesso al switch LIAGUO e la tua rete OOB è propagata in VLAN 99, puoi fare il test a distanza direttamente dalla camera da letto!

1.  Accendi PVE2 fisicamente.
2.  Dal tuo Mac Studio in camera da letto, esegui il ping a PVE2:
    ```bash
    ping 192.168.100.200
    ```
3.  Apri il browser su `https://192.168.100.200:8006`, accedi alla GUI Proxmox come root e valida lo stato hardware (RAM 64GB, dischi).
4.  Una volta validato, spegni PVE2: `ssh root@192.168.100.200 "shutdown -h now"`.
5.  Lascia PVE2 cablato ed alloggiato nella sua posizione nel rack; ora fa parte permanentemente dell'infrastruttura OOB!

---

## 4. Verifica di Funzionamento Finale

Esegui questi ping veloci dal Mac Studio (in Camera) per confermare il funzionamento complessivo attraverso gli switch della casa:
*   [ ] `ping -c 2 192.168.100.11` (PVE1)
*   [ ] `ping -c 2 192.168.100.200` (PVE2)
*   [ ] `ping -c 2 192.168.100.31` (PVE3, se configurato)

Hai finito! Ora hai un canale di amministrazione fisica OOB totalmente isolato, sicuro e ultra-semplice!

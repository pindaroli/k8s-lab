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
4.  **Mac Studio Single Link Trunk**: Il Mac Studio (in camera) si connette alla VLAN 99 tramite la sua interfaccia fisica nativa 10G **en0**. A livello di switch, la porta è configurata come Trunk (Native 20, Tagged 99). A livello di macOS, viene creata un'interfaccia VLAN virtuale associata a `en0`.
5.  **Split-Routing macOS su VLAN Virtuale**: L'interfaccia virtuale `vlan99` (legata a `en0` su Tag 99) ha IP statico `192.168.100.99/24` **senza default gateway e senza DNS**. macOS instraderà il traffico `192.168.100.x` su questa scheda virtuale, mentre internet e tutto il resto passeranno sull'interfaccia fisica principale `en0` (VLAN 20 Untagged).

---

## 2. Schema di Cablaggio ed IP Semplificato

```text
  [Mac Studio (Camera)]
         │ (Cavo Rame 10G - en0: IP 10.10.20.100 Untagged | vlan99: IP 192.168.100.99 Tagged 99)
         ▼
 ┌──────────────────────┐
 │   switch-25g-letto   │ (Camera da Letto)
 └──────────┬───────────┘
            │
            │ Trunk Link (VLAN 99 Tagged)
            ▼
 ┌──────────────────────┐
 │      switch10g       │ (Core ONTi - Sala Server)
 └──┬──────────┬──────┘
    │             │ Trunk Link (VLAN 99 Tagged)
    │             ▼
    │  ┌──────────────────────┐
    │  │  switch-25g-server   │ (LIAGUO - Sala Server)
    │  └──┬───┬───┬───┬───────┘
    │     │   │   │   │  (Access VLAN 99)
    │     ▼   ▼   ▼   ▼
    │ [PVE1][PVE2][PVE3][OPNsense igc3]
    │ (100.11)(100.200)(100.31)(100.1)
    │
    │  [PLANNED] Porta 5 LIAGUO → [KVM Extender (100.x)]
    │  [PLANNED] Porta 4 ONTi  → [OPNsense igc1 Trunk]
    │
    └───► [OPNsense igc1 via SFP+ transceiver - PLANNED]
```

| Dispositivo | Interfaccia Fisica | IP Statico OOB | Connessione Switch | Configurazione Porta Switch |
| :--- | :--- | :--- | :--- | :--- |
| **Mac Studio** (Camera) | en0 (Virtual interface `vlan99`) | `192.168.100.99/24` | **switch-25g-letto** Porta 6 | **Trunk (Native 20, Tagged 99)** |
| **PVE1** (Sala Server) | Port 3 (`nic0`) | `192.168.100.11/24` | **switch-25g-server** Porta 1 | **Access VLAN 99** (PVID 99) |
| **PVE2** (Sala Server) | Port 3 (`nic0`) | `192.168.100.200/24` | **switch-25g-server** Porta 2 | **Access VLAN 99** (PVID 99) |
| **PVE3** (Sala Server) | Port 3 (`nic0`) | `192.168.100.31/24` | **switch-25g-server** Porta 3 | **Access VLAN 99** (PVID 99) |
| **OPNsense** | `igc3` (interfaccia `lan`) | `192.168.100.1/24` | **switch-25g-server** Porta 4 | **Access VLAN 99** (PVID 99) |
| **KVM Extender** *(PLANNED)* | RJ45 nativo | `192.168.100.x` (TBD) | **switch-25g-server** Porta 5 | **Access VLAN 99** (PVID 99) |

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
4.  **Configura le Porte di Accesso e Trunk**:
    *   Sullo switch della stanza da letto (`switch-25g-letto`):
        *   Riconfigura la **Porta 6** (Mac Studio 10G) in modalità **Trunk** con **Native VLAN = 20** (PVID 20) e **Tagged VLAN = 99** (o `10-30;99`). La Porta 3 può essere liberata.
    *   Sullo switch della sala server (`switch-25g-server`):
        *   Associa **Porta 1 (PVE1 OOB)**, **Porta 2 (PVE2 OOB)** e **Porta 3 (PVE3 OOB)** in modalità **Access VLAN 99** (PVID 99).
        *   Riconfigura **Porta 4** (precedentemente Free) in modalità **Access VLAN 99** (PVID 99) per OPNsense `igc3`.
5.  **Verifica Importante**: Assicurati che **nessuno** degli switch abbia configurato un IP virtuale sulla VLAN 99 (lascia vuoto/disabilitato l'interfaccia VLAN 99).

---

### Step 2: Cablaggio Fisico delle Porte OOB (Il Cuore del Piano)
Ora procediamo a stendere i cavi fisici per connettere le porte di servizio:

1.  **Cablaggio PVE1**: Collega un cavo ethernet dalla **Porta 3 (`nic0`)** di PVE1 alla **Porta 1** (Access VLAN 99) del switch **switch-25g-server (LIAGUO)**.
2.  **Cablaggio PVE2**: Collega un cavo ethernet dalla **Porta 3 (`nic0`)** di PVE2 alla **Porta 2** (Access VLAN 99) del switch **switch-25g-server (LIAGUO)**.
3.  **Configurazione PVE3 (Stato OOB-Esclusivo - Bootstrap Mode)**:
    *   Applica la configurazione temporanea in `istruzioni/interfaces_pve3.txt` (che assegna le VLAN di produzione 10/20 alle schede fittizie `dac1`/`dac2` e la porta OOB `192.168.100.31/24` all'interfaccia fisica reale `nic0`).
    *   Collega un cavo ethernet dalla porta fisica **`nic0` (Porta 3)** di PVE3 alla **Porta 3** (Access VLAN 99) del switch **switch-25g-server (LIAGUO)**.
    *   *Perché*: Ti permette di avviare il nodo ed amministrarlo interamente via OOB, bypassando temporaneamente il cablaggio e i problemi delle porte 10G.

---

### Step 3: Configurazione della VLAN su Mac Studio e Convalida
1.  Sul Mac Studio, configuriamo la VLAN virtuale `vlan99` legata all'interfaccia fisica `en0` con Tag 99.
2.  Apri il terminale del Mac Studio ed esegui i comandi di creazione:
    ```bash
    # 1. Crea l'interfaccia virtuale vlan99 legata a en0 con tag 99
    sudo networksetup -createVLAN vlan99 en0 99

    # 2. Imposta l'IP statico (senza gateway e senza DNS per mantenere lo split-routing)
    sudo networksetup -setmanual vlan99 192.168.100.99 255.255.255.0 ""
    ```
3.  **Audit e Verifica Ingegneristica (dal Mac Studio in Camera)**:
    *   **Verifica dello Split-Routing**:
        Lancia `netstat -rn` ed assicurati che la rotta `default` punti a `10.10.20.1` (en0) e che la subnet `192.168.100.0/24` sia associata all'interfaccia virtuale `vlan99`.
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
*   [ ] `ping -c 2 192.168.100.1` (OPNsense `igc3`)
*   [ ] `ping -c 2 192.168.100.11` (PVE1)
*   [ ] `ping -c 2 192.168.100.200` (PVE2)
*   [ ] `ping -c 2 192.168.100.31` (PVE3)

> [!NOTE]
> Ricordare di disabilitare il DHCP sull'interfaccia `lan` di OPNsense (`igc3`) prima del cablaggio.
> Il server DHCP attivo su quella subnet potrebbe altrimenti inviare offerte indesiderate ai nodi PVE sulla VLAN 99.

---

## 5. Migrazione OPNsense igc1 su ONTi (PLANNED) + Aggiunta KVM Extender

Per poter collegare il KVM Extender alla Porta 5 del LIAGUO, è necessario prima spostare il trunk LAN
di OPNsense (`igc1`) dalla Porta 5 del LIAGUO alla **Porta 4 di switch10g (ONTi)**.

> [!IMPORTANT]
> **Prerequisito**: Acquistare un transceiver **SFP+ to RJ45 Multi-Gig (2.5G/10G)** compatibile con ONTi (es. FS.com, circa 30-35€).

### Step A — Riconfigurare ONTi Porta 4
- Porta 4 di `switch10g`: da `Access VLAN 1` → `Trunk` (Native 1, Tagged 10/20/30)

### Step B — Migrare il cavo di OPNsense `igc1`
1. Spegni qualsiasi servizio sensibile (opzionale ma consigliato).
2. Scollega il cavo da **LIAGUO Porta 5** (attuale LAN trunk OPNsense).
3. Inserisci il **transceiver SFP+ RJ45** nella Porta 4 di ONTi.
4. Collega il cavo a **ONTi Porta 4**.
5. Verifica che OPNsense recuperi immediatamente la connettività (nessuna modifica di config è necessaria su OPNsense).

### Step C — Riconfigurare LIAGUO Porta 5 e collegare KVM
- Porta 5 di `switch-25g-server`: da `Trunk` → `Access VLAN 99` (PVID 99)
- Collega il **KVM Extender** alla Porta 5 del LIAGUO.
- Assegna IP statico al KVM: `192.168.100.x` (scegliere IP libero nella subnet).

### Step D — Verifica finale
```bash
# Dal Mac Studio via vlan99
ping -c 2 192.168.100.x    # KVM Extender
ping -c 2 192.168.100.1    # OPNsense igc3 (deve ancora rispondere)
ping -c 2 10.10.20.1       # Gateway VLAN 20 (verifica LAN non interrotta)
```

Hai finito! Ora hai un canale di amministrazione fisica OOB totalmente isolato, sicuro e ultra-semplice, con accesso diretto anche al firewall!

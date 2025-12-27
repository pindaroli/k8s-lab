# Guida Configurazione Routing L3 (Switch + OPNsense)

Questa guida dettaglia i parametri esatti da inserire.

## 0. PREPARAZIONE (Bunker Anti-Disconnessione)
> **Obiettivo**: Non restare chiusi fuori durante il cambio di configurazione.

1.  **Connessione Fisica**:
    -   Collega il tuo PC via cavo ethernet a una porta libera dello **Switch Managed** (es. Port 3, 4, 5).
    -   **NON** collegarti allo "switch stupido" (diventerà Internet diretto / WAN).
2.  **IP Statico sul PC**:
    -   Il DHCP smetterà di funzionare durante il riavvio di OPNsense.
    -   Imposta manualmente sul tuo PC:
        -   **IP**: `192.168.100.99` (Se collegato a igc3)
        -   **Subnet**: `255.255.255.0`
        -   **Gateway**: `192.168.100.1`
    -   *Così rimani connesso allo Switch e a Proxmox anche se OPNsense si riavvia.*

---

## 1. SWITCH MANAGED (ONTi)
> **Obiettivo**: Lo switch diventa il Gateway per le VLAN 10 e 20.

### A. Impostazione Interfacce VLAN (L3)
Vai nel menu **VLAN Interface** (o "Layer 3 Interface"):
1.  **VLAN 10**:
    -   **IP Address**: `10.10.10.1`
    -   **Subnet Mask**: `255.255.255.0` (o `/24`)
    -   **Status**: Enable
2.  **VLAN 20**:
    -   **IP Address**: `10.10.20.1`
    -   **Subnet Mask**: `255.255.255.0` (o `/24`)
    -   **Status**: Enable
3.  **VLAN 1** (Management/Transit):
    -   **IP Address**: `192.168.2.1` (VLAN 1 Switch)
    -   **Subnet Mask**: `255.255.255.0`

### B. Rotta di Default (Per Internet)
Vai nel menu **Routing** > **Static Route**:
-   **Destination**: `0.0.0.0`
-   **Mask**: `0.0.0.0`
-   **Next Hop (Gateway)**: `192.168.2.254` (IP OPNsense su Transit)
-   *Significato*: "Se non conosci la destinazione, chiedi a OPNsense sulla rete di transito".

---

## 2. OPNSENSE (Firewall)
> **Obiettivo**: OPNsense deve avere una gamba sulla rete 192.168.2.x per parlare con lo switch.

### A. Configura Interfaccia
Vai su **Interfaces** -> **Assignments** (o usa un'interfaccia esistente se c'è):
-   **IP Address**: `192.168.2.254` (su interfaccia TRANSIT/igc1)
-   **Subnet**: `/24` (255.255.255.0)
    -   *Nota*: Questa interfaccia TRANSIT (igc1) collega lo switch.
    -   La porta `igc3` (ADMIN) avrà IP `192.168.100.1` per emergenza.

### B. Modifica IP Interfacce VLAN (Evitare Conflitti)
> **Critico**: Ora che lo Switch è `10.10.10.1` e `10.10.20.1`, OPNsense **NON** può avere gli stessi IP.
1.  Vai su **Interfaces** -> **[VLAN10]**:
    -   Cambia IP a `10.10.10.254`.
2.  Vai su **Interfaces** -> **[VLAN20]**:
    -   Cambia IP a `10.10.20.254`.
    -   *Serve solo affinché il servizio DHCP possa ascoltare/ricevere il Relay.*

---

## 10. Impostazione SSH Key su Switch (Bonus)
Per accedere allo switch senza password usando la tua chiave SSH Mac/Linux.

1.  Entra nello switch via Telnet/SSH/Console.
2.  Dai questi comandi:
    ```bash
    configure terminal
    ip ssh public-key
    username admin key-string ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIHfqmzsseaahUk4JlArzctgrXR7+Zt3cpJpOLQfA+PUA
    exit
    exit
    ```
    *(Nota: La sintassi esatta potrebbe variare leggermente a seconda del firmware (es. `ip ssh pubkey-chain`). Se fallisce, prova la variante Cisco standard)*.

---

### B. Crea Gateway
Vai su **System** -> **Gateways** -> **Configuration**:
-   **Name**: `SWITCH_L3`
-   **Interface**: (Seleziona quella con IP 192.168.2.254)
-   **IP Address**: `192.168.2.1` (IP dello Switch)
-   **Monitor IP**: `192.168.2.1`

### C. Rotte Statiche
Vai su **System** -> **Routes** -> **Configuration**:
1.  **Route 1 (Server)**:
    -   **Network**: `10.10.10.0/24`
    -   **Gateway**: `SWITCH_L3`
2.  **Route 2 (Client)**:
    -   **Network**: `10.10.20.0/24`
    -   **Gateway**: `SWITCH_L3`

### D. Outbound NAT (CRITICO / NO INTERNET FIX)
> **Problema**: Senza questo, i pacchetti escono verso Internet ma non sanno come tornare indietro perché OPNsense non fa NAT per 10.10.x.x in automatico.
1.  Vai su **Firewall** -> **NAT** -> **Outbound**.
2.  Imposta **Mode**: `Hybrid outbound NAT rule generation`.
3.  Clicca **Save**.
4.  Clicca **Add** (Freccia in su) per aggiungere una regola **in cima**:
    -   **Interface**: `WAN`.
    -   **Source Address**: `10.10.0.0/16` (o crea un Alias per le tue VLAN).
        *   *Alternativa*: Fai due regole, una per `10.10.10.0/24` e una per `10.10.20.0/24`.
    -   **Translation / Target**: `Interface address`.
    -   **Description**: `NAT for VLANs behind L3 Switch`.
5.  **Save** & **Apply Changes**.

### E. Firewall Rules (IMPORTANTE)
Vai su **Firewall** -> **Rules** -> (Interfaccia 192.168.2.x):
-   Aggiungi una regola PASS in cima:
    -   **Destination**: `Any`

---

## 4. Configurazione Network Proxmox
> **Obiettivo**: Configurare le interfacce di rete dei nodi Proxmox in coerenza con `rete.json`.

Ecco i file di configurazione `/etc/network/interfaces` da usare.

**1. File per PVE (Nodo 1 - 10.10.10.11)**
`vim /etc/network/interfaces`:
```auto
auto lo
iface lo inet loopback

iface eno1 inet manual
# Porta 1 (VLAN 10 - Server)

iface eno2 inet manual
# Porta 2 (VLAN 20 - Client)

# -----------------------------------------------------------
# PORTA DI SERVIZIO (DIRECT ACCESS)
# -----------------------------------------------------------
auto eno3
iface eno3 inet static
    address 192.168.99.2/24
    # NESSUN GATEWAY. Collega PC con IP 192.168.99.10

# -----------------------------------------------------------
# BRIDGE MANAGEMENT & SERVER (VLAN 10)
# -----------------------------------------------------------
auto vmbr10
iface vmbr10 inet static
    address 10.10.10.11/24
    gateway 10.10.10.1
    bridge-ports eno1
    bridge-stp off
    bridge-fd 0

# -----------------------------------------------------------
# BRIDGE CLIENT (VLAN 20)
# -----------------------------------------------------------
auto vmbr20
iface vmbr20 inet manual
    bridge-ports eno2
    bridge-stp off
    bridge-fd 0
```

**2. File per PVE2 (Nodo 2 - 10.10.10.12)**
`vim /etc/network/interfaces`:
```auto
auto lo
iface lo inet loopback

# -----------------------------------------------------------
# NODO: PVE2 (Node 2) - IP: 10.10.10.12
# -----------------------------------------------------------

iface eno1 inet manual
# Porta 1 (VLAN 10 - Server)

iface eno2 inet manual
# Porta 2 (VLAN 20 - Client)

# -----------------------------------------------------------
# BRIDGE MANAGEMENT & SERVER (VLAN 10)
# -----------------------------------------------------------
auto vmbr10
iface vmbr10 inet static
    address 10.10.10.12/24
    gateway 10.10.10.1
    bridge-ports eno1
    bridge-stp off
    bridge-fd 0

# -----------------------------------------------------------
# BRIDGE CLIENT (VLAN 20)
# -----------------------------------------------------------
auto vmbr20
iface vmbr20 inet manual
    bridge-ports eno2
    bridge-stp off
    bridge-fd 0
```



---

## 5. Gateway Transit (192.168.2.254)
> **Obiettivo**: OPNsense ha la porta `igc1` collegata allo switch. Deve fare da Gateway per la rete 192.168.2.x.

### A. OPNSENSE (TRANSIT Interface)
1.  Vai su **Interfaces** -> **Assignments**.
2.  Crea una nuova interfaccia assegnata a **`igc1`** (se non c'è già, es. OPT4).
3.  Chiamala **TRANSIT**.
4.  Abilita, IPv4 Static: **`192.168.2.254` / 24**.
3.  **Mode**: `IP Alias`.
4.  **Interface**: `TRANSIT` (Interfaccia su igc1).
5.  **Address**: `192.168.2.254` / `24`.
6.  **Description**: `Gateway Transit Switch`.
7.  **Salva e Applica**.

### B. Verifica
### B. Verifica
Collegati alla porta **ADMIN_LAN** (igc3) per gestire OPNsense su `192.168.100.1`.
I server e gli switch continueranno a usare `192.168.2.1` e `192.168.2.254` sulla rete di transito.

---


## 6. Configurazione Hardware OPNsense (Mini PC)
> **Nota**: OPNsense è installato su Mini PC fisico dedicato (4x 2.5GbE).

### A. Accesso Console
Per accedere alla console (menu testuale) hai due opzioni:
1.  **Fisica**: Collega un Monitor (HDMI) e una Tastiera USB direttamente al Mini PC.
2.  **Seriale (Se disponibile)**: Se il Mini PC ha una porta Console/Serial, usa un cavo console.
3.  **SSH**: Se hai abilitato SSH e conosci l'IP (es. `192.168.2.254` o `10.10.x.254`).

### B. Mappatura Porte (Tipica per 4 porte)
Assicurati di identificare correttamente le porte `igc0`, `igc1`, ecc.
*   **WAN**: Solitamente la prima porta (`igc0` o `eth0`).
*   **LAN**: Solitamente la seconda porta (`igc1` o `eth1`).
*   Verifica sempre collegando/scollegando il cavo e osservando la console ("link up/down").


## 7. Configurazione TrueNAS Scale (VM su Proxmox)
> **Obiettivo**: TrueNAS (Virtualizzato) deve avere "tre gambe": Management, Server e Client.

### A. Proxmox Hardware (VM Settings)
Invece di complicarci la vita con le VLAN dentro TrueNAS, diamo alla VM tre schede di rete virtuali collegate ai bridge che abbiamo appena creato.

1.  **Spegni** la VM TrueNAS.
2.  Vai su **Hardware** della VM.
3.  Aggiungi/Verifica le schede di rete:
    *   `net0` (Management): Collegata a **`vmbr0`** (192.168.1.x).
    *   `net1` (Server): Aggiungi Network Device -> Bridge **`vmbr10`**.
    *   `net2` (Client): Aggiungi Network Device -> Bridge **`vmbr20`**.
4.  **Accendi** la VM.

### B. TrueNAS GUI (Network)
1.  Vai su **Network** -> **Interfaces**.
2.  Vedrai tre interfacce fisiche (es. `enp0s1`, `enp0s2`...).
    *   *Nota: Non devi creare VLAN qui, perché per la VM il traffico arriva già pulito dal bridge.*
3.  **Configura IP Server (VLAN 10)**:
    -   Seleziona la scheda corrispondente a `vmbr10`.
    -   **DHCP**: No.
    -   **IP Address**: `10.10.10.250` / `24`.
4.  **Configura IP Client (VLAN 20)**:
    -   Seleziona la scheda corrispondente a `vmbr20`.
    -   **DHCP**: No.
    -   **IP Address**: `10.10.20.250` / `24`.
5.  **Test**: Prova ad accedere alla web UI di TrueNAS usando `https://10.10.20.250` dal tuo PC.

---

## 8. Configurazione DHCP (Relay)
> **Obiettivo**: Lo switch inoltra le richieste DHCP delle VLAN 10/20 a OPNsense.
> **Basato sul tuo Screenshot**.

### A. Switch Managed (DHCP User Interface)
1.  Vai su **DHCP Relay Config**.
2.  **Global Settings**:
    -   **DHCP Relay Forwarding**: `On` (Verde).
    -   **DHCP Broadcast Suppress**: `On` (Opzionale, meglio on).
3.  **Aggiungi Regola per VLAN 20 (Client)**:
    -   **Interface**: Seleziona `VLAN0020` dal menu a tendina.
    -   **Helper-server Address**: `192.168.2.254` (L'IP di OPNsense).
    -   Clicca **Add**.
4.  **Aggiungi Regola per VLAN 10 (Server)** (Opzionale):
    -   **Interface**: Seleziona `VLAN0010`.
    -   **Helper-server Address**: `192.168.2.254`.
    -   Clicca **Add**.

### B. OPNsense (Services > DHCPv4)
1.  Vai su **Services** -> **DHCPv4** -> **[VLAN20 Interface]**.
2.  **Enable**: Sì.
3.  **Range**: `10.10.20.50` - `10.10.20.100`.
4.  **Gateway**: `10.10.20.1` (IP dello Switch!).
5.  **DNS**: `10.10.20.254` (IP di OPNsense).

---

## 9. Configurazione DNS (Unbound ACL)
> **Problema**: Di default, il DNS Resolver (Unbound) risponde solo alle reti direttamente connesse (WAN, LAN). Le VLAN 10 e 20 arrivano dallo Switch, quindi Unbound le ignora.

### A. OPNsense GUI
1.  Vai su **Services** -> **Unbound DNS** -> **Access Lists**.
2.  Clicca su **Add** (+) per creare una nuova lista.
3.  **Access List Name**: `VLAN_Subnets`.
4.  **Action**: `Allow`.
5.  **Networks**: Aggiungi le subnet che devono poter risolvere i nomi:
    -   `10.10.10.0/24` (Server)
    -   `10.10.20.0/24` (Client)
6.  Clicca **Save** e poi **Apply Configuration**.

### B. Verifica
Prova di nuovo dal Mac:
```bash
nslookup google.com 192.168.2.254
```
Se risponde, il DNS è sbloccato!


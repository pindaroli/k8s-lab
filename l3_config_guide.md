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
        -   **IP**: `192.168.2.99`
        -   **Subnet**: `255.255.255.0`
        -   **Gateway**: `192.168.2.1`
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
    -   **IP Address**: `192.168.2.1` (Già presente, NON cambiare se accedi da qui!)
    -   **Subnet Mask**: `255.255.255.0`

### B. Rotta di Default (Per Internet)
Vai nel menu **Routing** > **Static Route**:
-   **Destination**: `0.0.0.0`
-   **Mask**: `0.0.0.0`
-   **Next Hop (Gateway)**: `192.168.2.254` (Nuovo IP di OPNsense)
-   *Significato*: "Se non conosci la destinazione, chiedi a OPNsense sulla rete di transito".

---

## 2. OPNSENSE (Firewall)
> **Obiettivo**: OPNsense deve avere una gamba sulla rete 192.168.2.x per parlare con lo switch.

### A. Configura Interfaccia
Vai su **Interfaces** -> **Assignments** (o usa un'interfaccia esistente se c'è):
-   **IP Address**: `192.168.2.254`
-   **Subnet**: `/24` (255.255.255.0)
    -   *Nota*: Questa interfaccia deve essere collegata a una porta dello switch che ha la **VLAN 1** (Native/Untagged).
    - In alternativa, se usi la porta 3 (Management), configura il tuo PC con IP statico `192.168.2.99`.

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

### D. Firewall Rules (IMPORTANTE)
Vai su **Firewall** -> **Rules** -> (Interfaccia 192.168.2.x):
-   Aggiungi una regola PASS in cima:
    -   **Destination**: `Any`

---

## 4. WAN VLAN (Native WAN su Switch Stupido)
> **Scenario**: Il Modem è collegato allo switch stupido. Lo switch stupido è collegato alla Porta 8 dello switch Managed.
> **Obiettivo**: Tutto il traffico "nudo" (Untagged) dello switch stupido deve essere WAN (999).

### A. SWITCH MANAGED (Porte Uplink)

**1. PORTA 2 (Verso Switch Stupido WAN: Modem + PVE2)**
Qui serve la WAN Nativa.
-   **PVID / Native VLAN**: `999` (Traffico modem entra qui).
-   **Tagged VLANs**: `1, 10, 20, 30` (VLAN 30 IoT passante per OPNsense).

**2. PORTA 8 (Verso Switch Stupido Client)**
-   **PVID / Native VLAN**: `20` (Traffico PC Client).
-   **Tagged VLANs**: `1, 30` (VLAN 30 IoT appena aggiunta).
-   **Forbidden**: `10, 999` (Niente Server e niente Internet diretto).

---

## 9. Configurazione IoT (VLAN 30 - Isolation)
> **Obiettivo**: I dispositivi IoT (VLAN 30) devono andare SOLO su Internet (No accesso ai Server 10 o Client 20).
> **Tecnica**: Non diamo un IP allo Switch sulla VLAN 30. Facciamo passare il traffico L2 diretto a OPNsense.

### A. Switch Managed (Pass-through)
1.  **VLAN 30 Interface**: **NON CREARLA** (o disabilitala).
    *   *Lo Switch non deve fare routing per la IoT.*
2.  Assicurati che la **Porta 2** e **Porta 8** abbiano "Tagged: 30".

### B. Proxmox (PVE2) - Aggiungi Ponte
1.  Modifica `/etc/network/interfaces`:
    ```auto
    auto vmbr30
    iface vmbr30 inet manual
        bridge-ports bond0.30
        bridge-stp off
        bridge-fd 0
        # Ponte puro per OPNsense (IoT)
    ```
2.  **Applica**: `ifreload -a`.
3.  **VM OPNsense**: Aggiungi `net4` collegata a `vmbr30`.

### C. OPNsense (Firewall Rules)
1.  **Interfaces**: Assegna `vtnet4` -> `IOT`.
2.  **DHCPv4**: Attiva il server DHCP per `IOT` (10.10.30.x).
3.  **Firewall Rules (IOT)**:
    *   **Regola 1 (BLOCK LANs)**:
        *   Action: Block
        *   Destination: `RFC1918` (Network Alias per 192.168/16, 10/8, 172.16/12).
    *   **Regola 2 (ALLOW Internet)**:
        *   Action: Pass
        *   Destination: Any.


### B. PROXMOX (PVE2 - Su Switch Stupido WAN)
Ecco i file di configurazione `/etc/network/interfaces` completi da usare.

**1. File per PVE (Nodo 1 - 192.168.1.125)**
`vim /etc/network/interfaces`:
```auto
auto lo
iface lo inet loopback

iface nic0 inet manual

iface nic1 inet manual

auto bond0
iface bond0 inet manual
    bond-slaves nic0 nic1
    bond-miimon 100
    bond-mode active-backup
    bond-primary nic0

# WAN Bridge (VLAN 999 - Untagged/Native from Switch)
auto vmbr999
iface vmbr999 inet manual
    bridge-ports bond0
    bridge-stp off
    bridge-fd 0
    # Collegata a OPNsense WAN

# Management / Transit Bridge (VLAN 1)
auto vmbr0
iface vmbr0 inet static
    address 192.168.1.125/24
    gateway 192.168.1.1
    bridge-ports bond0.1
    bridge-stp off
    bridge-fd 0
    # Gateway punta al VIP di OPNsense

# Server Bridge (VLAN 10)
auto vmbr10
iface vmbr10 inet manual
    bridge-ports bond0.10
    bridge-stp off
    bridge-fd 0

# Client Bridge (VLAN 20)
auto vmbr20
iface vmbr20 inet manual
    bridge-ports bond0.20
    bridge-stp off
    bridge-fd 0

# IoT Bridge (VLAN 30)
auto vmbr30
iface vmbr30 inet manual
    bridge-ports bond0.30
    bridge-stp off
    bridge-fd 0
```

**2. File per PVE2 (Nodo 2 - 192.168.1.10 - SU SWITCH WAN)**
`vim /etc/network/interfaces`:
```auto
auto lo
iface lo inet loopback

iface eno1 inet manual

iface enp2s0 inet manual

auto bond0
iface bond0 inet manual
    bond-slaves eno1 enp2s0
    bond-miimon 100
    bond-mode active-backup
    bond-primary eno1

# WAN Bridge (VLAN 999 - Untagged/Native from Switch)
auto vmbr999
iface vmbr999 inet manual
    bridge-ports bond0
    bridge-stp off
    bridge-fd 0
    # Collegata a OPNsense WAN

# Management / Transit Bridge (VLAN 1)
auto vmbr0
iface vmbr0 inet static
    address 192.168.1.10/24
    gateway 192.168.1.1
    bridge-ports bond0.1
    bridge-stp off
    bridge-fd 0
    # Gateway punta al VIP di OPNsense

# Server Bridge (VLAN 10)
auto vmbr10
iface vmbr10 inet manual
    bridge-ports bond0.10
    bridge-stp off
    bridge-fd 0

# Client Bridge (VLAN 20)
auto vmbr20
iface vmbr20 inet manual
    bridge-ports bond0.20
    bridge-stp off
    bridge-fd 0

# IoT Bridge (VLAN 30)
auto vmbr30
iface vmbr30 inet manual
    bridge-ports bond0.30
    bridge-stp off
    bridge-fd 0
```

### C. OPNSENSE
1.  **WAN Interface**: Collegata a `vmbr999`.
2.  **Management Interface**: Collegata a `vmbr0` (che ora è su VLAN 1).

---

## 5. Gateway Legacy (Recuperare 192.168.1.1)
> **Problema**: Spostando il modem, la rete `192.168.1.x` perde il suo gateway fisico (1.1).
> **Soluzione**: OPNsense deve diventare il nuovo 192.168.1.1.

### A. OPNSENSE
1.  Vai su **Interfaces** -> **Virtual IPs** -> **Settings**.
2.  Clicca **Add** (+).
3.  **Mode**: `IP Alias`.
4.  **Interface**: `vlan1` (La tua interfaccia di gestione/transito "LAN").
5.  **Address**: `192.168.1.1` / `24` (`255.255.255.0`).
6.  **Description**: `Gateway Legacy LAN`.
7.  **Salva e Applica**.

### B. Verifica
Dai server proxmox, prova a pingare `192.168.1.1`.
Se risponde, OPNsense ha preso il controllo ed è pronto a portarti su Internet!

---

## 6. Configurazione VM OPNsense (Proxmox Hardware)
> **Metodo Automatico**: Abbiamo creato uno script per configurare le 5 schede di rete virtuali correttamente.

1.  **Copia lo script su PVE2**:
    ```bash
    scp configure_opnsense.sh root@pve2:/root/
    ```
2.  **Contenuto Script `configure_opnsense.sh`**:
    ```bash
    #!/bin/bash
    
    # Configuration
    VMID=2100
    
    echo "Configurazione Network per OPNsense VM $VMID..."
    
    # 1. Stop VM (per applicare cambi hardware)
    echo "Stopping VM $VMID..."
    qm stop $VMID
    sleep 5
    
    # 2. Configura Interfacce di Rete
    # net0 -> WAN (Native VLAN su switch stupido) -> vmbr999
    # net1 -> Management/Transit (VLAN 1) -> vmbr0
    # net2 -> Server (VLAN 10) -> vmbr10
    # net3 -> Client (VLAN 20) -> vmbr20
    # net4 -> IoT (VLAN 30) -> vmbr30
    
    echo "Applying Network Interface settings..."
    qm set $VMID --net0 virtio,bridge=vmbr999
    qm set $VMID --net1 virtio,bridge=vmbr0
    qm set $VMID --net2 virtio,bridge=vmbr10
    qm set $VMID --net3 virtio,bridge=vmbr20
    qm set $VMID --net4 virtio,bridge=vmbr30
    
    # 3. Start VM
    echo "Starting VM $VMID..."
    qm start $VMID
    
    echo "Done! OPNsense configuration applied."
    ```

3.  **Lancia lo script (Safe Mode)**:
    ```bash
    ssh root@pve2 "nohup bash /root/configure_opnsense.sh > /root/opnsense_log.txt 2>&1 &"
    ```
    *Questo script spegnerà la VM, imposterà le 5 interfacce e riavvierà.*

3.  **IMPORTANTE: Console Check & Troubleshooting**:
    Appena la VM si riavvia, l'ordine delle interfacce (`vtnet0`, `vtnet1`...) potrebbe cambiare (es. WAN diventa LAN).
    
    1.  **Apri la Console** di OPNsense da Proxmox.
    2.  **Verifica MAC Address**:
        -   Sulla Console OPNsense vedi i MAC address accanto a `vtnetX`.
        -   Confrontali con Proxmox -> VM -> Hardware per capire chi è chi (es. Quale bridge corrisponde a quale vtnet).
    3.  **Se le interfacce sono sbagliate**:
        -   Usa l'opzione **1) Assign Interfaces**.
        -   Il sistema ti chiederà se vuoi configurare le VLAN (Rispondi **N** / No, le VLAN le gestisce Proxmox).
        -   Assegna le interfacce fisiche corrette:
            -   **WAN** -> `vtnet0` (quella su `vmbr999`)
            -   **LAN** -> `vtnet1` (quella su `vmbr0`)
            -   **OPT1** -> `vtnet2` (quella su `vmbr10`)
            -   **OPT2** -> `vtnet3` (quella su `vmbr20`)
        -   Conferma e procedi.
    4.  **Se perdi l'IP della LAN**:
        -   Usa l'opzione **2) Set interface IP address**.
        -   Seleziona la LAN e rimetti `192.168.2.254` / `24`.

---

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
5.  **DNS**: `192.168.2.254` o `1.1.1.1`.


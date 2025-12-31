# Configurazione TrueNAS Scale: Dual-Link Network

Questa guida descrive i passaggi per configurare la VM TrueNAS Scale per utilizzare la nuova topologia di rete con due cavi fisici separati (VLAN 10 Server e VLAN 20 Client).

## 1. Modifica Hardware VM (Proxmox)

Dobbiamo collegare le schede di rete ai bridge corretti e **RIMUOVERE i tag VLAN** (il tagging avviene a livello fisico/switch).

1.  L'**ID della VM** è **1100**.
2.  Apri la Shell di Proxmox (sul nodo dove gira TrueNAS).
3.  Esegui questi comandi:

```bash
# Configura net0 su vmbr0 (VLAN 10 - Server) - NO TAG
qm set 1100 --net0 virtio,bridge=vmbr0,firewall=1

# Configura net1 su vmbr20 (VLAN 20 - Client) - NO TAG
qm set 1100 --net1 virtio,bridge=vmbr20,firewall=1

# Applica le modifiche (Riavvia la VM)
qm shutdown 1100 && qm start 1100
```

*(In alternativa puoi farlo dalla GUI: Hardware -> Network Device -> Edit -> Togli 'VLAN Tag' e cambia Bridge)*.

---

## 2. Configurazione IP (TrueNAS Console)

Una volta riavviata la VM, è probabile che l'interfaccia web non sia raggiungibile perché le interfacce sono cambiate. Usa la **Console** di Proxmox.

1.  Vai su Proxmox GUI -> VM TrueNAS -> **Console**.
2.  Dovresti vedere il menu testuale di TrueNAS.
3.  Seleziona **1) Configure Network Interfaces**.
4.  Ti mostrerà le interfacce (es. `vtnet0`, `vtnet1`).

### Configura Interfaccia 1 (Server/Mgmt)
*   **Interface**: `vtnet0` (o quella col mac address di net0)
*   **Remove Interface?**: No
*   **DHCP**: No
*   **IPv4 Address**: `10.10.10.50/24`
*   **IPv6**: No

### Configura Interfaccia 2 (Client Direct)
*   **Interface**: `vtnet1` (o quella col mac address di net1)
*   **Remove Interface?**: No
*   **DHCP**: No
*   **IPv4 Address**: `10.10.20.50/24`
*   **IPv6**: No

## 3. Configurazione Gateway e DNS

1.  Dal menu principale, seleziona **4) Configure Default Route**.
2.  **IPv4 Default Route**: `10.10.10.1`
3.  **IPv6 Default Route**: (Lascia vuoto)

4.  Dal menu principale, seleziona **6) Configure DNS**.
5.  **DNS 1**: `10.10.10.1` (o il tuo DNS server 10.10.10.254)
6.  **DNS 2**: `1.1.1.1`

## 4. Verifica e Bind Servizi

Ora dovresti raggiungere la GUI di TrueNAS su: `https://10.10.10.50`

### Impostazioni SMB (Opzionale)
Per assicurarti che i client usino la rete veloce (VLAN 20):
1.  Vai su **System Settings** -> **Services** -> **SMB**.
2.  Assicurati che SMB sia in ascolto su `0.0.0.0` (tutte le interfacce) o seleziona esplicitamente entrambe le interfacce.
3.  I client nella VLAN 20 dovrebbero montare le share usando l'IP `10.10.20.50` per avere performance massime (L2 diretto).

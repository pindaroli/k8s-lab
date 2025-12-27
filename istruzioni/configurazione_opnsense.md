# Configurazione OPNsense

> **Sorgente di Verità**: Questa configurazione deriva rigorosamente da `rete.json`.
> **Obiettivo**: Configurare OPNsense come Gateway Internet e per servizi DHCP/DNS, delegando il routing Inter-VLAN (10<->20) allo Switch L3.

## 1. Assegnazione Interfacce (Interfaces > Assignments)

Identifica le porte fisiche (igc0, igc1, etc.) e assegna come segue:

| Dispositivo Fisico | Ruolo logico | Nome Interfaccia OPNsense | Configurazione IPv4 | Note |
| :--- | :--- | :--- | :--- | :--- |
| **igc0** | **WAN** | `WAN` | **DHCP** (o PPPoE) | Verso Modem/ISP |
| **igc1** | **TRANSIT / LAN** | `TRANSIT` (o OPT4) | **Statico**: `192.168.2.254/24` | Native VLAN. Gateway verso Switch. |
| **igc3** | **ADMIN_LAN** | `ADMIN` (o LAN) | **Statico**: `192.168.100.1/24` | Porta emergenza/gestione diretta. |

---

## 2. Configurazione VLAN (Interfaces > Other Types > VLAN)

Crea le VLAN "taggate" sulla porta fisica `igc1` (Parent).

| Tag VLAN | Descrizione | Device Name | IP Address (Static) | Gateway | Note |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **10** | Server | `vlan0.10` | `10.10.10.254/24` | *Nessuno* | Presente per DHCP Relay e Broadcast |
| **20** | Client | `vlan0.20` | `10.10.20.254/24` | *Nessuno* | Presente per DHCP Relay e Broadcast |
| **30** | IoT | `vlan0.30` | `10.10.30.1/24` | *Nessuno* | Gateway IoT (Switch non ruota IoT) |

> **Nota Importante**: Dopo aver creato le VLAN, vai su **Assignments** e assegna loro un nome (es. `VLAN10`, `VLAN20`, `IOT`).

---

## 3. Gestione Routing (System > Routes)

Poiché OPNsense ha un'interfaccia diretta su ogni VLAN (`.254`), **NON** servono rotte statiche per le VLAN 10 e 20. OPNsense sa già come raggiungerle (Rotta "Directly Connected").

### A. Crea Gateway (Solo per definizione)
1.  Vai su **System > Gateways > Single**.
2.  **Add New Gateway**:
    *   **Name**: `SWITCH_L3`
    *   **Interface**: `TRANSIT` (la interfaccia su 192.168.2.254)
    *   **IP Address**: `192.168.2.1` (L'IP dello Switch)
    *   **Far Gateway**: Spuntato.
    *   *Nota*: Questo gateway serve se dovessi aggiungere in futuro reti dietro lo switch che NON arrivano via Trunk a OPNsense.

### B. Flusso del Traffico (Importante)
Con questa configurazione si crea un **Routing Asimmetrico (Valid)** ottimizzato:
1.  **Andata (Client -> Internet)**: Client -> Switch (GW) -> OPNsense -> Internet.
2.  **Ritorno (Internet -> Client)**: Internet -> OPNsense -> Client (Diretto via VLAN).
    *   *Il ritorno non RIPASSA dal routing dello Switch, ma viene consegnato direttamente Layer 2.*
    *   **Conseguenza**: Le regole Firewall su OPNsense per le interfacce `VLAN10` e `VLAN20` **DEVONO** permettere il traffico in ingresso/uscita, anche se il Gateway dei client è lo Switch.

---

## 4. Servizi DHCP (Services > ISC DHCPv4)

configura i server DHCP per servire le richieste (dirette o relay).

### ADMIN (192.168.100.x)
*   **Enable**: Sì
*   **Range**: `192.168.100.100` - `192.168.100.200`
*   **Gateway**: `192.168.100.1`

### VLAN 10 (Server)
*   **Static Only**: Non abilitare il server DHCP. I server avranno IP fissi configurati manualmente su Proxmox.

### VLAN 20 (Client)
*   **Enable**: Sì
*   **Range**: `10.10.20.100` - `10.10.20.200`
*   **Gateway**: `10.10.20.1` (**IP dello SWITCH**)
*   **DNS**: `10.10.20.254`

### VLAN 30 (IoT)
*   **Enable**: Sì
*   **Range**: `10.10.30.100` - `10.10.30.200`
*   **Gateway**: `10.10.30.1` (**IP di OPNsense**, qui fa lui da router)
*   **DNS**: `1.1.1.1`, `8.8.8.8` (Esterni per sicurezza/isolamento).

---

## 5. DNS (Services > Unbound DNS)

Per permettere alle VLAN di interrogare il DNS.

1.  **Access Lists**:
    *   Aggiungi una ACL chiamata "Internal_Networks".
    *   Action: **Allow**.
    *   Networks: `10.10.0.0/16`, `192.168.2.0/24`, `192.168.100.0/24`.

---

## 6. Firewall & NAT

### A. Outbound NAT (Firewall > NAT > Outbound)
Essenziale per dare accesso a Internet alle VLAN (che hanno IP privati).

1.  Seleziona **Hybrid outbound NAT rule generation**.
2.  Crea regola Manuale:
    *   **Interface**: `WAN`
    *   **Source**: `10.10.0.0/16` (o le singole subnet 10.10.10.0/24, etc.)
    *   **Translation**: `Interface Address`
    *   **Description**: NAT per VLAN Interne.

### B. Regole Firewall (Rules)
*   **TRANSIT**: Allow All (o ristretto a necessità).
*   **VLAN 10 / 20**:
    *   Allow IPv4/IPv6 any to any (se vuoi permettere accesso a internet).
    *   *Nota*: Il traffico tra 10 e 20 passa dallo switch, ma se arrivano pacchetti a OPNsense (es. DHCP, DNS), devono essere accettati.
*   **VLAN 30 (IoT)**:
    *   Block destination RFC1918 (Reti private: 192.168.x.x, 10.x.x.x).
    *   Allow destination Any (Internet).

---

## Riassunto IP Chiave
*   **Gateway LAN/Server/Client**: Switch (10.10.x.1)
*   **Gateway IoT**: OPNsense (10.10.30.1)
*   **DNS Server**: OPNsense (10.10.x.254 o .1)
*   **Gateway di Transito**: Switch (192.168.2.1) <-> OPNsense (192.168.2.254)

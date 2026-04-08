# Architettura di Rete: Symmetric Routing (Stato Finale)

Questo documento descrive la configurazione definitiva di **Symmetric Routing** del Homelab GEMINI, dove lo Switch L3 gestisce interamente il traffico inter-VLAN e OPNsense funge esclusivamente da Gateway Internet.

## Architettura Strategica
*   **Routing L3**: Lo switch ONTi L3 è il Gateway predefinito per tutte le VLAN interne (10, 20). Gestisce il traffico tra server e client alla massima velocità (wire-speed) senza caricare il firewall.
*   **Symmetrical Path**: Il traffico verso Internet segue lo stesso percorso all'andata e al ritorno: `Client -> Switch L3 -> OPNsense -> WAN` e viceversa.
*   **Transit Network**: La comunicazione tra OPNsense e lo Switch avviene esclusivamente sulla rete `TRANSIT` (`192.168.2.0/24`).

---

## Configurazione Core (OPNsense)

1.  **Rotte Statiche**
    OPNsense deve sapere che le VLAN 10 e 20 sono raggiungibili tramite lo Switch.
    *   **Gateway**: `192.168.2.1` (IP dello switch su rete Transit).
    *   **Rotte**:
        *   `10.10.10.0/24` -> Gateway `192.168.2.1`
        *   `10.10.20.0/24` -> Gateway `192.168.2.1`

2.  **DNS & DHCP**
    *   **Gateway DHCP**: Deve puntare all'IP dello Switch nella VLAN (es. `10.10.20.1`).
    *   **DNS Servers**: Punta a `192.168.2.254` (IP OPNsense su Transit).
    *   **Unbound Listen**: Deve ascoltare sull'interfaccia `TRANSIT`.

3.  **Firewall Hygiene (Symmetry Check)**
    Dato che il routing è ora perfettamente simmetrico, gli "hack" per il routing asimmetrico sono stati rimossi.
    *   **Static route filtering**: Deve essere **DISABILITATO** (spunta rimossa in *Firewall > Settings > Advanced*). Questo garantisce che OPNsense operi come un firewall stateful corretto.
    *   **Outbound NAT**: Regola manuale per permettere alle reti `10.10.x.x` di uscire su WAN tramite l'interfaccia Transit.

---

## Configurazione Core (Switch L3)

1.  **VLAN Interfaces**
    *   VLAN 10: `10.10.10.1`
    *   VLAN 20: `10.10.20.1`
    *   VLAN 1 (Transit): `192.168.2.1`

2.  **Static Route (Default Gateway)**
    *   `0.0.0.0 0.0.0.0` -> `192.168.2.254` (OPNsense).

3.  **DHCP Relay**
    *   Helper-server Address: `192.168.2.254` (Inviato via rete Transit).

---

## Validazione del Percorso
Per confermare che il routing sia simmetrico:
1.  **Hop 1**: Deve essere lo switch (`10.10.x.1`).
2.  **Hop 2**: Deve essere OPNsense (`192.168.2.254`).
3.  **Hop 3**: Deve essere l'uscita ISP.

*Stato: Configurazione Migrata e Consolidata.*

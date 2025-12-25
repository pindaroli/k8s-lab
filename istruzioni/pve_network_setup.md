# Configurazione Rete PVE3

Dato che PVE3 si trova su **VLAN 10 (Server)** e **VLAN 20 (Client VM)**, ecco come configurare `/etc/network/interfaces`.

## 1. Identificare le Porte Fisiche
Prima di applicare la configurazione, dobbiamo essere sicuri di quale interfaccia linux (`eno1`, `eno2`, `enp1s0`, ecc.) corrisponde a quale cavo.

1.  Collega **solo** il cavo sulla **Porta 1** del PVE3 (che va allo Switch Porta 3 - VLAN 10).
2.  Esegui il comando:
    ```bash
    ip -c link
    ```
3.  Guarda quale interfaccia è **UP** e segnatela (es. `eno1` = VLAN 10).
4.  Collega il secondo cavo (VLAN 20) e verifica che vada UP l'altra (es. `eno2` = VLAN 20).

## 2. Modifica `/etc/network/interfaces`

Edita il file:
```bash
nano /etc/network/interfaces
```

Sostituisci tutto con questo contenuto (adattando i nomi `eno1`/`eno2` se diversi):

```auto
auto lo
iface lo inet loopback

# -----------------
# PORTA 1 -> SWITCH PORT 3 (VLAN 10 - SERVER/MGMT)
# -----------------
auto eno1
iface eno1 inet manual

# Bridge di Management (e per VM Server se servono)
auto vmbr10
iface vmbr10 inet static
    address 10.10.10.13/24
    gateway 10.10.10.1
    bridge-ports eno1
    bridge-stp off
    bridge-fd 0
    # Gateway è lo Switch Core (10.10.10.1)

# -----------------
# PORTA 2 -> SWITCH PORT 4 (VLAN 20 - CLIENT VM)
# -----------------
auto eno2
iface eno2 inet manual

# Bridge per le VM Client (Senza IP, L2 puro)
auto vmbr20
iface vmbr20 inet manual
    bridge-ports eno2
    bridge-stp off
    bridge-fd 0
    # Le VM collegate qui riceveranno IP dal DHCP VLAN 20 (10.10.20.x)
```

## 3. Applica e Verifica
1.  Riavvia la rete (o meglio il nodo se puoi):
    ```bash
    systemctl restart networking
    # oppure
    reboot
    ```
2.  Verifica di raggiungere il Gateway:
    ```bash
    ping 10.10.10.1
    ```
3.  Verifica di uscire su Internet (se OPNsense è configurato e lo switch ha la rotta di default):
    ```bash
    ping 1.1.1.1
    ```

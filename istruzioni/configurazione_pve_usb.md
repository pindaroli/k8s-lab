# Configurazione PVE: Rete Dual-Link e Storage USB

Questo documento descrive i passaggi per configurare un nodo Proxmox (PVE) secondo le nuove specifiche di rete (separazione traffico Server/Client) e come aggiungere uno storage USB esterno.

---

## Parte 1: Configurazione di Rete (Dual-Link)

La nuova topologia prevede l'uso di due cavi di rete fisici per separare il traffico di gestione/server da quello dei client (VM guest).

*   **Cavo 1 (VLAN 10)**: Management Proxmox, Cluster Traffic, VM/CT "Server" (es. DNS, Controller).
*   **Cavo 2 (VLAN 20)**: VM "Client" (Windows, Desktop remoti, ecc.) che ottengono IP dalla VLAN Client.

### 1. Identificazione delle Interfacce Fisiche

Prima di configurare, è **critico** identificare come Linux nomina le tue porte (es. `eno1`, `enp2s0`, `eth0`).

1.  Collega **SOLO** il cavo destinato alla **Porta 1** (VLAN 10 - Management).
2.  Accedi alla console (schermo fisico o SSH se ha preso IP temporaneo) e lancia:
    ```bash
    ip -c link
    ```
3.  Nota quale interfaccia è in stato `UP` (es. `eno1`). Questa sarà la tua **WAN/MGMT**.
4.  Collega il secondo cavo (VLAN 20).
5.  Rilancia `ip -c link` e benedici la seconda interfaccia che va `UP` (es. `eno2` o `enp1s0`). Questa sarà dedicata ai **CLIENT**.

### 2. Modifica `/etc/network/interfaces`

Apri il file di configurazione:
```bash
nano /etc/network/interfaces
```

### 2. File di Configurazione Pronti

Ho preparato 3 file separati per ogni nodo. Copia il contenuto del file appropriato dentro `/etc/network/interfaces` sul rispettivo server.

*   **PVE (Node 1)**: [istruzioni/interfaces_pve.txt](interfaces_pve.txt)
    *   *Nota*: Include la porta di servizio su `192.168.99.2`.
*   **PVE2 (Node 2)**: [istruzioni/interfaces_pve2.txt](interfaces_pve2.txt)
    *   *Nota*: Configurazione standard 2 cavi.
*   **PVE3 (Node 3)**: [istruzioni/interfaces_pve3.txt](interfaces_pve3.txt)
    *   *Nota*: Configurazione standard 2 cavi.

**IMPORTANTE**: Ricordati sempre di verificare i nomi delle interfacce (`eno1`, `eno2`, ecc.) con `ip -c link` prima di salvare!

Dopo aver salvato, applica le modifiche:
```bash
systemctl restart networking
# oppure
reboot
```

---

## Parte 3: Aggiornare `/etc/hosts` (Risoluzione Nomi)

Affinché i nodi del cluster si parlino correttamente via nome (essenziale per la GUI e le migrazioni), devi aggiornare il file hosts SU TUTTI I NODI.

1.  Apri il file:
    ```bash
    nano /etc/hosts
    ```

2.  Assicurati che le righe relative ai nodi PVE puntino ai nuovi IP della **VLAN 10** (`10.10.10.x`).

    *Esempio di configurazione corretta (da copiare su pve, pve2, pve3):*
    ```text
    127.0.0.1       localhost

    # Cluster Nodes (VLAN 10 - Server/Mgmt)
    10.10.10.11     pve.pindaroli.local pve
    10.10.10.12     pve2.pindaroli.local pve2
    10.10.10.13     pve3.pindaroli.local pve3

    # ... altre entries ...
    ```

3.  Salva e chiudi. Prova a pingare gli altri nodi per nome:
    ```bash
    ping -c 2 pve2
    ping -c 2 pve3
    ```

---

## Parte 4: Altri File Critici da Controllare

Se stai cambiando gli indirizzi IP di un cluster esistente, **NON BASTA** cambiare `interfaces` e `hosts`. Devi controllare anche questi file per evitare che il cluster si rompa.

### 1. `/etc/pve/corosync.conf` (CRITICO!)
Questo file definisce come i nodi si parlano per il quorum. Se l'IP qui è diverso dall'IP reale configurato in interfaces, il cluster **SI ROMPERÀ** (split-brain o offline).

1.  Controlla il file:
    ```bash
    cat /etc/pve/corosync.conf
    ```
    Cerchi la sezione `nodelist`. Assicurati che `ring0_addr` di ogni nodo corrisponda al nuovo IP della VLAN 10 (es. `10.10.10.11`).

2.  **Se devi modificarlo**:
    *   **È delicato**. Normalmente non si edita a mano `/etc/pve/...` perché è un filesystem condiviso (pmxcfs) che richiede quorum.
    *   Se il cluster è UP ma devi cambiare IP: Fallo **PRIMA** di cambiare le interfacce di rete, seguendo la guida ufficiale Proxmox "Edit corosync.conf".
    *   Se il cluster è DOWN: Devi fermare i servizi e modificare il file in modalità locale. *Se sei in questa situazione, chiedimi la procedura specifica di recovery.*

### 2. `/etc/resolv.conf` (DNS)
Controlla che il DNS sia corretto (es. il Gateway o un DNS esterno) per permettere al nodo di scaricare aggiornamenti.
```bash
nameserver 10.10.10.1
# oppure
nameserver 1.1.1.1
```

### 3. `/etc/pve/storage.cfg`
Se hai storage condivisi (come il NAS TrueNAS), verifica che puntino agli indirizzi IP corretti.
*   Esempio: Se il NAS è su `10.10.10.x`, assicurati che la config NFS non punti a un vecchio indirizzo irraggiungibile.

---

## Parte 5: Montare e Usare Storage USB

Se vuoi usare un disco USB per backup, ISO o storage aggiuntivo, segui questi passi.

### 1. Identificare il Disco
Collega il disco USB e lancia:
```bash
lsblk
```
Cerca il disco in base alla dimensione (es. `sdb`, `sdc`).
*Esempio output*: `sdb 931.5G 0 disk`

### 2. Formattazione (Opzionale ma Consigliata)
Se il disco non contiene dati, formattalo in `ext4` per massima compatibilità con Linux:
**(SDX = il tuo disco, es. sdb. ATTENZIONE A NON CANCELLARE IL DISCO DI SISTEMA!)**

1.  Crea partizione: `cfdisk /dev/sdx` -> Select `gpt` -> New -> Write.
2.  Formatta:
    ```bash
    mkfs.ext4 /dev/sdx1
    ```

### 3. Montaggio Permanente

1.  **Crea la cartella di mount**:
    ```bash
    mkdir -p /mnt/usb-storage
    ```

2.  **Trova l'UUID** (Più sicuro dei nomi sdb1):
    ```bash
    blkid /dev/sdx1
    ```
    Copia la stringa UUID (es. `UUID="1234-5678-abcd..."`).

3.  **Aggiungi a fstab**:
    ```bash
    nano /etc/fstab
    ```
    Aggiungi in fondo:
    ```text
    UUID=INCOLLA-IL-TUO-UUID-QUI /mnt/usb-storage ext4 defaults,nofail 0 2
    ```
    *(L'opzione `nofail` permette al server di avviarsi anche se l'USB è scollegata)*.

4.  **Monta subito**:
    ```bash
    mount -a
    ```

### 4. Aggiunta a Proxmox (GUI)

Ora che il disco è montato su Linux, dillo a Proxmox:

1.  Vai su **Datacenter** -> **Storage**.
2.  Clicca **Add** -> **Directory**.
3.  Compila:
    *   **ID**: `USB-Backup` (o nome a piacere)
    *   **Directory**: `/mnt/usb-storage`
    *   **Content**: Seleziona tutto ciò che vuoi metterci (Disk image, ISO, Vzdump backup, ecc.)
    *   **Shared**: Togli la spunta (è locale a questo nodo).
4.  Clicca **Add**.

Il nuovo storage sarà subito disponibile per quel nodo.

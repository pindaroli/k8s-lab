# Piano Esecutivo: Upgrade Nodi PVE (Maintenance Mode)

> [!IMPORTANT]
> **Strategia**: Offline / Maintenance Mode
> **Priorità**: Semplicità e Sicurezza dei Dati (vs Uptime)
> **Obiettivo**: Sostituzione PVE3 (Upgrade Ryzen 9) e Downgrade PVE2 (RAM).

Questo piano prevede lo spegnimento controllato del cluster per effettuare gli interventi hardware in parallelo, evitando rischi di Split-Brain o corruzione del Quorum.

---

## 🟢 FASE 1: Congelamento (Backup & Shutdown)
*Obiettivo: Mettere i dati in sicurezza e spegnere tutto senza corruzioni.*

1.  **Backup Talos (Dal Mac)**:
    Salviamo la configurazione di K8s per sicurezza.
    ```bash
    velero backup create maintenance-window-$(date +%F) --wait
    ```

2.  **Verifica Backup VM (Importante)**:
    Vai sulla GUI di Proxmox (PVE1) o PBS e assicurati di avere un backup "Verified" della **VM 3200 (CP03)**.
    *   Questa è l'unica VM che sarà necessario ripristinare integralmente.
    *   Le altre VM (CP02 su PVE2) resteranno sui dischi esistenti.

3.  **Shutdown "Gentile" di Talos**:
    Spegni i nodi Talos via API per preservare ETCD.
    ```bash
    # Spegni CP02 (che gira su PVE2)
    talosctl -n 10.10.20.142 shutdown
    
    # (Opzionale) Puoi spegnere anche CP01 se vuoi silenzio totale.
    ```

4.  **Rimozione PVE3 dal Cluster (PRE-SHUTDOWN)**
    Per evitare problemi ghost dopo, rimuovi il nodo PVE3 morto/da sostituire dal cluster *prima* di spegnere tutto, se possibile. Altrimenti fallo da PVE1 dopo.
    Da PVE1 Shell:
    ```bash
    pvecm delnode pve3
    ```

5.  **Shutdown PVE2**:
    Spegni il nodo PVE2 dalla GUI o via SSH (`poweroff`).

---

## 🔧 FASE 2: Intervento Hardware (Il Cacciavite)
*Obiettivo: Fare le modifiche fisiche in sicurezza.*

1.  **Su PVE2**:
    *   Apri chassis.
    *   Rimuovi i 32GB di RAM in eccesso.
    *   Richiudi.
    *   *Nota*: Il disco di sistema non viene toccato, quindi l'OS è intatto.

2.  **Su PVE3**:
    *   Assembla il nuovo Ryzen 9 9555HX, 64GB RAM.
    *   Installa i 2x512GB NVMe.
    *   Collega i cavi di rete (preferibilmente sulle stesse porte logiche per facilitare il bridging).

---

## 🔄 FASE 3: Ripristino Proxmox (Il Cluster)
*Obiettivo: Avere 3 nodi Proxmox verdi.*

1.  **Riaccendi PVE2**:
    *   Dato che non hai toccato il disco, partirà normalmente.
    *   K8s (CP02/VM 2300) ripartirà automaticamente (se `onboot: 1`).
    *   **Stato**: PVE1 + PVE2 si vedono. Quorum Proxmox OK (2/2).

2.  **Installa & Configura PVE3 (Nuovo)**:
    *   Installa Proxmox VE (Debian 13/Trixie) da ISO.
    *   **Hostname**: `pve3`
    *   **IP**: `10.10.10.31` (Stesso di prima).
    *   **Storage**: Crea un ZFS Pool chiamato `stripe` sui 2 NVMe in RAID0.
    *   **Network**: Configura il bridge `vmbr0` sulla subnet `10.10.10.0/24`.
    *   Aggiorna sistema: `apt update && apt dist-upgrade`.

3.  **Join PVE3 al Cluster**:
    *   **Importante**: Se PVE1 ha ancora la vecchia fingerprint SSH di PVE3, puliscila su PVE1:
        ```bash
        ssh-keygen -f "/root/.ssh/known_hosts" -R "10.10.10.31"
        ```
    *   Da PVE3 (Nuovo):
        ```bash
        pvecm add 10.10.10.x  # IP di PVE1
        ```

---

## 💾 FASE 4: Ripristino Talos (Il Nodo Mancante)
*Obiettivo: Riportare CP03 in vita.*

1.  **Setup PVE3**:
    *   Configura lo Storage PBS (o NFS Backup) su PVE3 per vedere i backup.
    *   **Hook Script**: Copia lo script necessario per l'avvio sincronizzato con TrueNAS.
        ```bash
        # Da PVE1 verso PVE3
        scp /var/lib/vz/snippets/wait-for-truenas.sh root@10.10.10.31:/var/lib/vz/snippets/
        ```

2.  **Restore VM 3200 (CP03)**:
    *   Da GUI Proxmox > PVE3 > Storage Backup.
    *   Seleziona l'ultimo backup della VM 3200 > **Restore**.
    *   **⚠️ CRITICO**: Assicurati che **"Unique MAC"** (o rigenerazione MAC) sia **DISABILITATO**.
        *   Talos usa il MAC address come ID del nodo. Se cambia, non farà join al cluster ETCD esistente.

3.  **Avvio**:
    *   Avvia la VM 3200 (`qm start 3200`).
    *   La VM attenderà TrueNAS (grazie allo script hook) e poi booterà Talos.

---

## ✅ FASE 5: Verifica Finale

1.  **Proxmox**:
    *   Datacenter Summary: 3 Nodi Online (Green).
    *   Quorum OK.

2.  **Talos / Kubernetes**:
    *   Dal Mac:
        ```bash
        talosctl get members
        ```
    *   Tutti i 3 Control Plane (CP01, CP02, CP03) devono essere `Ready`.
    *   `kubectl get nodes -o wide` mostra tutti i nodi pronti.

3.  **Pulizia**:
    *   Verifica che i backup programmati (PBS/Velero) per la notte successiva siano ri-abilitati e corretti.

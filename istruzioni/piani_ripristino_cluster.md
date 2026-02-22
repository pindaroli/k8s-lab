# Piani di Ripristino del Cluster Proxmox / Kubernetes

Alla luce dell'avvenuta reinstallazione dei nodi PVE2 e PVE3 e dell'allineamento delle configurazioni di rete (`/etc/network/interfaces`), ci troviamo di fronte a due alternative principali per ricostruire il cluster Kubernetes e rimettere in piedi i servizi.

Di seguito l'analisi e i passi operativi per entrambe le opzioni.

---

## Opzione A: Reinstallazione da zero (Clean Slate) + Ripristino Dati K8s

Questa opzione prevede di ignorare i backup interi delle VM fatti da Proxmox Backup Server (PBS) per i nodi, creando un cluster Talos e VM completamente puliti da zero e affidandosi a Velero/NFS per ripristinare solo lo stato dei workload Kubernetes.

### Pro e Contro
*   **Pro**: 
    * Massima pulizia del sistema (niente scorie dalle precedenti installazioni).
    * Ottima occasione per testare il Disaster Recovery di livello applicativo (Velero).
    * Evita potenziali conflitti di MAC address o UUID di vecchie VM.
*   **Contro**:
    * Più lunga e laboriosa (richiede di rigenerare le VM Talos via CLI/ISO).
    * È necessario riconfigurare manualmente il cluster Talos (VIP, certificati, etcd).

### Procedura Esecutiva (Bozza)
1. **Creazione Cluster Proxmox:** Unire PVE2 e PVE3 al cluster PVE padre (PVE1).
2. **Creazione VM Talos:** Ricreare manualmente le VM `1300`, `2300` e `3200` sui rispettivi nodi Proxmox, allocando IP, CPU e disco come in origine.
3. **Bootstrap Talos:** Installare Talos OS usando l'immagine ISO aggiornata, applicando i file `controlplane.yaml` della repository locale (o generarne di nuovi se non abbiamo il backup di `talosconfig` con i secret corretti).
4. **Validazione ETCD:** Avviare il cluster e attendere che i tre control plane formino quorum.
5. **Configurazione Storage & Ingress:** Re-installare e configurare TrueNAS NFS, CSI driver e Traefik/MetalLB.
6. **Restore Velero:** Collegarsi a TrueNAS (MinIO via Velero) e lanciare il restore completo:
   `velero restore create --from-backup <ultimo_backup_full> --wait`

---

## Opzione B: Ripristino Integrale da PBS (Time Machine)

Questa opzione prevede di rimettere PVE2 e PVE3 nel cluster Proxmox (se necessario) e poi scaricare le VM Talos (`2300`, `3200`) ei container (`2200` Jellyfin) direttamente dal Proxmox Backup Server, in modo da avere cloni esatti pre-disastro.

### Pro e Contro
*   **Pro**: 
    * Velocità di ripristino eccellente (è sufficiente un click e il tempo di trasferimento rete).
    * Il cluster Talos/ETCD riparte esattamente dallo stesso stato (stessi certificati, chiavi, IP, MAC Address).
    * Non serve toccare Velero né riconfigurare il cluster K8s.
*   **Contro**:
    * I backup di PBS potrebbero essere "stale" (vecchi di qualche ora/giorno a seconda della schedulazione), quindi alcune minuscole modifiche applicative molto recenti andrebbero perse se non compensate con Velero.
    * Le VM manterranno l'hardware e l'impronta esatta del momento del backup, che potrebbe divergere se si modificano i dischi o le allocazioni di RAM (nota: PVE2 e PVE3 hanno entrambi 64GB allocati).

### Procedura Esecutiva (Bozza)
1. **Creazione Cluster Proxmox:** Unire PVE2 e PVE3 a PVE1 per formare il quorum.
2. **Storage PBS:** Assicurarsi che PVE2 e PVE3 abbiano accesso al datastore PBS (aggiungendolo in *Datacenter > Storage* sui nuovi nodi).
3. **Restore VM 2300 (Talos CP02):** Su PVE2, navigare nello storage PBS, selezionare l'ultimo backup della VM 2300 e cliccare Restore. **Attenzione: mantenere il MAC address originale (non spuntare *Unique MAC*).** Prima di avviare, se necessario modificare la RAM/Disco in base al nuovo hardware di PVE2.
4. **Restore VM 3200 (Talos CP03):** Su PVE3, eseguire la stessa procedura per la VM 3200.
5. **Restore altre VM/LXC:** Ripristinare eventuali workload standalone (es. LXC Jellyfin 2200) sui nodi appropriati.
6. **Avvio Sequenziale:** Avviare le VM ristabilite. Il cluster ETCD si ricompatterà automaticamente riconoscendo le macchine dai certificati e dai MAC address in PVE.

---

### Conclusione e Consiglio

L'**Opzione B (PBS)** è di gran lunga l'approccio ingegneristicamente più affidabile ed è il "metodo Proxmox ufficiale" per gestire failure fisici. Il disco e la configurazione virtuale sono congelati, riducendo a zero l'errore umano di reimpostazione. Se decidi di procedere con B, possiamo dettagliare i passi precisi sui comandi Proxmox per reinnestare le macchine.

Se invece preferisci cogliere l'occasione per testare la solidità di **Velero** e la riproducibilità "Infrastructure-as-Code" (Opzione A), procediamo con la guida al bootstrap.

---
title: "Piano di Manutenzione Hardware: Migrazione PVE3 (10G) e Ripristino Cluster (Fase Principale)"
type: plan
status: archived
certified_for_ai: false
created_at: 2026-06-27
archived_at: 2026-06-27
tags:
  - "#plan"
  - "#network"
  - "#storage"
  - "#proxmox"
  - "#talos"
---

# Piano di Manutenzione Hardware: Migrazione PVE3 (10G) e Ripristino Cluster (Fase Principale)

Questo piano dettagliato descrive le fasi per la migrazione fisica di PVE3 al core switch 10G, la sua riconfigurazione di rete, e il successivo ripristino ordinato dei cluster Proxmox e Kubernetes (inclusa la reinstallazione di `talos-cp-02`).

> [!IMPORTANT]
> **PREREQUISITO**: Prima di eseguire questo piano, è necessario aver completato con successo il [[plan-out-of-band-service-access]]. L'accesso alle porte di servizio fisiche e la verifica iniziale a freddo di PVE2 devono essere già operativi nello Studio.

---

## 1. Stato Attuale e Obiettivi

1.  **PVE2**: Hardware ripristinato e testato con successo nello Studio (tramite porta di servizio OOB). Posizionato nel rack definitivo e connesso allo switch core **switch10g (ONTi)** in Access VLAN 99.
2.  **PVE3**: **[COMPLETATO]** Riconfigurazione di rete 10G effettuata con successo via OOB (`nic0`) e testata. Server ora pienamente operativo sui link `enp101s0f0` e `enp101s0f1` a 10G tramite nuova scheda Intel X520.
3.  **Obiettivi di questa fase**:
    *   Effettuare il backup manuale dello stato del cluster Proxmox.
    *   Spegnere in sicurezza l'intera infrastruttura.
    *   Riavviare tutto l'homelab, allineare i cluster Proxmox e Kubernetes, e reinstallare/re-integrare `talos-cp-02`.

---

## 2. Fase 1: Backup Preventivo e Verifica dello Stato (A Caldo)

> [!IMPORTANT]
> Non procedere allo spegnimento senza prima aver verificato e forzato i backup delle macchine virtuali e dei container.

### Step 1.1: Eseguire Backup Manuale delle VM/LXC su PBS
1. Accedi alla Web GUI di Proxmox su PVE1 (`https://10.10.10.11:8006`).
2. Vai su **Datacenter** -> **Backup**.
3. Seleziona il Job di backup associato a **PBS** (Proxmox Backup Server, LXC `1400`) e clicca su **Run Now**.
4. Attendi il completamento dei backup di tutte le VM/LXC critiche (inclusi Talos `1300`, `3200`, Jellyfin `2200`).

### Step 1.2: Backup della Configurazione dei Cluster Proxmox (PVE1 e PVE3)
1. Accedi via SSH a **PVE1** (`10.10.10.11`) ed esegui:
   ```bash
   tar -czf /root/pve1-etc-pve-backup.tar.gz /etc/pve
   cp /var/lib/pve-cluster/config.db /root/pve1-cluster-config.db
   ```
2. Accedi via SSH a **PVE3** (`10.10.10.31`) ed esegui:
   ```bash
   tar -czf /root/pve3-etc-pve-backup.tar.gz /etc/pve
   cp /var/lib/pve-cluster/config.db /root/pve3-cluster-config.db
   ```
3. Scarica questi file sul tuo Mac Studio via `scp` per sicurezza:
   ```bash
   scp root@10.10.10.11:/root/pve1-* ~/Desktop/
   scp root@10.10.10.31:/root/pve3-* ~/Desktop/
   ```

---

## 3. Fase 2: Protocollo di Spegnimento Sicuro (Shutdown Lab)

Seguiamo l'ordine inverso delle dipendenze per evitare corruzioni di file e deadlock di database.

### Step 2.1: Spegnimento del Cluster Kubernetes (Talos)
1. Dal tuo Mac Studio, esegui i comandi `talosctl` per spegnere i nodi attivi:
   ```bash
   # Spegni talos-cp-01
   talosctl -n 10.10.20.141 shutdown

   # Spegni talos-cp-03
   talosctl -n 10.10.20.143 shutdown
   ```
2. Attendi circa **3 minuti** affinché i nodi salvino lo stato e si spengano completamente.

### Step 2.2: Spegnimento dei Servizi Dipendenti (Jellyfin, PBS)
1. Accedi a **PVE3** (`10.10.10.31`) e arresta Jellyfin LXC:
   ```bash
   pct shutdown 2200 --forceStop 0
   ```
2. Accedi a **PVE1** (`10.10.10.11`) e arresta PBS LXC:
   ```bash
   pct shutdown 1400 --forceStop 0
   ```

### Step 2.3: Spegnimento del Storage (TrueNAS)
1. Accedi a **PVE1** (`10.10.10.11`) ed esegui lo shutdown della VM TrueNAS (`1100`):
   ```bash
   qm shutdown 1100 --forceStop 0
   ```
2. Attendi **30-60 secondi** per consentire il flush completo della cache ZFS su TrueNAS prima di procedere.

### Step 2.4: Spegnimento Fisico degli Hypervisor
1. Spegni **PVE3**:
   ```bash
   ssh root@10.10.10.31 "shutdown -h now"
   ```
2. Spegni **PVE1**:
   ```bash
   ssh root@10.10.10.11 "shutdown -h now"
   ```
3. Se gli switch o altri apparati di rete devono essere spenti fisicamente, togli l'alimentazione dalla PDU/UPS solo adesso.

---

## 4. Fase 3: Intervento Fisico e Recablatura di PVE3

Ora che tutto è spento, procediamo alle modifiche fisiche.

1.  **Scollegamento PVE3**:
    *   Scollega i due cavi ethernet di PVE3 da `switch-25g-server` (Porte 3 e 4).
2.  **Collegamento a switch10g (ONTi)**:
    *   Collega le nuove porte 10G SFP+ di PVE3 a due porte libere sullo switch **switch10g** (ad esempio, porta 2 e porta 7).
3.  **Configurazione delle porte VLAN su switch10g**:
    *   Accendi solo lo switch `switch10g` (se spento) ed entra nella Web GUI all'indirizzo `http://192.168.2.1`.
    *   Associa la porta dello switch collegata alla **Porta 1 di PVE3** in modalità **ACCESS VLAN 10** e la porta collegata alla **Porta 2 di PVE3** in modalità **ACCESS VLAN 20**.

---

## 5. Fase 4: Riconfigurazione Rete PVE3 (Nuove Schede 10G)

Poiché hai cambiato le schede fisiche di PVE3 collegandolo allo switch 10G, i nomi delle interfacce all'interno di Debian saranno cambiati (ad esempio da `nic0`/`nic1` a nomi come `enp3s0f0`/`enp3s0f1` o simili). Dobbiamo riconfigurarle per ridare connettività al nodo.

### Step 4.1: Avvio e Accesso Locale a PVE3
1. Collega **solo il cavo della Porta 1 (VLAN 10 - Server)** di PVE3 al core switch 10G. Lascia scollegato il cavo VLAN 20 per il momento.
2. Accendi PVE3 fisicamente.
3. Puoi accedere a PVE3 tramite la sua porta di servizio OOB fisica (`https://192.168.100.31:8006` o SSH `192.168.100.31`), garantendoti totale indipendenza dalla rete di produzione!
4. Accedi come `root`.

### Step 4.2: Identificazione delle Nuove Schede di Rete
Dobbiamo scoprire come Linux chiama la tua nuova porta 10G attiva.
1. Esegui il comando:
   ```bash
   ip -c link
   ```
2. Cerca le interfacce che si trovano in stato **UP** o **LOWER_UP** (ovvero che rilevano il link fisico dei cavi collegati). Annota i loro nomi esatti (es. `enp101s0f0` e `enp101s0f1`). Queste saranno le due porte dedicate rispettivamente alla **VLAN 10** e alla **VLAN 20** in modalità Access.

### Step 4.3: Aggiornamento di `/etc/network/interfaces`
1. **FONDAMENTALE: Fai un backup del file originale prima di modificarlo**:
   ```bash
   cp /etc/network/interfaces /etc/network/interfaces.bak-$(date +%F_%H-%M-%S)
   ```
2. Apri il file delle interfacce:
   ```bash
   nano /etc/network/interfaces
   ```
3. Modifica il file inserendo i nomi delle schede 10G attive (Intel X520) identificate al punto precedente. In questo modo assegneremo ogni porta fisica alla rispettiva VLAN (modalità Access), eliminando la necessità di sub-interfacce VLAN a livello OS:

   ```text
   auto lo
   iface lo inet loopback

   # -----------------------------------------------------------
   # PORTA DI SERVIZIO OOB (VLAN 99 Access dal LIAGUO)
   # -----------------------------------------------------------
   auto nic0
   iface nic0 inet static
       address 192.168.100.31/24

   # -----------------------------------------------------------
   # VLAN 10 (Server/Mgmt PVE3) - Porta 1 10G Access
   # -----------------------------------------------------------
   auto enp101s0f0
   iface enp101s0f0 inet manual

   auto vmbr10
   iface vmbr10 inet static
       address 10.10.10.31/24
       gateway 10.10.10.1
       bridge-ports enp101s0f0
       bridge-stp off
       bridge-fd 0

   # -----------------------------------------------------------
   # VLAN 20 (Client VM) - Porta 2 10G Access
   # -----------------------------------------------------------
   auto enp101s0f1
   iface enp101s0f1 inet manual

   auto vmbr20
   iface vmbr20 inet manual
       bridge-ports enp101s0f1
       bridge-stp off
       bridge-fd 0
   ```
4. Salva il file (`Ctrl+O`, `Invio`, `Ctrl+X`).

### Step 4.4: Applicazione delle Modifiche e Verifica
1. Riavvia il nodo:
   ```bash
   reboot
   ```
2. Una volta riavviato, verifica che PVE3 sia raggiungibile ed esca su internet:
   ```bash
   ping -c 3 10.10.10.1   # Ping al Gateway (Switch L3)
   ping -c 3 1.1.1.1      # Ping a Internet
   ```

---

## 5. Fase 5: Riaccensione Completa e Ripristino Cluster Proxmox

Ora che la parte hardware e di rete è completata, riavviamo l'intero Homelab secondo la sequenza corretta.

### Step 5.1: Sequenza di Boot Ordinata
1.  **Accendi PVE1**. Questo nodo avvierà TrueNAS (`1100`) per primo.
2.  **Attendi ~3-5 minuti**. TrueNAS deve completare il boot e montare i pool ZFS.
3.  **Accendi PVE2 e PVE3** nelle loro posizioni definitive nel rack.
4.  Gli hook di Proxmox ("Wait-for-TrueNAS") ritarderanno l'avvio delle VM fin a quando gli share NFS non saranno attivi.

### Step 5.2: Correzione dei File `/etc/hosts` (Risoluzione Nomi)
Verifichiamo che tutti i nodi abbiano gli IP aggiornati della VLAN 10 e gli hostname allineati.
> [!WARNING]
> Ricorda che gli IP e hostname corretti reali e definitivi sono:
> *   **PVE1**: `10.10.10.11` -> hostname `pve1`
> *   **PVE2**: `10.10.10.21` -> hostname `pve2`
> *   **PVE3**: `10.10.10.31` -> hostname `pve3`

Su **tutti e tre i nodi** (`pve1`, `pve2`, `pve3`), apri `/etc/hosts` e assicurati che le righe relative all'infrastruttura Proxmox siano esattamente le seguenti (correggendo eventuali riferimenti al vecchio nome `pve` in `pve1`):
```text
10.10.10.11     pve1.pindaroli.local pve1
10.10.10.21     pve2.pindaroli.local pve2
10.10.10.31     pve3.pindaroli.local pve3
```

### Step 5.3: Verifica e Ripristino Corosync (Quorum)
Con PVE2 offline per molto tempo, Corosync potrebbe aver perso la sincronizzazione.
1. Accedi via SSH ad uno qualsiasi dei nodi (es. `pve1`) ed esegui:
   ```bash
   pvecm status
   ```
2. Controlla che tutti e 3 i nodi siano visibili e che compaia la dicitura `Quorum: Yes` o `Quorum acquired`.
3. **Troubleshooting in caso di Quorum Perduto**:
   Se il cluster Proxmox non acquisisce il quorum (perché vede solo 2 nodi su 3 o ha partizionamento di rete), forza temporaneamente il quorum ad un valore inferiore per sbloccare la GUI ed eseguire le modifiche:
   ```bash
   pvecm expected 2
   ```
   Quindi riavvia i servizi cluster sui nodi:
   ```bash
   systemctl restart pve-cluster
   systemctl restart corosync
   ```

---

## 6. Fase 6: ➡️ Ripristino Cluster Kubernetes (Talos)

> [!IMPORTANT]
> Il ripristino completo del cluster Kubernetes (talos-cp-02, etcd, CloudNativePG) è documentato ed eseguito interamente tramite il piano dedicato:
> ### [[talos-k8s-cluster-restoration]]
>
> Questo piano va eseguito come **ultimo step**, dopo che:
> - L'intero piano `[[pve2-reinstallation-migration]]` è completato (PVE2 online, VM 2300 ripristinata da PBS).
> - L'intero piano `[[pve3-10g-migration-recovery]]` (questo documento) è completato fino alla Fase 5.
> - Il cluster Proxmox ha **3 nodi in quorum stabile** (`pve1`, `pve2`, `pve3`).

## Dipendenze tra Piani

```
[[plan-out-of-band-service-access]]   → Infrastruttura OOB (COMPLETATO)
        ↓
[[pve2-reinstallation-migration]]     → PVE2 nuovo SSD, ripristino VM talos-cp-02
        ↓
[[pve3-10g-migration-recovery]]       → PVE3 migrazione 10G
        ↓
[[pve1-hostname-rename]]              → Rinomina Hostname PVE1 (pve → pve1)
        ↓
[[talos-k8s-cluster-restoration]]     ← QUESTO PIANO (eseguire per ultimo)
```

---

## 7. Piano di Verifica ed Accettazione (Test DR)

Una volta terminata la procedura, esegui questi controlli per confermare che l'intero Homelab sia perfettamente funzionante:

### Verifiche di Rete
*   [ ] Esegui un ping a tutti i nodi dal Mac Studio: `10.10.10.11`, `10.10.10.21`, `10.10.10.31`.
*   [ ] Esegui il check DNS dei servizi interni: `nslookup prowlarr.internal.pindaroli.org`.

### Verifiche dei Cluster
*   [ ] Controlla lo stato dei nodi Proxmox: verifica l'accesso individuale alle Web GUI di `pve1`, `pve2` e `pve3` e che gli hypervisor rispondano correttamente.
*   [ ] Controlla lo stato di Talos: `talosctl containers -n 10.10.20.142` per assicurarti che tutti i servizi di sistema siano up.
*   [ ] Controlla Kubernetes: `kubectl get pods -A | grep -v Running` (non devono esserci pod in CrashLoopBackOff a regime).

### Verifiche Database e Applicazioni
*   [ ] Controlla CNPG: `kubectl cnpg status postgres-main -n cnpg-system` o verifica i log dell'operatore. Il cluster deve essere in stato `Healthy` con 3 repliche attive.
*   [ ] Verifica l'accesso ai servizi principali: controlla che Lidarr, n8n, Jellyfin e gli altri servizi web siano raggiungibili e non presentino errori di connessione al database.

# PROMPT PER GEMINI DEEP SEARCH (Copia e Incolla - Piano Migrazione Semplificato Finale)

```text
Valuta e valida dal punto di vista dell'ingegneria del software, dell'affidabilità dei sistemi (SRE) e dell'amministrazione dei database il seguente Piano di Migrazione Fisica a 10G per un nodo Proxmox e il conseguente piano di Disaster Recovery e ripristino dei cluster (Proxmox, Talos Kubernetes e CloudNativePG).

L'homelab adotta una rete Out-of-Band (OOB) "Direct-Connect" fisica isolata su VLAN 99 (subnet 192.168.100.0/24), escludendo l'uso di Bastion Host virtuali per garantire la raggiungibilità dei sistemi anche se l'intera sala server e tutti gli hypervisor sono completamente spenti. Il client (Mac Studio in camera da letto) si connette alla rete OOB tramite un adattatore USB-to-Ethernet fisico dedicato ed esclusivo (IP statico 192.168.100.99, no gateway, no DNS) su switch-25g-letto (GoodTop). Le porte di servizio (OOB) dei tre nodi sono collegate allo switch switch-25g-server (LIAGUO) in sala server, e il traffico transita in trunk VLAN 99 taggata attraverso gli switch intermedi. La rete è ad accesso privato esclusivo dell'amministratore, quindi abbiamo escluso l'hardening enterprise (DAI, DHCP Snooping, BPDU Guard) per massima semplicità operativa.

---

## 1. CONTESTO DELL'INFRASTRUTTURA E STATO ATTUALE

L'homelab è composto da 3 hypervisor Proxmox VE 9.1 collegati a tre switch managed L2/L3 ed a un firewall OPNsense.

I nodi hypervisor ospitano un cluster Kubernetes gestito tramite il sistema operativo immutabile ed API-driven **Talos Linux (v1.12.0)** con 3 nodi Control Plane (CP) in Alta Affidabilità (HA), ed un cluster di database relazionale altamente resiliente gestito da **CloudNativePG (CNPG) PostgreSQL v18.1**.

### I Nodi Hypervisor (Proxmox VE 9.1):
- **Porte Principali 10G (Dati)**: I tre nodi Proxmox (PVE1, PVE2, PVE3) sono collegati direttamente tramite cavi DAC (Direct Attach Copper) allo switch a 10G **switch10g (ONTi)**.
- **Porte di Servizio (OOB - subnet `192.168.100.0/24`)**:
  - Le tre porte di servizio fisiche dei nodi (`eno3` su PVE1, `nic0` su PVE2, e la porta OOB di PVE3) **saranno collegate allo switch a 2.5G switch-25g-server (LIAGUO)** in sala server. Questo cablaggio fisico fa parte del piano.
  - IP statici dei nodi sulla rete OOB:
    - **PVE1**: `192.168.100.11/24` (Senza Gateway)
    - **PVE2**: `192.168.100.200/24` (Senza Gateway)
    - **PVE3**: `192.168.100.31/24` (Senza Gateway)

### Lo Storage del Database:
- Il database `postgres-main` utilizza dischi locali ad alte prestazioni (**Local-Path Storage**) vincolati fisicamente ai singoli nodi di controllo Talos per massimizzare le IOPS (non usa gli share NFS di TrueNAS).

---

## 2. DETTAGLIO DEL PIANO DI MANUTENZIONE E MIGRAZIONE (Fase Principale)

Il piano che intendiamo eseguire è suddiviso nelle seguenti macro-fasi:

### Fase A: Backup e Spegnimento Ordinato (Procedura a Freddo)
1. **Forzatura Backup**: Trigger manuale del job di backup di tutte le VM/LXC su Proxmox Backup Server (PBS).
2. **Backup Logico Proxmox**: Backup manuale della directory `/etc/pve` (pmxcfs logico) e del database sqlite `/var/lib/pve-cluster/config.db` su tutti i nodi attivi.
3. **Shutdown Kubernetes**: Spegnimento controllato dei nodi Talos attivi tramite comando `talosctl -n <IP> shutdown`.
4. **Shutdown Servizi e Storage**: Arresto dei container dipendenti (Jellyfin LXC 2200, PBS LXC 1400) e infine shutdown controllato di TrueNAS Scale (VM 1100) per garantire che ZFS esegua il flush totale delle cache sui dischi fisici.
5. **Spegnimento Fisico**: Shutdown dei nodi Proxmox satelliti (PVE3, PVE2) ed infine del Master (PVE1).

### Fase B: Intervento Fisico, Recablatura 10G e Rete PVE3
1. **Spostamento PVE3**: Scollegamento fisico dei cavi di PVE3 dallo switch a 2.5G e collegamento alle nuove porte SFP+ 10G del core switch ONTi (`switch10g`).
2. **Configurazione VLAN Switch**: Impostazione delle porte del switch 10G associate a PVE3 in modalità Access VLAN 10 (Server/Management) e Access VLAN 20 (Client VM).
3. **Boot ed Interface Renaming su PVE3**:
   - Boot isolato di PVE3 con accesso tramite la porta di servizio OOB fisica (`192.168.100.31`), garantendo connettività diretta dal Mac Studio anche con il resto del rack completamente spento.
   - Identificazione dei nuovi nomi logici assegnati da Debian alle interfacce 10G (es. `enp3s0f0` e `enp3s0f1` al posto di `nic0`/`nic1`) tramite comando `ip -c link`.
   - Modifica di `/etc/network/interfaces` per mappare i nuovi nomi logici sotto i bridge `vmbr10` e `vmbr20`.
   - Riavvio della rete e validazione della connettività al gateway.

### Fase C: Riaccensione dell'Homelab e Ripristino Quorum Proxmox
1. **Sequenza di Boot**: Avvio di PVE1 (TrueNAS parte per primo ed esporta le share NFS). Avvio di PVE2 e PVE3 (con hook "wait-for-truenas" per ritardare l'avvio delle VM fino alla disponibilità NFS).
2. **Allineamento Corosync**: Verifica del quorum Proxmox tramite `pvecm status`. Correzione preventiva degli IP dei nodi all'interno di `/etc/hosts` per eliminare vecchi riferimenti obsoleti ed assicurare il corretto funzionamento di `pmxcfs` e Corosync su IP reali:
   - `10.10.10.11` (PVE1)
   - `10.10.10.21` (PVE2)
   - `10.10.10.31` (PVE3)

### Fase D: Re-integrazione di Talos CP02 e Database CNPG
1. **Re-installazione Pulita di talos-cp-02**:
   - Montaggio dell'ISO di installazione di Talos sulla VM `2300` su PVE2 ed avvio in console.
   - Applicazione della configurazione specifica tramite comando:
     `talosctl apply-config -n 10.10.20.142 --file talos-config/controlplane-cp-02.yaml --insecure`
   - *Comportamento Atteso*: Poiché la configurazione contiene gli stessi segreti del cluster, l'Etcd Manager di Talos in esecuzione su CP01 e CP03 dovrebbe rilevare il nuovo nodo (con database etcd vuoto) e ri-accoglierlo automaticamente nel quorum etcd senza intervento manuale.
2. **Unfencing e Ripristino Database**:
   - Verifica dello stato di salute di Kubernetes (`kubectl get nodes`).
   - Rimozione del flag di *fencing* sul database CNPG `postgres-main`.
   - Ridimensionamento delle repliche CNPG a 3 per forzare l'operatore a allocare una nuova replica locale su `talos-cp-02` (tramite StorageClass `local-postgres`) e ri-sincronizzare i dati da zero dal nodo primario attivo.

---

## 3. DOMANDE PER LA VALIDAZIONE E L'ANALISI (DEEP SEARCH)

Chiedo un'analisi tecnica di alto livello, focalizzata sui seguenti nodi cruciali:

1. **Protocollo di Shutdown & NFS Stale Mounts**:
   - La sequenza proposta per lo spegnimento ed il riavvio è considerata robusta?
   - Quali sono i rischi legati ai client NFS (nodi Talos, LXC Jellyfin) se TrueNAS si spegne prima di loro o se si avvia dopo? Il meccanismo di hook su Proxmox ("wait-for-truenas") è sufficiente a prevenire "stale NFS mounts" ed instabilità del kernel linux?

2. **Modifica Network Interfaces e Rischio Corosync Split-Brain**:
   - Modificare la configurazione delle schede di rete e `/etc/network/interfaces` su PVE3 tramite connessione OOB fisica mentre gli altri due nodi Proxmox (PVE1, PVE2) sono spenti è una procedura sicura?
   - C'è il rischio che, al riavvio, il cluster Proxmox entri in split-brain o perda il quorum perché un nodo ha cambiato il proprio hardware di rete e non ha potuto scambiare i messaggi di heartbeat Corosync temporaneamente? Come possiamo blindare questa fase?

3. **Re-join etcd su Talos OS (La trappola del quorum)**:
   - L'Etcd Manager di Talos gestisce realmente in modo trasparente l'aggiunta di un nodo Control Plane (`talos-cp-02`) che era stato *precedentemente rimosso dal quorum* tramite comando `talosctl etcd remove-member`?
   - Quali sono i requisiti esatti e le potenziali trappole (es. token scaduti, disallineamento dell'ora NTP, UUID di etcd orfani) che potrebbero bloccare l'inclusione automatica del nodo? È consigliato eseguire un reset completo (`talosctl reset`) prima di inviare la configurazione?

4. **Ripristino Database CNPG su Local-Path Storage**:
   - Quando si ri-scala CNPG da 2 a 3 repliche su un nodo appena ricostruito, come si comporta l'operatore rispetto a vecchi PersistentVolume (PV) o PersistentVolumeClaim (PVC) orfani presenti sul disco locale?
   - C'è il rischio di conflitti di identità, o di lock residui (es. file `postmaster.pid` orfani su dischi fisici non formattati) che potrebbero indurre l'operatore in un loop infinito di riconciliazione ("dangling volumes")?
   - Qual è la procedura migliore per garantire che CNPG esegua un "clean sync" da zero sul proprio nodo?

5. **Consolidamento SRE (Disaster Recovery)**:
   - Fornisci una checklist finale di 5 punti critici da verificare assolutamente prima di spegnere i server per accertarsi che il ripristino sia matematicamente possibile senza perdite di dati.
```

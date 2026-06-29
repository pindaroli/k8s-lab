# Workflow: Node Maintenance & Safe Shutdown

Questa procedura descrive come preparare un nodo del cluster per la manutenzione fisica o lo spegnimento senza causare deadlock nei servizi critici (specialmente il Database).

## 1. Identificazione dei Carichi (Discovery)
Prima di spegnere il nodo (es. `talos-cp-02`), verifica cosa ci gira sopra:
```bash
kubectl get pods -A -o wide | grep <NOME_NODO>
```

> [!IMPORTANT]
> **Check Database (CNPG)**: Controlla se il nodo ospita un'istanza di `postgres-main`.
> ```bash
> kubectl get pods -n cnpg-system -o wide
> ```
> Se il nodo ospita un'istanza (es. `postgres-main-2`), segui il punto 2.

## 2. Preparazione Database (Solo per nodi con Postgres)
Se devi spegnere il nodo per più di qualche minuto, hai due opzioni:

### Opzione A: Mantenere l'Alta Affidabilità (Consigliato)
Se hai altri nodi liberi, sposta l'istanza:
1.  **Scala il cluster**: Aumenta temporaneamente le istanze (es. da 3 a 4).
2.  **Attendi**: Aspetta che la nuova istanza sia `Ready` su un altro nodo.
3.  **Elimina il PVC sul nodo da spegnere**: Cancella il PVC dell'istanza che sta sul nodo in manutenzione. L'operatore la ricreerà altrove.

### Opzione B: Riduzione Carico (Se non hai nodi extra)
1.  **Scala il cluster a 2**: `kubectl edit cluster postgres-main -n cnpg-system`.
2.  L'operatore eliminerà una delle istanze. Assicurati che quella eliminata sia quella sul nodo da spegnere.

## 3. Svuotamento del Nodo (Drain)
Esegui il drain per spostare tutti gli altri pod (Lidarr, n8n, ecc.) su altri nodi:
```bash
kubectl drain <NOME_NODO> --ignore-daemonsets --delete-emptydir-data
```

## 4. Spegnimento Fisico
Ora puoi spegnere l'host o la VM in sicurezza.

## 5. Ritorno alla Normalità
Dopo aver riacceso il nodo e verificato che sia `Ready` in Kubernetes:
1.  **Uncordon**: `kubectl uncordon <NOME_NODO>`.
2.  **Ri-scala il database**: Riporta le istanze al numero originale (es. 3).

---

## 💾 Proxmox Cluster Backup & Disaster Recovery
Per garantire la possibilità di un disaster recovery completo o di un rollback delle modifiche alle configurazioni del cluster ipervisore Proxmox VE (PVE1, PVE2, PVE3):

### 1. Locazione Fisica dei Backup (Mac Studio)
Tutti i backup di configurazione e di rete fisica dei nodi Proxmox vengono archiviati esternamente al cluster sul Mac Studio all'interno della directory:
`/Users/olindo/devices-backup/proxmox-cluster-config/`

La struttura delle sottocartelle è organizzata per host:
*   `/global/`: Contiene l'archivio `.tar.gz` di `/etc/pve/` (il cluster filesystem `pmxcfs` distribuito).
*   `/pve1/`: Contiene i file di configurazione locali e di rete fisica di PVE1.
*   `/pve2/`: Contiene i file di configurazione locali e di rete fisica di PVE2.
*   `/pve3/`: Contiene i file di configurazione locali e di rete fisica di PVE3.

### 2. Procedura di Backup Manuale (Configurazioni)
Per eseguire un backup fresco delle configurazioni ed esportarlo sul Mac Studio:
```bash
# 1. Su PVE1 (OOB 192.168.100.11), crea l'archivio del cluster filesystem escludendo le chiavi SSH
ssh root@192.168.100.11 "tar -czf /root/proxmox_cluster_backup_\$(date +%Y%m%d).tar.gz --exclude='/etc/pve/priv/authorized_keys' /etc/pve"

# 2. Scarica il backup globale sul Mac Studio
scp "root@192.168.100.11:/root/proxmox_cluster_backup_*.tar.gz" /Users/olindo/devices-backup/proxmox-cluster-config/global/

# 3. Scarica i file locali dei nodi (es. interfaces e hosts)
scp root@192.168.100.11:/etc/{hostname,hosts,network/interfaces,resolv.conf} /Users/olindo/devices-backup/proxmox-cluster-config/pve1/
scp root@10.10.10.21:/etc/{hostname,hosts,network/interfaces,resolv.conf} /Users/olindo/devices-backup/proxmox-cluster-config/pve2/
scp root@10.10.10.31:/etc/{hostname,hosts,network/interfaces,resolv.conf} /Users/olindo/devices-backup/proxmox-cluster-config/pve3/
```

### 3. Procedura di Ripristino (Disaster Recovery)
Se un nodo del cluster viene reinstallato da zero o le configurazioni risultano corrotte:
1.  **Ferma i servizi del cluster** su tutti i nodi per evitare conflitti distribuiti:
    `systemctl stop pve-cluster corosync`
2.  **Monta il filesystem in modalità locale** sul nodo da ripristinare:
    `pmxcfs -l`
3.  **Scompatta il backup di `/etc/pve`** sovrascrivendo la radice virtuale:
    `tar -xzf /Users/olindo/devices-backup/proxmox-cluster-config/global/proxmox_cluster_backup_DATE.tar.gz -C /`
4.  **Ripristina i file locali di rete** (es. `/etc/network/interfaces` e `/etc/hosts`) copiandoli dalla directory del rispettivo nodo.
5.  **Riavvia i servizi di cluster** o riavvia la macchina fisica:
    `systemctl start corosync pve-cluster pvedaemon pveproxy`
    All'avvio, Corosync sincronizzerà in tempo reale la configurazione ripristinata con gli altri nodi.

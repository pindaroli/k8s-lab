# Strategia di Backup "Smart Ibrida" 🧠

Questa strategia bilancia la robustezza di ZFS con la flessibilità di Proxmox Backup Server (PBS) e Point-In-Time Recovery per i Database.

## 1. Il Piano d'Azione (I 3 Livelli)

| Livello | Oggetto | Metodo | Frequenza | Destinazione | Scenario Recupero (Disaster Recovery) |
|---|---|---|---|---|---|
| **HARDWARE** | **Intero Pool NVMe** | **ZFS Replication** | Ogni ora | HDD `oliraid` | **Disastro Totale**. Muore l'SSD NVMe. Cloni indietro tutto il pool. Zero config, riparti in 5 min. |
| **SISTEMA** | **VM Proxmox (OS)** | **PBS (LXC)** | Ogni Ora | NFS `backup-proxmox` | **VM corrotta**. Aggiornamento Talos andato male? Restore della VM dal GUI di Proxmox in 1 click. Deduplica efficientissima. |
| **APPLICAZIONE** | **Database Postgres** | **CNPG Backup** | Ogni 6h / WAL | NFS / S3 | **Errore Umano**. Hai cancellato una tabella? Restore puntuale (Point-In-Time) senza toccare le altre VM. |
| **DATI UTENTE** | **Media / Config** | **ZFS Snapshot** | Notte | HDD `oliraid` | **Ransomware/Errore**. Hai cancellato un file? Entri nella cartella `.zfs/snapshot` nascosta e lo copi indietro. |

---

## 2. Dettagli Implementativi

### A. Livello Storage (TrueNAS) - La Rete di Sicurezza
1.  **Snapshot Task**: Recursive su `stripe` (NVMe). Frequenza: 30 min. Retention: 2 settimane.
2.  **Replication Task**:
    *   Sorgente: `stripe`
    *   Destinazione: `oliraid/backup-stripe` (HDD).
    *   Risultato: Hai una copia "Cold" sempre pronta.

### B. Livello Proxmox - Proxmox Backup Server (PBS)
**Implementazione Attuale**: Installato come **LXC Container** su **Proxmox Node 1 (`pve`)**.
*   **ID**: `1400`
*   **IP**: `10.10.10.100` (`pbs.pindaroli.org`)
*   **OS**: Debian 13 (Trixie) - Manual Install.

**Configurazione**:
1.  **LXC PBS**: Deploy Manuale (`pct create`) su `pve`.
2.  **Storage**: Monta la share NFS `oliraid/pbs-store` su `/mnt/pbs-store`.
3.  **Datastore**: `pbs-store` creato su tale mount.
4.  **Job**: Backup Automatico (Snapshot) di TUTTE le VM/LXC ogni notte alle 02:00.
5.  **Retention**: Keep Last 3, Daily 7, Weekly 4.
6.  **Sicurezza**: Se muore l'LXC, i dati sono salvi sul NAS. Reinstalli un LXC vuoto, colleghi lo storage, e i backup tornano (Fingerprint/Key richiesti).

### 3. Postgres Backup (CloudNativePG)
- **Method**: WAL Archiving to S3 Object Store.
- **Backend**: **MinIO App** on TrueNAS Scale.
  - **URL**: `http://10.10.10.50:9000` (Internal Host Network)
  - **Bucket**: `postgres-wal`
  - **Storage**: Host Path `/mnt/oliraid/cnpg-wal`
  - **User**: `minio` (UID 3000)
- **CSI Driver**: Not used for backup (Direct S3 protocol).
- **Retention**: 30 Days (configured in `cluster.yaml`).
- **Recovery**: Point-In-Time Recovery (PITR) enabled via Barman.

---

## 3. Perché questa strategia è "Furbissima"?
1.  **ZFS** fa il lavoro sporco (Heavy Lifting) senza impattare le prestazioni.
2.  **PBS** deduplica i dati identici delle VM Talos (risparmiando il 90% di spazio).
3.  **CNPG** ti protegge dagli errori logici ("Ho cancellato il cliente X").

Questa architettura copre ogni scenario di guasto possibile nel tuo homelab.

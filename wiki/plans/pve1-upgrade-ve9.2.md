---
title: "Upgrade PVE1 a Proxmox VE 9.2"
type: plan
status: archived
certified_for_ai: false
created_at: 2026-06-27
archived_at: 2026-06-27
tags:
  - "#plan"
  - "#storage"
  - "#proxmox"
  - "#talos"
---

# Upgrade PVE1 a Proxmox VE 9.2

Questo piano descrive i passaggi per aggiornare **PVE1** (il nodo master attuale del cluster) a Proxmox VE 9.2 tramite un in-place upgrade, garantendo la continuità dei servizi critici ospitati localmente (TrueNAS, PBS e Talos Control Plane).

## User Review Required

> [!IMPORTANT]
> **SPEGNIMENTO SERVIZI CRITICI**:
> Durante l'upgrade e il conseguente reboot di PVE1, la VM **TrueNAS (1100)** verrà arrestata. Questo significa che tutti i nodi e i servizi del cluster che consumano storage NFS/SMB (come Jellyfin, Lidarr, Radarr, e i pod Kubernetes) perderanno temporaneamente la connessione allo storage.
> Per evitare blocchi o corruzioni di dati (I/O hang), tutti i pod applicativi e gli LXC dipendenti su PVE3 dovranno essere arrestati o messi in pausa prima di procedere.

> [!TIP]
> **PREVENZIONE HANG GRAFICO (NOMODESET)**:
> PVE1 è equipaggiato con una CPU **AMD Ryzen 9 7945HX** con GPU integrata **Raphael**. Benché questa GPU sia storicamente stabile su Linux, per prevenire qualsiasi hang grafico all'avvio con il nuovo kernel 7.x (analogo al problema di PVE3), **applicheremo preventivamente `nomodeset` in `/etc/kernel/cmdline` prima del riavvio**. Questo elimina alla radice la possibilità di blocchi del KMS della GPU.

---

## Stato Attuale (Raccolta Dati)
* **CPU**: AMD Ryzen 9 7945HX with Radeon Graphics
* **GPU**: AMD Raphael (rev d8)
* **OS**: Proxmox VE 9.1.1 (running kernel: `6.17.2-1-pve`).
* **Bootloader**: UEFI gestito via `systemd-boot` (partizione EFI `AB91-646A`).
* **Sorgenti APT**: Repository `pve-no-subscription` (trixie) già configurato e abilitato.
* **VM/LXC attivi su PVE1**:
  - `1100` (truenas) - Running
  - `1300` (talos-cp-01) - Running
  - `1400` (pbs) - Running (LXC)

---

## Proposed Changes

### FASE 1: Preparazione e Spegnimento Ordinato

1. **Stop Workloads Kubernetes**:
   Mettere in manutenzione o spegnere i pod non critici su K8s per evitare scritture pendenti su TrueNAS.
2. **Spegnimento VM Talos Control Plane (`1300`)**:
   Arrestare la VM `talos-cp-01` per evitare split-brain transitori o tentativi continui di riconnessione a etcd:
   ```bash
   qm shutdown 1300
   ```
3. **Spegnimento LXC Proxmox Backup Server (`1400`)**:
   ```bash
   pct shutdown 1400
   ```
4. **Spegnimento Ordinato TrueNAS (`1100`)**:
   Questo è l'ultimo step di spegnimento delle macchine per garantire che tutti i file system NFS siano chiusi:
   ```bash
   qm shutdown 1100
   ```
   *Verificare con `qm status 1100` che la macchina sia effettivamente in stato `stopped`.*

---

### FASE 2: In-Place Upgrade di PVE1

1. Accedere in SSH a PVE1 (`10.10.10.11` o OOB `192.168.100.11`).
2. Sincronizzare i pacchetti ed eseguire l'avanzamento di versione:
   ```bash
   apt update
   apt dist-upgrade -y
   ```
3. **Applicazione Preventiva `nomodeset`**:
   Per prevenire blocchi della GPU integrata AMD Raphael col nuovo kernel, modifichiamo `/etc/kernel/cmdline` appendendo `nomodeset` all'unica riga.
   - Leggere la configurazione attuale:
     ```bash
     cat /etc/kernel/cmdline
     ```
   - Esempio di riga attesa: `root=ZFS=rpool/ROOT/pve-1 boot=zfs`
   - Modificare la riga aggiungendo `nomodeset` in fondo (separato da uno spazio).
4. Rigenerare le voci di boot di `systemd-boot` per applicare i nuovi parametri su tutte le partizioni EFI:
   ```bash
   proxmox-boot-tool refresh
   ```
5. Riavviare il nodo:
   ```bash
   reboot
   ```

---

### FASE 3: Verifica Boot e Ripristino Servizi

1. Verificare che PVE1 risponda al ping e che la console sia raggiungibile.
2. Controllare la versione di Proxmox e il kernel in esecuzione:
   ```bash
   pveversion
   cat /proc/cmdline
   ```
3. **Avvio Sequenziale delle VM/LXC**:
   - Avviare **TrueNAS (`1100`)** per primo per ristabilire lo storage NFS/SMB:
     ```bash
     qm start 1100
     ```
     *(Attendere che TrueNAS sia completamente online e che le share NFS siano esportate)*
   - Avviare **PBS (`1400`)**:
     ```bash
     pct start 1400
     ```
   - Avviare **talos-cp-01 (`1300`)**:
     ```bash
     qm start 1300
     ```

---

## Verification Plan

### Automated Tests
- `pveversion` su PVE1 per confermare la versione 9.2.x.
- `pvecm status` per confermare che PVE1 e PVE3 ristabiliscano il quorum.
- `kubectl get nodes` (dal Mac Studio) per confermare che `talos-cp-01` torni online e Ready.

### Manual Verification
- Accesso alla GUI di Proxmox di PVE1 (`https://10.10.10.11:8006`).
- Verifica del mount corretto delle share NFS di TrueNAS su PVE3 e PVE1.

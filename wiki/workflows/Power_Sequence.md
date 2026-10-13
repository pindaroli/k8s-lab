---
title: "Workflow: Safe Shutdown & Startup Sequence"
last_updated: "2026-10-13"
confidence: "High"
tags:
  - "#workflow"
  - "#maintenance"
  - "#automation"
  - "#power"
  - "#wol"
---

# Safe Shutdown & Startup (Rack Power Orchestration)

Questa procedura garantisce la coerenza dei dati e l'idempotenza durante lo spegnimento o l'accensione dell'intero rack Homelab, supportando sia la modalità **Full Rack** sia la modalità a risparmio energetico **Eco (TrueNAS-only)**.

---

## 🧭 Matrice delle Procedure Disponibili

| Obiettivo Operativo | Script Eseguibile | Playbook Ansible Sottostante | Notifiche Start & Stop | Notifiche Intermedie | Notifica di Errore |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Startup Completo (Full Rack)** | [`startup_all_lab.sh`](file:///Users/olindo/prj/k8s-lab/scripts/infrastructure/startup_all_lab.sh) | `ansible/playbooks/infrastructure/startup_all_lab.yml` | Telegram + Email HTML | Solo Telegram (nodi) | Telegram + Email con **Log Allegato** |
| **Startup da TrueNAS-only** | [`startup_from_truenas_only.sh`](file:///Users/olindo/prj/k8s-lab/scripts/infrastructure/startup_from_truenas_only.sh) | `ansible/playbooks/infrastructure/startup_from_truenas_only.yml` | Telegram + Email HTML | Solo Telegram (nodi) | Telegram + Email con **Log Allegato** |
| **Shutdown a TrueNAS-only (Eco)**| [`shutdown_to_truenas_only.sh`](file:///Users/olindo/prj/k8s-lab/scripts/infrastructure/shutdown_to_truenas_only.sh) | `ansible/playbooks/infrastructure/shutdown_to_truenas_only.yml` | Telegram + Email HTML | Solo Telegram (step) | Telegram + Email con **Log Allegato** |
| **Shutdown Completo (Rack Dark)** | [`shutdown_all_lab.sh`](file:///Users/olindo/prj/k8s-lab/scripts/infrastructure/shutdown_all_lab.sh) | `ansible/playbooks/infrastructure/shutdown_all_lab.yml` | Telegram + Email HTML | Solo Telegram (step) | Telegram + Email con **Log Allegato** |

---

## 1. Procedure di Startup (Accensione)

### 1.1 Startup Completo dell'Intero Homelab (`startup_all_lab`)
Avvia da freddo (S5) TrueNAS Bare Metal, ne verifica la salute storage e successivamente sveglia i nodi Proxmox e il cluster Talos:
```bash
./scripts/infrastructure/startup_all_lab.sh
```
**Checkpoint Vincolanti**:
1. **WoL Idempotente TrueNAS**: probe porta 22 su `10.10.20.50` (se già online salta il WoL).
2. **Gate TrueNAS SSH & WebUI**: attesa porte 22 e 443.
3. **Gate ZFS Health**: verifica via SSH `zpool status -x` che confermi `all pools are healthy` (`stripe` e `oliraid`).
4. **Gate Storage Services**: attesa porte 3000 (Homepage), 8080 (qBittorrent), 8096 (Jellyfin) ed export NFS. *(Notifica Telegram)*.
5. **Innesco Sequenza PVE**: avvio automatico di `startup_from_truenas_only`.

---

### 1.2 Startup da Modalità Solo TrueNAS (`startup_from_truenas_only`)
Porta l'Homelab dalla modalità eco (solo storage attivo) a pieno regime computazionale:
```bash
./scripts/infrastructure/startup_from_truenas_only.sh
```
**Checkpoint Vincolanti**:
1. **WoL Idempotente PVE**: probe porta 22 su `pve1`, `pve2`, `pve3` $\rightarrow$ invio Magic Packet mirato solo ai nodi spenti.
2. **Gate PVE Hypervisors**: attesa porte 22 (SSH) e 8006 (WebUI) su tutti i 3 nodi. *(Notifica Telegram)*.
3. **Gate Talos & K8s VIP**: attesa porta 50000 e API Server K8s su VIP `10.10.20.55:6443`. *(Notifica Telegram)*.
4. **Sync Barrier (Anti-Valanga)**: polling affinché `talos-cp-01`, `talos-cp-02` e `talos-cp-03` abbiano simultaneamente `Ready=True`. Segue una pausa di grazia di 10s per Flannel CNI. *(Notifica Telegram)*.
5. **Uncordon Atomico Parallelo**: sblocco contemporaneo dello scheduling con preservazione del taint `control-plane:NoSchedule` su `talos-cp-03`. *(Notifica Telegram)*.
6. **Health-Check Finale**: verifica Traefik Ingress VIP `10.10.20.56:443` e cluster CloudNativePG `postgres-main`.

---

## 2. Procedure di Shutdown (Spegnimento)

### 2.1 Spegnimento a Risparmio Energetico (`shutdown_to_truenas_only`)
Spegne in sicurezza i workload Kubernetes e gli hypervisor fisici Proxmox VE, lasciando TrueNAS attivo 24/7 per Servarr e storage:
```bash
./scripts/infrastructure/shutdown_to_truenas_only.sh
```
**Fasi Operative**:
1. Cordon globale dei nodi Talos per prevenire rescheduling indesiderato.
2. Esecuzione `CHECKPOINT;` nel database PostgreSQL (`postgres-main`).
3. Invio segnale di spegnimento parallelo Talos OS (`talosctl shutdown`) e verifica porte 50000, 6443, 443 STOPPED. *(Notifica Telegram)*.
4. Shutdown ACPI satelliti Proxmox (`pve3`, `pve2`) e successivamente del master (`pve1`). Verifica porte 22 e 8006 STOPPED. *(Notifica Telegram)*.
5. Verifica servizi permanenti TrueNAS.

---

### 2.2 Spegnimento Totale del Rack (`shutdown_all_lab`)
Esegue la procedura completa di arresto per portare l'intero rack a zero consumo (PDU/UPS safe):
```bash
./scripts/infrastructure/shutdown_all_lab.sh
```
**Fasi Operative**:
1. Esecuzione completa di `shutdown_to_truenas_only` (K8s e PVE offline).
2. Flush I/O dei file system e pool ZFS su TrueNAS (`sync`).
3. Shutdown controllato TrueNAS via comando diretto: `sudo -n shutdown -h now` (segnale diretto a systemd, bypass code middleware).
4. Verifica chiusura porta SSH 22 su TrueNAS (STOPPED) con polling visivo. *(Notifica Telegram)*.

---

## 🛡️ Gestione Errori e Notifiche

- **Libreria Centralizzata**: [`scripts/infrastructure/utils.sh`](file:///Users/olindo/prj/k8s-lab/scripts/infrastructure/utils.sh).
- **Zero Plaintext Secrets**: tutte le credenziali (Telegram bot/chat ID e credenziali SMTP Gmail) vengono caricate dinamicamente in memoria tramite `sops` dai file cifrati in `secrets-sops/`.
- **Trap di Errore**: in caso di fallimento di qualsiasi comando o checkpoint, lo script bash intercetta l'uscita anomala (`trap ERR`), invia un alert immediato su Telegram e inoltra un'email HTML con **allegato il file di log completo della sessione** salvato in `logs/automation/`.

---

## 🔗 Relazioni & Riferimenti
- Piano Operativo: [[homelab-full-power-automation]]
- Utilità WoL: [`wake_node.py`](file:///Users/olindo/prj/k8s-lab/scripts/network/wake_node.py)
- Componenti: [[TrueNAS]], [[Talos_Cluster]], [[OPNsense]], [[sops-secret-sovereignty]]

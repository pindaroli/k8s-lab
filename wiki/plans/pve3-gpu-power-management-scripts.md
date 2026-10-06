---
title: "Piano: Script di Gestione Energetica GPU Radeon 890M su PVE3 e Backup Host PBS"
type: plan
status: completed
certified_for_ai: true
created_at: 2026-10-05
completed_at: 2026-10-05
tags:
  - "#pve3"
  - "#gpu"
  - "#power-management"
  - "#amdgpu"
  - "#pbs"
  - "#backup"
  - "#automation"
  - "#gaming"
---

# Piano: Script di Gestione Energetica GPU Radeon 890M su PVE3 e Backup Host PBS

Il presente piano definisce l'implementazione, l'integrazione Git, l'installazione su **PVE3** (`10.10.10.31`) e la strategia di **backup automatico su Proxmox Backup Server (PBS)** dei tre script di gestione dei profili energetici della iGPU **AMD Radeon 890M (RDNA 3.5)**:
- `gpu-turbo`: forza la GPU a 2900 MHz (profilo `high`).
- `gpu-eco`: ripristina la modulazione dinamica (profilo `auto`, idle a 600 MHz per risparmiare 8–15W).
- `gpu-mode`: interroga lo stato energetico del kernel e la frequenza di clock istantanea.

---

## 1. Decisioni Architetturali e Scelte Utente

In accordo con le scelte architetturali concordate con l'utente:
1. **Source of Truth su Git (Repository `k8s-lab`)**:
   - I file sorgente risiedono stabilmente in `scripts/infrastructure/` nel repository Git.
   - Garantisce tracciamento, versioning semantico e resilienza contro reinstallazioni disastrose bare-metal.
2. **Deploy Atomico su PVE3 (`/usr/local/bin/`)**:
   - I tre script vengono copiati in `/usr/local/bin/` con permessi `755` (`root:root`).
   - La gerarchia `/usr/local/bin/` resiste al 100% ad aggiornamenti del sistema operativo, pacchetti apt e future versioni di Proxmox VE.
3. **Backup Automatico Host su PBS (Opzione 1 Selezionata)**:
   - Configurazione su PVE3 di un'automazione notturna basata sul client ufficiale `/usr/bin/proxmox-backup-client` verso il datastore `pbs-store` su **PBS** (`10.10.10.100`).
   - Esegue il backup deduplicato e crittografato di `/usr/local/bin/` e delle configurazioni locali dell'host.
   - *Scelta esclusa su indicazione dell'utente*: scartata la copia in chiaro su share NFS TrueNAS (si fa affidamento esclusivo su PBS e Git).
4. **Semplificazione Alias macOS (`~/.zshrc`)**:
   - Gli alias locali sul Mac Studio delegano direttamente l'invocazione degli script remoti (`ssh root@10.10.10.31 <script>`).

---

## 2. Specifiche dei File Sorgente

I sorgenti vengono collocati nel repository `k8s-lab` in `scripts/infrastructure/`:

### A. `scripts/infrastructure/pve3-gpu-turbo.sh`
```bash
#!/bin/bash
set -e
echo high > /sys/class/drm/card0/device/power_dpm_force_performance_level
echo "GPU PVE3: TURBO (2900MHz / high)"
```

### B. `scripts/infrastructure/pve3-gpu-eco.sh`
```bash
#!/bin/bash
set -e
echo auto > /sys/class/drm/card0/device/power_dpm_force_performance_level
echo "GPU PVE3: ECO (auto-scaling)"
```

### C. `scripts/infrastructure/pve3-gpu-mode.sh`
```bash
#!/bin/bash
set -e
printf "GPU Mode: "
cat /sys/class/drm/card0/device/power_dpm_force_performance_level
printf "Clock: "
grep "*" /sys/class/drm/card0/device/pp_dpm_sclk || true
```

---

## 3. Fasi Operative Dettagliate (Test-Driven Protocol)

### Fase 1: Creazione Sorgenti in Git e Deploy su PVE3
- **Obiettivo**: Creare i tre file in `scripts/infrastructure/` e copiarli su PVE3 in `/usr/local/bin/` con permessi `755`.
- **Azioni**:
  1. Scrittura dei tre file sorgente nel repository.
  2. Deploy via SSH su PVE3 (`/usr/local/bin/gpu-turbo`, `/usr/local/bin/gpu-eco`, `/usr/local/bin/gpu-mode`).
  3. Applicazione permessi `chmod 755 /usr/local/bin/gpu-*`.
- **Verifica**: `ssh root@10.10.10.31 "ls -la /usr/local/bin/gpu-*"` conferma ownership `root:root` e permessi `rwxr-xr-x`.

---

### Fase 2: Validazione Funzionale su PVE3
- **Obiettivo**: Eseguire sequenzialmente i comandi per accertare il cambio di stato del driver `amdgpu`.
- **Passi**:
  1. Esecuzione `gpu-turbo` → verifica: `/sys/class/drm/card0/device/power_dpm_force_performance_level` contiene `high`.
  2. Esecuzione `gpu-mode` → verifica output formattato (`GPU Mode: high`).
  3. Esecuzione `gpu-eco` → verifica: ripristino ad `auto` e sclk minimo a 600 MHz.
  4. Esecuzione `gpu-mode` → verifica output formattato (`GPU Mode: auto`).

---

### Fase 3: Configurazione Backup Host Automatico su PBS (Opzione 1)
- **Obiettivo**: Automatizzare il salvataggio notturno di `/usr/local/bin` sul datastore `pbs-store` di PBS (`10.10.10.100`).
- **Azioni**:
  1. Creare lo script di backup `/usr/local/bin/pve3-host-backup-pbs.sh`:
     ```bash
     #!/bin/bash
     set -e
     export PBS_REPOSITORY="root@pam@10.10.10.100:pbs-store"
     export PBS_FINGERPRINT="93:B3:92:68:5C:04:3C:30:18:EF:CB:53:09:6B:A6:1F:0E:4C:94:F6:76:08:CC:56:13:8B:19:31:86:9C:87:EF"
     proxmox-backup-client backup \
       scripts.pxar:/usr/local/bin \
       --backup-id pve3-host \
       --backup-type host
     ```
  2. Creare il systemd service e timer `/etc/systemd/system/pve3-host-backup.timer` (esecuzione quotidiana alle ore 03:30).
  3. Abilitare il timer (`systemctl enable --now pve3-host-backup.timer`).
- **Verifica**:
  - Esecuzione di prova manuale del backup con `pve3-host-backup-pbs.sh`.
  - Ispezione con `proxmox-backup-client snapshot list --repository root@pam@10.10.10.100:pbs-store` per validare la presenza dello snapshot `host/pve3-host/<timestamp>`.

---

### Fase 4: Aggiornamento Alias macOS (`~/.zshrc`)
- **Obiettivo**: Snellire gli alias su Mac Studio delegandoli ai nuovi comandi nativi di PVE3:
  ```zsh
  alias gpu-turbo="ssh root@10.10.10.31 gpu-turbo"
  alias gpu-eco="ssh root@10.10.10.31 gpu-eco"
  alias gpu-mode="ssh root@10.10.10.31 gpu-mode"
  ```
- **Verifica**: Esecuzione `gpu-mode` da Mac per validare l'invocazione pulita.

---

## 💾 Stato di Ripristino (AI Save-State)
- **Fase Attiva**: Tutte le Fasi Completate con Successo ✅
- **Ultima Azione Completata**: Fase 3 e Fase 4 completate. Primo backup host su PBS eseguito e verificato (`host/pve3-host/2026-10-05T14:54:11Z`), systemd timer notturno (`03:30`) abilitato su PVE3. Alias in `~/.zshrc` su Mac snelliti e verificati. Autostart verificato per VM `pbs` e impostato a `unless-stopped` per App `garage` su TrueNAS SCALE.
- **Prossimo Passo Operativo**: Nessuno, piano concluso e operativo.
- **Evoluzione**: Implementata l'automazione ad eventi e l'orchestrazione LXC tra Steam e Ollama documentata in [[pve3-lxc-steam-ollama-gpu-orchestration]].
- **Blocchi/Decisioni Pendenti**: Nessuno.

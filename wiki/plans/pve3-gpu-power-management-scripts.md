---
title: "Piano: Script di Gestione Energetica GPU Radeon 890M su PVE3"
type: plan
status: active
certified_for_ai: true
created_at: 2026-10-05
tags:
  - "#pve3"
  - "#gpu"
  - "#power-management"
  - "#amdgpu"
  - "#automation"
  - "#gaming"
---

# Piano: Script di Gestione Energetica GPU Radeon 890M su PVE3

Il presente piano definisce l'implementazione, l'installazione e la verifica di tre script shell nativi su **PVE3** (`10.10.10.31`) per la gestione puntuale dei profili di potenza della iGPU **AMD Radeon 890M (RDNA 3.5)**:
- `/usr/local/bin/gpu-turbo`
- `/usr/local/bin/gpu-eco`
- `/usr/local/bin/gpu-mode`

Inoltre, il piano prevede l'allineamento degli alias locali su macOS (`~/.zshrc`) per invocare direttamente i comandi remoti standardizzati.

---

## 1. Architettura e Razionale Tecnico

Su PVE3 (Proxmox VE 9.2, kernel Linux 6.8+ / Debian 13 Trixie), il driver kernel `amdgpu` espone il sottosistema Dynamic Power Management (DPM) tramite sysfs:
- **Controllo Profilo Energetico**: `/sys/class/drm/card0/device/power_dpm_force_performance_level`
  - `high`: forza il clock di baseline del motore grafico (`sclk`) a **2900 MHz** e il bus Infinity Fabric (`fclk`) a **1960 MHz**, eliminando la latenza di transizione energetica per carichi gaming (Fallout 4, Steam, ecc.).
  - `auto`: ripristina la modulazione dinamica (frequenza minima 600 MHz a riposo, risparmio di 8–15 Watt continuativi).
- **Stato Operativo Istantaneo**: `/sys/class/drm/card0/device/pp_dpm_sclk` (visualizzazione del clock attivo contraddistinto da `*`).

Installare questi script in `/usr/local/bin/` su PVE3 garantisce:
1. **Esecuzione Atomica e Nativa**: gli script risiedono direttamente sul nodo Proxmox host dove il driver amdgpu è proprietario dei device node.
2. **Accessibilità Universale**: utilizzabili direttamente da shell PVE3, da chiamate SSH remote (Mac Studio, script di automazione) e da job di orchestrazione.
3. **Semplicità e Manutenibilità**: niente stringhe complesse annidate negli alias del Mac.

---

## 2. Specifiche degli Script

### A. `/usr/local/bin/gpu-turbo`
- **Scopo**: Attiva la modalità prestazioni massime (2900 MHz).
- **Logica**:
  ```bash
  #!/bin/bash
  set -e
  echo high > /sys/class/drm/card0/device/power_dpm_force_performance_level
  echo "GPU PVE3: TURBO (2900MHz / high)"
  ```

### B. `/usr/local/bin/gpu-eco`
- **Scopo**: Ripristina il dynamic scaling a basso consumo (600 MHz in idle).
- **Logica**:
  ```bash
  #!/bin/bash
  set -e
  echo auto > /sys/class/drm/card0/device/power_dpm_force_performance_level
  echo "GPU PVE3: ECO (auto-scaling)"
  ```

### C. `/usr/local/bin/gpu-mode`
- **Scopo**: Stampa a video la modalità DPM attiva e il clock operativo in MHz.
- **Logica**:
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

### Fase 1: Creazione e Permessi degli Script su PVE3
- **Obiettivo**: Scrivere i 3 script in `/usr/local/bin/` su PVE3 e renderli eseguibili (`chmod 755`).
- **Verifica**: Ispezione con `ls -la /usr/local/bin/gpu-*` per confermare permessi `rwxr-xr-x` e proprietario `root:root`.

### Fase 2: Test Funzionale Individuale su PVE3
- **Obiettivo**: Eseguire sequenzialmente i comandi in locale su PVE3 per validare il cambio di stato del kernel.
- **Passi**:
  1. Esecuzione `/usr/local/bin/gpu-turbo` → verifica: `/sys/class/drm/card0/device/power_dpm_force_performance_level` contiene `high`.
  2. Esecuzione `/usr/local/bin/gpu-mode` → verifica: output formattato con `GPU Mode: high`.
  3. Esecuzione `/usr/local/bin/gpu-eco` → verifica: ritorno a `auto`.
  4. Esecuzione `/usr/local/bin/gpu-mode` → verifica: output con `GPU Mode: auto`.

### Fase 3: Semplificazione Alias su macOS (`~/.zshrc`)
- **Obiettivo**: Aggiornare gli alias nel file `~/.zshrc` del Mac Studio per invocare direttamente i comandi remoti:
  - `alias gpu-turbo="ssh root@10.10.10.31 gpu-turbo"`
  - `alias gpu-eco="ssh root@10.10.10.31 gpu-eco"`
  - `alias gpu-mode="ssh root@10.10.10.31 gpu-mode"`
- **Verifica**: Esecuzione `gpu-mode` dal Mac per confermare la corretta delega remota.

---

## 💾 Stato di Ripristino (AI Save-State)
- **Fase Attiva**: Fase 1 — Creazione e Permessi degli Script su PVE3
- **Ultima Azione Completata**: Redazione del piano operativo e formalizzazione dei requisiti.
- **Prossimo Passo Operativo**: Creazione dei tre script `/usr/local/bin/gpu-turbo`, `/usr/local/bin/gpu-eco`, `/usr/local/bin/gpu-mode` su PVE3 (`10.10.10.31`).
- **Blocchi/Decisioni Pendenti**: In attesa di approvazione esplicita dell'utente per l'esecuzione della Fase 1.

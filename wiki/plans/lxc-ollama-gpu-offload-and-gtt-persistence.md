---
title: "Piano: Ottimizzazione 100% GPU Offload per Modelli 32B su LXC Ollama e Persistenza Kernel VRAM GTT/TTM su PVE3"
type: plan
status: completed
certified_for_ai: true
created_at: 2026-10-21
completed_at: 2026-10-21
tags:
  - "#pve3"
  - "#ollama"
  - "#lxc"
  - "#vulkan"
  - "#rdna35"
  - "#gtt"
  - "#ttm"
  - "#ansible"
  - "#guidellm"
---

# Piano: Ottimizzazione 100% GPU Offload per Modelli 32B su LXC Ollama e Persistenza Kernel VRAM GTT/TTM su PVE3

Il presente piano operativo risolve il collo di bottiglia rilevato sul nodo **`lxc-ollama`** (`10.10.20.33`, CT 300 su **PVE3**) durante l'esecuzione del modello **`qwen2.5:32b-instruct-q5_K_M`**, eliminando l'offload parziale su CPU (`23% CPU / 77% GPU`, 3.45 tok/s) e garantendo in modo **100% permanente e dichiarativo** sia l'allocazione integrale su GPU nell'immediato, sia la persistenza a livello boot EFI dei limiti kernel `amdgpu.gttsize` e `ttm.pages_limit` (54 GiB) su PVE3.

---

## 🗺️ Mappe Concettuali e Relazioni
- [[purpose]] (Governance Homelab e Principi Core)
- [[SCHEMA]] (Regole di Governance del Wiki)
- [[Ollama]] (Entità Flotta Ollama Homelab)
- [[Network_Registry]] (Single Source of Truth `rete.json`)
- [[lxc-ollama-hardware-limit-optimization]] (Dimensionamento Hardware 54 GB / 20 vCPU del CT 300)
- [[lxc-ollama-llama-ocr-qwen25-sidecar]] (Sidecar Vision/OCR `llama-ocr` su porta 8081)
- [[guidellm-benchmark-script]] (Launcher Benchmark GuideLLM)

---

## 1. Analisi della Causa Radice (Root Cause Analysis)

Dal confronto dei benchmark GuideLLM tra `mac studio` (`10.10.20.100`, 18.73 tok/s, 100% successo) e `lxc-ollama` (`10.10.20.33`, 3.45–4.00 tok/s, 15 richieste in timeout) e dall'ispezione live di `lxc-ollama` e `pve3` sono emersi tre fattori concomitanti:

1. **Raddoppio della KV Cache a 65.536 token (`8.7 GiB` di sola KV cache)**:
   - Con `OLLAMA_NUM_PARALLEL=2` e `default_num_ctx=32768`, Ollama avvia `llama-server` con `-c 65536 -np 2`, richiedendo **8.704 MiB** solo per la KV cache oltre ai **21.668 MiB** dei pesi di `qwen2.5:32b-instruct-q5_K_M` (**30.586 MiB totali**).
2. **Co-presenza fissa del sidecar `llama-ocr` (`~6.9 GiB` VRAM)**:
   - Il processo `/usr/local/bin/llama-server` per `Qwen2.5-VL-7B-Instruct` sulla porta `8081` mantiene riservati ~6.9 GiB di memoria Vulkan RADV.
3. **Limite Kernel GTT/TTM di default su `pve3` (`31.7 GiB` totali / `24.8 GiB` liberi)**:
   - Su `pve3` (`/proc/cmdline`: `root=ZFS=rpool/ROOT/pve-1 boot=zfs video=1024x768`), il kernel Linux 7.0 applica il limite di default del 50% della RAM sia a `amdgpu.gttsize` (`-1` $\rightarrow$ 30.7 GiB GTT + 1 GiB VRAM = **31.7 GiB**) sia al sottosistema TTM (`ttm.pages_limit = 8051195` pagine da 4 KB = **30.7 GiB**).
   - Avendo solo **24.8 GiB** di VRAM Vulkan libera contro i **30.5 GiB** richiesti, Ollama carica solo **51 layer su 65 in GPU** e scarica **14 layer su CPU** (`23% CPU / 77% GPU`).

---

## 2. Decisioni Architetturali Concordate

1. **Ottimizzazione Immediata Runtime Ollama in `rete.json` (Zero Reboot Host)**:
   - `OLLAMA_NUM_PARALLEL`: `"1"` (dedica tutte le 16 CU RDNA 3.5 alla singola richiesta attiva e dimezza la KV cache da 65.536 a 32.768 token, pari a ~4.3 GiB).
   - `OLLAMA_CONTEXT_LENGTH`: `"32768"` (mantiene la finestra di contesto massima di 32k token per singolo utente).
   - `OLLAMA_MAX_LOADED_MODELS`: `"1"` (evita che un secondo modello caricato in Ollama frammenti la VRAM spingendo layer su CPU, mentre `llama-ocr` gira già come servizio indipendente su `:8081`).
2. **Persistenza Dichiarativa Kernel VRAM (54 GiB GTT + TTM) su `pve3` via Ansible**:
   - Configurazione permanente su `pve3` (tramite `ansible/playbooks/infrastructure/configure_ollama_fleet.yml`) di:
     - `/etc/modprobe.d/amdgpu.conf` con `options amdgpu gttsize=55296` e `options ttm pages_limit=14155776 page_pool_size=14155776`.
     - `/etc/kernel/cmdline` con l'aggiunta idempotente di `amdgpu.gttsize=55296 ttm.pages_limit=14155776 ttm.page_pool_size=14155776`.
     - Esecuzione automatica degli handler `update-initramfs -u -k all` e `proxmox-boot-tool refresh` sulla partizione EFI (`09FE-8352`).
   - **Nessun reboot immediato di `pve3`**: i parametri kernel restano pronti e si attiveranno automaticamente al prossimo riavvio dell'host.
3. **Verifica Empirica con Benchmark GuideLLM**:
   - Esecuzione di `ollama ps` e nuovo run di `scripts/benchmarks/run_guidellm_benchmark.sh` su `lxc-ollama` con `qwen2.5:32b-instruct-q5_K_M` per certificare il 100% GPU offload e il guadagno prestazionale.

---

## 3. Fasi Operative di Esecuzione (Protocollo Test-Driven)

### Fase 1: Aggiornamento Dichiarativo di `rete.json`
1. Modifica del nodo `lxc-ollama` (`services[0].env`) in `rete.json`:
   - `OLLAMA_NUM_PARALLEL`: `"1"`
   - `OLLAMA_MAX_LOADED_MODELS`: `"1"`
   - `OLLAMA_CONTEXT_LENGTH`: `"32768"`
2. **Verifica Fase 1**: Esecuzione di `python3 scripts/network/validate_network.py` per certificare l'integrità sintattica e di schema di `rete.json`.

### Fase 2: Estensione del Playbook Ansible `configure_ollama_fleet.yml`
1. Aggiunta del play `"Configura Persistenza Kernel AMDGPU GTT/TTM (54 GiB) su PVE3"` in `ansible/playbooks/infrastructure/configure_ollama_fleet.yml` (target `10.10.10.31`):
   - Creazione/aggiornamento di `/etc/modprobe.d/amdgpu.conf`.
   - Aggiornamento idempotente di `/etc/kernel/cmdline` preservando `root=ZFS=rpool/ROOT/pve-1 boot=zfs video=1024x768`.
   - Handler condizionali per `update-initramfs -u -k all` e `proxmox-boot-tool refresh`.
2. **Verifica Fase 2**: Esecuzione di `ansible-playbook --syntax-check -i ansible/inventory.ini ansible/playbooks/infrastructure/configure_ollama_fleet.yml`.

### Fase 3: Esecuzione Playbook Ansible e Convergenza Live (`pve3` + `lxc-ollama`)
1. Esecuzione di `ansible-playbook -i ansible/inventory.ini ansible/playbooks/infrastructure/configure_ollama_fleet.yml`.
2. **Verifica Fase 3**:
   - Su `pve3`: controllo di `/etc/modprobe.d/amdgpu.conf`, `/etc/kernel/cmdline` e `proxmox-boot-tool status`.
   - Su `lxc-ollama`: controllo di `/etc/systemd/system/ollama.service.d/override.conf`, warmup del modello `qwen2.5:32b-instruct-q5_K_M` e verifica con `ollama ps` e `journalctl -u ollama` dell'allocazione layer su GPU.

### Fase 4: Benchmark GuideLLM di Certificazione e Allineamento Wiki
1. Esecuzione del benchmark GuideLLM su `lxc-ollama` (`qwen2.5:32b-instruct-q5_K_M`) e confronto metriche pre/post ottimizzazione.
2. Aggiornamento di `wiki/entities/Ollama.md`, `todo.md` e `GEMINI.md`.
3. **Verifica Fase 4**: Esecuzione di `python3 scripts/network/validate_network.py && python3 scripts/wiki/build_wiki_context.py`.

---

## 💾 Stato di Ripristino (AI Save-State)
- **Fase Attiva**: Tutte le fasi completate con successo (Piano Chiuso ✅).
- **Ultima Azione Completata**: Esecuzione benchmark GuideLLM di certificazione (`qwen2.5:32b-instruct-q5_K_M`, 100% GPU offload, zero errori/timeout) e allineamento documentale di `wiki/entities/Ollama.md` e `todo.md`.
- **Prossimo Passo Operativo**: Nessuno (piano completato e architetturalmente convergente).
- **Blocchi/Decisioni Pendenti**: Nessuno.

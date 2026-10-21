---
title: "Ollama LLM Fleet"
type: entity
tags:
  - "#llm"
  - "#ollama"
  - "#ai"
  - "#vulkan"
  - "#metal"
  - "#pve3"
  - "#mac"
  - "#ansible"
---

# Ollama LLM Fleet

L'infrastruttura homelab adotta un'architettura di inferenza neurale distribuita basata su due nodi fisici complementari che eseguono il runtime **Ollama**:
1. **`lxc-ollama` (PVE3, CT 300)**: Server di inferenza homelab 24/7 con accelerazione hardware su APU AMD Strix Point (Radeon 890M RDNA 3.5 / Vulkan RADV) e 54 GB di memoria condivisa.
2. **`mac` (Localhost)**: Nodo client su MacBook Pro con Apple Silicon (Metal 3 e 64 GB di Unified Memory).

Entrambi i nodi sono gestiti dichiarativamente con **[[Network_Registry]] (`rete.json`) come Single Source of Truth** e sincronizzati tramite il playbook Ansible `ansible/playbooks/infrastructure/configure_ollama_fleet.yml`.

---

## 🗺️ Mappe Concettuali e Relazioni
- [[Network_Registry]] (Censimento canonico dei servizi Ollama e dei rispettivi blocchi `env`)
- [[lxc-ollama-hardware-limit-optimization]] (Dimensionamento al limite fisico del CT 300 su PVE3)
- [[pve3-lxc-ollama-nfs-stripe-storage]] (Mount storage NFS `stripe/ollama` su 10 GbE)
- [[guidellm-benchmark-script]] (Launcher di benchmark conforme al naming canonico)

---

## 1. Censimento Nodi e Risorse

| Parametro | `lxc-ollama` (Server PVE3) | `mac` (Localhost Client) |
| :--- | :--- | :--- |
| **Identificativo rete.json** | `lxc-ollama` | `mac studio` / `localhost` |
| **Endpoint HTTP** | `http://10.10.20.33:11434/v1` | `http://127.0.0.1:11434/v1` |
| **VLAN / Network** | VLAN 20 (`vmbr20`, Server/Workload) | Loopback locale / VLAN 20 |
| **Processore** | AMD Ryzen AI 9 HX 370 (20 vCPU: 4 Core Zen 5 @ 5.1GHz + 6 Zen 5c) | Apple Silicon (Core Performance + Efficiency) |
| **Acceleratore GPU** | AMD Radeon 890M (16 CU RDNA 3.5 @ 2900 MHz `gpu-turbo`) | Apple GPU Metal Cores |
| **Backend Calcolo** | Mesa RADV Vulkan (`amdgpu.gttsize=57344`) | Apple Metal 3 (MPS) |
| **Memoria / VRAM** | 54 GB LPDDR5-7500 UMA (~45.5 GiB VRAM allocabili) | 64 GB Unified Memory (~48 GiB Metal allocabili) |
| **Storage Modelli** | NFS TrueNAS `stripe/ollama` via 10 GbE SFP+ | SSD NVMe Interno Apple APFS (~5-7 GB/s) |
| **Gestore di Servizio** | `systemd` (`/etc/systemd/system/ollama.service.d/override.conf`) | `launchd` (`~/Library/LaunchAgents/homebrew.mxcl.ollama.plist`) |

---

## 2. Parametri di Configurazione Canonici (`rete.json`)

Tutti i parametri di runtime sono dichiarati in `rete.json` sotto ciascun nodo (`services[].env`):

### Parametri Condivisi
- `OLLAMA_FLASH_ATTENTION=1`: Dimezza l'occupazione di memoria della KV Cache sui contesti estesi (attenzione sub-quadratica).
- `OLLAMA_KV_CACHE_TYPE=q8_0`: Quantizzazione della KV Cache a 8 bit per dimezzare l'impronta VRAM del contesto.
- `OLLAMA_MAX_QUEUE=128`: Coda di richieste limitata a 128 per evitare saturazione e timeout HTTP indefiniti.
- `OLLAMA_LOAD_TIMEOUT=10m`: Timeout esteso a 10 minuti per il cold-load di modelli ad alto numero di parametri.

### Parametri Specifici
- **`lxc-ollama`**:
  - `OLLAMA_HOST=0.0.0.0:11434`: Binding di rete per consentire l'accesso da tutti i nodi e container del lab.
  - `OLLAMA_IGPU_ENABLE=1`: Forza l'abilitazione del sottosistema ROCm/Vulkan sull'APU integrata.
  - `HSA_OVERRIDE_GFX_VERSION=11.5.0`: Override compatibilità GFX per architettura RDNA 3.5.
  - `OLLAMA_NUM_PARALLEL=1`: Dedica tutte le 16 CU RDNA 3.5 alla singola richiesta attiva, dimezzando l'occupazione della KV cache a ~4.25 GiB per contesto 32k.
  - `OLLAMA_MAX_LOADED_MODELS=1`: Evita frammentazione della VRAM allocata (mentre il sidecar vision `llama-ocr` gira autonomamente su porta `:8081`).
  - `OLLAMA_CONTEXT_LENGTH=32768`: Finestra di contesto estesa nativa fino a 32k token per utente.
  - `OLLAMA_KEEP_ALIVE=-1`: Modello permanentemente residente in memoria (nessun timeout di inattività).
- **`mac` (Localhost)**:
  - `OLLAMA_NUM_PARALLEL=2`: Gestione concorrente fino a 2 richieste simultanee sullo stesso modello.
  - `OLLAMA_MAX_LOADED_MODELS=2`: Consente di mantenere in memoria contemporaneamente 2 modelli su Unified Memory.
  - `OLLAMA_KEEP_ALIVE=15m`: Scaricamento automatico dopo 15 minuti di inattività per liberare RAM al sistema desktop.

---

## 3. Gestione e Convergenza Ansible

L'applicazione della configurazione è affidata al playbook idempotente:
```bash
ansible-playbook -i ansible/inventory.ini ansible/playbooks/infrastructure/configure_ollama_fleet.yml
```

Il playbook esegue:
1. **Persistenza Kernel EFI/GTT su PVE3**: Configura `/etc/modprobe.d/amdgpu.conf` e `/etc/kernel/cmdline` con parametri `amdgpu.gttsize=55296` e `ttm.pages_limit=14155776` (54 GiB), rigenerando initramfs e sincronizzando la partizione EFI via `proxmox-boot-tool refresh`.
2. Parsing diretto di `rete.json` (nessuna variabile duplicata).
3. Generazione del drop-in systemd su `lxc-ollama` tramite template Jinja2.
4. Generazione del launchd plist su macOS tramite template Jinja2.
5. Riavvio controllato dei rispettivi servizi solo se i file di configurazione sono variati.
6. Health-check HTTP su entrambi gli endpoint (`/api/version`).

---

## 4. Benchmark e Performance di Inferenza (GuideLLM)

Con la configurazione a 100% GPU Offload (65/65 layer in GPU per `qwen2.5:32b-instruct-q5_K_M`):
- **Offload**: 100% GPU (Vulkan RADV GFX1150), 0 layer su CPU.
- **Throughput**: ~3.7 tokens/s in generazione continua (`ITL` 235 ms, `TTFT` 2.5s).
- **Stabilità**: Zero errori / zero timeout nei benchmark GuideLLM (Livello 2 Standard).

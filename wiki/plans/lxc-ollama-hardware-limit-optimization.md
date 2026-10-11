---
title: "Piano: Ottimizzazione e Dimensionamento al Limite Fisico di LXC Ollama su PVE3"
type: plan
status: active
certified_for_ai: true
created_at: 2026-10-11
tags:
  - "#pve3"
  - "#ollama"
  - "#lxc"
  - "#hardware"
  - "#gpu"
  - "#rdna35"
  - "#tuning"
  - "#guidellm"
---

# Piano: Ottimizzazione e Dimensionamento al Limite Fisico di LXC Ollama su PVE3

Il presente piano operativo definisce l'analisi architetturale, le strategie dimensionali e la procedura test-driven per spingere il container **`lxc-ollama`** (CT 300, `10.10.20.33`) su **PVE3** (`10.10.10.31`) al **massimo dei suoi limiti fisici hardware** (SoC AMD Ryzen AI 9 HX 370 con 64 GB LPDDR5-7500 unificata e iGPU Radeon 890M RDNA 3.5).

---

## 🗺️ Mappe Concettuali e Relazioni
- [[purpose]] (Governance Homelab e Principi Core)
- [[SCHEMA]] (Regole di Governance del Wiki)
- [[homepage-steam-lxc-control-button]] (Hookscript di Mutua Esclusione `lxc-steam-hook.sh` tra CT 301 e CT 300)
- [[pve3-gpu-power-management-scripts]] (Gestione Energetica e Clock Radeon 890M: `gpu-turbo`, `gpu-eco`)
- [[pve3-lxc-ollama-nfs-stripe-storage]] (Mount NFS TrueNAS `stripe/ollama` su 10 GbE per Modelli Ollama)
- [[guidellm-benchmark-script]] (Tool di Benchmark GuideLLM per la Validazione Empirica del Throughput)
- [[Network_Registry]] (Censimento Dichiarativo in `rete.json`)

---

## 1. Vincolo Architetturale Chiave: Mutua Esclusione tra Steam e Ollama

Su PVE3 è già attivo ed operativo l'hookscript canonico `/usr/local/bin/lxc-steam-hook.sh` (`[[homepage-steam-lxc-control-button]]`):
- **All'avvio di `lxc-steam` (`CT 301`)**: l'hook `pre-start` esegue lo shutdown controllato (`pct shutdown 300`) di `lxc-ollama` prima di attivare la sessione grafica Direct-HDMI.
- **All'arresto di `lxc-steam` (`CT 301`)**: l'hook `post-stop` riavvia automaticamente `lxc-ollama` (`pct start 300`).

```
┌────────────────────────────────────────────────────────────────────────┐
│                        Proxmox VE PVE3 Host (64 GB)                    │
│                                                                        │
│   [VM 3200 talos-cp-03]: 4 GB RAM fissa / 2 vCPU (Zen 5c 20-23)       │  <-- Sempre Attiva (etcd HA)
│   [PVE3 Host OS / ZFS ARC]: ~4-6 GB RAM residua riservata              │  <-- Sempre Attiva
│                                                                        │
│   ┌────────────────────────────────────────────────────────────────┐   │
│   │             MUTUA ESCLUSIONE RUNTIME (lxc-steam-hook.sh)       │   │
│   │                                                                │   │
│   │   MODALITÀ GAMING (Direct-HDMI):                               │   │
│   │   • CT 301 (lxc-steam): ATTIVO  --> 16 GB RAM + Zen 5 (0-7)    │   │
│   │   • CT 300 (lxc-ollama): SPENTO --> 0 GB RAM / 0 vCPU          │   │
│   │                                                                │   │
│   │   MODALITÀ INFERENZA AI (Default Homelab 24/7):                │   │
│   │   • CT 301 (lxc-steam): SPENTO  --> 0 GB RAM / 0 vCPU          │   │
│   │   • CT 300 (lxc-ollama): ATTIVO --> 54–56 GB RAM + 20 vCPU!    │   │
│   └────────────────────────────────────────────────────────────────┘   │
└────────────────────────────────────────────────────────────────────────┘
```

> [!IMPORTANT]
> Poiché i due container **NON girano mai in contemporanea**, `lxc-ollama` **NON DEVE competere per la RAM o per i core veloci Zen 5** con Steam. Quando Ollama è attivo, Steam consuma **0 MB di RAM** e **0 cicli CPU**.

---

## 2. Dimensionamento al Limite Fisico dell'Hardware

### 2.1 Ripartizione Memoria RAM e Massimizzazione VRAM Vulkan (GTT)
Il budget fisico di 64 GB LPDDR5-7500 su PVE3 viene quindi così ripartito quando Ollama è in esecuzione:
- **VM 3200 (`talos-cp-03`)**: **4 GB fissa** (Quorum etcd K8s intoccabile).
- **Host PVE3 OS / ZFS ARC / Kernel**: **4–6 GB** (Riserva protetta per il sistema operativo host).
- **CT 301 (`lxc-steam`)**: **0 GB** (Spento).
- **CT 300 (`lxc-ollama`)**:
  - **Opzione Conservativa**: **54 GB RAM** (lascia 6 GB liberi a PVE3 host).
  - **Opzione Limite Fisico Assoluto**: **56 GB RAM** (lascia 4 GB liberi a PVE3 host).

#### Impatto sulla VRAM Vulkan RADV
Su architettura APU UMA con driver `amdgpu` e Mesa RADV, la memoria video allocabile corrisponde all'heap di sistema esposto al container:
- **Stato Attuale (38 GB RAM)**: VRAM rilevata da Ollama = **~31.7 GiB**.
- **Nuovo Dimensionamento (54 GB RAM)**: VRAM rilevata da Ollama = **~45.5 GiB** (+13.8 GiB!).
- **Nuovo Dimensionamento (56 GB RAM)**: VRAM rilevata da Ollama = **~47.5 GiB** (+15.8 GiB!).

Con oltre 45–47 GiB di VRAM reale:
1. **Modelli 31B–32B** (`gemma4:31b`, `qwen2.5:32b`, `qwen3-vl:32b`): possono essere caricati in quantizzazioni ad altissima fedeltà (**Q8_0** o perfino **FP16** parziale) con finestre di contesto complete da **32.768 token** senza rischiare OOM o fallback su CPU.
2. **Modelli 70B–72B** (`llama3.3:70b`, `qwen2.5:72b`): diventano **pienamente eseguibili** su PVE3 in quantizzazione **Q4_K_M** (~40–42 GB di peso in VRAM), aprendo l'accesso locale a modelli di classe frontier su un singolo mini-PC bare-metal!

### 2.2 Ripartizione CPU e Sblocco Core Zen 5 (Performance)
Attualmente `300.conf` assegna solo 12 thread Zen 5c (Thread 8–19). Poiché Steam (CT 301) è spento durante l'inferenza, i **4 core Zen 5 ad alte frequenze** (Thread 0–7, 16 MB L3 cache, boost a 5.1 GHz) rimangono completamente inutilizzati!

- **Nuova Assegnazione vCPU**:
  - Assegnare a `lxc-ollama` **20 vCPU** mappate sui thread **0–19** (4 Core Zen 5 + 6 Core Zen 5c).
  - I thread 20–23 rimangono permanentemente isolati e riservati a `talos-cp-03` (`VM 3200`).
- **Threading Ottimale in llama.cpp / Ollama**:
  - La fase di token generation su GPU non richiede molti thread CPU.
  - Tuttavia, la fase di **prompt evaluation / prefill** (BLAS, tokenizzazione) beneficia in modo spettacolare dei core Zen 5 a 5.1 GHz con AVX-512 e cache L3 da 16 MB, riducendo drasticamente il **Time To First Token (TTFT)**.
  - In llama.cpp, il numero ideale di thread di calcolo per non saturare la cache L1/L2 è pari ai core fisici (10 core fisici = 8–10 thread di computazione).

---

## 3. Ottimizzazioni di Runtime e Kernel Host

### 3.1 Parametro Kernel Host `amdgpu.gttsize`
Per consentire alla Radeon 890M di mappare oltre 32 GB di memoria di sistema senza blocchi o soglie conservative del kernel Linux:
- Verificare `/sys/module/amdgpu/parameters/gttsize`.
- Impostare su PVE3 in `/etc/modprobe.d/amdgpu.conf`:
  ```ini
  options amdgpu gttsize=57344
  ```
  (Consente fino a 56 GB di allocazione grafica dinamica).

### 3.2 Variabili d'Ambiente e Runtime Ollama
Configurazione all'interno di `lxc-ollama` in `/etc/systemd/system/ollama.service.d/override.conf`:
- `OLLAMA_FLASH_ATTENTION=1`: Abilita l'attenzione flash (dimezza l'occupazione VRAM della KV Cache su contesti lunghi).
- `OLLAMA_KV_CACHE_TYPE=q8_0`: Quantizzazione a 8-bit della KV Cache (zero degradazione semantica, risparmio di gigabyte su prompt estesi).
- `OLLAMA_KEEP_ALIVE=-1`: Previene lo scaricamento del modello dalla VRAM unificata.
- `OLLAMA_MAX_LOADED_MODELS=1`: Riserva il 100% della memoria al modello attivo.
- `OLLAMA_NUM_PARALLEL=1`: Dedica tutte le 16 Compute Unit della 890M al singolo stream per massimizzare il throughput.

### 3.3 Profilo di Clock GPU (2900 MHz)
- Verificare che durante le sessioni di inferenza o di benchmark GuideLLM, la GPU sia forzata a 2900 MHz tramite `/usr/local/bin/gpu-turbo` su PVE3.

---

## 4. Matrice Comparativa: Prima vs Dopo

| Parametro | Configurazione Attuale | Nuova Configurazione al Limite Fisico | Guadagno Netto |
| :--- | :--- | :--- | :--- |
| **RAM Assegnata (CT 300)** | 38 GB | **54 GB** (o 56 GB) | **+16 GB (+42%)** |
| **VRAM Vulkan RADV** | ~31.7 GiB | **~45.5 GiB** | **+13.8 GiB di VRAM** |
| **vCPU Assegnate** | 12 vCPU (solo Zen 5c) | **20 vCPU** (Zen 5 + Zen 5c, thread 0–19) | Accesso ai 4 Core Zen 5 ad alte prestazioni |
| **TTFT (Prompt Ingestion)** | Rallentato da core Zen 5c | Accelerato da Zen 5 (5.1 GHz + 16MB L3) | Abbattimento della latenza iniziale |
| **Modello Massimo Testabile** | 31B (Q4_K_M, 8k ctx) | **32B (Q8_0, 32k ctx)** oppure **70B (Q4_K_M)** | Sblocco modelli di classe frontier (70B) |
| **Coesistenza con Steam** | Presunta concorrenza | **Mutua esclusione trasparente** | Zero impatto su Steam (16 GB intatti) |

---

## 5. Fasi Operative di Esecuzione (Test-Driven Protocol)

### Fase 1: Verifica Baseline e Ispezione PVE3
1. Verifica dello stato dei container su PVE3 (`pct status 300`, `pct status 301`).
2. Ispezione dei parametri kernel `gttsize` su PVE3: `cat /sys/module/amdgpu/parameters/gttsize`.
3. Esecuzione del benchmark di baseline GuideLLM con lo script standard:
   `./scripts/benchmarks/run_guidellm_benchmark.sh -n lxc-ollama -m gemma4:31b -b batch`

### Fase 2: Configurazione Parametri Kernel AMDGPU su Host PVE3
1. Configurazione di `options amdgpu gttsize=57344` in `/etc/modprobe.d/amdgpu.conf` su PVE3.
2. Validazione del parametro attivo.

### Fase 3: Riconfigurazione Risorse CT 300 (`300.conf`)
1. Aggiornamento dichiarativo di `/etc/pve/lxc/300.conf`:
   - `memory: 55296` (54 GB) oppure `57344` (56 GB).
   - `swap: 512` (o 0).
   - `cores: 20` (con pinning `cpuset.cpus = 0-19`).
2. Riavvio di CT 300: `pct reboot 300`.
3. Verifica all'interno del container della RAM libera e della VRAM rilevata da Vulkan RADV.

### Fase 4: Applicazione Ottimizzazioni di Runtime Ollama
1. Aggiornamento delle variabili di sistema (`OLLAMA_FLASH_ATTENTION=1`, `OLLAMA_KV_CACHE_TYPE=q8_0`, `OLLAMA_KEEP_ALIVE=-1`).
2. Riavvio del demone Ollama: `systemctl restart ollama`.
3. Verifica dei log di avvio di Ollama (`journalctl -u ollama -n 50`) per accertare il caricamento corretto del backend Vulkan RADV con la nuova VRAM estesa.

### Fase 5: Validazione Empirica con GuideLLM Benchmark
1. Esecuzione del test di benchmark formale GuideLLM:
   `./scripts/benchmarks/run_guidellm_benchmark.sh -n lxc-ollama -m gemma4:31b -b batch`
2. Confronto analitico tra i risultati di baseline e la nuova configurazione (Throughput, Token/s, TTFT).
3. Test di caricamento di un modello esteso (es. `qwen2.5:32b` o modello 70B in Q4_K_M).

### Fase 6: Allineamento Registri e Chiusura
1. Aggiornamento di `rete.json` (valore di memoria e specifiche vCPU per `lxc-ollama`).
2. Validazione con `python3 scripts/network/validate_network.py`.
3. Rigenerazione contesto Wiki con `python3 scripts/wiki/build_wiki_context.py`.
4. Chiusura del piano e commit Git.

---

## 💾 Stato di Ripristino (AI Save-State)
- **Fase Attiva**: Fase 1 / Ispezione Preliminare e Approvazione Dimensionamento Finale
- **Ultima Azione Completata**: Formalizzazione del piano aggiornato con mutua esclusione nativa Steam/Ollama, allocazione fino a 54–56 GB RAM e sblocco dei core Zen 5 (0–19).
- **Prossimo Passo Operativo**: Conferma dell'utente tra **54 GB** (conservativa per PVE host) o **56 GB** (limite estremo), ed esecuzione della Fase 1 (ispezione parametri `gttsize` ed esecuzione benchmark baseline).
- **Blocchi/Decisioni Pendenti**: Attesa scelta utente tra 54 GB e 56 GB RAM.

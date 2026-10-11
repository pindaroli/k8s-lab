---
title: "Piano: Integrazione Sidecar llama-server Vulkan (Qwen2.5-VL-7B OCR) su LXC Ollama"
type: plan
status: completed
certified_for_ai: true
created_at: 2026-10-11
completed_at: 2026-10-12
tags:
  - "#pve3"
  - "#ollama"
  - "#llm"
  - "#vulkan"
  - "#ocr"
  - "#lxc"
  - "#rdna35"
  - "#truenas"
---

# Piano: Integrazione Sidecar llama-server Vulkan (Qwen2.5-VL-7B OCR) su LXC Ollama

Il presente piano operativo definisce l'architettura, la configurazione e la procedura test-driven per l'integrazione come servizio di sistema permanente di **`llama-server`** (da `llama.cpp`) all'interno del container **`lxc-ollama`** (CT 300, `10.10.20.33`) su **PVE3** (`10.10.10.31`).
Il servizio ospita il modello Vision-Language **`Qwen2.5-VL-7B-Instruct`** dedicato a OCR e Document Understanding con accelerazione hardware nativa **Vulkan RADV** sulla iGPU **AMD Radeon 890M** (RDNA 3.5), coesistendo in modo non interferente con l'istanza Ollama già attiva su porta 11434.

L'architettura adotta la strategia **Zero-Compilation via Binari Ufficiali Precompilati Vulkan** e **Storage Unificato su TrueNAS SCALE NFS (`stripe/ollama`)**.

---

## 🗺️ Mappe Concettuali e Relazioni
- [[purpose]] (Governance Homelab e Principi Core)
- [[SCHEMA]] (Regole del Wiki e Protocollo Test-Driven)
- [[lxc-ollama-hardware-limit-optimization]] (Dimensionamento Hardware Limite Fisico: 54 GB RAM, 20 vCPU pinned 0-19)
- [[pve3-lxc-ollama-nfs-stripe-storage]] (Storage Modelli NFS TrueNAS `stripe/ollama` su PVE3)
- [[homepage-steam-lxc-control-button]] (Hookscript di Mutua Esclusione `lxc-steam-hook.sh` tra CT 301 e CT 300)
- [[pve3-gpu-power-management-scripts]] (Gestione Energetica e Clock Radeon 890M: `gpu-turbo`, `gpu-eco`)
- [[Network_Registry]] (Censimento Dichiarativo in `rete.json`)

---

## 1. Architettura di Sistema e Decisioni Tecniche

### 1.1 Risorse Hardware e Allocazione VRAM (CT 300)
- **Host PVE3**: AMD Ryzen AI 9 HX 370 (12 Core / 24 Thread: 4 Zen 5 @ 5.1 GHz + 8 Zen 5c @ 3.3 GHz) con 64 GB LPDDR5-7500 unificata.
- **Container `lxc-ollama` (CT 300)**:
  - Unprivileged LXC (`unprivileged: 1`) su VLAN 20 (`10.10.20.33`).
  - Assegnati **54 GB RAM** (55.296 MB) e **20 vCPU** (pinned core 0–19).
  - iGPU pass-through: `/dev/dri/renderD128` (Mesa RADV 25.2.8, GFX1150) con circa **45.5 GiB di VRAM dinamica** disponibile.
- **Ripartizione VRAM**:
  - **Ollama (`:11434`)**: modelli di chat/coding on-demand (14B–32B, fino a ~20–22 GiB di VRAM max).
  - **`llama-server` (`:8081`)**: modello OCR fisso e permanente `Qwen2.5-VL-7B` (**~7.0–7.5 GiB di VRAM** residenti).
  - **Margine Libero**: oltre **15 GiB di VRAM libera** per buffer di sistema e allocazioni dinamiche.

```
┌────────────────────────────────────────────────────────────────────────┐
│                   CT 300 (lxc-ollama) - 54 GB RAM / 20 vCPU            │
│                 iGPU AMD Radeon 890M (Vulkan RADV ~45.5 GiB VRAM)      │
├───────────────────────────────────┬────────────────────────────────────┤
│   SERVIZIO OLLAMA (Porta 11434)   │   SERVIZIO LLAMA-OCR (Porta 8081)  │
│                                   │                                    │
│ • Uso: Chat generalista, tool-call│ • Uso: OCR, Document Understanding │
│ • Modelli: 14B - 32B (on-demand)  │ • Modello: Qwen2.5-VL-7B (fissa)   │
│ • VRAM impegnata: ~20-22 GiB max  │ • VRAM impegnata: ~7.0-7.5 GiB max │
│ • Unload dinamico via keep-alive  │ • Sempre residente (Zero-Latency)  │
│                                   │                                    │
│       VRAM TOTALE CONDIVISA: ~28-30 GiB <= 45.5 GiB DISPONIBILI        │
│       (Margine di sicurezza: > 15 GiB liberi per buffer di sistema)   │
└───────────────────────────────────┴────────────────────────────────────┘
```

---

## 2. Adattamenti Architetturali e Scelte di Progetto

| Componente | Scelta Adottata | Motivazione Tecnica |
| :--- | :--- | :--- |
| **Distribuzione Binari** | **Release Ufficiale Precompilata Vulkan** (`llama-*-bin-ubuntu-vulkan-x64.tar.gz`) | Elimina l'installazione di oltre 500 MB di toolchain di compilazione (`gcc`, `g++`, `cmake`, `git`), installazione istantanea in 10 secondi e massima pulizia del container. |
| **Storage Modelli** | **TrueNAS SCALE NFS `stripe/ollama`** (`/usr/share/ollama/.ollama/models/gguf/`) | Unifica tutti i file AI (Ollama blobs e file GGUF standalone) nello stesso pool NVMe ZFS con snapshot TrueNAS, lasciando il rootfs locale del container pulito. |
| **Naming File Modelli** | `Qwen_Qwen2.5-VL-7B-Instruct-Q4_K_M.gguf` e `mmproj-Qwen_Qwen2.5-VL-7B-Instruct-f16.gguf` | **Bugfix anti-404**: include il prefisso `Qwen_` presente nel repository ufficiale di Bartowski su HuggingFace. |
| **CPU Threading** | Vincolo a `--threads 8` (`-t 8`) | Sfrutta i 4 core veloci Zen 5 a 5.1 GHz con AVX-512 e 16 MB L3 cache, evitando cross-CCX cache thrashing sui core Zen 5c durante il prefill dei token visivi. |
| **GPU Pinning** | Vincolo a `--device 0` | Vincola l'inferenza all'iGPU fisica `AMD Radeon 890M Graphics`, escludendo `GPU1: llvmpipe` (rasterizer CPU). |
| **Flash Attention** | Abilitazione flag `--flash-attn` (`-fa`) | Dimezza del 50% il consumo VRAM della KV-cache per immagini ad alta risoluzione e accelera il prefill visivo. |
| **Sicurezza & Privilegi** | Utente unprivileged `ollama` (`video`, `render`) | Nessuna esecuzione da `root`; riutilizzo dell'account di sistema con accesso certificato a `/dev/dri/renderD128`. |
| **Resilienza Boot** | `RequiresMountsFor=/usr/share/ollama/.ollama/models` | Garantisce che `llama-ocr.service` attenda il bind mount NFS prima di caricare i file pesi. |
| **Mutua Esclusione Gaming**| Integrato con `lxc-steam-hook.sh` | L'hookscript PVE3 spegne e riavvia CT 300 durante le sessioni Steam; abilitando il servizio con `systemctl enable`, ripartirà in automatico. |
| **Governance Homelab** | Censimento in `rete.json` sotto `lxc-ollama` | Registrazione canonica della porta 8081 con protocollo HTTP e API OpenAI Vision `/v1`. |

---

## 3. Fasi Operative di Esecuzione (Test-Driven Protocol)

### Fase 1: Verifica Prerequisiti Vulkan e Preparazione Directory
1. **Verifica GPU Vulkan e Device Index**:
   ```bash
   vulkaninfo --summary
   ```
   *Criterio di successo*: Conferma `GPU0: AMD Radeon 890M Graphics (RADV GFX1150)` e driver Mesa RADV attivo.
2. **Creazione Directory per Binari e Storage Modelli su TrueNAS NFS**:
   ```bash
   mkdir -p /opt/llama.cpp
   mkdir -p /usr/share/ollama/.ollama/models/gguf/qwen2.5-vl-7b
   chown -R ollama:ollama /usr/share/ollama/.ollama/models/gguf
   chmod -R 775 /usr/share/ollama/.ollama/models/gguf
   ```
3. **Verifica Fase 1**:
   - `ls -ld /opt/llama.cpp /usr/share/ollama/.ollama/models/gguf/qwen2.5-vl-7b`
   - Verifica permessi utente `ollama` su directory NFS.

---

### Fase 2: Installazione Binari Ufficiali Precompilati Vulkan (`llama.cpp`)
1. **Rilevamento e Download Ultima Release Ufficiale Vulkan**:
   Download dell'archivio precompilato ufficiale Ubuntu Vulkan da GitHub Releases:
   ```bash
   LATEST_TAG=$(curl -sL https://api.github.com/repos/ggml-org/llama.cpp/releases?per_page=1 | python3 -c 'import json, sys; print(json.load(sys.stdin)[0]["tag_name"])')
   echo "Rilevata release llama.cpp: ${LATEST_TAG}"
   curl -L -o /tmp/llama-vulkan.tar.gz "https://github.com/ggml-org/llama.cpp/releases/download/${LATEST_TAG}/llama-${LATEST_TAG}-bin-ubuntu-vulkan-x64.tar.gz"
   ```
2. **Estrazione Binari e Librerie in `/opt/llama.cpp`**:
   ```bash
   tar -zxvf /tmp/llama-vulkan.tar.gz --strip-components=1 -C /opt/llama.cpp
   rm -f /tmp/llama-vulkan.tar.gz
   ```
3. **Registrazione Librerie Condivise (`ldconfig`)**:
   ```bash
   echo "/opt/llama.cpp" > /etc/ld.so.conf.d/llama.conf
   ldconfig
   ```
4. **Creazione Symlink Eseguibili di Sistema**:
   ```bash
   ln -sf /opt/llama.cpp/llama-server /usr/local/bin/llama-server
   ln -sf /opt/llama.cpp/llama-cli /usr/local/bin/llama-cli
   ```
5. **Verifica Fase 2**:
   ```bash
   /usr/local/bin/llama-server --version
   ```
   *Criterio di successo*: Il binario restituisce la versione corrente e conferma il supporto Vulkan tra i backend.

---

### Fase 3: Download e Posizionamento dei Modelli GGUF (Bartowski su NFS TrueNAS)
1. **Download Pesi LLM (Q4_K_M)**:
   ```bash
   curl -L -C - -o /usr/share/ollama/.ollama/models/gguf/qwen2.5-vl-7b/Qwen_Qwen2.5-VL-7B-Instruct-Q4_K_M.gguf \
     "https://huggingface.co/bartowski/Qwen_Qwen2.5-VL-7B-Instruct-GGUF/resolve/main/Qwen_Qwen2.5-VL-7B-Instruct-Q4_K_M.gguf"
   ```
2. **Download Proiettore Multimodale (F16)**:
   ```bash
   curl -L -C - -o /usr/share/ollama/.ollama/models/gguf/qwen2.5-vl-7b/mmproj-Qwen_Qwen2.5-VL-7B-Instruct-f16.gguf \
     "https://huggingface.co/bartowski/Qwen_Qwen2.5-VL-7B-Instruct-GGUF/resolve/main/mmproj-Qwen_Qwen2.5-VL-7B-Instruct-f16.gguf"
   ```
3. **Verifica Integrità File (Anti-LFS Placeholder Check)**:
   ```bash
   ls -lh /usr/share/ollama/.ollama/models/gguf/qwen2.5-vl-7b/
   ```
   *Criterio di successo*: Pesi LLM ~4.7 GB (non un puntatore LFS da 1 KB) e proiettore ~1.35 GB, allocati su pool NVMe `stripe` di TrueNAS.
4. **Smoke Test Rapido CLI (Offload Vulkan)**:
   ```bash
   /usr/local/bin/llama-cli \
     -m /usr/share/ollama/.ollama/models/gguf/qwen2.5-vl-7b/Qwen_Qwen2.5-VL-7B-Instruct-Q4_K_M.gguf \
     --mmproj /usr/share/ollama/.ollama/models/gguf/qwen2.5-vl-7b/mmproj-Qwen_Qwen2.5-VL-7B-Instruct-f16.gguf \
     -ngl 99 --device 0 -p "Ciao" -n 5
   ```
   *Criterio di successo*: Tutti i 28 layer LLM e il proiettore visivo caricati con successo su Vulkan0 (Radeon 890M), generazione token completata con esito positivo.

---

### Fase 4: Configurazione del Servizio systemd (`llama-ocr.service`)
1. **Creazione File di Configurazione `/etc/default/llama-ocr`**:
   ```ini
   # Configurazione Llama.cpp OCR & Vision Server (Qwen2.5-VL-7B)
   LLAMA_HOST=0.0.0.0
   LLAMA_PORT=8081
   LLAMA_MODEL=/usr/share/ollama/.ollama/models/gguf/qwen2.5-vl-7b/Qwen_Qwen2.5-VL-7B-Instruct-Q4_K_M.gguf
   LLAMA_MMPROJ=/usr/share/ollama/.ollama/models/gguf/qwen2.5-vl-7b/mmproj-Qwen_Qwen2.5-VL-7B-Instruct-f16.gguf
   LLAMA_CTX_SIZE=8192
   LLAMA_THREADS=8
   LLAMA_PARALLEL=1
   LLAMA_NGL=99
   LLAMA_DEVICE=0
   LLAMA_EXTRA_ARGS="--flash-attn"
   ```
2. **Creazione Service Unit `/etc/systemd/system/llama-ocr.service`**:
   ```ini
   [Unit]
   Description=Llama.cpp OCR & Vision Sidecar Server (Qwen2.5-VL-7B)
   After=network.target remote-fs.target
   Wants=network.target
   RequiresMountsFor=/usr/share/ollama/.ollama/models

   [Service]
   Type=simple
   User=ollama
   Group=ollama
   SupplementaryGroups=video render
   EnvironmentFile=/etc/default/llama-ocr
   ExecStart=/usr/local/bin/llama-server \
     -m ${LLAMA_MODEL} \
     --mmproj ${LLAMA_MMPROJ} \
     --host ${LLAMA_HOST} \
     --port ${LLAMA_PORT} \
     -c ${LLAMA_CTX_SIZE} \
     -t ${LLAMA_THREADS} \
     -np ${LLAMA_PARALLEL} \
     -ngl ${LLAMA_NGL} \
     --device ${LLAMA_DEVICE} \
     ${LLAMA_EXTRA_ARGS}
   Restart=always
   RestartSec=5
   LimitNOFILE=65536

   [Install]
   WantedBy=multi-user.target
   ```
3. **Abilitazione e Avvio del Servizio**:
   ```bash
   systemctl daemon-reload
   systemctl enable --now llama-ocr
   ```
4. **Verifica Fase 4**:
   ```bash
   systemctl status llama-ocr
   journalctl -u llama-ocr -n 30 --no-pager
   ```
   *Criterio di successo*: Servizio `active (running)`, log mostrano allocazione su `Vulkan0 (AMD Radeon 890M Graphics)` e binding HTTP su `0.0.0.0:8081`.

---

### Fase 5: Validazione End-to-End e Test di Coesistenza
1. **Health Check HTTP**:
   ```bash
   curl -s http://10.10.20.33:8081/health
   ```
   *Criterio di successo*: Risposta HTTP 200 con `{"status":"ok"}`.
2. **Test API OpenAI Vision (`/v1/chat/completions`)**:
   Esecuzione di una chiamata REST con un'immagine di test codificata in base64:
   ```bash
   curl -s http://10.10.20.33:8081/v1/chat/completions \
     -H "Content-Type: application/json" \
     -d '{
       "model": "qwen2.5-vl-7b",
       "messages": [
         {
           "role": "user",
           "content": [
             {"type": "text", "text": "Describe this image briefly."},
             {"type": "image_url", "image_url": {"url": "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII="}}
           ]
         }
       ],
       "max_tokens": 50
     }'
   ```
   *Criterio di successo*: Risposta strutturata JSON con completamento visivo valido.
3. **Smoke Test Coesistenza con Ollama**:
   Mentre `llama-ocr` è attivo su porta 8081, esecuzione simultanea di una query verso Ollama su porta 11434:
   ```bash
   curl -s http://10.10.20.33:11434/api/tags
   ollama run bge-m3 "test ping coesistenza ollama"
   ```
   *Criterio di successo*: Entrambi i servizi rispondono regolarmente senza contesa di memoria o crash GPU.

---

### Fase 6: Censimento e Sincronizzazione Registri
1. **Aggiornamento `rete.json`**:
   Aggiunta del servizio `llama-ocr` in `nodi[lxc-ollama].services`.
2. **Aggiornamento `todo.md`**:
   Tracciamento delle fasi completate.
3. **Rigenerazione Contesto Wiki**:
   ```bash
   python3 scripts/network/validate_network.py && python3 scripts/wiki/build_wiki_context.py
   ```

---

## 4. Esito Esecuzione (2026-10-12)

L'intero piano è stato completato con successo seguendo il protocollo test-driven:

- **Fase 1 (Verifica Prerequisiti & Directory)**: Verificato `vulkaninfo` con rilevamento di `GPU0: AMD Radeon 890M Graphics (RADV GFX1150)` (driver Mesa 25.2.8). Creata directory `/opt/llama.cpp` e directory NFS `/usr/share/ollama/.ollama/models/gguf/qwen2.5-vl-7b` sul dataset TrueNAS `stripe/ollama` con permessi di scrittura certificati per l'utente `ollama`.
- **Fase 2 (Installazione Binari Precompilati Vulkan)**: Scaricata ed estratta la release ufficiale upstream `b11559` di `llama.cpp` (`llama-b11559-bin-ubuntu-vulkan-x64.tar.gz`), installato `libgomp1`, registrate le librerie in `/etc/ld.so.conf.d/llama.conf` ed eseguiti symlink in `/usr/local/bin/`. Rilevato `Vulkan0` con 32.4 GiB di memoria dedicata via `llama-cli --list-devices`.
- **Fase 3 (Download Modelli & Smoke Test)**: Scaricati con successo i pesi LLM `Qwen_Qwen2.5-VL-7B-Instruct-Q4_K_M.gguf` (4.4 GiB) e il proiettore multimodale `mmproj-Qwen_Qwen2.5-VL-7B-Instruct-f16.gguf` (1.3 GiB) su TrueNAS NFS. Eseguito smoke test reale con `llama-cli` su Vulkan0: prefill a **91.3 token/s** e generazione a **20.6 token/s**.
- **Fase 4 (Servizio systemd)**: Configurati `/etc/default/llama-ocr` e `/etc/systemd/system/llama-ocr.service` (utente unprivileged `ollama`, gruppi `video render`, 8 thread Zen 5, GPU `Vulkan0`, Flash Attention `auto`, mount dependency `RequiresMountsFor`). Servizio abilitato e attivo (`active (running)`), listening su `0.0.0.0:8081` con `/health` rispondente `status: ok`.
- **Fase 5 (Validazione End-to-End & Coesistenza)**: Chiamata API OpenAI Vision `/v1/chat/completions` con immagine di test base64 eseguita con successo in 1.9s (20.87 t/s). Test simultaneo di inferenza con Ollama (`/api/embeddings` vettore 1024) eseguito con successo e zero contese GPU/VRAM (34 GiB RAM liberi nel container).
- **Fase 6 (Governance & Registri)**: Censito formalmente il servizio `llama-ocr` in `rete.json` sotto `lxc-ollama` e nella sezione `applicazioni`, sincronizzati `todo.md` e `wiki_context.md`.

---

## 💾 Stato di Ripristino (AI Save-State)
- **Fase Attiva**: [Piano Completato con Successo ✅]
- **Ultima Azione Completata**: Eseguite con successo tutte le 6 Fasi del piano. Il servizio `llama-ocr` è permanente, monitorato da systemd e censito nei registri canonici.
- **Prossimo Passo Operativo**: Nessuno.
- **Blocchi/Decisioni Pendenti**: Nessun blocco.

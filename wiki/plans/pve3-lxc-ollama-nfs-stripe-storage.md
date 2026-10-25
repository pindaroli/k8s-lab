---
title: "Piano: Storage NFS per Modelli Ollama su TrueNAS Stripe per LXC Ollama su PVE3"
type: plan
status: archived
certified_for_ai: false
archived_at: 2026-10-25
created_at: 2026-10-11
tags:
  - "#pve3"
  - "#ollama"
  - "#truenas"
  - "#nfs"
  - "#storage"
  - "#lxc"
  - "#zfs"
---

# Piano: Storage NFS per Modelli Ollama su TrueNAS Stripe per LXC Ollama su PVE3

Il presente piano operativo definisce l'architettura, la configurazione e la procedura test-driven per la creazione e l'assegnazione di uno storage NFS dedicato ai modelli e file di **Ollama** su **PVE3** (`10.10.10.31`), attestato sul pool ad altissime prestazioni **`stripe` (NVMe)** di **TrueNAS SCALE** (`10.10.20.50`), ed assegnato al container **`lxc-ollama`** (`CT 300` - `10.10.20.33`).

---

## 1. Contesto e Analisi Architetturale

### Stato Attuale
1. **Container `lxc-ollama` (CT 300)**:
   - Ospitato su PVE3, unprivileged (`unprivileged: 1`).
   - Dispone di 250 GB di rootfs locale su pool ZFS host `rpool/data/subvol-300-disk-0`.
   - Il servizio Ollama è in esecuzione con utente dedicato `ollama` (`uid=999`, `gid=990`).
   - I modelli risiedono attualmente nel percorso predefinito `/usr/share/ollama/.ollama/models` e occupano circa **40 GB** (`qwen3-vl:32b`, `gemma4:31b`, `bge-m3:latest`).
2. **Storage TrueNAS SCALE**:
   - Il pool NVMe `stripe` ha oltre **3.42 TiB** di spazio disponibile.
   - La gestione della rete è attestata su LACP `bond0` con IP `10.10.20.50` (VLAN 20).
   - La connettività tra PVE3 (`10.10.10.31` su VLAN 10) e TrueNAS (`10.10.20.50` su VLAN 20) avviene tramite routing L3 su switch Extreme Summit X620 a 10G con latenza sub-millisecondo (~0.1 ms). Il container CT 300 si trova direttamente su VLAN 20 (`10.10.20.33`), nello stesso segmento L2 di TrueNAS.

### Obiettivi
- Creare un dataset ZFS dedicato `stripe/ollama` su TrueNAS con recordsize ottimizzato per file di pesi LLM (1M).
- Esporre il dataset tramite NFSv4.2 con permessi idonei e compatibili con container unprivileged.
- Montare la risorsa su PVE3 e assegnarla a CT 300 come mount point dedicato per Ollama.
- Migrare i 40 GB di modelli esistenti per evitare il riscaricamento e recuperare lo spazio sul disco locale di PVE3.
- Allineare la documentazione canonica (`storage.json` e `wiki/`).

---

## 2. Decisione Architetturale: Metodo di Assegnazione Storage in Proxmox

Per collegare la share NFS a un container LXC unprivileged in Proxmox VE, sono valutabili due modalità:

```
┌────────────────────────────────────────────────────────────────────────┐
│                        TrueNAS SCALE (10.10.20.50)                     │
│                        Dataset: /mnt/stripe/ollama                     │
│                        Export NFS: networks 10.10.10.0/24, 20.0/24     │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │ NFSv4.2 (10 GbE)
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│                         Proxmox VE PVE3 Host                           │
│              Storage PVE: truenas-ollama (/mnt/pve/truenas-ollama)     │
└───────────────────┬────────────────────────────────┬───────────────────┘
                    │                                │
         [Opzione A - Consigliata]         [Opzione B]
       Bind Mount Diretto Directory      Virtual Disk Managed (.raw)
                    │                                │
                    ▼                                ▼
       File nativi su ZFS TrueNAS       File raw monolitico ext4
       Ispezionabili e condivisibili    Opaco per TrueNAS
       Pattern identico a CT 301 Games  Quota rigida Proxmox GUI
                    │                                │
                    └────────────────┬───────────────┘
                                     ▼
                    ┌────────────────────────────────┐
                    │      CT 300 (lxc-ollama)       │
                    │   mp0: ... -> /mnt/ollama      │
                    │   (oppure ~/.ollama/models)    │
                    └────────────────────────────────┘
```

| Parametro | Opzione A: Storage PVE + Bind Mount Nativo (Consigliata) | Opzione B: Virtual Disk Formattato (.raw su NFS) |
| :--- | :--- | :--- |
| **Definizione Proxmox** | Configurazione in `/etc/pve/storage.cfg` e bind `mp0: /mnt/pve/truenas-ollama,mp=...` in `300.conf` | `pct set 300 -mp0 truenas-ollama:<dimensione_in_G>,mp=...` |
| **Formato su TrueNAS** | File nativi GGUF/safetensors/blobs leggibili su ZFS `/mnt/stripe/ollama` | File monolitico `images/300/subvol-300-disk-1.raw` (ext4 incapsulato) |
| **Overhead I/O** | Minimo (chiamate POSIX dirette via client NFS host) | Doppio overhead (filesystem ext4 su loop-device sopra NFS) |
| **Ispezione & Backup** | File visibili da snapshot TrueNAS e script | Richiede mount loopback per estrarre file |
| **Coerenza Homelab** | Identico all'implementazione già operativa su CT 301 (`lxc-steam` con `/mnt/pve/games`) | Non usato per altri dataset multimediali o dati |

> [!TIP]
> Si raccomanda l'**Opzione A**: l'export NFS viene censito in Proxmox come storage `truenas-ollama`, montato nativamente su PVE3 in `/mnt/pve/truenas-ollama`, e agganciato a CT 300 tramite mountpoint `mp0`. In questo modo tutti i modelli restano file ZFS nativi trasparenti e performanti.

---

## 3. Schema Dati e Permessi (NFS Storage Schema)

In conformità alle policy homelab (Golden Rule *NFS STORAGE SCHEMA*):
- **Percorso TrueNAS**: `/mnt/stripe/ollama`
- **Owner TrueNAS**: `olindo:k8s` (`chown -R olindo:k8s /mnt/stripe/ollama`)
- **Permessi cartella**: `777` (`chmod -R 777 /mnt/stripe/ollama`) per garantire lettura/scrittura all'utente `ollama` (`uid=999`, che sull'host PVE si mappa a `uid=100999` a causa dell'unprivileged user namespace mapping).
- **Export NFS TrueNAS**:
  - `networks`: `["10.10.10.0/24", "10.10.20.0/24"]`
  - `maproot_user`: `"root"`
  - `maproot_group`: `"wheel"`
  - `ro`: `false`
- **Mountpoint nel Container CT 300**:
  - Percorso target nel container: `/usr/share/ollama/.ollama/models` (oppure `/mnt/ollama` con variabile `OLLAMA_MODELS=/mnt/ollama`). Il montaggio diretto su `/usr/share/ollama/.ollama/models` evita qualsiasi modifica alle unit systemd di Ollama.

---

## 4. Fasi Operative di Esecuzione (Test-Driven Protocol)

### Fase 1: Creazione Dataset ed Export NFS su TrueNAS SCALE (`10.10.20.50`)
1. **Creazione Dataset ZFS**:
   Creazione del dataset con recordsize a 1M e compressione lz4:
   ```bash
   sudo zfs create -o recordsize=1M -o compression=lz4 -o atime=off stripe/ollama
   ```
2. **Applicazione Permessi e Ownership**:
   ```bash
   sudo chown -R olindo:k8s /mnt/stripe/ollama
   ```
   ```bash
   sudo chmod -R 777 /mnt/stripe/ollama
   ```
3. **Creazione Condivisione NFS via `midclt`**:
   ```bash
   sudo midclt call sharing.nfs.create '{"path": "/mnt/stripe/ollama", "comment": "Ollama Models storage for PVE3 CT 300", "networks": ["10.10.10.0/24", "10.10.20.0/24"], "hosts": [], "ro": false, "maproot_user": "root", "maproot_group": "wheel", "enabled": true}'
   ```
4. **Verifica Fase 1**:
   - Esecuzione `showmount -e 10.10.20.50` da PVE3 per confermare la presenza di `/mnt/stripe/ollama` con le subnet autorizzate.

---

### Fase 2: Configurazione Storage NFS su Proxmox VE PVE3 (`10.10.10.31`)
1. **Creazione Punto di Mount Locale sull'Host**:
   ```bash
   mkdir -p /mnt/pve/truenas-ollama
   ```
2. **Aggiunta Storage NFS in `/etc/pve/storage.cfg`**:
   Registrazione dello storage vincolato al nodo `pve3`:
   ```bash
   pvesm add nfs truenas-ollama --server 10.10.20.50 --export /mnt/stripe/ollama --path /mnt/pve/truenas-ollama --nodes pve3 --content images,rootdir --options nfsvers=4.2,soft,timeo=50,retrans=3,noatime
   ```
3. **Verifica Fase 2**:
   - `pvesm status --storage truenas-ollama` deve restituire stato `active`.
   - `findmnt /mnt/pve/truenas-ollama` deve confermare il filesystem NFSv4.2 montato correttamente su PVE3.

---

### Fase 3: Migrazione Modelli e Configurazione Mount Point su CT 300
1. **Arresto Servizio Ollama su CT 300**:
   ```bash
   systemctl stop ollama
   ```
2. **Sincronizzazione Dati Esistenti**:
   Copia dei file presenti in `/usr/share/ollama/.ollama/models` verso il nuovo mount NFS:
   ```bash
   rsync -aHAXvP /usr/share/ollama/.ollama/models/ /mnt/pve/truenas-ollama/
   ```
3. **Verifica Integrità e Permessi Dati su TrueNAS**:
   - Verifica che le cartelle `blobs`, `manifests`, `metadata` siano presenti in `/mnt/pve/truenas-ollama`.
   - `chmod -R 777 /mnt/pve/truenas-ollama` per garantire accesso trasparente al namespace unprivileged del container.
4. **Backup della Directory Originale su CT 300**:
   Rinomina temporanea per rollback immediato in caso di anomalie:
   ```bash
   mv /usr/share/ollama/.ollama/models /usr/share/ollama/.ollama/models.old
   ```
   ```bash
   mkdir -p /usr/share/ollama/.ollama/models
   ```
5. **Configurazione Mount Point in `/etc/pve/lxc/300.conf` su PVE3**:
   Aggiunta del bind mountpoint `mp0`:
   ```bash
   pct set 300 -mp0 /mnt/pve/truenas-ollama,mp=/usr/share/ollama/.ollama/models
   ```
6. **Verifica Fase 3**:
   - Ispezione file di configurazione `/etc/pve/lxc/300.conf`.
   - All'interno del container (`lxc-attach 300` o ssh), verifica che `/usr/share/ollama/.ollama/models/blobs` contenga i 40 GB di dati e sia scrivibile da utente `ollama`.

---

### Fase 4: Avvio e Validazione End-to-End
1. **Riavvio Servizio Ollama**:
   ```bash
   systemctl start ollama
   ```
2. **Verifica Lista Modelli**:
   ```bash
   ollama list
   ```
   Deve elencare i modelli attuali: `qwen3-vl:32b`, `gemma4:31b`, `bge-m3:latest`.
3. **Test di Inferenza (Smoke Test)**:
   Esecuzione di una query rapida di test con il modello di embedding o chat:
   ```bash
   ollama run bge-m3 "test ping ollama"
   ```
4. **Pulizia Spazio Disco Locale (Post-Validazione)**:
   Solo dopo esito positivo confermato del test di inferenza:
   ```bash
   rm -rf /usr/share/ollama/.ollama/models.old
   ```
   Verifica recupero spazio su disco: `df -h /` su CT 300.

---

### Fase 5: Consolidamento Documentale e Registri
1. **Aggiornamento `storage.json`**:
   Aggiunta dell'export `ollama` nella sezione `nas.exports`.
2. **Validazione e Rigenerazione Wiki**:
   ```bash
   python3 scripts/network/validate_network.py && python3 scripts/wiki/build_wiki_context.py
   ```
3. **Chiusura e Commit Git**:
   Commit dei file tracciati e allineamento dello stato su `todo.md`.

## 5. Esito Esecuzione (2026-10-11)

L'intero piano è stato completato con successo seguendo il protocollo test-driven:
- **TrueNAS SCALE**: creato dataset ZFS `stripe/ollama` (`recordsize=1M`, `compression=lz4`, `atime=off`, permessi `777`, owner `olindo:k8s`). Export NFS (ID 15) attivo per le subnet `10.10.10.0/24` e `10.10.20.0/24`.
- **Proxmox PVE3**: registrato storage NFS `truenas-ollama` in `/etc/pve/storage.cfg` su `/mnt/pve/truenas-ollama` con opzioni `nfsvers=4.2,soft,timeo=50,retrans=3,noatime` (stato `active`, 3.66 TB disponibili).
- **Migrazione Dati**: trasferiti 40 GB di modelli (`blobs`, `manifests`, `metadata`) con `rsync`. Permessi impostati a `100999:100990` (`chmod 777`) per la compatibilità con il namespace unprivileged.
- **Configurazione CT 300**: aggiunto `mp0: /mnt/pve/truenas-ollama,mp=/usr/share/ollama/.ollama/models` in `/etc/pve/lxc/300.conf`. Riavviato CT 300.
- **Validazione Funzionale**: `ollama.service` attivo con accelerazione iGPU Radeon 890M Vulkan0 (31.7 GiB VRAM allocabili). Modelli censiti regolarmente (`qwen3-vl:32b`, `gemma4:31b`, `bge-m3:latest`). Eseguito smoke test di inferenza con esito positivo immediato.
- **Recupero Spazio Locale**: rimossa la directory `models.old` su PVE3. Spazio rootfs CT 300 sceso da 44 GB a **3.8 GB** (247 GB liberi su 250 GB).
- **Allineamento Configurazione**: registrato export in `storage.json` e sincronizzato `todo.md`.

---

## 💾 Stato di Ripristino (AI Save-State)
- **Fase Attiva**: Piano Completato con Successo ✅
- **Ultima Azione Completata**: Eseguite Fasi 1, 2, 3, 4 e 5: storage NFS operativo su TrueNAS stripe, bind mount attivo su CT 300, 40 GB migrati, inferenza validata e spazio locale recuperato su PVE3.
- **Prossimo Passo Operativo**: Nessuno.
- **Blocchi/Decisioni Pendenti**: Nessun blocco.

---
title: "Piano Operativo: Out-of-Band Automation Engine (LXC su TrueNAS NFS oliraid + Semaphore + MCP Gateway)"
type: plan
status: active
certified_for_ai: true
created_at: 2026-09-05
tags:
  - "#plan"
  - "#proxmox"
  - "#storage"
  - "#mcp"
  - "#ansible"
---

# Piano Operativo: Out-of-Band Automation Engine (LXC su TrueNAS NFS `oliraid` + Semaphore + MCP Gateway)

Questo piano definisce la configurazione dell'infrastruttura centrale di automazione per il cluster Proxmox VE e l'homelab, operante **fuori banda (*out-of-band*)** rispetto al cluster Kubernetes/Talos per scongiurare il problema della dipendenza circolare (*Ouroboros*).

Il piano si articola in due parti disaccoppiate da un gate di approvazione:
1. **Piano Principale (Parent Plan)**: Provisioning dell'engine di automazione su LXC non privilegiato (VMID 200, `ansible-engine`) ospitato su storage TrueNAS `oliraid` (ottimizzato per dischi meccanici con SSD Special VDEV mirror 64K), setup del runtime Ansible e di Semaphore UI con BoltDB, collaudo e test di migrazione HA.
2. **Sottopiano Specifico (Sub-Plan — Modello 3 Agile)**: Integrazione dell'MCP server in Kubernetes (`mcp-system`) tramite la Project Chart `helm-charts/mcp-gateway` con iniezione del codice FastMCP via ConfigMap (zero build Docker, aggiornamento istantaneo). **Da eseguire solo dopo il collaudo del Piano Principale.**

---

## 🗺️ Mappe Concettuali e Relazioni
- [[Proxmox]] (Cluster PVE: `pve1` 10.10.10.11, `pve2` 10.10.10.21, `pve3` 10.10.10.31)
- [[TrueNAS]] (TrueNAS SCALE 10.10.10.50, pool `oliraid`)
- [[MCP_Platform]] (Piattaforma Kuadrant & ToolHive in `mcp-system`)
- [[Traefik]] (IngressRoute per `semaphore-mcp-internal.pindaroli.org`)
- [[Secret_Registry]] (Gestione credenziali cifrate con SOPS)

---

## 🏗️ PARTE 1: PIANO PRINCIPALE (Parent Plan)

### 1. Parametri e Topologia (Source of Truth)
- **Pool TrueNAS:** `oliraid` (RAID-Z2 dischi meccanici con vdev SSD Mirror Special `mirror-2`).
- **Dataset TrueNAS:** `/mnt/oliraid/pve-shared-lxc` (Storage IP: `10.10.10.50`).
- **Storage ID Proxmox:** `truenas-nfs` (abilitato sui nodi `pve1`, `pve2`, `pve3`).
- **Container LXC:** VMID `200`, hostname `ansible-engine`.
- **Rete:** IP statico `10.10.10.60/24`, Bridge `vmbr10`, Gateway `10.10.10.1`, DNS `192.168.2.254`.
- **Database:** BoltDB embedded (`/opt/semaphore/database.bolt`).

### 2. Fasi Operative del Piano Principale

#### FASE 1: Storage ZFS Ottimizzato su TrueNAS e Montaggio PVE
1. **Creazione Dataset su TrueNAS (`10.10.10.50`):**
   ```bash
   zfs create -o recordsize=64K -o special_small_blocks=64K -o atime=off -o xattr=sa -o acltype=posix -o compression=lz4 oliraid/pve-shared-lxc
   chown -R olindo:k8s /mnt/oliraid/pve-shared-lxc
   chmod 777 /mnt/oliraid/pve-shared-lxc
   ```
2. **Configurazione Export NFS su TrueNAS:**
   - Percorso: `/mnt/oliraid/pve-shared-lxc`, reti ammesse `10.10.10.0/24`, `maproot_user=root`, `maproot_group=wheel`, opzione `insecure`.
3. **Aggiunta Storage `truenas-nfs` nel Cluster Proxmox VE (da `pve1`):**
   ```bash
   pvesm add nfs truenas-nfs --server 10.10.10.50 --export /mnt/oliraid/pve-shared-lxc --content rootdir,images --options vers=4.1,hard,intr,noatime --nodes pve1,pve2,pve3
   ```
4. **Verifica:** `pvesm status --storage truenas-nfs` -> `active` su tutti i nodi.

#### FASE 2: Provisioning Container LXC 200
1. **Verifica/Download Template Debian 12:** `pveam list local | grep debian-12`.
2. **Creazione Container:**
   ```bash
   pct create 200 local:vztmpl/debian-12-standard_12.7-1_amd64.tar.zst \
     --hostname ansible-engine \
     --cores 2 \
     --memory 1024 \
     --swap 512 \
     --storage truenas-nfs \
     --rootfs volume=truenas-nfs:15 \
     --net0 name=eth0,bridge=vmbr10,ip=10.10.10.60/24,gw=10.10.10.1 \
     --nameserver 192.168.2.254 \
     --unprivileged 1 \
     --features nesting=1 \
     --onboot 1 \
     --start 1
   ```
3. **Integrazione Proxmox HA Manager:**
   ```bash
   ha-manager add ct:200 --state started --max_relocate 1
   ```
4. **Verifica:** `pct status 200` (`running`), ping `10.10.10.60`.

#### FASE 3: Runtime Ansible & Hardening LXC
Operazioni all'interno di LXC 200 (`pct enter 200`):
1. **Installazione Pacchetti:** `apt-get update && apt-get install -y python3-full python3-pip python3-venv git curl jq openssh-client ca-certificates sudo`
2. **Utente e Virtualenv:**
   - Creazione utente `semaphore` con home `/opt/semaphore`.
   - Creazione venv `/opt/ansible-runtime/venv`.
   - Installazione `ansible-core>=2.16.0,<2.18.0`, `proxmoxer`, `requests`, `kubernetes`.
   - Installazione collezioni `community.general`, `community.proxmox`, `kubernetes.core`.
3. **Setup SSH Passwordless:**
   - Generazione chiave ED25519 per `semaphore`.
   - Distribuzione della chiave pubblica sui nodi (`pve1`, `pve2`, `pve3`, `truenas`, `pbs`).
4. **Verifica:** Test `ansible --version` e test SSH verso `pve1` con `BatchMode=yes`.

#### FASE 4: Installazione ed Avvio Semaphore (BoltDB)
1. **Installazione Binario:** Scaricamento `.deb` ufficiale Semaphore UI ed installazione con `dpkg -i`.
2. **Configurazione BoltDB (`/etc/semaphore/config.json`):**
   - Dialetto `bolt`, file host `/opt/semaphore/database.bolt`, porta `3000`.
   - Generazione chiavi di cifratura casuali a 32 byte base64 (`openssl rand -base64 32`).
3. **Creazione Systemd Unit (`/etc/systemd/system/semaphore.service`):**
   - Servizio con `User=semaphore` ed environment `/opt/ansible-runtime/venv/bin`.
   - `systemctl enable --now semaphore`.
4. **Verifica:** `curl -I http://10.10.10.60:3000` (HTTP 200 OK). Inizializzazione primo utente admin ed estrazione API Token.

#### FASE 5: Acceptance Test del Piano Principale (Gate di Approvazione)
1. **Verifica Storage su TrueNAS:** `pct config 200 | grep "rootfs:"` su `truenas-nfs`.
2. **Test di Migrazione (Restart Migration tra nodi PVE):**
   - Esecuzione `pct migrate 200 pve2 --restart`.
   - Verifica riavvio del container e ripresa di Semaphore su `pve2` in < 15 secondi.
   - Rientro su `pve1`: `pct migrate 200 pve1 --restart`.
3. **Persistenza Documentazione Parent:** Creazione di `docs/wiki/infrastructure/automation-engine-lxc-nfs-setup.md`.
4. **Aggiornamento Registri:** `rete.json` (aggiunta `ansible-engine`) e `storage.json` (aggiunta export `pve-shared-lxc`).

> [!CAUTION]
> **GATE DI TRANSIZIONE:** La PARTE 2 (Sottopiano MCP) verrà avviata **SOLTANTO DOPO** il superamento con successo di tutti i punti della Fase 5 del Piano Principale e previa tua conferma esplicita.

---

## ⚡ PARTE 2: SOTTOPIANO SPECIFICO (Sub-Plan: K8s MCP Gateway — Modello 3)

### Obiettivo Architetturale
Integrare il worker MCP all'interno della Project Chart esistente **`helm-charts/mcp-gateway`** nel namespace `mcp-system`, adottando il **Modello 3 (ConfigMap Mount)**:
- Il codice Python sorgente risiede direttamente nel repository in `scripts/semaphore-mcp/server.py`.
- Viene iniettato nel Pod Kubernetes tramite una ConfigMap sincronizzata da Helm.
- **Vantaggio Agile:** Qualsiasi modifica a `server.py` viene applicata in 2 secondi con `helm upgrade`, senza alcuna necessità di compilare immagini Docker su GHCR.

### Fasi del Sottopiano
1. **Sottofase 1: Codice Sorgente FastMCP:** Creazione di `scripts/semaphore-mcp/server.py`.
2. **Sottofase 2: Secret SOPS:** Creazione e cifratura di `secrets-sops/semaphore-mcp-credentials.enc.yaml`.
3. **Sottofase 3: Estensione `helm-charts/mcp-gateway`:**
   - Inclusione script via ConfigMap in `helm-charts/mcp-gateway/templates/semaphore-configmap.yaml`.
   - Override valori in `mcp-gateway/mcp-gateway-values.yaml`.
   - Bump di versione semantica `Chart.yaml` (`0.2.3` $\to$ `0.2.4`) ed `helm upgrade`.
4. **Sottofase 4: Client AI (`mcp_config.json`):** Aggiunta entry `"semaphore": { "serverUrl": "https://semaphore-mcp-internal.pindaroli.org/mcp" }`.
5. **Sottofase 5: Acceptance Test Sottopiano:** Validazione `curl -k https://semaphore-mcp-internal.pindaroli.org/mcp` e test chiamata tool `list_automation_templates()`.

---

## 💾 Stato di Ripristino (AI Save-State)
- **Fase Attiva**: PARTE 1 - Fase 1 / Configurazione Storage ZFS su TrueNAS
- **Ultima Azione Completata**: Persistenza del piano nel Wiki (`docs/wiki/` e `wiki/plans/`) e allineamento di `todo.md`
- **Prossimo Passo Operativo**: Esecuzione Passo 1.1 (Creazione dataset `oliraid/pve-shared-lxc` con recordsize=64K, special_small_blocks=64K, atime=off, xattr=sa, lz4, chmod 777, olindo:k8s)
- **Blocchi/Decisioni Pendenti**: In attesa di autorizzazione per eseguire il Passo 1.1

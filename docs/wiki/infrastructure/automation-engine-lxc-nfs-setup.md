# Out-of-Band Automation Engine: LXC su TrueNAS NFS (`oliraid`) + Semaphore + MCP Gateway

## 1. Overview Architetturale
Per garantire la massima resilienza operativa ed evitare il blocco circolare (*paradosso dell'Ouroboros*), l'engine centrale di automazione dell'infrastruttura Proxmox VE e dell'homelab è disaccoppiato dal cluster Kubernetes/Talos e opera in modalità **fuori banda (*out-of-band*)**.

L'architettura adotta un **Container LXC non privilegiato (VMID 200, `ansible-engine`)** il cui rootfs risiede su storage condiviso NFS fornito da TrueNAS SCALE sul pool meccanico **`oliraid`**:
* **Preservazione Hardware NVMe:** Tutte le scritture generate dai log Ansible e dalle transazioni BoltDB vengono convogliate su TrueNAS, azzerando la write amplification sugli SSD NVMe dei nodi Proxmox.
* **Special VDEV SSD Acceleration:** Sfruttando il vdev `mirror-2` (SSD SATA Mirror) su `oliraid` con `special_small_blocks=64K`, tutti i metadati ZFS e i blocchi $\le$ 64 KB (pagine BoltDB, file Python, script) godono di latenza SSD senza generare seek sulle testine meccaniche.
* **Mobilità di Cluster & High Availability (HA):** L'LXC può migrare a caldo/restart tra i tre nodi Proxmox (`pve1`, `pve2`, `pve3`) con downtime $< 15$ secondi ed è gestito dal Proxmox HA Manager (`ha-manager`).
* **Integrazione Duale (WebUI + MCP Gateway K8s):** Durante la normale operatività, l'AI interagisce via Kubernetes tramite la Project Chart `helm-charts/mcp-gateway` (FastMCP su IngressRoute `https://semaphore-mcp-internal.pindaroli.org/mcp`). In caso di disastro o spegnimento di K8s, Semaphore rimane autonomamente accessibile via WebUI (`http://10.10.10.60:3000`).

---

## 2. Storage & NFS Configuration (`oliraid`)

### Specifiche Dataset ZFS su TrueNAS (`10.10.10.50`)
* **Percorso:** `/mnt/oliraid/pve-shared-lxc`
* **Recordsize:** `64K` (allineato alla soglia del vdev Special per ottimizzare I/O random)
* **Special Small Blocks:** `64K` (dirotta metadati e file $\le$ 64KB sul mirror SSD `mirror-2`)
* **Atime:** `off` (elimina le continue micro-scritture ad ogni import di moduli Python)
* **Xattr:** `sa` (System Attributes in inode, velocizza i metadati POSIX di Linux)
* **Acltype:** `posix` (compatibilità nativa container Debian)
* **Compression:** `lz4` (massimo throughput I/O)
* **Permessi Fisici:** `chmod 777` con ownership `olindo:k8s`

### Configurazione Export NFS su TrueNAS
* **Path:** `/mnt/oliraid/pve-shared-lxc`
* **Allowed Networks:** `10.10.10.0/24` (VLAN 10 Server)
* **Maproot User:** `root`
* **Maproot Group:** `wheel`
* **Options:** `insecure` (porte non privilegiate ammesse)

### Storage Proxmox VE (`truenas-nfs`)
Configurato a livello di cluster PVE per tutti i nodi (`pve1`, `pve2`, `pve3`):
```bash
pvesm add nfs truenas-nfs \
  --server 10.10.10.50 \
  --export /mnt/oliraid/pve-shared-lxc \
  --content rootdir,images \
  --options vers=4.1,hard,intr,noatime \
  --nodes pve1,pve2,pve3
```

---

## 3. LXC Deployment (VMID 200: `ansible-engine`)

### Parametri di Creazione
* **Nodo iniziale:** `pve1`
* **VMID:** `200`
* **Template OS:** `local:vztmpl/debian-12-standard_12.7-1_amd64.tar.zst`
* **Hostname:** `ansible-engine`
* **Cores:** 2
* **Memory:** 1024 MB
* **Swap:** 512 MB
* **RootFS:** `truenas-nfs:15` (15 GB)
* **Network:** `eth0`, Bridge `vmbr10`, IP `10.10.10.60/24`, Gateway `10.10.10.1`, DNS `192.168.2.254`
* **Features:** `nesting=1`, `unprivileged=1`, `onboot=1`

### Comando CLI Proxmox:
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

### Registrazione High Availability:
```bash
ha-manager add ct:200 --state started --max_relocate 1
```

---

## 4. Ansible & Semaphore Runtime (LXC Internals)

### Isolamento Virtualenv e Collezioni
* Utente di servizio dedicato: `semaphore` (home `/opt/semaphore`).
* Virtualenv: `/opt/ansible-runtime/venv`.
* Pacchetti Python: `ansible-core>=2.16.0,<2.18.0`, `proxmoxer`, `requests`, `kubernetes`.
* Collezioni Ansible: `community.general`, `community.proxmox`, `kubernetes.core`.
* Autenticazione: Coppia di chiavi SSH ED25519 (`/opt/semaphore/.ssh/id_ed25519`) autorizzata su tutti i nodi (`pve1`, `pve2`, `pve3`, `truenas`, `pbs`) senza password (`BatchMode=yes`).

### Configurazione Semaphore (BoltDB)
File `/etc/semaphore/config.json`:
```json
{
  "dialect": "bolt",
  "bolt": {
    "host": "/opt/semaphore/database.bolt"
  },
  "port": "3000",
  "interface": "0.0.0.0",
  "tmp_path": "/tmp/semaphore",
  "cookie_hash": "<GENERATED_BASE64_32>",
  "cookie_encryption": "<GENERATED_BASE64_32>",
  "access_key_encryption": "<GENERATED_BASE64_32>"
}
```

### Systemd Unit (`/etc/systemd/system/semaphore.service`)
```ini
[Unit]
Description=Ansible Semaphore UI & Engine
After=network.target

[Service]
Type=simple
User=semaphore
Group=semaphore
Environment="PATH=/opt/ansible-runtime/venv/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"
ExecStart=/usr/bin/semaphore server --config /etc/semaphore/config.json
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

---

## 5. MCP Service Definition (Integrazione K8s Modello 3 Agile)

L'MCP server è integrato nella Project Chart `helm-charts/mcp-gateway` nel namespace `mcp-system`.

### Componenti del Sottopiano MCP:
1. **Codice Sorgente FastMCP:** risiede in `scripts/semaphore-mcp/server.py` dentro `k8s-lab`.
2. **Iniezione via ConfigMap (Modello 3):** il codice Python viene montato nel Pod via ConfigMap gestita da Helm. Modificando `server.py`, basta un `helm upgrade` per ricaricare il Pod in 2 secondi senza alcuna build Docker.
3. **Valori Helm (`mcp-gateway/mcp-gateway-values.yaml`):**
   ```yaml
   servers:
     - name: semaphore
       url: "http://mcp-semaphore-mcp-proxy.mcp-system.svc.cluster.local:8080/mcp"
       hostname: "mcp-semaphore-mcp-proxy.mcp-system.svc.cluster.local"
       enabled: true
       prefix: "semaphore_"
       ingress:
         enabled: true
         host: "semaphore-mcp-internal.pindaroli.org"
         port: 8080
       toolhive:
         enabled: true
         name: semaphore-mcp
         image: python:3.12-slim
         transport: stdio
         proxyPort: 8080
         secrets:
           - name: semaphore-mcp-credentials
             key: SEMAPHORE_API_TOKEN
             targetEnvName: SEMAPHORE_API_TOKEN
         env:
           - name: SEMAPHORE_URL
             value: "http://10.10.10.60:3000/api"
           - name: SEMAPHORE_PROJECT_ID
             value: "1"
   ```
4. **Client AI (`~/.gemini/antigravity/mcp_config.json`):**
   ```json
   "semaphore": {
     "serverUrl": "https://semaphore-mcp-internal.pindaroli.org/mcp"
   }
   ```

---

## 6. Runbook di Disaster Recovery & Migrazione

### Scenario 1: Migrazione Programmata tra Nodi PVE
Per spostare l'LXC 200 su un altro nodo (es. durante manutenzione o upgrade di `pve1`):
```bash
# Esecuzione restart migration verso pve2
pct migrate 200 pve2 --restart

# Verifica stato su pve2
pct status 200
curl -I http://10.10.10.60:3000
```
Il tempo di fermo fisiologico è di circa 5–10 secondi. Al termine, BoltDB si rimonta automaticamente e Semaphore riprende senza errori di lock.

### Scenario 2: Guasto Hardware del Nodo PVE Primario (HA Automatico)
1. Il watchdog di Proxmox HA rileva la caduta di `pve1`.
2. Proxmox HA Manager ordina l'avvio di `ct:200` su `pve2` o `pve3`.
3. Il disco `truenas-nfs:subvol-200-disk-0` viene montato dal secondo nodo senza necessità di migrazione dati (storage già condiviso su TrueNAS).
4. Il servizio Semaphore riparte automaticamente sulla stessa interfaccia IP `10.10.10.60`.

### Scenario 3: Cluster Kubernetes/Talos Totalmente Inaccessibile
In caso di blocco di K8s (es. quorum etcd perso, upgrade bloccato, ingress non funzionante):
1. **Accesso Web Diretto:** Accedere da qualsiasi browser della LAN a `http://10.10.10.60:3000`.
2. **Esecuzione Playbook di Ripristino:** Lanciare direttamente da Semaphore i task template pre-configurati per il ripristino dei nodi Talos o dei servizi K8s.
3. **Nessuna dipendenza circolare:** L'automazione non richiede nulla di K8s per operare.

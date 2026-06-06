# Piano: Reinstallazione PVE2 su newPVE2 e Migrazione Dati

> [!IMPORTANT]
> **PREREQUISITO**: PVE2 deve essere acceso e raggiungibile via SSH (`10.10.10.21`) per la Fase 0. Console fisica (monitor + tastiera) disponibile per la Fase 1.
>
> **Accesso OOB attuale**: IP OOB corrente è `192.168.100.21` (allineato e configurato).

## Dizionario Fisico (DEFINITIVO)

| Alias | Device | Modello | Dimensione | Stato |
|-------|--------|---------|------------|-------|
| **oldPVE2** | `nvme1n1` | Acer SSD N7000 2TB (`ASBK53470103815`) | 1.8 TB | Ha Proxmox VE 9.1 installato |
| **newPVE2** | `nvme0n1` | INTEL 512GB (`BTHP95240V0D512C`) | 476.9 GB | Target installazione Proxmox VE 9.2 |

> [!NOTE]
> **PBS**: Confermato online su PVE1 (LXC 1400, uptime 17 giorni, disk 24.9%). Backup disponibili.
> **OOB IP PVE2**: IP OOB è impostato a `192.168.100.21` (allineato con il pattern di PVE1 e PVE3).
> **IP Management**: `10.10.10.21` — confermato come definitivo.

---

## Fase 0: Raccolta Dati da oldPVE2 (PRIMA di qualsiasi intervento)

> [!CAUTION]
> Questa fase deve essere eseguita **con oldPVE2 acceso** e raggiungibile, prima di toccare qualsiasi SSD fisicamente.
> PVE2 può essere raggiunto via produzione (`10.10.10.21`) oppure OOB (`192.168.100.21`).

### Step 0.1: Dump Configurazione Completa di oldPVE2

```bash
# Check: Verifica che oldPVE2 sia raggiungibile
ssh root@10.10.10.21 "hostname && cat /etc/debian_version && pveversion"
```
**Risultato atteso**: hostname `pve2`, versione Debian, Proxmox VE 9.1.

```bash
# Raccolta configurazioni
ssh root@10.10.10.21 "cat /etc/network/interfaces"
ssh root@10.10.10.21 "cat /etc/hosts"
ssh root@10.10.10.21 "cat /etc/pve/corosync.conf"
ssh root@10.10.10.21 "qm list && pct list"
ssh root@10.10.10.21 "cat /etc/pve/storage.cfg"
ssh root@10.10.10.21 "cat /etc/default/grub"
ssh root@10.10.10.21 "lsblk -o NAME,SIZE,MODEL,SERIAL,TYPE | grep disk"
```

**CHECK OBBLIGATORIO** — salva il dump sul Mac:
```bash
ssh root@10.10.10.21 "tar -czf /tmp/pve2-config-dump.tar.gz \
  /etc/network/interfaces \
  /etc/hosts \
  /etc/pve/corosync.conf \
  /etc/pve/storage.cfg \
  /etc/default/grub \
  /etc/modprobe.d/ \
  2>/dev/null || true"

scp root@10.10.10.21:/tmp/pve2-config-dump.tar.gz \
  ~/Desktop/pve2-config-backup-$(date +%F).tar.gz
```

---

### Step 0.2: Backup Manuale Forzato su PBS

```bash
# Verifica PBS online
ssh root@10.10.10.11 "pct status 1400"

# Forza backup di tutte le VM/LXC di PVE2
ssh root@10.10.10.21 "vzdump --all --storage pbs --mode snapshot --compress zstd"
```

**CHECK OBBLIGATORIO**: Verificare su PBS (`https://10.10.10.100:8007`) che tutti i backup abbiano status OK e timestamp recente.

---

### Step 0.3: Identificazione Fisica dei Dischi

```bash
ssh root@10.10.10.21 "lsblk -o NAME,SIZE,MODEL,SERIAL,TYPE | grep disk"
```

**Risultato atteso e mappatura definitiva**:
- `nvme1n1`: 1.8 TB — Acer SSD N7000 2TB (`ASBK53470103815`) → **oldPVE2** (OS corrente Proxmox 9.1)
- `nvme0n1`: 476.9 GB — INTEL 512GB (`BTHP95240V0D512C`) → **newPVE2** (target installazione)

> [!WARNING]
> **ATTENZIONE**: Il disco target è `nvme0n1` (Intel, 476.9 GB). NON selezionare `nvme1n1` (Acer 2TB, oldPVE2) durante l'installazione o si cancelleranno i dati originali.

---

## Fase 1: Installazione di Proxmox VE 9.2 su newPVE2

> [!CAUTION]
> **INTERVENTO FISICO**: Console (monitor + tastiera) confermata disponibile. Collegala a PVE2 prima di avviare l'installazione.

### Step 1.1: Preparazione USB di Installazione (dal Mac Studio)

```bash
# Identifica la USB sul Mac
diskutil list

# Scrivi l'ISO (adatta disk4 al tuo device USB — VERIFICA bene il device!)
sudo dd if=~/Downloads/proxmox-ve_9.2-1.iso of=/dev/rdisk4 bs=4M status=progress
```

> Scarica l'ISO da: https://www.proxmox.com/en/downloads (sezione Proxmox VE)

### Step 1.2: Installazione via Wizard

Nel wizard Proxmox:
- **Target disk**: **`nvme0n1` (Intel 512GB)** — newPVE2. Verificare che sia il disco da ~476 GB.
- **Hostname**: `pve2.pindaroli.local`
- **IP Management**: `10.10.10.21/24`
- **Gateway**: `10.10.10.1`
- **DNS**: `10.10.10.254`

**CHECK POST-INSTALLAZIONE**:
```bash
ping -c 3 10.10.10.21
ssh root@10.10.10.21 "pveversion && hostname && uname -r"
```
**Risultato atteso**: Proxmox VE 9.2, hostname `pve2`.

---

## Fase 2: Configurazione Post-Installazione di newPVE2

### Step 2.1: Verifica Nomi Interfacce di Rete

```bash
ssh root@10.10.10.21 "ip -c link show"
```

Confronta con i nomi attesi (da `rete.json` e `istruzioni/interfaces_pve2.txt`):
- `enp1s0f0np0` → VLAN 10 (vmbr10)
- `enp1s0f1np1` → VLAN 20 (vmbr20)
- `nic0` → OOB Service Port

> [!IMPORTANT]
> Se i nomi differiscono, adatta il file di configurazione di conseguenza prima di applicarlo.

### Step 2.2: Applicazione `/etc/network/interfaces`

```bash
ssh root@10.10.10.21 "cat > /etc/network/interfaces" << 'EOF'
auto lo
iface lo inet loopback

# NODO: PVE2 (Node 2) - IP: 10.10.10.21
auto nic0
iface nic0 inet static
    address 192.168.100.21/24
# Porta OOB di servizio (VLAN 99 - No Gateway)

iface enp1s0f0np0 inet manual
# Porta 1 (VLAN 10 - Server)

iface enp1s0f1np1 inet manual
# Porta 2 (VLAN 20 - Client)

# BRIDGE MANAGEMENT & SERVER (VLAN 10)
auto vmbr10
iface vmbr10 inet static
    address 10.10.10.21/24
    gateway 10.10.10.1
    bridge-ports enp1s0f0np0
    bridge-stp off
    bridge-fd 0

# BRIDGE CLIENT (VLAN 20)
auto vmbr20
iface vmbr20 inet manual
    bridge-ports enp1s0f1np1
    bridge-stp off
    bridge-fd 0
EOF
```

```bash
# Verifica e riavvia networking
ssh root@10.10.10.21 "systemctl restart networking && ip addr show"
```

### Step 2.3: Aggiornamento `/etc/hosts`

```bash
ssh root@10.10.10.21 'cat > /etc/hosts << EOF
127.0.0.1       localhost
127.0.1.1       pve2.pindaroli.local pve2

10.10.10.11     pve.pindaroli.local pve
10.10.10.21     pve2.pindaroli.local pve2
10.10.10.31     pve3.pindaroli.local pve3
EOF'
```

**CHECK**:
```bash
ssh root@10.10.10.21 "ping -c 2 pve && ping -c 2 pve3"
```

### Step 2.4: Configurazione Repositori (No Subscription)

```bash
ssh root@10.10.10.21 "
echo 'deb http://download.proxmox.com/debian/pve bookworm pve-no-subscription' \
  > /etc/apt/sources.list.d/pve-install-repo.list
sed -i 's/^deb/#deb/' /etc/apt/sources.list.d/pve-enterprise.list 2>/dev/null || true
apt-get update && apt-get dist-upgrade -y
"
```

### Step 2.5: Ripristino Selettivo delle Configurazioni da Backup ("Diff & Port")

```bash
# 1. Copia ed estrazione del dump di configurazione temporaneo su newPVE2
scp ~/Desktop/pve2-config-backup-*.tar.gz root@10.10.10.21:/tmp/pve2-config-dump.tar.gz
ssh root@10.10.10.21 "mkdir -p /tmp/old-pve2-config && tar -xzf /tmp/pve2-config-dump.tar.gz -C /tmp/old-pve2-config/"

# 2. Ispezione dei vecchi parametri del kernel in GRUB
ssh root@10.10.10.21 "cat /tmp/old-pve2-config/etc/default/grub | grep GRUB_CMDLINE_LINUX_DEFAULT"

# 3. Confronto e ripristino di eventuali driver custom in /etc/modprobe.d/
ssh root@10.10.10.21 "ls -la /tmp/old-pve2-config/etc/modprobe.d/"
# Se ci sono file custom (es. vfio.conf), copiarli manualmente:
# ssh root@10.10.10.21 "cp /tmp/old-pve2-config/etc/modprobe.d/NOMEFILE.conf /etc/modprobe.d/"

# 4. Configurazione Esplicita di "nomodeset" (e altri parametri IOMMU)
# UEFI usa systemd-boot: i parametri vanno scritti come unica riga in /etc/kernel/cmdline
# Leggi l'attuale riga di comando:
ssh root@10.10.10.21 "cat /etc/kernel/cmdline"

# Aggiungi esplicitamente "nomodeset" per prevenire hang grafici della GPU integrata
# Esegui l'append sicuro (aggiunge nomodeset in fondo se non già presente):
ssh root@10.10.10.21 "grep -q 'nomodeset' /etc/kernel/cmdline || sed -i 's/$/ nomodeset/' /etc/kernel/cmdline"

# Se necessario, aggiungi "intel_iommu=on" (o altri parametri estratti dal vecchio GRUB al punto 2):
# ssh root@10.10.10.21 "sed -i 's/$/ intel_iommu=on/' /etc/kernel/cmdline"

# Verifica il contenuto finale di /etc/kernel/cmdline:
ssh root@10.10.10.21 "cat /etc/kernel/cmdline"

# Rigenera il bootloader (OBBLIGATORIO dopo ogni modifica a /etc/kernel/cmdline):
ssh root@10.10.10.21 "proxmox-boot-tool refresh"

# 5. Append dei nodi del cluster a /etc/hosts (senza sovrascrivere il resto)
ssh root@10.10.10.21 "cat /tmp/old-pve2-config/etc/hosts | grep -E 'pve|pve3' >> /etc/hosts"
```

---

## Fase 3: Re-Integrazione nel Cluster Proxmox

> [!CAUTION]
> **PREREQUISITO**: PVE1 e PVE3 devono essere online con cluster in quorum.

### Step 3.1: Verifica Stato Cluster

```bash
ssh root@10.10.10.11 "pvecm status && pvecm nodes"
```
**Risultato atteso**: Cluster con 2 nodi online (pve + pve3). PVE2 assente o offline.

### Step 3.2: Rimozione Entrata Obsoleta di PVE2

```bash
# Se pve2 risulta come nodo zombie
ssh root@10.10.10.11 "pvecm delnode pve2"

# Verifica
ssh root@10.10.10.11 "pvecm nodes"
```

### Step 3.3: Join di newPVE2 al Cluster

```bash
# Eseguito su newPVE2
ssh root@10.10.10.21 "pvecm add 10.10.10.11"
# Richiederà la password root di PVE1
```

**CHECK OBBLIGATORIO** (attendi 30-60 secondi dopo il join):
```bash
ssh root@10.10.10.11 "pvecm status && pvecm nodes"
```
**Risultato atteso**: 3 nodi (pve, pve2, pve3), `Quorum acquired`, tutti Online.

### Step 3.4: Verifica Corosync

```bash
ssh root@10.10.10.21 "journalctl -u corosync --since '5 minutes ago' | tail -20"
ssh root@10.10.10.21 "cat /etc/pve/corosync.conf | grep -A5 'pve2'"
```

### Step 3.5: Pulizia ed Inizializzazione del Disco da 2 TB (nvme1n1)

```bash
# 1. Verifica identificativi del disco per non sbagliare target
ssh root@10.10.10.21 "lsblk -o NAME,SIZE,MODEL,SERIAL"
# target: nvme1n1 (Acer SSD N7000 2TB, serial ASBK53470103815)

# 2. Pulizia radicale delle vecchie partizioni e tabelle dei dischi
ssh root@10.10.10.21 "sgdisk --zap-all /dev/nvme1n1"
ssh root@10.10.10.21 "wipefs -a /dev/nvme1n1"

# 3. Creazione del Volume Group LVM 'pve-2tb'
ssh root@10.10.10.21 "pvcreate /dev/nvme1n1"
ssh root@10.10.10.21 "vgcreate pve-2tb /dev/nvme1n1"

# 4. Creazione del thin pool 'data'
ssh root@10.10.10.21 "lvcreate -l 100%FREE --thinpool data pve-2tb"
```

**CHECK**:
```bash
ssh root@10.10.10.21 "lvs && vgs"
```

### Step 3.6: Registrazione dello Storage LVM-Thin nel Cluster

```bash
# Aggiunta dello storage nel file condiviso /etc/pve/storage.cfg limitandolo a PVE2
ssh root@10.10.10.21 "pvesm add lvmthin local-lvm-2tb \
  --vgname pve-2tb \
  --thinpool data \
  --content images,rootdir \
  --nodes pve2"
```

**CHECK**:
```bash
ssh root@10.10.10.21 "pvesm status | grep local-lvm-2tb"
```

---

## Fase 4: Ripristino VM e LXC da PBS

> [!IMPORTANT]
> **PREREQUISITO**: Cluster in quorum (Fase 3 completata). PBS online.

### Step 4.1: Verifica Storage PBS su newPVE2

```bash
ssh root@10.10.10.21 "pvesm status"
```

Se PBS non è presente come storage (dovrebbe esserlo in automatico ereditato dal cluster):
```bash
# Se mancante, aggiungilo:
ssh root@10.10.10.21 "pvesm add pbs pbs \
  --server 10.10.10.100 \
  --datastore main \
  --username root@pam \
  --content backup"
```

### Step 4.2: Lista Backup Disponibili

```bash
# Lista backup su PBS
ssh root@10.10.10.21 "pvesm list pbs"
```

### Step 4.3: Ripristino di talos-cp-02 (VM 2300) — CRITICA

> [!IMPORTANT]
> VM 2300 ha `host_node_sticky: true` — deve essere ripristinata **su PVE2** e **sullo storage local-lvm-2tb**.
> Se la configurazione orfana (zombie) della VM 2300 è già visibile sulla GUI dopo il join, si deve usare `--force` per sovrascriverla.

```bash
# Ripristino da CLI (sostituisci TIMESTAMP con il timestamp reale del backup ottenuto dallo step 4.2)
ssh root@10.10.10.21 "qmrestore pbs:backup/vm/2300/TIMESTAMP 2300 --storage local-lvm-2tb --unique 0 --force"
```

**CHECK**:
```bash
ssh root@10.10.10.21 "qm list"
```

### Step 4.4: Ripristino Eventuali Altri LXC/VM su local-lvm-2tb

Per ogni altra macchina presente precedentemente su oldPVE2:
```bash
# Per le VM:
# ssh root@10.10.10.21 "qmrestore pbs:backup/vm/<VMID>/<TIMESTAMP> <VMID> --storage local-lvm-2tb --unique 0 --force"

# Per i Container LXC:
# ssh root@10.10.10.21 "pct restore <CTID> pbs:backup/ct/<CTID>/<TIMESTAMP> --storage local-lvm-2tb --force"
```

---

## Fase 5: ➡️ Continuazione — Ripristino Cluster Kubernetes

> [!IMPORTANT]
> **Il ripristino di Kubernetes (talos-cp-02, etcd, CloudNativePG) è documentato nel piano dedicato:**
> ### [[talos-k8s-cluster-restoration]]
>
> Eseguire quel piano solo dopo aver verificato che:
> - Il cluster Proxmox ha **3 nodi in quorum** (verificato in Fase 3).
> - La VM `talos-cp-02` (ID 2300) è **ripristinata da PBS e presente su PVE2** (verificato in Fase 4).
> - L'intero piano `[[pve3-10g-migration-recovery]]` è stato completato.



## Fase 6: Aggiornamento Documentazione

- [ ] Aggiornare `rete.json`: rimuovere status `OFFLINE`, aggiornare dischi PVE2, verificare IP OOB `192.168.100.21`, aggiornare `talos-cp-02`.
- [ ] Aggiornare `istruzioni/interfaces_pve2.txt` con il file di rete definitivo (OOB `.21`).
- [ ] Aggiornare `wiki/entities/Talos_Cluster.md` con la topologia aggiornata.
- [ ] Creare incident/report di completamento migrazione in `wiki/incidents/`.

---

## Checklist Finale (Scope: Proxmox Only)

> [!NOTE]
> I check K8s/PostgreSQL sono nella checklist del piano [[talos-k8s-cluster-restoration]].

| # | Test | Comando | Risultato Atteso |
|---|------|---------|------------------|
| 1 | PVE2 raggiungibile | `ping -c 3 10.10.10.21` | 0% packet loss |
| 2 | Cluster Proxmox | `pvecm status` da PVE1 | 3 nodi, Quorum OK |
| 3 | VM 2300 ripristinata | `ssh root@10.10.10.21 "qm list"` | VM 2300 presente (stopped) |
| 4 | PBS backup verificato | GUI PBS `https://10.10.10.100:8007` | Backup OK e recenti |

---

## Note (Risposte alle Open Questions)

- ✅ **Q1 — Disco Target**: `nvme1n1` (Acer 2TB) = **oldPVE2** (OS corrente). `nvme0n1` (Intel 512GB) = **newPVE2** (target installazione). Piano aggiornato.
- ✅ **Q2 — Console**: Disponibile fisicamente su PVE2.
- ✅ **Q3 — PBS**: Online confermato (LXC 1400, uptime 17 giorni, screenshot GUI PVE1).
- ✅ **Q4 — IP OOB**: IP OOB allineato definitivamente a `192.168.100.21`.

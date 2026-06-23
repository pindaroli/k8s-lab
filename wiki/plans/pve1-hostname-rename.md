---
title: "Rinomina Hostname Nodo PVE1: pve → pve1"
created: "2026-06-22"
status: "WAITING — Prerequisito: cluster quorate (3/3 nodi online)"
tags:
  - "#proxmox"
  - "#infrastructure"
  - "#maintenance"
depends_on:
  - "[[pve1-upgrade-ve9.2]]"
  - "PVE2 e PVE3 online e in quorum"
---

# Rinomina Hostname Nodo PVE1: `pve` → `pve1`

## Obiettivo

Il nodo Proxmox principale ha hostname `pve` (legacy, da installazione iniziale). L'obiettivo è allinearlo al nome logico `pve1` usato in tutta la documentazione, in `rete.json` e nel progetto.

---

## Prerequisito BLOCCANTE

> [!CAUTION]
> **NON ESEGUIRE** finché non è soddisfatto questo prerequisito.
>
> Il piano richiede che **tutti e 3 i nodi PVE siano online e il cluster sia quorate**.
> Verificare con: `pvecm status` → `Quorate: Yes`, `Nodes: 3`
>
> **Motivo tecnico**: `/etc/pve/corosync.conf` è un filesystem distribuito (`pmxcfs`).
> La modifica del nodename viene propagata agli altri nodi **solo se il cluster ha quorum**.
> Eseguire la rinomina con PVE2/PVE3 offline crea un conflitto di `config_version` al loro rientro → potenziale split-brain difficile da risolvere.
>
> ⏳ **Stato (2026-06-22)**: PVE2 e PVE3 in manutenzione. Esecuzione rimandata.

---

## Analisi Dipendenze

### Layer 1 — Corosync (CRITICO)

**Stato attuale in `/etc/pve/corosync.conf`:**
```
node { name: pve   nodeid: 2  ring0_addr: 10.10.10.11 }
node { name: pve2  nodeid: 1  ring0_addr: 10.10.10.21 }
node { name: pve3  nodeid: 3  ring0_addr: 10.10.10.31 }
```

Da aggiornare: `name: pve` → `name: pve1`, `config_version: 12` → `config_version: 13`.

### Layer 2 — Filesystem cluster `/etc/pve/nodes/` (CRITICO)

```
/etc/pve/nodes/pve/    ← da rinominare a /etc/pve/nodes/pve1/
/etc/pve/nodes/pve2/
/etc/pve/nodes/pve3/
```

Contiene SSL keys, configurazioni VM, LXC e log del nodo.

### Layer 3 — Storage Config

In `/etc/pve/storage.cfg`, due entry con riferimento al vecchio nodename:
```
nfs: truenas-media    → nodes pve2,pve,pve3
pbs: pbs              → nodes pve,pve3,pve2
```

### Layer 4 — OS Hostname

- `/etc/hostname` → `pve`
- `/etc/hosts` → `10.10.10.11 pve.pindaroli.org pve.local pve`

### Layer 5 — DNS / rete.json

- Aggiornamento `host_node` per talos-cp-01 (VM 1300) e pbs (LXC 1400) da `"pve"` a `"pve1"`.
- Re-sync Unbound via playbook Ansible.

### Layer 6 — Talos (IMMUNE ✅)

Talos usa solo IP e VIP (`10.10.20.55`), zero riferimenti all'hostname Proxmox. Nessuna modifica richiesta.

---

## Matrice Impatti

| Layer | Impattato? | Rischio | Azione |
|---|---|---|---|
| Corosync / pvecm | ✅ Sì | 🔴 Alto | Stop servizi → edit → restart |
| `/etc/pve/nodes/` | ✅ Sì | 🔴 Alto | Rinomina directory (atomica) |
| hostname OS | ✅ Sì | 🟡 Medio | `hostnamectl` + `/etc/hosts` |
| storage.cfg | ✅ Sì | 🟡 Medio | Sostituzione testo |
| DNS / rete.json | ✅ Sì | 🟢 Basso | Ansible sync |
| Talos / K8s | ❌ No | 🟢 Nessuno | — |
| VM/LXC runtime | ❌ No | 🟢 Nessuno | Bridge `vmbr*` non cambiano |

---

## Sequenza Operativa

> [!IMPORTANT]
> Eseguire **esclusivamente via OOB SSH** (`192.168.100.11`) — mai da sessione sulla VLAN 10.
> Ogni step richiede approvazione esplicita prima di procedere.

### FASE 0 — Backup preventivo

```bash
cp /etc/hostname /root/hostname.bak-$(date +%Y%m%d-%H%M%S)
cp /etc/hosts /root/hosts.bak-$(date +%Y%m%d-%H%M%S)
cp /etc/pve/corosync.conf /root/corosync.conf.bak-$(date +%Y%m%d-%H%M%S)
cp /etc/pve/storage.cfg /root/storage.cfg.bak-$(date +%Y%m%d-%H%M%S)
```

### FASE 1 — Spegnimento VM critiche

```bash
qm shutdown 1300   # talos-cp-01
qm shutdown 1100   # truenas
pct shutdown 1400  # pbs LXC
qm list            # verifica: tutti stopped
```

### FASE 2 — Stop cluster, modifica Corosync e rinomina directory

> [!CAUTION]
> Finestra di manutenzione: ~2-3 minuti. Cluster non-quorate. GUI Proxmox irraggiungibile.

```bash
# Stop servizi cluster
systemctl stop pve-cluster pvedaemon pveproxy corosync

# Mount filesystem cluster in modalità locale
pmxcfs -l

# Aggiorna hostname OS
echo "pve1" > /etc/hostname
# Aggiorna /etc/hosts:
# DA: 10.10.10.11 pve.pindaroli.org pve.local pve
# A:  10.10.10.11 pve1.pindaroli.org pve1.local pve1 pve

# Modifica corosync.conf (config_version: 13, name: pve1)
# Rinomina directory nodo
mv /etc/pve/nodes/pve /etc/pve/nodes/pve1

# Riavvio servizi
killall pmxcfs
systemctl start corosync
sleep 5
systemctl start pve-cluster pvedaemon pveproxy

# Verifica
pvecm status    # Nodes: 3, Quorate: Yes
pvecm nodes     # lista: pve1, pve2, pve3
```

### FASE 3 — Aggiornamento storage.cfg

```bash
# In /etc/pve/storage.cfg sostituire:
# nodes pve2,pve,pve3  →  nodes pve2,pve1,pve3
# nodes pve,pve3,pve2  →  nodes pve1,pve3,pve2
pvesm status   # verifica: tutti gli storage accessibili
```

### FASE 4 — DNS e rete.json

Aggiornare `rete.json`:
- `talos-cp-01`: `"host_node": "pve"` → `"host_node": "pve1"`
- `pbs` (LXC 1400): `"host_node": "pve"` → `"host_node": "pve1"`

```bash
ansible-playbook ansible/playbooks/opnsense_sync_dns.yml
```

### FASE 5 — Riavvio VM e verifica finale

```bash
qm start 1100   # TrueNAS (~60s attesa NFS ready)
pct start 1400  # PBS
qm start 1300   # talos-cp-01

# Verifica finale
pvecm status         # 3 nodi, quorate
pvecm nodes          # pve1, pve2, pve3
qm list              # tutti running
kubectl get nodes    # talos-cp-01/02/03 Ready
ping pve1            # 10.10.10.11
# GUI: https://10.10.10.11:8006 → nodo appare come pve1
```

---

## Rollback

In caso di errore nella Fase 2:

```bash
cp /root/corosync.conf.bak-* /etc/pve/corosync.conf
echo "pve" > /etc/hostname
cp /root/hosts.bak-* /etc/hosts
mv /etc/pve/nodes/pve1 /etc/pve/nodes/pve   # se già rinominata
killall pmxcfs
systemctl start corosync pve-cluster pvedaemon pveproxy
```

---

## Relazioni

- Dipende da: [[pve1-upgrade-ve9.2]] (completare upgrade prima di rinominare)
- Impatta: `rete.json`, `storage.cfg`, Ansible DNS playbook
- Non impatta: [[Talos_Cluster]], bridge `vmbr*`, VM/LXC in runtime

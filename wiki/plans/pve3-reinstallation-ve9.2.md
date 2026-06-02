# Upgrade PVE3 a Proxmox VE 9.2 & Cluster Re-join

Questo piano descrive i passaggi per aggiornare **PVE3** a Proxmox VE 9.2 tramite un in-place upgrade (molto più semplice e pulito di una formattazione) e, in una fase separata, il ripristino del nodo all'interno del cluster.

## User Review Required

- Nessuna operazione distruttiva prevista sui dischi locali.

## Open Questions

- Per l'aggiornamento in-place, PVE3 ha già accesso ai repository corretti (es. `pve-no-subscription`) e la sottoscrizione enterprise disabilitata?

---

## Proposed Changes

### FASE 1: Upgrade In-Place a Proxmox VE 9.2

L'approccio in-place è infinitamente superiore a una reinstallazione perché preserva la configurazione di rete 10G appena collaudata, lo storage locale e i dischi delle VM.

1. **Backup Preventivo**: Snapshot o backup su PBS delle VM critiche (se presenti localmente).
2. **Aggiornamento Repository**: Verifica ed eventuale correzione dei file in `/etc/apt/sources.list` e `/etc/apt/sources.list.d/pve-enterprise.list`.
3. **Esecuzione Upgrade**:
   ```bash
   apt update
   apt dist-upgrade -y
   ```
4. **Riavvio (Reboot)**: Riavvio del nodo per caricare il nuovo kernel e verificare il corretto avvio sulla rete 10G.

### FASE 2: Rientro in Cluster (Re-join)

Dato che i nodi sono attualmente isolati/staccati tra loro, la priorità post-upgrade è ricreare l'anello di fiducia.

1. **Analisi dello Stato Attuale**: Verifica dello stato di Corosync su PVE1 e PVE3 (`pvecm status`).
2. **Bonifica (Se necessaria)**: Se i nodi presentano configurazioni cluster corrotte o split-brain irrecuperabile, forzeremo la modalità locale fermando Corosync e pulendo `/etc/pve/corosync.conf`.
3. **Unione al Cluster**:
   - Da PVE3 eseguiremo il comando per rientrare sotto il master PVE1:
     ```bash
     pvecm add 10.10.10.11
     ```
   - *Nota*: Qualora l'infrastruttura fosse totalmente compromessa lato cluster, valuteremo la creazione di un nuovo cluster da zero partendo da PVE1 (`pvecm create nuovo-cluster`).
4. **Allineamento Certificati**: Aggiornamento delle chiavi SSH (`pvecm updatecerts`).

---

## Verification Plan

### Automated Tests
- `pveversion` su PVE3 per confermare la versione 9.2.
- `pvecm status` per confermare la corretta visibilità tra PVE1 e PVE3 (Nodes: 2, Quorum: 2).

### Manual Verification
- Accesso alla GUI di PVE1 e PVE3: verificare che l'interfaccia risponda e che i nodi non presentino il classico punto di domanda grigio (segno di disconnessione).

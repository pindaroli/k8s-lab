---
title: "Piano: Risoluzione Timeout Startup Talos & Riallineamento Rete TrueNAS VLAN 20"
type: plan
status: active
certified_for_ai: true
created_at: 2026-10-12
tags:
  - "#plan"
  - "#talos"
  - "#kubernetes"
  - "#proxmox"
  - "#postgres"
  - "#ansible"
  - "#vlan20"
---

# Piano: Risoluzione Timeout Startup Talos & Riallineamento Rete TrueNAS VLAN 20

Questo piano documenta l'analisi, le azioni correttive eseguite e le attività pendenti relative al fallimento al Gate 2.1 del playbook di avvio `startup_from_truenas_only.yml`, con le successive discrepanze di rete legacy (TrueNAS VLAN 10 vs VLAN 20) rilevate su Proxmox VE e nel cluster PostgreSQL CloudNativePG.

---

## 🎯 Obiettivo & Contesto

All'avvio dell'infrastruttura Homelab dalla modalità a risparmio energetico (TrueNAS Only), l'esecuzione del playbook `ansible/playbooks/infrastructure/startup_from_truenas_only.yml` è fallita al task:
```text
TASK [⏳ Gate 2.1: Attesa apertura porte API Talos OS (Porta 50000)]
Timeout when waiting for 10.10.20.141:50000 (talos-cp-01)
```

L'analisi ha evidenziato due discrepanze dovute alla migrazione di TrueNAS da VLAN 10 (`10.10.10.50`) a VLAN 20 (`10.10.20.50`, vedi [[truenas-vlan20]]):
1. **Hookscript di avvio Proxmox VE**: Lo script pre-start `/var/lib/vz/snippets/wait-for-truenas.sh` agganciato alle VM Talos (`1300`, `2300`, `3200`) attendeva `10.10.10.50`, provocando un ritardo forzato di 240 secondi (4 minuti) prima dell'accensione delle VM.
2. **Archiviazione WAL di PostgreSQL (CNPG)**: La risorsa live `postgres-main` su Kubernetes puntava al vecchio endpoint Garage S3 `http://10.10.10.50:3900`, bloccando l'archiviazione WAL e la sincronizzazione della replica `postgres-main-7`.

---

## 🔍 Root Cause Analysis

### 1. Proxmox Hookscript Stale IP
- Su `pve1`, `pve2` e `pve3`, la direttiva `hookscript: local:snippets/wait-for-truenas.sh` esegue un loop di attesa ping:
  ```bash
  TRUENAS_IP="10.10.10.50"
  TIMEOUT_SECONDS=240
  ```
- Poiché TrueNAS è attestato su `10.10.20.50`, il ping falliva sistematicamente fino allo scadere del timeout (240s).
- All'avvio di PVE1 (09:56:45), la VM `1300` è rimasta bloccata nello script pre-start ed è partita solo alle 10:00:49.
- Il playbook Ansible, con `timeout: 180` al Gate 2.1, è andato in timeout prima che `talos-cp-01` completasse l'avvio del sistema operativo Talos.

### 2. Disallineamento Endpoint S3 CloudNativePG
- L'istanza master `postgres-main-3` era operativa, ma l'istanza replica `postgres-main-7` è rimasta in stato non pronto (`0/1 Running`).
- Nei log di `postgres-main-7`:
  ```text
  ERROR: Barman cloud WAL archiver exception: Could not connect to the endpoint URL: "http://10.10.10.50:3900/postgres-wal/..."
  ```
- Il file locale del repository `postgres/cluster.yaml` conteneva già `http://10.10.20.50:3900`, ma non era stato applicato al cluster live.

---

## 🛠️ Azioni Eseguite e Validate

### ✅ Fase 1: Bonifica Hookscript Proxmox VE (Completata)
- Aggiornato `/var/lib/vz/snippets/wait-for-truenas.sh` su `pve1` (`10.10.10.11`), `pve2` (`10.10.20.21`) e `pve3` (`10.10.10.31`):
  ```bash
  TRUENAS_IP="10.10.20.50"
  ```
- **Verifica**: Eseguito `grep TRUENAS_IP` su tutti e tre i nodi. L'IP su VLAN 20 è attivo e verificato.

### ✅ Fase 2: Esecuzione Playbook Startup (Completata)
- Eseguito `ansible-playbook -i ansible/inventory.ini ansible/playbooks/infrastructure/startup_from_truenas_only.yml`:
  - **Gate 1 (PVE)**: OK.
  - **Gate 2 (Talos API & VIP 6443)**: OK immediato (nessun timeout).
  - **Gate 3 (Sync Barrier)**: OK, nodi Ready.
  - **Gate 4 (Uncordon atomico)**: `talos-cp-01`, `talos-cp-02`, `talos-cp-03` uncordonati con successo.
  - **Gate 5.1 (Traefik Ingress VIP)**: OK (porta 443 aperta).

### ✅ Fase 3: Riallineamento CNPG S3 Endpoint (Completata)
- Applicato il manifesto dichiarativo `kubectl apply -f postgres/cluster.yaml`.
- L'istanza `postgres-main-7` ha immediatamente stabilito la connessione con Garage S3 su `http://10.10.20.50:3900` e avviato lo svuotamento della coda dei WAL pendenti (con velocità di ~3-4 WAL/s archiviati con successo).

---

## ⚠️ Anomalia Rilevata (Session Freeze)

Intorno alle 11:26, le comunicazioni di rete verso la subnet VLAN 20 (`10.10.20.55:6443`, `10.10.20.141`, `10.10.20.142`, `10.10.20.143`) hanno smesso di rispondere ai pacchetti ICMP e TCP (`connect: operation timed out`, `No route to host`).

Su esplicita richiesta dell'utente ("persisti il piano e lo rimandiamo dopo"), la sessione operativa viene congelata per permettere una diagnostica fisica/infrastrutturale successiva.

---

## 💾 Stato di Ripristino (AI Save-State)
- **Fase Attiva**: Fase 4 - Diagnostica e Ripristino Connettività VLAN 20 / Talos K8s
- **Ultima Azione Completata**: Corretti gli hookscript Proxmox (`TRUENAS_IP="10.10.20.50"`), completato startup e uncordon Talos con playbook Ansible, applicato `postgres/cluster.yaml` e avviato svuotamento WAL su S3.
- **Prossimo Passo Operativo**:
  1. Verificare l'accessibilità OOB dei nodi Proxmox sulla VLAN 99 (`192.168.100.11`, `192.168.100.21`, `192.168.100.31`).
  2. Verificare lo stato dello switch Extreme (`192.168.2.1`), connettività porte VLAN 20 e log SFP+.
  3. Verificare lo stato delle VM Talos su Proxmox (`qm status 1300`, `2300`, `3200`) e console seriale.
  4. Riconvalidare la risposta del VIP Kubernetes (`10.10.20.55:6443`) e lo stato finale `Cluster in healthy state` di `postgres-main`.
- **Blocchi/Decisioni Pendenti**: Esecuzione sospesa e rimandata su istruzione dell'utente.

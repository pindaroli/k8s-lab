---
status: archived
certified_for_ai: false
note: "Progetto abbandonato: la causa dell'isolamento di rete (creduto un bug di virtio) è stata identificata come un disallineamento della VLAN sullo switch fisico (Incident 2026-07-24). Il workaround del watchdog non è più necessario."
---
# Proxmox Talos Watchdog

## Obiettivo
Implementare una soluzione di "Self-Healing" Out-of-Band per le macchine virtuali Talos (Control Plane) ospitate su Proxmox VE. 
A causa di un bug noto nel demone di rete di Talos, un flap del link fisico della scheda di rete (es. riavvio o spegnimento momentaneo dello switch) porta alla perdita dell'IP statico della VM, che risulta perennemente disconnessa.

La soluzione consiste in uno script Bash deployato sui nodi Proxmox via Ansible che esegue un controllo intelligente sulla connettività della VM.

## Architettura (Watchdog Intelligente)
1. **Trigger**: Job `cron` in `/etc/cron.d/talos-watchdog` in esecuzione ogni 3 minuti sui nodi Proxmox (`pve1`, `pve2`, `pve3`).
2. **Logica di verifica**:
   - Se la VM è volontariamente spenta (`qm status`), lo script esce.
   - Ping dell'IP della VM Talos (es. `10.10.20.141`). Se risponde, lo script esce.
   - Ping del Gateway di riferimento (`10.10.20.1`, switch L3). Se NON risponde, lo switch è staccato/offline, quindi lo script NON riavvia la VM per evitare un boot-loop infinito.
   - Se la VM non risponde MA lo switch risponde (rete fisica UP, VM isolata), viene lanciato il comando di recupero `qm reboot <vmid>`.

## Riferimenti Nodi
- `pve1`: VM `1300` (IP: `10.10.20.141`)
- `pve2`: VM `2300` (IP: `10.10.20.142`)
- `pve3`: VM `3200` (IP: `10.10.20.143`)

## Deployment
Il deploy e l'aggiornamento dello script verranno gestiti tramite un ruolo Ansible `proxmox_talos_watchdog` nella cartella `ansible/playbooks/roles/` del repository.

---
## 💾 Stato di Ripristino (AI Save-State)
- **Fase Attiva**: Pianificazione
- **Ultima Azione Completata**: Redazione dell'artifact `implementation_plan.md` e del piano Wiki `proxmox-talos-watchdog.md`.
- **Prossimo Passo Operativo**: Attesa approvazione del piano da parte dell'utente per avviare la creazione del ruolo Ansible.
- **Blocchi/Decisioni Pendenti**: Attesa via libera per creare il file `ansible/playbooks/roles/proxmox_talos_watchdog/tasks/main.yml` e configurare i file di template.

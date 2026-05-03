---
title: "Workflow: Safe Shutdown & Startup Sequence"
last_updated: "2026-05-03"
confidence: "High"
tags:
  - "#workflow"
  - "#maintenance"
  - "#automation"
---

# Safe Shutdown & Startup (Rack Management)

Questa procedura garantisce la coerenza dei dati durante lo spegnimento o l'accensione dell'intero rack (PDU/UPS).

## 1. Procedura di Shutdown (Spegnimento)
> [!WARNING]
> NON spegnere mai forzatamente i nodi o TrueNAS senza aver prima fermato i carichi di lavoro.

1.  **Lancia il Playbook Ansible**:
    ```bash
    ansible-playbook ansible/playbooks/shutdown_lab.yml --vault-password-file ~/.vault_pass.txt
    ```
2.  **Monitora Telegram**: L'automazione invierà messaggi per ogni fase (Fase 1: Talos, Fase 2: Database, Fase 3: TrueNAS).
3.  **Spegnimento Fisico**: Solo quando TrueNAS è spento, spegni l'interruttore della PDU/UPS.

## 2. Procedura di Startup (Accensione)
L'ordine di avvio è AUTOMATIZZATO tramite hook di Proxmox (Vedi [[TrueNAS]]).

1.  **Accensione Fisica**: Attiva la PDU/UPS.
2.  **PVE1 (TrueNAS)**: Si avvia per primo.
3.  **Wait-for-TrueNAS**: Gli altri nodi (PVE2/3) attendono che TrueNAS sia pingabile prima di avviare le VM critiche (Talos, Jellyfin).
4.  **Cluster Quorum**: Attendi ~5 minuti affinché il [[Talos_Cluster]] formi il quorum.

## Relazioni
- Dipende da: [[TrueNAS]], [[Talos_Cluster]], [[OPNsense]].
- Gestito via: [[Ansible]].

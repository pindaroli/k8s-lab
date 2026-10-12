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
L'ordine di avvio delle VM su Proxmox è automatizzato con hook e boot-order, seguito dall'orchestrazione con barriera di sincronizzazione Talos.

1.  **Accensione Remota via Wake-on-LAN**:
    Lancia l'avvio centralizzato via rete tramite [`wake_node.py`](file:///Users/olindo/prj/k8s-lab/scripts/network/wake_node.py) (sulla VLAN 99 OOB):
    ```bash
    # Accensione globale automatica
    ./scripts/network/wake_node.py all

    # Oppure mirata in sequenza storage -> compute:
    ./scripts/network/wake_node.py truenas
    ./scripts/network/wake_node.py pve1
    ./scripts/network/wake_node.py pve2
    ./scripts/network/wake_node.py pve3
    ```
2.  **TrueNAS Bare Metal**: Esporta i dataset ZFS/NFS necessari a Proxmox e K8s.
3.  **Wait-for-TrueNAS**: I nodi Proxmox attendono che TrueNAS sia raggiungibile prima di avviare le VM Talos K8s.
4.  **Startup Sincronizzato & Uncordon (Sync Barrier)**:
    Per evitare il disequilibrio di carico (effetto *thundering herd*) tra i nodi worker `talos-cp-01` e `talos-cp-02`, lancia lo script:
    ```bash
    ./scripts/infrastructure/startup_from_truenas_only.sh
    ```
    Lo script attende che tutti i 3 nodi siano simultaneamente in stato `Ready` e rilascia l'**uncordon atomico parallelo**, preservando il taint `control-plane:NoSchedule` su `talos-cp-03`.

## Relazioni
- Dipende da: [[TrueNAS]], [[Talos_Cluster]], [[OPNsense]].
- Gestito via: [[Ansible]], [[talos-startup-sync-uncordon]].

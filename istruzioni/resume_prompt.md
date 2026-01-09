# Prompt di Ripartenza per Migrazione Talos

Copia e incolla il seguente testo in una nuova chat per riprendere il lavoro esattamente da dove lo abbiamo lasciato.

---

```text
Sistema, siamo nel progetto GEMINI (Kubernetes Homelab Migration).

STATO ATTUALE (Sessione Precedente - 08/01/2026):
1. [x] **DATABASE MIGRATION (DONE)**:
   - Radarr, Lidarr, Prowlarr migrati con successo a PostgreSQL (Cluster CloudNativePG).
   - Readarr annullato/rimosso.
   - Vecchi file SQLite (`.db`) rimossi dalla share NFS e dal NAS.
   - Postgres esposto su LoadBalancer MetalLB (`10.10.20.57`) per gestione via DBeaver.

2. [x] **CLEANUP STORAGE (DONE)**:
   - Identificata e pulita la share NFS `/mnt/stripe/k8s-arr`.
   - Rimossi dataset orfani (`k8s-fast-gen`, `proxmox-hot`) su TrueNAS.
   - Verificato che i dati vitali (Config/Media) sono al sicuro.

PROSSIMO OBIETTIVO (Immediato):
- [ ] **Fase 05: Implementazione Strategia di Backup (Smart Hybrid).**
      - Seguire il piano definito in `istruzioni/04_backup_strategy.md`.
      - **Step 1**: Configurare TrueNAS Replication (NVMe -> HDD).
      - **Step 2**: Deploy PBS (Proxmox Backup Server) come LXC.
      - **Step 3**: Configurare Backup CNPG (Postgres) su NFS.

Per favore:
1. Leggi il piano di backup in `istruzioni/04_backup_strategy.md`.
2. Leggi lo stato della rete in `rete.json`.
3. Guidami nell'implementazione dello Step 1 (TrueNAS Replication).
```

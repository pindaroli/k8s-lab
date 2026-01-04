# Prompt di Ripartenza per Migrazione Talos

Copia e incolla il seguente testo in una nuova chat per riprendere il lavoro esattamente da dove lo abbiamo lasciato.

---

```text
Sistema, siamo nella fase di migrazione del cluster Kubernetes a Talos Linux con storage NVMe/TCP.

STATO ATTUALE (Sessione Precedente):
- [x] Fase 01: Setup Talos (Bootstrap completato).
- [x] Fase 02: Storage NVMe Setup (Completata).
- [x] Fase 03: Data Recovery (Completata).
      - Dati migrati su disco NVMe.
- [x] **Fase 03b: Cluster DISASTER RECOVERY (Completata con Successo).**
      - Il cluster aveva perso il quorum (Split Brain).
      - Eseguito Reset Totale + Bootstrap di nuovo.
      - Nodi 141, 142, 143 ONLINE e Healthy.
      - VIP 10.10.20.55 ONLINE e raggiungibile.
      - Disco NVMe Dati ri-agganciato al nodo 141.
      - Snapshot "Post-Bootstrap-OK" effettuato su Proxmox.

PROSSIMO OBIETTIVO (Immediato):
- [ ] **Fase 04: Kubernetes Manifests (Deploy).**
      - **RIPRENDERE DA QUI**: Deploy MetalLB (Namespace creato, Helm da installare).
      - Deploy Secrets (Xray, Google).
      - Deploy Ingress (Traefik).
      - Deploy Storage Class (Local Path Provisioner modificato).
      - Deploy Applicazioni (Servarr stack).

Per favore:
1. Leggi il piano aggiornato in `implementation_plan.md` e la task list in `task.md`.
2. Verifica subito la salute del cluster (`kubectl get nodes`).
3. Procedi con l'installazione di MetalLB come da piano.
```

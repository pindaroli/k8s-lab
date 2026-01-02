# Prompt di Ripartenza per Migrazione Talos

Copia e incolla il seguente testo in una nuova chat per riprendere il lavoro esattamente da dove lo abbiamo lasciato.

---

```text
Sistema, siamo nella fase di migrazione del cluster Kubernetes a Talos Linux con storage NVMe/TCP.

STATO ATTUALE (Sessione Precedente):
- [x] Fase 01: Setup Talos (Bootstrap completato).
- [x] Fase 02: Storage NVMe Setup (Completata).
      - TrueNAS configurato (Zvol + NVMe Target).
      - Proxmox: Maintenance script creato `/root/maintenance-mode.sh`.
      - Talos: Disco collegato e mountato su `/var/mnt/hot`.
- [x] Fase 02b: Network Stabilization (Completata).
      - IP Fissi assegnati su OPNsense (DHCP Reservations).
      - talos-cp-01: 10.10.20.141
      - talos-cp-02: 10.10.20.142
      - talos-cp-03: 10.10.20.143

PROSSIMO OBIETTIVO:
- [ ] Fase 03: Data Recovery (Migrazione Dati).
      - Accendere Recovery VM.
      - Montare vecchio backup NFS.
      - Copiare dati su nuovo disco NVMe.
      - Ri-switch su Talos.

Per favore:
1. Leggi la strategia in `istruzioni/storage_strategy.md`.
2. Leggi il piano per oggi in `istruzioni/migration/03_data_recovery.md`.
3. Assisti nell'esecuzione passo-passo della Fase 03.
```

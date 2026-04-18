# Project GEMINI: Roadmap & Expansion Plans

Questo documento delinea i prossimi passi per l'evoluzione dell'infrastruttura Homelab GEMINI.

## 1. Ripristino e Consolidamento Hardware
- **Ripristino PVE2**: Analisi e reintegrazione del nodo `pve2` nel cluster Proxmox.
- **Allineamento Hook**: Assicurarsi che tutti i nodi (PVE, PVE2, PVE3) utilizzino la versione definitiva dello script `wait-for-truenas.sh`.

## 2. Espansione Cluster Kubernetes (Hybrid Mac/K8s)
- **Talos Worker su Mac Studio**: Configurazione di un'istanza Worker di Talos Linux direttamente sul Mac Studio M2 Ultra (tramite UTM o virtualizzazione).
- **Targeting Workload**: Utilizzo di Node Affinity per spostare i carichi di calcolo pesanti sulla CPU M2 Ultra del Mac.

## 3. Servizi IA Unificati (AI Server)
- **Deployment AI Server (Mac Studio)**: Configurazione di un server IA locale (es. Ollama) che sfrutti la GPU del Mac Studio M2 Ultra.
- **Accessibilità**: Esporre le API via DNS interno per permettere ai Pod K8s e agli altri nodi di interrogare l'IA.

## 4. Nuovi Workload
- **Stream-Headless su PVE2**: Installazione di `stream-headless` su PVE2 per leveraging del calcolo remoto.

---
*Stato: Draft - Aggiornato il 08/04/2026*

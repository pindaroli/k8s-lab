---
title: "Aggiornamento Puntamenti KUBECONFIG e TALOSCONFIG in .zshrc"
type: incident
status: archived
certified_for_ai: false
date: 2026-06-28
severity: P3
resolved: true
resolved_at: 2026-06-28T10:14:00Z
tags:
  - "#incident"
  - "#environment"
  - "#config"
---

# Incident: Aggiornamento Puntamenti KUBECONFIG e TALOSCONFIG in .zshrc

**Data**: 2026-06-28  
**Status**: RESOLVED  
**Severity**: Low / P3  

## 🔍 Diagnosi
All'avvio dei controlli nel file `~/.zshrc`, è stato riscontrato che:
1. `KUBECONFIG` puntava al percorso inesistente `/Users/olindo/prj/k8s-lab/talos-config/kubeconfig`.
2. La cartella `talos-config` (contenente certificati sensibili e il `talosconfig` reale) si trovava all'interno del repository Git, benché correttamente esclusa dal tracciamento tramite `.gitignore`.

## 🛠️ Risoluzione
Per ripristinare la corretta operatività ed evitare la presenza di file sensibili all'interno dell'albero di Git:
1. Spostata la cartella reale `talos-config` sotto la home directory dell'utente (`/Users/olindo/talos-config`).
2. Creato un link simbolico nel repository in `/Users/olindo/prj/k8s-lab/talos-config` puntante a `/Users/olindo/talos-config` per non rompere script o automazioni del progetto.
3. Aggiornate le variabili d'ambiente nel file `~/.zshrc`:
   - `KUBECONFIG` impostato su `/Users/olindo/.kube/config`.
   - `TALOSCONFIG` impostato su `/Users/olindo/talos-config/talosconfig`.

## 🧪 Verifica
* I percorsi dei file e i link simbolici sono stati convalidati e si risolvono correttamente.
* `talosctl` risponde correttamente utilizzando la nuova posizione della configurazione.

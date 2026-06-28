---
title: "Piano: Installazione Kubernetes MCP Server e Bonifica Kubeconfig"
type: plan
status: active
certified_for_ai: true
created_at: 2026-06-28
tags:
  - "#plan"
  - "#kubernetes"
  - "#mcp"
---

# Piano di Installazione Kubernetes MCP Server ed Eliminazione talos-config/kubeconfig

Questo piano descrive le attività completate e il piano di test per l'integrazione di `kubernetes-mcp-server` in Antigravity e la bonifica degli script di progetto per supportare la variabile globale `KUBECONFIG`.

## Stato dell'Infrastruttura
* **Metodo MCP**: Configurato per l'avvio dinamico tramite `npx`.
* **Kubeconfig Globale**: `/Users/olindo/.kube/config`.
* **Kubeconfig Locale**: Spostato temporaneamente in `talos-config/kubeconfig.bak` (in attesa di eliminazione).

## Modifiche Effettuate

1. **Aggiornamento degli Script di Progetto (Pattern "Pippo" di Fallback ibrido)**:
   * [prefect/install.sh](file:///Users/olindo/prj/k8s-lab/prefect/install.sh)
   * [scripts/check_k8s.py](file:///Users/olindo/prj/k8s-lab/scripts/check_k8s.py)
   * [scripts/check_qbittorrent_net.sh](file:///Users/olindo/prj/k8s-lab/scripts/check_qbittorrent_net.sh)
   * [scripts/setup_postgres_dbs.sh](file:///Users/olindo/prj/k8s-lab/scripts/setup_postgres_dbs.sh)
   * [scripts/verify_network_fix.sh](file:///Users/olindo/prj/k8s-lab/scripts/verify_network_fix.sh)
   * [GEMINI.md](file:///Users/olindo/prj/k8s-lab/GEMINI.md)

2. **Pulizia mcp_config.json**:
   * Rimosso il server MCP `olilab-agent` per risolvere l'errore di caricamento.
   * Aggiunto il server MCP `kubernetes` configurato via `npx` che legge `/Users/olindo/.kube/config`.

---

## Piano di Verifica (Dopo il Ripristino di Talos)

Da eseguire nell'ordine seguente non appena il cluster Talos sarà online e operativo:

### 1. Test di Funzionamento Kubernetes MCP Server
* **Obiettivo**: Verificare che l'MCP `kubernetes` funzioni correttamente leggendo `/Users/olindo/.kube/config`.
* **Azione**: Chiedere in chat ad Antigravity: *"Mostra i nodi del cluster"* o *"Elenca i pod nel namespace arr"*.
* **Esito Atteso**: L'AI deve rispondere correttamente utilizzando i tool forniti dall'MCP server.

### 2. Verifica Avvio Antigravity (Risoluzione Errore `olilab-agent`)
* **Obiettivo**: Confirmare che l'errore all'avvio relativo a `olilab-agent` sia sparito.
* **Azione**: Riavviare l'applicazione o l'IDE Antigravity e controllare i log di caricamento degli MCP.
* **Esito Atteso**: Nessun errore `MODULE_NOT_FOUND` relativo a `/Users/olindo/prj/olilab-agent/index.js`.

### 3. Test di Ereditarietà Dinamica degli Script (Fallback "Pippo")
* **Obiettivo**: Verificare che tutti gli script locali del progetto ereditino correttamente `$KUBECONFIG` o effettuino il fallback a `~/.kube/config`.
* **Azione**:
  1. Aprire una nuova sessione di terminale.
  2. Eseguire lo script di diagnostica principale:
     ```bash
     python3 scripts/check_k8s.py
     ```
* **Esito Atteso**: Lo script deve interpellare con successo il cluster utilizzando `~/.kube/config` (poiché `talos-config/kubeconfig` non esiste più, essendo stato rinominato in `.bak`).

### 4. Clean-up e Rimozione Definitiva
* **Obiettivo**: Pulire il repository ed eliminare i riferimenti obsoleti.
* **Azione**:
  1. Eliminare il file di backup temporaneo:
     ```bash
     rm talos-config/kubeconfig.bak
     ```
  2. Modificare il tuo file `~/.zshrc` rimuovendo la riga 121:
     ```bash
     export KUBECONFIG="/Users/olindo/prj/k8s-lab/talos-config/kubeconfig"
     ```

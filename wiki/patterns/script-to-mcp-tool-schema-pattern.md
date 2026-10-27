---
title: "Pattern: Script to MCP Tool Schema & Registration"
type: pattern
status: active
certified_for_ai: true
date: 2026-10-25
tags:
  - "#pattern"
  - "#mcp"
  - "#automation"
  - "#scripting"
in_use_by:
  - "scripts/mcp_tools.yaml"
---

# Pattern: Script to MCP Tool Schema & Registration

Questo pattern definisce lo schema dichiarativo e le regole di trasformazione per esporre script esistenti (Python, Bash, Ansible Playbook) come tool di un Model Context Protocol (MCP) server.

## 📌 Obiettivo e Motivazione
All'interno del repository `k8s-lab`, risiedono numerosi script operativi (diagnostica di rete, gestione storage, playbook Ansible, verifica salute cluster).
Invece di invocare arbitrariamente processi shell non strutturati, il pattern abilita una transizione pulita verso tool MCP con:
1. **Schema di input tipizzato (JSON Schema)** per validazione degli argomenti da parte dei modelli LLM.
2. **Policy di esecuzione sicura**: timeout, directory di lavoro (`cwd`), variabili d'ambiente e flag `read_only` / `destructive`.
3. **Mappatura dichiarativa**: compilazione manuale da parte dell'utente di un file centrale `scripts/mcp_tools.yaml` (o `.json`).

---

## 📐 Struttura dello Schema Dichiarativo (`mcp_tools.yaml`)

Il file di configurazione compila l'elenco dei tool MCP che devono essere generati o esposti dinamicamente dal server wrapper MCP.

### Campi Principali

| Campo | Tipo | Descrizione |
| :--- | :--- | :--- |
| `version` | string | Versione dello schema di configurazione (es. `"1.0"`). |
| `server` | object | Metadati del server MCP generato (nome, versione, descrizione). |
| `tools` | array | Lista delle definizioni dei tool MCP. |

### Dettaglio del Singolo Tool

Ogni elemento in `tools` supporta:
- `name`: Identificativo univoco del tool MCP (snake_case, max 64 caratteri).
- `description`: Descrizione chiara ad uso dell'LLM (cosa fa, pre-requisiti, output).
- `type`: Tipologia di runtime: `python`, `bash`, `ansible`.
- `path`: Percorso relativo dello script/playbook rispetto alla root del repo.
- `read_only`: Boolean. Se `true`, indica all'LLM che l'operazione non altera lo stato del sistema.
- `async_capable`: Boolean (default: `false`). Se `true`, indica che il tool è idoneo per l'esecuzione asincrona/background (es. job lunghi, orchestrazioni cluster, scan massivi). Il server MCP o il runtime dell'agente può eseguire il comando come task disaccoppiato restituendo un Job ID o notifica a termine esecuzione.
- `executionType`: String enum (`"sync"` | `"async"`). Mappatura del protocollo MCP 2.0 che definisce il modello di esecuzione del tool: `"sync"` per chiamate sincrone inline bloccanti (richiesta $\rightarrow$ risposta diretta); `"async"` per chiamate asincrone disaccoppiate (job background, task differiti o polling).
- `timeout_seconds`: Timeout massimo di esecuzione del comando (default: 60s).
- `parameters`: Oggetto JSON Schema (o schema semplificato) che definisce gli input accettati.
- `command_template`: Mapping di interpolazione degli argomenti CLI o variabili extra (`extra_vars` per Ansible).

---

## 📄 Esempio di Riferimento

```yaml
version: "2.0"
server:
  name: "homelab-ops-mcp"
  description: "Server MCP dinamico per l'automazione e gestione del homelab - MCP 2.0"
  protocol_version: "2.0"

tools:
  - name: "validate_network_dns"
    description: "Valida la coerenza DNS e topologia IP di rete.json"
    type: "python"
    path: "scripts/network/validate_network.py"
    read_only: true
    async_capable: false
    executionType: "sync"
    timeout_seconds: 30
    parameters:
      type: object
      properties:
        verbose:
          type: boolean
          description: "Abilita output dettagliato"
          default: false
      required: []
    cli_mapping:
      args:
        - flag: "--verbose"
          bind: "verbose"
          type: "boolean_flag"

  - name: "run_proxmox_smart_audit"
    description: "Esegue il playbook Ansible per l'audit SMART hardware dei dischi sui nodi Proxmox"
    type: "ansible"
    path: "ansible/proxmox_smart_audit.yml"
    inventory: "ansible/inventory.ini"
    read_only: true
    async_capable: true
    timeout_seconds: 120
    parameters:
      type: object
      properties:
        target_node:
          type: string
          enum: ["pve1", "pve2", "pve3", "all"]
          description: "Nodo target Proxmox da auditare"
          default: "all"
      required: ["target_node"]
    ansible_mapping:
      limit: "{{ target_node }}"
```

---

## 🔒 Regole di Sicurezza e Best Practices
1. **Passwordless Mandate**: Nessun parametro deve accettare o trasmettere password; le esecuzioni SSH/Ansible devono basarsi su chiavi scambiate (`BatchMode=yes`).
2. **CWD Independence**: Il runner del server MCP deve eseguire i comandi con `cwd` impostato stabilmente alla root di `k8s-lab`.
3. **Timeout Rigorosi**: Ogni script deve avere un timeout esplicito per prevenire deadlock del server MCP.

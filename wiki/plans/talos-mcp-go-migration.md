---
title: "Piano: Migrazione a Nosmoht Talos MCP Server (Go)"
type: plan
status: archived
certified_for_ai: false
resolved: true
resolved_at: 2026-09-10
created_at: 2026-09-10
tags:
  - "#plan"
  - "#talos"
  - "#mcp"
  - "#golang"
  - "#toolhive"
---

# Piano: Migrazione a Nosmoht Talos MCP Server (Go Native)

Questo documento definisce il piano operativo e architetturale per la migrazione del server MCP **`talos`** dall'implementazione legacy Python (`CBEPX/talos-mcp-server:0.3.10`) all'implementazione nativa in Go: **`Nosmoht/talos-mcp-server`** (v2.5.1).

---

## 🗺️ Mappe Concettuali e Relazioni
- [[MCP_Platform]] (Infrastruttura ToolHive e Traefik IngressRoute in `mcp-system`)
- [[Talos_Cluster]] (Cluster Control Plane Talos Linux nodi `10.10.20.141`, `10.10.20.142`, `10.10.20.143`)
- [[mcp-secret-projection-pattern]] (Archetipo 2: Volume Secret Projection & Workload Immutability)
- [[SCHEMA]] (Regole del Wiki)

---

## 1. Motivazione Architetturale

L'attuale server Python (`CBEPX/talos-mcp-server:0.3.10`):
1. **Crash sistematico su `server/discover`**: l'SDK Python `mcp 1.3.0` non supporta il metodo stateless `server/discover` introdotto nelle specifiche MCP di luglio 2026 ed emesso da ToolHive `v0.46.0`, provocando `ValidationError` di Pydantic e crash del processo (`CrashLoopBackOff`, `503 Service Unavailable`).
2. **Subshell e dipendenze esterne**: esegue `talosctl` invocando comandi da riga di comando shell con flag non più supportati (`--timeout 5s` su Talos 1.13.5).
3. **Footprint elevato**: immagine Python pesante (>200MB) e complessità di monkeypatching.

L'implementazione nativa Go (**`Nosmoht/talos-mcp-server` v2.5.1**):
1. **Comunicazione gRPC nativa**: usa direttamente il package client ufficiale Talos Linux (`github.com/siderolabs/talos/pkg/machinery/client`) con mTLS certificato. Nessun binario `talosctl` esterno o parsing di testo.
2. **Supporto MCP moderno**: supporta nativamente sia `stdio` che `streamable-http`, gestendo correttamente le richieste discovery senza crash.
3. **Footprint minimo e sicurezza**: immagine container minimale (<30MB su Alpine), non-root UID 1000, read-only rootfs nativo.
4. **Toolset COSI avanzato**: supporta 15 tool read-only e 8 tool mutanti con guardrail di conferma espliciti.

---

## 2. Fasi Operative

### Fase 1: Docker Container Packaging (`docker/talos-mcp/`)
1. Riscrittura di `docker/talos-mcp/Dockerfile`:
   - Base `alpine:3.21`.
   - Download e installazione del binario ufficiale compilato `talos-mcp-server_2.5.1_linux_amd64.tar.gz`.
   - Creazione utente non-root `talos` (UID 1000).
   - Entrypoint `["/usr/local/bin/talos-mcp"]`.
2. Eliminazione dello script wrapper obsoleto `docker/talos-mcp/talos_mcp_wrapper.py`.
3. Aggiornamento workflow CI `.github/workflows/docker-talos-mcp.yml` con tag semantico `2.5.1` e `:latest`.
4. Trigger workflow e push su `ghcr.io/pindaroli/talos-mcp:2.5.1`.

### Fase 2: Configurazione Kubernetes & Helm (`mcp-gateway`)
1. Aggiornamento `mcp-gateway/mcp-gateway-values.yaml`:
   - `image: ghcr.io/pindaroli/talos-mcp:2.5.1`.
   - `transport: stdio`.
   - Mount del volume `talosconfig-vol` da secret `talos-mcp-credentials`.
   - Env: `TALOSCONFIG: /etc/talos/talosconfig`.
2. Bump patch chart version `helm-charts/mcp-gateway/Chart.yaml` a `0.2.12`.
3. `helm upgrade` del release `mcp-gateway`.

### Fase 3: Audit Client e Allineamento Nomi Tool
1. Verifica assenza di script o regole con nomi vecchi hardcoded nel workspace.
2. Mappatura operativa dei tool nel wiki e documentazione.

### Fase 4: Validazione Test-Driven
1. Verifica pod `talos-mcp-0` in stato `1/1 Running` senza riavvii.
2. Verifica risposta su probe `server/discover` e handshake `initialize`.
3. Test end-to-end con `talos_version` e `talos_services` sui nodi Control Plane (`10.10.20.141`, `10.10.20.142`, `10.10.20.143`).

---

## 3. Matrice di Mappatura Tool (Python $\rightarrow$ Go)

| Categoria | Vecchio Tool (Python 0.3.10) | Nuovo Tool (Go 2.5.1) | Note Operative |
| :--- | :--- | :--- | :--- |
| **Versione** | `talos_get_version` | `talos_version` | Restituisce versione client/server Talos via gRPC nativo |
| **Servizi** | `talos_get_services` | `talos_services` | Elenco servizi COSI (running/stopped/healthy) |
| **Risorse** | `talos_get_resources` | `talos_resource_definitions` + `talos_get` | `talos_get` accetta il tipo di risorsa (es. `Member`, `NodeAddress`) |
| **File Read** | `talos_read` | `talos_read_file` | Legge file da filesystem nodo remoto |
| **File List** | `talos_list` | `talos_list_files` | Lista directory su nodo remoto |
| **Container** | `talos_get_containers` | `talos_containers` | Namespace di default `k8s.io` |
| **Processi** | `talos_get_processes` | `talos_processes` | Elenco processi con PID, CPU, memoria |
| **Etcd** | `talos_etcd_members` | `talos_etcd` | Parametro `action: members` o `action: status` |
| **Health** | `talos_health` | `talos_health` | Verifica etcd, k8s API, readiness |
| **Log** | `talos_get_logs` | `talos_logs` | Parametri `service` e `tail_lines` |
| **Kernel** | `talos_dmesg` | `talos_dmesg` | Ring buffer dmesg |
| **Azioni** | `talos_restart_service` | `talos_service_action` | Richiede `confirm: true` |
| **Reboot** | `talos_reboot` | `talos_reboot` | Richiede `confirm: true` e nodi espliciti |
| **Upgrade** | `talos_upgrade` | `talos_upgrade` | Verifica minor upgrade path sequenziale |

---

## 💾 Stato di Ripristino (AI Save-State)
- **Fase Attiva**: Piano Completato con Successo ✅
- **Ultima Azione Completata**: Migrazione a Nosmoht Go v2.5.1 completata, pod 1/1 Running in mcp-system, test end-to-end positivi (`talos_version`, `talos_etcd`, `talos_services`) e documentazione allineata.
- **Prossimo Passo Operativo**: Nessuno (Server MCP Talos nativo Go pienamente operativo e stabile in produzione).
- **Blocchi/Decisioni Pendenti**: Nessuno.

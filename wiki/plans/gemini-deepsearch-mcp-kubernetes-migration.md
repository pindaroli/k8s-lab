---
title: "Piano & Analisi Alternative: Migrazione Kubernetes di Gemini DeepSearch MCP"
type: plan
status: active
certified_for_ai: true
created_at: 2026-09-05
tags:
  - "#plan"
  - "#mcp"
  - "#gemini"
  - "#kubernetes"
  - "#toolhive"
  - "#helm"
---

# Piano & Analisi Alternative: Migrazione Kubernetes di Gemini DeepSearch MCP

Questo documento definisce l'analisi architetturale comparativa e il piano operativo per migrare il server MCP **`gemini-deepsearch`** (attualmente eseguito localmente tramite virtualenv Python in `/Users/olindo/prj/gemini-deepsearch-mcp/.venv/bin/gemini-deepsearch-mcp`) sul cluster Kubernetes homelab GEMINI nel namespace dedicato `mcp-system`.

---

## 🗺️ Mappe Concettuali e Relazioni
- [[MCP_Platform]] (Piattaforma federata Kuadrant, ToolHive Operator e Traefik IngressRoute)
- [[mcp-secret-projection-pattern]] (Pattern di Proiezione Segreti & Immutabilità)
- [[Secret_Registry]] (Cifratura della chiave API con SOPS + Age)
- [[SCHEMA]] (Regole di compilazione e catalogazione del Wiki)

---

## 1. Analisi del Workload Attuale

Il repository `/Users/olindo/prj/gemini-deepsearch-mcp` implementa un agente di ricerca web avanzato multi-step basato su **LangGraph**, **Google GenAI SDK** (`google-genai`), **LangChain** e **FastMCP**:

1. **Flusso di Ricerca Iterativo**:
   - Riceve la query utente e il livello di sforzo (`low`, `medium`, `high`).
   - Genera sotto-query ottimizzate con Gemini Flash.
   - Esegue ricerche web in parallelo tramite Google Search Grounding API.
   - Esegue un loop di riflessione/sintesi delle fonti.
   - Produce un report finale ricco di citazioni bibliografiche.
2. **Requisiti di Sistema & Credenziali**:
   - Runtime: Python $\ge 3.12$.
   - Credenziale: `GEMINI_API_KEY` (stringa scalare, attualmente presente in chiaro in `mcp_config.json`).
3. **Peculiarità Critica Identificata nel Codice**:
   - In `src/gemini_deepsearch_mcp/main.py` (entrypoint `stdio`), il tool scrive il risultato su un file JSON temporaneo su disco (`tempfile.gettempdir()`) e restituisce al client `{ "file_path": "/tmp/What_is_...json" }`.
   - In `src/gemini_deepsearch_mcp/app.py` (server HTTP FastMCP), il tool restituisce invece direttamente `{ "answer": answer, "sources": sources }` in memoria.

---

## 2. Analisi Comparativa delle Alternative Architetturali

### Dimensione A: Strategia di Gestione del Codice & CI/CD

| Criterio | Opzione A1: Monorepo `k8s-lab` (Raccomandata) | Opzione A2: Fork Indipendente GitHub (`pindaroli/gemini-deepsearch-mcp`) | Opzione A3: Build Locale Docker senza CI |
| :--- | :--- | :--- | :--- |
| **Descrizione** | Il codice sorgente python e il `Dockerfile` risiedono in `k8s-lab` (`docker/gemini-deepsearch-mcp/`), con CI in `.github/workflows/docker-gemini-deepsearch.yml`. | Fork di `alexcong/gemini-deepsearch-mcp` su GitHub con repository separato e workflow CI autonomo. | Build eseguita sul Mac dello sviluppatore con push manuale su GHCR. |
| **Allineamento Flotta** | **Identico** a `opnsense-mcp` e `talos-mcp`. | Identico a `truenas-master-mcp`. | Non standard (anti-pattern). |
| **Tracciabilità GitOps** | Massima: codice e manifesti risiedono nello stesso repo. | Buona, ma richiede la gestione di 2 repository git separati. | Pessima: nessuna tracciabilità della build. |
| **Complessità Operativa** | Minima: singola pipeline di push e deploy. | Media: push su repo esterno $\rightarrow$ trigger GHCR $\rightarrow$ update su `k8s-lab`. | Bassa all'inizio, insostenibile a lungo termine. |
| **Aggiornamenti Upstream** | Richiede copia manuale o merge selettivo da `alexcong`. | Semplice merge tramite `git pull upstream master`. | Non applicabile. |

> **Valutazione A**: L'**Opzione A1 (Monorepo)** è fortemente raccomandata per coerenza con le recenti migrazioni di `opnsense-mcp` e `talos-mcp`. In alternativa, l'**Opzione A2 (Fork)** è valida qualora si desideri mantenere un legame formale con la repository upstream di Alex Cong.

---

### Dimensione B: Protocollo di Output & Compatibilità Client AI

| Criterio | Opzione B1: Inline Data Return (Raccomandata) | Opzione B2: Scrittura su File Temporaneo (`file_path`) |
| :--- | :--- | :--- |
| **Comportamento** | Il tool `deep_search` restituisce direttamente il payload strutturato: `{"answer": str, "sources": list}`. | Il tool tenta di scrivere un file JSON in `/tmp` e restituisce il percorso assoluto: `{"file_path": "/tmp/...json"}`. |
| **Compatibilità K8s Immutabile** | **100% conforme**: zero scritture su disco, pienamente compatibile con `securityContext.readOnlyRootFilesystem: true`. | **Incompatibile out-of-the-box**: va in crash (`OSError: [Errno 30] Read-only file system`) a meno di volume `emptyDir`. |
| **Fruibilità Client Antigravity** | **Immediata**: Antigravity riceve il testo sintetizzato e i link direttamente nel contesto della risposta. | **Rotta**: Il file `/tmp/...json` risiede nel filesystem del pod remoto Kubernetes. Antigravity sul Mac non può accedervi. |
| **Consumo Token** | I risultati vengono inseriti direttamente nel tool result dell'agente. | Richiederebbe un meccanismo di recupero remoto (es. API separata). |

> **Valutazione B**: L'**Opzione B1 (Inline Data Return)** è l'unica soluzione tecnicamente corretta per un'architettura client-server remota. La logica di `main.py` verrà allineata a quella di `app.py` eliminando ogni dipendenza dal filesystem locale.

---

### Dimensione C: Runtime, Orchestrazione & Networking in `mcp-system`

| Criterio | Opzione C1: ToolHive stdio + ProxyRunner HTTP/SSE (Raccomandata) | Opzione C2: FastMCP Nativo HTTP/SSE / Uvicorn |
| :--- | :--- | :--- |
| **Architettura** | Pod StatefulSet ToolHive (`stdio`) + Pod Deployment ToolHive (`proxyrunner:v0.46.0` bridge HTTP/SSE :8080). | Singolo pod containerizzato che espone direttamente l'app FastAPI/FastMCP via Uvicorn su porta 8080. |
| **Uniformità Flotta** | **Totale**: Gestito nativamente dal CRD `MCPServer` (`toolhive.stacklok.dev/v1beta1`) via `helm-charts/mcp-gateway`. | Differenziato: richiederebbe un Deployment/Service standard K8s o ToolHive con `transport: sse`. |
| **Ingress & Routing** | Traefik IngressRoute standard: `gemini-deepsearch-mcp-internal.pindaroli.org` $\rightarrow$ porta 8080. | Traefik IngressRoute standard: `gemini-deepsearch-mcp-internal.pindaroli.org` $\rightarrow$ porta 8080. |
| **Affidabilità & Timeout** | ToolHive gestisce il lifecycle del processo stdio, ma per ricerche "high effort" (che durano 30-60 secondi) occorre assicurare timeout adeguati su Traefik. | Gestione nativa HTTP keep-alive / streaming. |

> **Valutazione C**: L'**Opzione C1 (ToolHive stdio + ProxyRunner)** garantisce la perfetta omogeneità con tutti gli altri 4 server MCP della flotta Kubernetes.

---

### Dimensione D: Proiezione dei Segreti & Hardening di Sicurezza

In conformità al pattern attivo [[mcp-secret-projection-pattern]]:
- `GEMINI_API_KEY` è una stringa scalare (API Key Google AI Studio / Gemini).
- Si applica tassativamente l'**Archetipo 1: Scalar Direct Injection (In-Memory)**:
  - Cifratura in `secrets-sops/gemini-deepsearch-credentials.enc.yaml`.
  - Iniezione da parte di ToolHive direttamente in RAM via `targetEnvName: GEMINI_API_KEY`.
  - Nessun volume secret o disco montato, nessuna persistenza fisica della chiave nel container.

---

## 3. Architettura Finale Proposta (Target State)

```mermaid
flowchart TD
    subgraph Client["Client AI"]
        AG["Antigravity IDE (macOS)"]
        CONF["mcp_config.json\n(serverUrl: https://gemini-deepsearch-mcp-internal...)"]
    end

    subgraph Edge["Traefik Edge & DNS"]
        DNS["OPNsense Unbound DNS\n(gemini-deepsearch-mcp-internal -> 10.10.20.56)"]
        ING["Traefik IngressRoute\n(gemini-deepsearch-mcp-internal)"]
    end

    subgraph Cluster["Kubernetes (mcp-system)"]
        PROXY["Deployment ToolHive ProxyRunner\n(:8080 HTTP/SSE Bridge)"]
        POD["StatefulSet ToolHive: gemini-deepsearch-mcp-0\n(ghcr.io/pindaroli/gemini-deepsearch-mcp:latest)"]
        SOPS["Secret SOPS: gemini-deepsearch-credentials\n(GEMINI_API_KEY -> RAM)"]
    end

    subgraph Cloud["Google AI Studio & Search Grounding"]
        API["Google Gemini Flash / Pro API\n(Configurabili via GEMINI_FLASH_MODEL / GEMINI_PRO_MODEL)\n+ Google Search Grounding"]
    end

    CONF -->|HTTPS /mcp| DNS --> ING
    ING --> PROXY
    PROXY <-->|stdio JSON-RPC (In-Memory)| POD
    SOPS -.->|Iniezione RAM (Archetipo 1)| POD
    POD -->|HTTPS REST| API
```

---

## 4. Piano di Implementazione Dettagliato (Fasi 1-6)

### Fase 1: Consolidamento Codice & Dockerfile Monorepo
1. Creare la directory `docker/gemini-deepsearch-mcp/` in `k8s-lab`.
2. Copiare i sorgenti python ottimizzati da `/Users/olindo/prj/gemini-deepsearch-mcp/src/`:
   - Modificare `main.py` per restituire inline `{"answer": answer, "sources": sources}` anziché scrivere su `/tmp`.
   - Parametrizzare i modelli via env: `GEMINI_FLASH_MODEL` (default: `gemini-3.5-flash`) e `GEMINI_PRO_MODEL` (default: `gemini-2.5-pro`).
3. Creare `docker/gemini-deepsearch-mcp/Dockerfile`:
   - Base `python:3.12-slim`.
   - Installazione dipendenze tramite `pip` o `uv` (`langgraph`, `langchain-google-genai`, `google-genai`, `fastmcp`, `pydantic`).
   - Entrypoint non-root per esecuzione stdio.
4. Creare `.github/workflows/docker-gemini-deepsearch.yml` con path filtering selettivo su `docker/gemini-deepsearch-mcp/**`.
5. Push su `main` e pubblicazione dell'immagine su `ghcr.io/pindaroli/gemini-deepsearch-mcp:latest`.

### Fase 2: Provisioning Segreto SOPS
1. Creare `secrets-sops/gemini-deepsearch-credentials.enc.yaml` cifrato con chiave Age contenente `GEMINI_API_KEY`.
2. Decifrare e applicare in Kubernetes:
   ```bash
   sops --decrypt secrets-sops/gemini-deepsearch-credentials.enc.yaml | kubectl apply -f -
   ```
3. Verificare la presenza del secret `gemini-deepsearch-credentials` in `mcp-system`.

### Fase 3: Integrazione Helm Project Chart (`mcp-gateway`)
1. Incrementare la versione in `helm-charts/mcp-gateway/Chart.yaml` (`0.2.5` $\rightarrow$ `0.2.6`).
2. Aggiungere il blocco `gemini-deepsearch` in `mcp-gateway/mcp-gateway-values.yaml`:
   - ToolHive: `name: gemini-deepsearch-mcp`, `image: ghcr.io/pindaroli/gemini-deepsearch-mcp:latest`, `transport: stdio`, `proxyPort: 8080`.
   - Secrets: `gemini-deepsearch-credentials` $\rightarrow$ `GEMINI_API_KEY`.
   - Resources: requests `100m`/`256Mi`, limits `500m`/`1Gi` (per gestire i grafi LangGraph in memoria).
   - Ingress: host `deepsearch-mcp-internal.pindaroli.org`.
   - Timeout: configurare timeout esteso a 180s per gestire le ricerche high effort.
3. Eseguire l'upgrade dichiarativo:
   ```bash
   helm upgrade mcp-gateway helm-charts/mcp-gateway -f mcp-gateway/mcp-gateway-values.yaml -n mcp-system
   ```
4. Verificare che `gemini-deepsearch-mcp-0` e il proxy runner siano `1/1 Running`.

### Fase 4: Routing Traefik & DNS OPNsense
1. Verificare la creazione dell'IngressRoute `gemini-deepsearch-internal` con host `deepsearch-mcp-internal.pindaroli.org`.
2. Aggiungere l'alias `deepsearch-mcp-internal` al VIP Traefik (`10.10.20.56`) in `rete.json` ed eseguire `validate_network.py`.
3. Creare l'Host Override in OPNsense Unbound DNS via API:
   - Host: `deepsearch-mcp-internal` $\rightarrow$ IP: `10.10.20.56`.
4. Riconfigurare Unbound e testare la risoluzione DNS (`dig`).

### Fase 5: Configurazione Client Antigravity
1. Modificare `~/.gemini/antigravity/mcp_config.json`:
   - Sostituire il comando locale `command: /Users/olindo/prj/gemini-deepsearch-mcp/.venv/bin/...` e l'API key in chiaro con:
     ```json
     "gemini-deepsearch": {
       "serverUrl": "https://deepsearch-mcp-internal.pindaroli.org/mcp"
     }
     ```
2. Rimuovere la chiave API in chiaro dal file di configurazione locale.

### Fase 6: Validazione Funzionale Test-Driven & Consolidamento
1. Eseguire una ricerca di prova tramite `call_mcp_tool` (es. `deep_search` con query *"Novità release Kubernetes 1.36"* ed effort *"low"*).
2. Verificare che la risposta contenga sia `answer` che `sources` formattate inline senza errori su file o timeout.
3. Aggiornare `wiki/entities/MCP_Platform.md` e la matrice dei server in `todo.md`.
4. Rigenerare il contesto LLM con `build_wiki_context.py` e completare il piano.

---

## 5. Rischi e Strategie di Mitigazione

1. **Timeout su Ricerche Complesse (High Effort)**:
   - *Rischio*: Ricerche ad alto sforzo (`effort: high`) richiedono molteplici loop LangGraph e chiamate API esterne, potendo superare il timeout di default di Traefik (solitamente 60s).
   - *Mitigazione*: Configurare un `responseTimeout: 180s` nell'IngressRoute o utilizzare `effort: low` / `medium` come default per query interattive.
2. **Crash per Filesystem in Sola Lettura**:
   - *Rischio*: LangGraph o librerie caching (es. `.cache`) potrebbero tentare di scrivere su disco.
   - *Mitigazione*: Verificare che non vi siano scritture su filesystem o impostare `PYTHONPYCACHEPREFIX=/tmp` solo se indispensabile. Con l'adozione del ritorno inline dei dati, il container rispetta pienamente l'immutabilità.

---

## 💾 Stato di Ripristino (AI Save-State)
- **Fase Attiva**: Piano Completato con Successo ✅
- **Ultima Azione Completata**: Migrazione completa su Kubernetes (Fasi 1-6), correzione upstream dict format per `google_search`, aggiornamento modelli a `gemini-3.6-flash`/`gemini-3.1-pro-preview`, test e consolidamento documentale in `MCP_Platform.md` e `todo.md`.
- **Prossimo Passo Operativo**: Nessuno. Server MCP operativo in produzione su `https://deepsearch-mcp-internal.pindaroli.org/mcp`.
- **Blocchi/Decisioni Pendenti**: Nessuno. Per l'uso intensivo di Google Search Grounding è richiesta una quota attiva su Google AI Studio.

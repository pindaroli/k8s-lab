---
id: mcp-registry-package
title: "Pattern: Registry-Backed Packaging for Published MCP Servers"
type: pattern
status: active
certified_for_ai: true
created_at: 2026-09-08
last_updated: 2026-09-08
in_use_by:
  - project: "k8s-lab"
    paths:
      - "docker/ollama-mcp"
      - "docker/opnsense-mcp"
      - "docker/talos-mcp"
      - "docker/nowaikit-mcp"
      - ".github/workflows/docker-ollama-mcp.yml"
      - ".github/workflows/docker-opnsense-mcp.yml"
      - ".github/workflows/docker-talos-mcp.yml"
      - ".github/workflows/docker-nowaikit-mcp.yml"
      - "mcp-gateway/mcp-gateway-values.yaml"
tags:
  - "#pattern"
  - "#mcp"
  - "#packaging"
  - "#npm"
  - "#pypi"
  - "#kubernetes"
  - "#docker"
---

# Pattern: Registry-Backed Packaging for Published MCP Servers

Questo pattern definisce lo standard architetturale del lab per impacchettare, manutenere e distribuire server MCP open-source di terze parti che **dispongono di pacchetti ufficiali versionati rilasciati su registri pubblici** (come **npm** per Node.js o **PyPI** per Python).

---

## 🗺️ Mappe Concettuali e Relazioni
- [[MCP_Platform]] (Infrastruttura dei server MCP e ToolHive Operator in `mcp-system`)
- [[mcp-upstream-tracking-pattern]] (Pattern gemello per server da repository Git upstream privi di pacchetti)
- [[mcp-secret-projection-pattern]] (Proiezione dei segreti SOPS e immutabilità)
- [[SCHEMA]] (Regole di governance e catalogazione del Wiki)

---

## 1. Problema e Ambito di Applicazione

Quando un server MCP viene rilasciato come modulo pubblico (es. `ollama-mcp` o `@richard-stovall/opnsense-mcp-server` su npm, oppure `talos-mcp-server` su PyPI), non è necessario né desiderabile clonare il repository Git sorgente o gestirne la compilazione interna:
* Il gestore di pacchetti ufficiale (`npm` o `pip`) garantisce la risoluzione automatica delle dipendenze, l'installazione dei binari eseguibili nel `$PATH` e la verifica crittografica dell'integrità degli archivi.
* Tuttavia, eseguire questi pacchetti direttamente sul sistema operativo dell'host o in container non standardizzati introdurrebbe eterogeneità, rischi di sicurezza (esecuzione come root) e incompatibilità con ToolHive Operator.

Questo pattern stabilisce la **struttura canonica del Dockerfile**, le **politiche di version pinning** e la **pipeline CI/CD** per trasformare un pacchetto di registro in un container OCI pronto per Kubernetes.

---

## 2. Architettura della Soluzione

```mermaid
flowchart TD
    subgraph Registry["Registro Pubblico Ufficiale (npm / PyPI)"]
        PKG["Pacchetto con Versione Semantica Fissa\nes. ollama-mcp@2.1.0 o talos-mcp-server==0.3.10"]
    end

    subgraph CI["GitHub Actions (k8s-lab CI/CD)"]
        DOCKERFILE["docker/<app>/Dockerfile\n- Base image minimale (alpine/slim)\n- Strict version pinning\n- Utente non-root (UID 1000)\n- Wrapper stdio (se necessario)"]
        GHA["Workflow .github/workflows/docker-<app>.yml\nBuild automatica su push main a docker/<app>/**"]
        GHCR["ghcr.io/pindaroli/<app>:<version>"]
    end

    subgraph K8s["Kubernetes (mcp-system)"]
        VALUES["mcp-gateway-values.yaml"]
        TH["ToolHive MCPServer (readOnlyRootFilesystem)"]
        ING["Traefik IngressRoute (<app>-mcp-internal.pindaroli.org)"]
        GW["Kuadrant MCP Gateway"]
    end

    PKG -->|Download build-time| DOCKERFILE
    DOCKERFILE --> GHA --> GHCR
    GHCR --> VALUES --> TH
    TH --> ING
    TH --> GW
```

---

## 3. Regole Fondamentali del Pattern

### 1. Strict Version Pinning e Divieto Assoluto di `latest`
È **tassativamente vietato** l'uso del tag `:latest` o di versioni fluttuanti a qualsiasi livello dello stack:
* **Base Image Dockerfile**: Non utilizzare tag mobili generici; utilizzare la release stabile raccomandata.
* **Pacchetti e Dipendenze**: Installare esclusivamente l'**ultima release stabile formalmente pubblicata** sul registro ufficiale, definita tramite build ARG esplicito (`ARG <PKG>_VERSION=<x.y.z>`).
  - **Node.js (npm)**:
    ```dockerfile
    ARG OPNSENSE_MCP_VERSION=0.5.3
    RUN npm install -g @richard-stovall/opnsense-mcp-server@${OPNSENSE_MCP_VERSION}
    ```
  - **Python (pip)**:
    ```dockerfile
    ARG TALOS_MCP_VERSION=0.3.10
    RUN pip install --no-cache-dir "talos-mcp-server==${TALOS_MCP_VERSION}" "mcp==1.3.0" "pydantic==2.10.6"
    ```
* **Immagini nei Manifesti Kubernetes**: In `mcp-gateway-values.yaml` o in qualsiasi chart Helm è fatto divieto di puntare a `:latest`; utilizzare sempre il tag semantico fisso corrispondente alla release stabile (es. `ghcr.io/pindaroli/ollama-mcp:2.1.0`).

### 2. Clausola di Ambiguità della Versione (Scelta Utente)
Durante la ricerca e il censimento della versione del pacchetto sul registro pubblico:
* Qualora siano presenti versioni pre-release, tag `@beta`, `@rc`, `@next`, versioni non semantiche o vi sia ambiguità tra pacchetti/fork simili, l'agente o l'operatore **NON deve effettuare assunzioni arbitrarie**.
* L'agente deve **fermarsi e interpellare l'utente**, esponendo l'elenco delle versioni rilevate e lasciando all'utente la selezione della versione finale da adottare.

### 3. Utente Non-Root Unprivileged (UID 1000)
Tutti i container devono obbligatoriamente rilasciare i privilegi di root e impostare un utente unprivileged con UID fisso `1000`:
* In immagini Node alpine: `USER node` (già preconfigurato con UID 1000).
* In immagini Python slim:
  ```dockerfile
  RUN useradd -u 1000 -m -s /bin/bash appuser && \
      chown -R appuser:appuser /app
  USER appuser
  ```
Questo assicura la piena conformità con la policy di sicurezza `securityContext.readOnlyRootFilesystem: true` imposta dal ToolHive Operator.

### 4. Supporto al Trasporto `stdio` e Wrapper di Compatibilità
I server MCP pacchettizzati devono comunicare nativamente tramite `stdio`. Qualora il pacchetto richieda parametri CLI specifici, variabili d'ambiente non standard o intercettazione di log verbosi (come nel caso di `talos-mcp-server` che loggava su file locale non scrivibile), è consentito affiancare un wrapper minimale:
* File: `docker/<app>/<app>_wrapper.py`
* Esempio: `talos_mcp_wrapper.py` reindirizza i log su `/dev/null` per rispettare il filesystem read-only.

### 5. Tag OCI Immutabili su GHCR e Rilascio Controllato
La pipeline CI/CD (`.github/workflows/docker-<app>.yml`) deve taggare e pubblicare l'immagine su GHCR prioritariamente con la versione semantica del pacchetto (es. `ghcr.io/pindaroli/ollama-mcp:2.1.0`) e il commit short SHA (`sha-xxxxxxx`). L'eventuale tag `:latest` può essere aggiornato solo ad uso informativo, ma non deve mai essere referenziato nei valori GitOps di produzione.

### 6. Configurazione Dichiarativa Helm
Nessun manifesto loose: il container compilato viene censito in [mcp-gateway-values.yaml](file:///Users/olindo/prj/k8s-lab/mcp-gateway/mcp-gateway-values.yaml) all'interno del blocco `servers`, specificando:
* Nome del server e prefisso Kuadrant (`prefix: "<name>_"`).
* Immagine con tag semantico fisso (`image: ghcr.io/pindaroli/<app>:<version>`).
* Host Ingress LAN (`<name>-mcp-internal.pindaroli.org`).
* Risorse CPU/Memoria (`requests: 50m/64Mi`, `limits: 300m/256Mi`).

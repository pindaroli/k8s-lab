---
name: k8s-mcp-server-onboarding
type: skill
description: "Procedura standardizzata e guidata per l'introduzione, containerizzazione e deployment di nuovi Model Context Protocol (MCP) server sul cluster Kubernetes (mcp-system, ToolHive Operator, Kuadrant Gateway, Traefik IngressRoute, OPNsense Unbound DNS)."
when_to_use: "Quando l'utente richiede di aggiungere, integrare, impacchettare o migrare un nuovo server MCP all'interno del cluster Kubernetes o nella configurazione di Antigravity."
status: active
tags:
  - mcp
  - kubernetes
  - toolhive
  - docker
  - gitops
  - sops
  - traefik
---

# K8s MCP Server Onboarding (`k8s-mcp-server-onboarding`)

## Panoramica

Questo skill standardizza l'intero ciclo di vita per l'introduzione di nuovi server **Model Context Protocol (MCP)** nell'architettura Kubernetes dell'homelab (`mcp-system`). 

I server MCP sono containerizzati nel monorepo (`docker/<app>/`), pubblicati su GitHub Container Registry (**GHCR**), orchestrati da **ToolHive Operator** con bridging `stdio`-to-HTTP/SSE su porta `8080`, federati da **Kuadrant MCP Gateway**, esposti in LAN tramite **Traefik IngressRoute** su dominio `-internal.pindaroli.org` e infine censiti centralmente in `~/.gemini/antigravity/mcp_config.json`.

---

## 🗺️ Mappe Concettuali e Pattern Obbligatori

Ogni implementazione DEVE conformarsi ai seguenti pattern architetturali attivi:
- [[mcp-registry-package-pattern]]: per server MCP distribuiti come pacchetti ufficiali su **npm** o **PyPI**.
- [[mcp-upstream-tracking-pattern]]: per server MCP residenti solo su repository Git di terze parti senza release ufficiali.
- [[mcp-secret-projection-pattern]]: per la gestione sicura delle credenziali SOPS e rispetto del filesystem immutabile.
- [[MCP_Platform]]: documentazione della piattaforma centrale del lab.

---

## ⛔ Golden Rules Non Negoziabili

Prima di scrivere qualsiasi file, l'agente DEVE verificare il rispetto delle seguenti 5 regole:

1. **Divieto Assoluto di `:latest` e Version Pinning Rigoroso**:
   È vietato l'uso di `:latest` nei `Dockerfile`, nei pacchetti installati, nei tag pubblicati e nei valori Helm di Kubernetes. Bisogna sempre identificare l'**ultima release stabile ufficialmente pubblicata**.
2. **Clausola di Ambiguità (Scelta Utente vs Fallback Mono-Branch)**:
   - Se il pacchetto su registry presenta versioni pre-release/beta/rc o ambiguità di nome, l'agente **deve fermarsi e consultare l'utente**.
   - Se un repository Git upstream non ha alcun tag di release ed esiste un solo branch (`main`), adottare automaticamente il branch emettendo un **warning formale per l'utente**; se vi sono tag/branch multipli non ordinati, demandare la scelta all'utente.
3. **Immutabilità del Filesystem (`readOnlyRootFilesystem: true`) e UID 1000**:
   I pod girano con utente non-root fisso (`UID 1000`: `node` su Alpine o `appuser` su Python slim) e filesystem sigillato. Nessun file può essere scritto a runtime fuori da `/tmp`.
4. **Anti-Loose-YAML Guard (Helm-First Mandate)**:
   È vietato creare file manifest YAML isolati o eseguire `kubectl apply` manuali. Tutte le istanze MCP devono essere dichiarate in [mcp-gateway/mcp-gateway-values.yaml](file:///Users/olindo/prj/k8s-lab/mcp-gateway/mcp-gateway-values.yaml).
5. **Port-Forward Policy (Debug-Only)**:
   È vietato usare o proporre `kubectl port-forward` come soluzione permanente. Tutti i client accedono via Traefik IngressRoute (`https://<app>-mcp-internal.pindaroli.org/mcp`) o K8s DNS interno.

---

## ⚡ Playbook Operativo a 7 Fasi

### Fase 1: Classificazione del Package & Selezione Pattern
1. Verificare l'origine del software:
   - **Esiste su npm?** Usare [[mcp-registry-package-pattern]] (vedi template `templates/Dockerfile.npm.tpl`).
   - **Esiste su PyPI?** Usare [[mcp-registry-package-pattern]] (vedi template `templates/Dockerfile.pypi.tpl`).
   - **Solo repository GitHub?** Usare [[mcp-upstream-tracking-pattern]] (vedi template `templates/Dockerfile.git.tpl`).
2. Interrogare il registro (es. `https://registry.npmjs.org/<pkg>` o `https://pypi.org/pypi/<pkg>/json`) o i tag Git (`list_tags`) per identificare l'ultima release stabile.
3. Se ricade nella **Clausola di Ambiguità**, applicare le regole descritte sopra.

### Fase 2: Containerizzazione Monorepo (`docker/<app>/`)
1. Creare la cartella `docker/<app>/`.
2. Creare `docker/<app>/Dockerfile` utilizzando il template corrispondente.
3. Se il server MCP logga su disco fisso o richiede argomenti CLI non configurabili da env, creare un wrapper minimale `docker/<app>/<app>_wrapper.py` o `entrypoint.py` che reindirizzi i log su `/dev/null` o `/tmp`.
4. Creare il workflow GitHub Actions `.github/workflows/docker-<app>.yml` (vedi `templates/workflow-docker.yml.tpl`).

### Fase 3: Gestione Credenziali e Segreti (SOPS)
1. Identificare l'archetipo di credenziali ([[mcp-secret-projection-pattern]]):
   - **Archetipo 1 (Stringhe scalari: API Key, Token, Password)**: Creare secret cifrato in `secrets-sops/<app>-mcp-credentials.enc.yaml`. Verrà iniettato in RAM da ToolHive tramite `spec.secrets`.
   - **Archetipo 2 (File strutturati / mTLS: talosconfig, kubeconfig, chiavi SSH)**: Montare il secret cifrato come volume read-only proiettato in `/etc/<app>/` (tramite `podTemplateSpec.spec.volumes` e `volumeMounts`), senza alcuna scrittura a runtime.
2. Applicare il secret decifrato nel namespace `mcp-system`:
   ```bash
   sops --decrypt secrets-sops/<app>-mcp-credentials.enc.yaml | kubectl apply -f -
   ```

### Fase 4: Routing Dichiarativo GitOps (`mcp-gateway`)
1. Aggiungere il server alla lista `servers` in [mcp-gateway/mcp-gateway-values.yaml](file:///Users/olindo/prj/k8s-lab/mcp-gateway/mcp-gateway-values.yaml) utilizzando il template `templates/values-snippet.yaml.tpl`.
2. Incrementare la versione del chart in `helm-charts/mcp-gateway/Chart.yaml` (SemVer patch o minor).
3. Eseguire l'upgrade Helm dichiarativo:
   ```bash
   helm upgrade mcp-gateway helm-charts/mcp-gateway -f mcp-gateway/mcp-gateway-values.yaml -n mcp-system
   ```
4. Attendere e verificare lo stato del pod StatefulSet `MCPServer` (`<app>-mcp-0`) e del proxy runner `mcp-<app>-mcp-proxy`.

### Fase 5: DNS Unbound su OPNsense
1. Creare l'Host Override su OPNsense via Unbound DNS:
   - **Host**: `<app>-mcp-internal`
   - **Dominio**: `pindaroli.org`
   - **Tipo**: `A`
   - **IP**: `10.10.20.56` (Traefik VIP VLAN 20 Server)
2. Validare la coerenza di rete:
   ```bash
   python3 scripts/network/validate_network.py
   ```

### Fase 6: Configurazione Client Antigravity
1. Aggiornare `~/.gemini/antigravity/mcp_config.json` aggiungendo l'endpoint LAN HTTPS:
   ```json
   "<app>": {
     "serverUrl": "https://<app>-mcp-internal.pindaroli.org/mcp"
   }
   ```

### Fase 7: Validazione Test-Driven & Wiki Sync
1. Eseguire uno smoke test live invocando uno dei tool esposti dal nuovo server MCP per verificare connettività e permessi.
2. Aggiornare la tabella dei server attivi in [[MCP_Platform]].
3. Aggiornare il campo `in_use_by` nei pattern utilizzati (`mcp-registry-package-pattern` o `mcp-upstream-tracking-pattern`).
4. Ricompilare il contesto wiki:
   ```bash
   python3 scripts/wiki/build_wiki_context.py
   ```

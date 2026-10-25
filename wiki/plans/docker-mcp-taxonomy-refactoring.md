---
title: "Piano: Riorganizzazione Tassonomica della Directory docker/mcp per Pattern di Packaging"
type: plan
status: archived
certified_for_ai: false
archived_at: 2026-10-25
created_at: 2026-10-20
tags:
  - "#plan"
  - "#mcp"
  - "#docker"
  - "#cicd"
  - "#refactoring"
  - "#gitops"
---

# Piano: Riorganizzazione Tassonomica della Directory docker/mcp per Pattern di Packaging

Questo piano definisce la ristrutturazione architetturale e la migrazione ordinata delle 10 directory di build dei container MCP, attualmente collocate come sottocartelle sparse alla radice di `docker/`, all'interno della directory unificata `docker/mcp/`. Le directory vengono categorizzate in sottocartelle tassonomiche speculari ai **Pattern di Packaging & Ingestion degli Artefatti (Sorgente → Immagine OCI)** definiti nel lab.

---

## 🗺️ Mappe Concettuali e Relazioni
- [[MCP_Platform]]: Piattaforma unificata dei server Model Context Protocol.
- [[mcp-registry-package-pattern]]: Standard di containerizzazione per pacchetti ufficiali su registri (npm, PyPI) e binari ufficiali upstream.
- [[mcp-upstream-tracking-pattern]]: Standard di tracciamento controllato per repository Git di terze parti senza release formali.
- [[zero-install-executable-package-pattern]]: Standard per package autonomi, CLI effimere e codebase interne.
- [[k8s-mcp-server-onboarding]]: Skill e procedure di introduzione di nuovi server MCP.

---

## 🎯 Obiettivo e Razionale Architetturale

Attualmente alla radice di `docker/` coesistono 10 cartelle indipendenti di server MCP (`docker/*mcp*`, `docker/github-mcp-server`), insieme alla cartella `docker/mcp/` che ospita esclusivamente il file `docker-compose.yaml`.

La riorganizzazione persegue i seguenti obiettivi:
1. **Unificazione del Namespace MCP**: Tutta la flotta di server MCP risiede sotto un'unica radice `docker/mcp/`.
2. **Strutturazione Tassonomica per Pattern di Packaging**: Suddivisione dei componenti secondo la natura della sorgente e il pattern architetturale associato:
   - **`docker/mcp/registry-package/`**: per server basati su moduli npm, pacchetti PyPI o container/binari ufficiali upstream.
   - **`docker/mcp/upstream-tracking/`**: per server che effettuano il checkout di codice sorgente da repo Git di terze parti privi di release ufficiali.
   - **`docker/mcp/in-house/`**: per server sviluppati o manutenuti internamente come codebase monorepo (`src/`, script nativi).
3. **Preservazione dell'Orchestrazione di Runtime**: `docker/mcp/docker-compose.yaml` rimane la cabina di regia dichiarativa a livello di root di `docker/mcp/`.
4. **Preservazione Integrale della Cronologia Git**: Tutti gli spostamenti sono eseguiti tramite `git mv` per garantire continuità di `git log` e `git blame`.
5. **Riallineamento Completo CI/CD & Governance**: Aggiornamento coordinato dei 10 workflow GitHub Actions, dei pattern nel Wiki e dello skill `k8s-mcp-server-onboarding`.

---

## 📂 Mappatura Tassonomica dei Server MCP

| Percorso Attuale | Categoria Pattern | Nuovo Percorso Canonico | Origine Software & Base Image |
| :--- | :--- | :--- | :--- |
| `docker/github-mcp-server/` | `registry-package` | `docker/mcp/registry-package/github-mcp-server/` | Binario ufficiale `ghcr.io/github/github-mcp-server` + Supergateway Alpine |
| `docker/nowaikit-mcp/` | `registry-package` | `docker/mcp/registry-package/nowaikit-mcp/` | Pacchetto npm `nowaikit@4.15.1` + Supergateway Alpine |
| `docker/ollama-mcp/` | `registry-package` | `docker/mcp/registry-package/ollama-mcp/` | Pacchetto npm `ollama-mcp@2.1.0` + Supergateway Alpine |
| `docker/opnsense-mcp/` | `registry-package` | `docker/mcp/registry-package/opnsense-mcp/` | Pacchetto npm `@richard-stovall/opnsense-mcp-server@0.5.3` + Supergateway Alpine |
| `docker/talos-mcp/` | `registry-package` | `docker/mcp/registry-package/talos-mcp/` | Release tarball GitHub Nosmoht `v2.5.1` + Supergateway Alpine |
| `docker/truenas-mcp/` | `registry-package` | `docker/mcp/registry-package/truenas-mcp/` | Binario `truenas-master-mcp:1.0.0-alpha.1` + Supergateway Alpine |
| `docker/kef-mcp/` | `upstream-tracking` | `docker/mcp/upstream-tracking/kef-mcp/` | Repository Git upstream `nqrwhal/kef-mcp` (commit 8423b7d) |
| `docker/arrstack-mcp/` | `in-house` | `docker/mcp/in-house/arrstack-mcp/` | Codebase monorepo Python (`src/arrstack_mcp`, `server.py`) |
| `docker/gemini-deepsearch-mcp/` | `in-house` | `docker/mcp/in-house/gemini-deepsearch-mcp/` | Codebase monorepo Python (`src/gemini_deepsearch_mcp`) |
| `docker/ragflow-mcp/` | `in-house` | `docker/mcp/in-house/ragflow-mcp/` | Codebase monorepo Python (`pyproject.toml`, `uv.lock`, `src/`) |

---

## ⚡ Fasi Operative del Piano

### Fase 1: Creazione della Struttura di Directory Tassonomica
- Creare le 3 sottocartelle tassonomiche all'interno di `docker/mcp/`:
  - `docker/mcp/registry-package/`
  - `docker/mcp/upstream-tracking/`
  - `docker/mcp/in-house/`
- Verificare che `docker/mcp/docker-compose.yaml` rimanga intatto nella radice di `docker/mcp/`.

### Fase 2: Migrazione delle Directory tramite `git mv`
Esecuzione puntuale di `git mv` per preservare lo storico dei commit:
```bash
# 1. Server basati su pacchetti di registro e binari ufficiali (registry-package)
git mv docker/github-mcp-server docker/mcp/registry-package/github-mcp-server
git mv docker/nowaikit-mcp docker/mcp/registry-package/nowaikit-mcp
git mv docker/ollama-mcp docker/mcp/registry-package/ollama-mcp
git mv docker/opnsense-mcp docker/mcp/registry-package/opnsense-mcp
git mv docker/talos-mcp docker/mcp/registry-package/talos-mcp
git mv docker/truenas-mcp docker/mcp/registry-package/truenas-mcp

# 2. Server con tracciamento controllato upstream (upstream-tracking)
git mv docker/kef-mcp docker/mcp/upstream-tracking/kef-mcp

# 3. Server con codice sorgente interno (in-house)
git mv docker/arrstack-mcp docker/mcp/in-house/arrstack-mcp
git mv docker/gemini-deepsearch-mcp docker/mcp/in-house/gemini-deepsearch-mcp
git mv docker/ragflow-mcp docker/mcp/in-house/ragflow-mcp
```

### Fase 3: Riallineamento Pipeline CI/CD GitHub Actions (`.github/workflows/`)
Aggiornare i percorsi nei 10 file workflow:
- `.github/workflows/docker-github-mcp-server.yml`: trigger path, context, Dockerfile, VERSION (`docker/mcp/registry-package/github-mcp-server/**`)
- `.github/workflows/docker-nowaikit-mcp.yml`: trigger path, context, Dockerfile, VERSION (`docker/mcp/registry-package/nowaikit-mcp/**`)
- `.github/workflows/docker-ollama-mcp.yml`: trigger path, context, Dockerfile, VERSION (`docker/mcp/registry-package/ollama-mcp/**`)
- `.github/workflows/docker-opnsense-mcp.yml`: trigger path, context, Dockerfile, VERSION (`docker/mcp/registry-package/opnsense-mcp/**`)
- `.github/workflows/docker-talos-mcp.yml`: trigger path, context, Dockerfile, VERSION (`docker/mcp/registry-package/talos-mcp/**`)
- `.github/workflows/docker-truenas-mcp.yml`: trigger path, context, Dockerfile, VERSION (`docker/mcp/registry-package/truenas-mcp/**`)
- `.github/workflows/docker-kef-mcp.yml`: trigger path, context, Dockerfile, VERSION, upstream checkout path (`docker/mcp/upstream-tracking/kef-mcp/**`)
- `.github/workflows/docker-arrstack-mcp.yml`: trigger path, context, Dockerfile, VERSION (`docker/mcp/in-house/arrstack-mcp/**`)
- `.github/workflows/docker-gemini-deepsearch.yml`: trigger path, context, Dockerfile, VERSION (`docker/mcp/in-house/gemini-deepsearch-mcp/**`)
- `.github/workflows/docker-ragflow-mcp.yml`: trigger path, context, Dockerfile, VERSION (`docker/mcp/in-house/ragflow-mcp/**`)

### Fase 4: Riallineamento Skill Onboarding, Template e Pattern di Governance
1. **Skill `.agents/skills/k8s-mcp-server-onboarding/`**:
   - `SKILL.md`: aggiornare le istruzioni della Fase 2 specificando la cartella target `docker/mcp/<pattern>/<app>/`.
   - `references/checklist.md`: aggiornare il check del Dockerfile.
   - `templates/workflow-docker.yml.tpl`: aggiornare il template con i percorsi parametrizzati su `docker/mcp/<category>/<app>`.
2. **Pattern Wiki (`wiki/patterns/`)**:
   - `wiki/patterns/mcp-registry-package-pattern.md`: aggiornare il campo frontmatter `in_use_by.paths`.
   - `wiki/patterns/mcp-upstream-tracking-pattern.md`: aggiornare il campo frontmatter `in_use_by.paths`.
   - `wiki/patterns/mcp-secret-projection-pattern.md`: aggiornare il campo frontmatter `in_use_by.paths`.
3. **Entità Wiki (`wiki/entities/MCP_Platform.md`)**:
   - Aggiornare i riferimenti al monorepo Docker per riflettere la nuova tassonomia.

### Fase 5: Validazione Test-Driven & Wiki Sync
1. **Verifica Sintassi YAML Workflows**: Validazione con script Python per assicurare zero regressioni nei file `.github/workflows/`.
2. **Verifica Integrità Dockerfile e VERSION**: Script di controllo per testare la presenza e leggibilità di `Dockerfile` e `VERSION` in tutti i 10 nuovi percorsi.
3. **Validazione Coerenza Homelab**:
   ```bash
   python3 scripts/network/validate_network.py && python3 scripts/wiki/build_wiki_context.py
   ```
4. **Verifica Git Status & Commit Atomico**: Confermare che nessun file orfano sia rimasto nella root di `docker/`.

---

## 💾 Stato di Ripristino (AI Save-State)
- **Fase Attiva**: Piano completato con successo ✅ (Tutte le Fasi 1-5 completate)
- **Ultima Azione Completata**: Validazione test-driven sintassi YAML workflow (10/10), verifica integrità percorsi su disco (10/10), test suite interne (21/21 superati) e sincronizzazione wiki context completata con successo
- **Prossimo Passo Operativo**: Commit atomico delle modifiche su Git
- **Blocchi/Decisioni Pendenti**: Nessun blocco; refactoring completato al 100%

---
title: "Piano: Convergenza Wiki Karpathy llmwiki (Fork Multi-Cartella Locale stdio) e Hardening mcp_tools.yaml"
type: plan
status: completed
certified_for_ai: true
created_at: 2026-10-27
last_updated: 2026-10-27
tags:
  - "#mcp"
  - "#llm-wiki"
  - "#gitops"
  - "#automation"
  - "#core"
---

# Piano: Convergenza Wiki Karpathy `llmwiki` (Fork Multi-Cartella Locale `stdio`) e Hardening `mcp_tools.yaml`

> **Percorso Canonico Wiki**: `wiki/plans/llmwiki-mcp-sse-convergence-and-tools-hardening.md`
> **Comando di Ripresa**: `/resume [[llmwiki-mcp-sse-convergence-and-tools-hardening]]`
> **Pattern di Riferimento**: [[script-to-mcp-tool-schema-pattern]], [[mcp-secret-projection-pattern]], [[go-launcher-script-pattern]]

---

## 1. Contesto, Problema e Decisioni Architetturali Consolidate

L'analisi della base di codice `k8s-lab` e il successivo **Consulto Architetturale SRE** hanno evidenziato due ambiti di intervento prioritari: la risoluzione definitiva dello *Split-Brain* documentale tra il motore `llmwiki` (Metodo Karpathy) e la struttura tassonomica di `k8s-lab`, e l'hardening degli script esposti dal runner containerizzato tramite `scripts/mcp_tools.yaml`.

### A. Risoluzione dello Split-Brain tra `llmwiki` e la Struttura Semantica di `k8s-lab`
1. **Limite strutturale del pacchetto PyPI upstream `llmwiki==0.9.0`**:
   - Il pacchetto upstream scansiona in modo rigido solo `wiki/concepts/*.md` e `wiki/outputs/*.md` (`concepts_dir.glob("*.md")`), ignorando i **41+ documenti fondamentali** distribuiti in `wiki/entities/` (25 file), `wiki/patterns/` (9 file), `wiki/workflows/` (5 file), `wiki/procedures/` (1 file) e i piani operativi attivi in `wiki/plans/`.
   - Inoltre, in assenza di `config.yaml`, `llmwiki` applica di default il profilo trilingue CJK (`en`, `zh`, `ja`), motivo per cui i 7 file attuali in `wiki/concepts/` contengono sezioni ridondanti in Cinese (`## 中文`) e Giapponese (`## 日本語`).
2. **Cecità inversa di `build_wiki_context.py`**:
   - Lo script [`scripts/wiki/build_wiki_context.py`](file:///Users/olindo/prj/k8s-lab/scripts/wiki/build_wiki_context.py) assembla il monolite `wiki/wiki_context.md` includendo `entities`, `patterns`, `workflows`, `istruzioni` e `plans`, ma **ignora `wiki/concepts/` e `wiki/procedures/`**.

### B. Esito del Consulto Architetturale (Decision Gates Approvati)

| Decision Gate | Scelta Approvata | Motivazione Tecnica (Principio KISS & Zero Workaround) |
| :--- | :--- | :--- |
| **1. Strategia di Convergenza del Corpus `llmwiki`** | **Opzione A: Fork di `llmwiki` su Repository GitHub Esterno** (`git+https://github.com/pindaroli/llmwiki-mcp.git@v0.9.1-k8slab`) | È il tool PyPI upstream a essere rigido (`.glob("*.md")` su una sola cartella), mentre la tassonomia multi-cartella di `k8s-lab` (`entities/`, `patterns/`, `workflows/`, `procedures/`, `concepts/`, `plans/`) rispetta le best practice Knowledge Graph. Un fork pulito abilita `paths.content_dirs` nativamente, **eliminando qualsiasi cartella ombra di staging (`_compiled_concepts/`), symlink duplicati o monkeypatching in `launcher.py`**, e azzera il rischio di duplicazione 2x in `wiki/wiki_context.md`. |
| **2. Gestione di `wiki/plans/*.md` nel Corpus `llmwiki`** | **2.1: Indicizzazione Selettiva dei soli Piani Attivi** (`status: active \| approved \| in_progress`) | Permette agli agenti che interrogano `kb_search`, `kb_get` e `kb_ask` di accedere al piano operativo attivo e risolvere i relativi `[[wikilink]]`, evitando il *context poisoning* derivante da vecchi piani completati o ritirati. |
| **3. Trattamento delle Sezioni CJK nei 7 File in `wiki/concepts/`** | **3.1: Bonifica Deterministica Diretta in Git + `config.yaml` Monolingue (`bare_body: true`)** | Rimozione immediata dei blocchi `## 中文` e `## 日本語` dai 7 file in `wiki/concepts/` (risparmio del ~60% di token) e adozione del profilo monolingue `bare_body: true` in `config.yaml`. |
| **4. Modalità di Erogazione del Server MCP `llmwiki`** | **Esecuzione Esclusivamente Locale (`stdio`) tramite il Fork Git** (Nessun Container SSE / No K8s / No `supergateway`) | `llmwiki` viene eseguito localmente in modalità `stdio` tramite `uv run --no-project --with git+https://github.com/pindaroli/llmwiki-mcp.git@v0.9.1-k8slab` e `scripts/llmwiki/launcher.py`, operando direttamente sul working tree locale di `k8s-lab` con file-locking atomico (`fcntl.flock`) su `wiki/_meta/`. Viene rimossa ogni sovrastruttura non necessaria (`Dockerfile`, `supergateway`, deployment Kubernetes/TrueNAS per `llmwiki`). |

---

### C. Hardening di `scripts/mcp_tools.yaml` e degli Script per il Container Runner GitOps
1. **Correzione dei 3 Bug Bloccanti nei Path di `scripts/mcp_tools.yaml`**:
   - `audit_proxmox_smart_disks`: punta a `ansible/proxmox_smart_audit.yml` (inesistente) invece di `ansible/playbooks/infrastructure/proxmox_smart_audit.yml`.
   - `audit_movie_duplicates`: punta a `scripts/servarr/audit_movie_duplicates.py` (che cerca `/mnt/oliraid` localmente fallendo fuori da TrueNAS) invece del wrapper SSH `scripts/servarr/audit_movie_duplicates.sh`.
   - `exos_bounce_sfp_port10`: punta a `scripts/network/exos/bounce_port10.py` (che esegue `import exsh`, libreria esclusiva del firmware dello switch ExtremeXOS) invece del playbook Ansible `ansible/playbooks/infrastructure/exos_port10_boot_recovery.yml`.
2. **Eliminazione delle Dipendenze da File Non Tracciati da Git e da Alias SSH Locali**:
   - `scripts/network/test_dhcp.sh`: legge solo `ansible/OPNsense.internal_root_apikey.txt` (in `.gitignore`). Va esteso per decifrare le credenziali da `secrets-sops/opnsense-mcp-credentials.enc.yaml` tramite `sops -d`, interrogare in via primaria le API REST di OPNsense (`/api/kea/leases4/search` e `/api/diagnostics/interface/getArp`) per funzionare anche in network namespace isolati, e supportare `ip neigh` su Linux.
   - `scripts/ragflow/ingestion_stats.sh` e `scripts/servarr/audit_movie_duplicates.sh`: sostituire l'alias SSH `truenas` (presente solo nel `~/.ssh/config` del Mac Studio) con `${TRUENAS_SSH_TARGET:-olindo@10.10.20.50}` e opzioni SSH non interattive (`-o BatchMode=yes -o StrictHostKeyChecking=accept-new -o ConnectTimeout=5`).
   - `scripts/security/check-sops-encrypted.sh`: controlla solo `git diff --cached` (vuoto in un container immutabile o fuori da un pre-commit hook); va esteso per scansionare tutti i file `secrets-sops/*.enc.yaml` quando lo stage Git è vuoto.

---

## 2. Specifiche Tecniche del Fork Esterno `llmwiki` (`v0.9.1-k8slab`)

Nel repository GitHub dedicato al fork di `llmwiki` (`https://github.com/pindaroli/llmwiki-mcp.git`, tag `v0.9.1-k8slab`), sono applicate le seguenti 4 evoluzioni strutturali retrocompatibili:

1. **Supporto Multi-Cartella Tassonomico (`paths.content_dirs` in `llmwiki/config.py` e `llmwiki/k8slab_dirs.py`)**:
   - Se `config.yaml` definisce `paths.content_dirs` (mappa `{categoria: percorso_relativo}`), la funzione `get_content_dirs(cfg, root)` restituisce tutte le cartelle abilitate (`concept`, `entity`, `pattern`, `workflow`, `procedure`, `plan`); altrimenti ripiega sul comportamento standard `{"concept": root / cfg["paths"]["concepts"]}`.
2. **Scansione Unificata, Filtro Piani Attivi e Risoluzione Slug (`llmwiki/search.py` & `llmwiki/operations.py`)**:
   - L'helper centralizzato `iter_kb_markdown_files(cfg, root)` itera su tutte le directory di `get_content_dirs(cfg, root)`, ignorando `README.md` e i file che iniziano con `_`.
   - Per la categoria `plan` (`wiki/plans/`), vengono indicizzati esclusivamente i file il cui frontmatter YAML ha `status` in `{"active", "approved", "in_progress"}`.
   - `resolve_slug_path(cfg, root, slug, category=None)` cerca `<slug>.md` attraverso tutte le `content_dirs` in lettura (`kb_get`, `kb_backlinks`, `kb_lint`) e, in scrittura (`kb_compile`), salva il file nella directory associata alla `category` specificata (con fallback su `paths.concepts`).
3. **Normalizzazione Trasparente del Frontmatter `k8s-lab` (`llmwiki/taxonomy.py`)**:
   - Accetta in modo nativo `type` come alias di `category`, `last_updated` come alias di `updated`, e rimuove automaticamente il prefisso `#` dai tag (es. `"#mcp"` $\rightarrow$ `"mcp"`), garantendo zero falsi positivi in `kb_lint`.
4. **File-Locking Atomico su `wiki/_meta/` (`llmwiki/operations.py`)**:
   - Ogni scrittura su `wiki/_meta/index.json`, `wiki/_meta/_index.md` e `wiki/_meta/log.md` acquisisce un lock esclusivo `fcntl.flock` su `wiki/_meta/.lock` e utilizza scrittura atomica (`tempfile` nella stessa directory + `os.replace()`).

---

## 3. Mappa dei File da Creare o Modificare in `k8s-lab`

| Percorso File | Operazione | Scopo |
| :--- | :--- | :--- |
| `config.yaml` | **Creazione** | Configurazione nativa per il fork `llmwiki`: profilo lingua `single` (`bare_body: true`), mappatura completa `paths.content_dirs` e puntamento a `LiteLLM` (`http://10.10.20.50:4000/v1`). |
| `wiki/concepts/*.md` (7 file) | **Modifica** | Rimozione deterministica delle sezioni CJK (`## 中文` e `## 日本語`) generate dal vecchio default trilingue. |
| `wiki/patterns/script-to-mcp-tool-schema-pattern.md` | **Modifica** | Aggiunta `id: script-to-mcp-tool-schema-pattern`, `created_at`, `last_updated`, `in_use_by` strutturato e allineamento specifica `cli_mapping` / `ansible_mapping`. |
| `GEMINI.md` | **Modifica** | Registrazione di `[[script-to-mcp-tool-schema-pattern]]` nella mappa concettuale dei Pattern. |
| `scripts/wiki/build_wiki_context.py` | **Modifica** | Inclusione di `("concepts", "🧠 Concetti Compilati (LLM Wiki)")` e `("procedures", "🛠️ Procedure Operative")` in `SECTION_ORDER` (senza alcuna duplicazione) e validazione dei path di `scripts/mcp_tools.yaml`. |
| `scripts/llmwiki/launcher.py` | **Modifica** | Avvio locale `stdio` conforme a `[[go-launcher-script-pattern]]` (`os.chdir(ROOT_DIR)`), configurazione `LLMWIKI_CONFIG` e variabili d'ambiente LLM (`LiteLLM` / `Ollama`). |
| `schemas/mcp-tools.schema.json` | **Creazione** | JSON Schema Draft 2020-12 formale per validare la struttura e i vincoli di `scripts/mcp_tools.yaml`. |
| `scripts/mcp_tools.yaml` | **Modifica** | Correzione dei 3 path errati (`audit_proxmox_smart_disks`, `audit_movie_duplicates`, `exos_bounce_sfp_port10`) e allineamento dei tool di `go.py`. |
| `scripts/network/test_dhcp.sh` | **Modifica** | Fallback automatico a `sops -d` su `secrets-sops/opnsense-mcp-credentials.enc.yaml`, interrogazione primaria API REST OPNsense e supporto `ip neigh` su Linux. |
| `scripts/ragflow/ingestion_stats.sh` | **Modifica** | Sostituzione alias `ssh truenas` con `${TRUENAS_SSH_TARGET:-olindo@10.10.20.50}` e fallback SOPS. |
| `scripts/servarr/audit_movie_duplicates.sh` | **Modifica** | Sostituzione alias `ssh truenas` con `${TRUENAS_SSH_TARGET:-olindo@10.10.20.50}` e opzioni SSH non interattive per esecuzione in container Linux. |
| `scripts/security/check-sops-encrypted.sh` | **Modifica** | Fallback di scansione sull'intera cartella `secrets-sops/*.enc.yaml` quando `git diff --cached` è vuoto. |

---

## 4. Fasi Operative con Protocollo Test-Driven (§12)

### Fase 0: Preparazione e Tagging del Fork Esterno `llmwiki` (`v0.9.1-k8slab`)
1. **Azione**:
   - Creazione del fork GitHub `pindaroli/llmwiki-mcp` e implementazione del supporto a `paths.content_dirs`, filtro `status` per `plans`, normalizzazione frontmatter (`type`/`last_updated`/`#tags`) e file-locking atomico su `_meta/`.
   - Creazione del tag Git `v0.9.1-k8slab`.
2. **Test di Verifica**:
   ```bash
   /opt/homebrew/bin/uv run --no-project --refresh \
     --with "git+https://github.com/pindaroli/llmwiki-mcp.git@v0.9.1-k8slab" \
     python -c "import llmwiki.k8slab_dirs as kd, llmwiki.config as c; assert hasattr(c, 'get_content_dirs'); print('OK: Fork llmwiki caricato correttamente:', kd.__name__)"
   ```

### Fase 1: Bonifica CJK in `wiki/concepts/`, Allineamento Governance e `build_wiki_context.py`
1. **Azione**:
   - Rimozione deterministica delle sezioni `## 中文` e `## 日本語` dai 7 file presenti in `wiki/concepts/`.
   - Aggiornamento del frontmatter di `wiki/patterns/script-to-mcp-tool-schema-pattern.md` e registrazione in `GEMINI.md`.
   - Estensione di `SECTION_ORDER` in `scripts/wiki/build_wiki_context.py` con `("concepts", "🧠 Concetti Compilati (LLM Wiki)")` e `("procedures", "🛠️ Procedure Operative")`.
2. **Test di Verifica (Assenza CJK + Assenza Duplicati in `wiki_context.md`)**:
   ```bash
   ! grep -rnE "^## (中文|日本語)" wiki/concepts/ && \
   python3 scripts/wiki/build_wiki_context.py && \
   grep -E "^# (🧠|🛠️|📐)" wiki/wiki_context.md && \
   python3 -c '
   import re, collections
   txt = open("wiki/wiki_context.md").read()
   sources = re.findall(r"^## 📄 File: `(wiki/[^`]+)`", txt, re.M)
   dups = [k for k, v in collections.Counter(sources).items() if v > 1]
   assert not dups, f"Duplicati rilevati in wiki_context.md: {dups}"
   print(f"OK: {len(sources)} file unici nel contesto monolitico e zero sezioni CJK.")
   '
   ```

### Fase 2: Configurazione `config.yaml`, `scripts/llmwiki/launcher.py` e Rebuild Indice Unificato Locale
1. **Azione**:
   - Creazione di `config.yaml` nella root del repository con `bare_body: true` e mappatura completa `paths.content_dirs`.
   - Aggiornamento di `scripts/llmwiki/launcher.py` per esecuzione `stdio` locale agganciata al fork di `llmwiki`.
   - Rigenerazione dell'indice `wiki/_meta/` sull'intero corpus del repository (`concepts`, `entities`, `patterns`, `workflows`, `procedures`, `plans` attivi).
2. **Test di Verifica (Profilo Lingua + Corpus Unificato >= 48 Articoli + Ricerca Cross-Cartella)**:
   ```bash
   /opt/homebrew/bin/uv run --no-project \
     --with "git+https://github.com/pindaroli/llmwiki-mcp.git@v0.9.1-k8slab" \
     --with "pyyaml>=6.0.1" \
     python -c '
   import llmwiki.config as c, llmwiki.operations as ops, llmwiki.search as s
   cfg = c.load_config()
   prof = c.get_language_profile(cfg)
   assert prof.get("bare_body") is True, f"Profilo non bare_body: {prof}"
   ops.kb_rebuild_index(cfg)
   items = ops.kb_list(cfg)
   assert len(items) >= 48, f"Attesi >= 48 articoli indicizzati, trovati {len(items)}"
   hits = s.search(cfg, "script-to-mcp-tool-schema-pattern")
   assert hits, "Ricerca su wiki/patterns/ fallita!"
   print(f"OK: {len(items)} articoli indicizzati nativamente dal fork in modalità locale stdio!")
   '
   ```

### Fase 3: Hardening Script per Esecuzione in Container (`test_dhcp.sh`, `ingestion_stats.sh`, `audit_movie_duplicates.sh`, `check-sops-encrypted.sh`)
1. **Azione**:
   - Aggiornamento di `scripts/network/test_dhcp.sh` con decifratura SOPS automatica da `secrets-sops/opnsense-mcp-credentials.enc.yaml`, interrogazione REST OPNsense e fallback `ip neigh`.
   - Sostituzione dell'alias SSH `truenas` con `${TRUENAS_SSH_TARGET:-olindo@10.10.20.50}` in `scripts/ragflow/ingestion_stats.sh` e `scripts/servarr/audit_movie_duplicates.sh`.
   - Estensione di `scripts/security/check-sops-encrypted.sh` per scansionare tutti i file `secrets-sops/*.enc.yaml` quando `git diff --cached` è vuoto.
2. **Test di Verifica**:
   ```bash
   bash scripts/security/check-sops-encrypted.sh && \
   ! grep -rnE "ssh[[:space:]]+truenas\b" scripts/ragflow/ingestion_stats.sh scripts/servarr/audit_movie_duplicates.sh && \
   echo "OK: SOPS check superato e zero alias SSH hardcoded."
   ```

### Fase 4: Correzione e Validazione Automatica di `scripts/mcp_tools.yaml`
1. **Azione**:
   - Creazione di `schemas/mcp-tools.schema.json` (JSON Schema Draft 2020-12).
   - Correzione dei 3 path errati in `scripts/mcp_tools.yaml` (`audit_proxmox_smart_disks`, `audit_movie_duplicates`, `exos_bounce_sfp_port10`) e allineamento con i comandi di `scripts/go.py`.
2. **Test di Verifica (JSON Schema Draft 2020-12 + Esistenza Fisica dei File)**:
   ```bash
   python3 -c '
   import yaml, json, os, jsonschema
   schema = json.load(open("schemas/mcp-tools.schema.json"))
   data = yaml.safe_load(open("scripts/mcp_tools.yaml"))
   jsonschema.validate(instance=data, schema=schema)
   missing = [t["name"] for t in data["tools"] if not os.path.isfile(t["path"])]
   assert not missing, f"Path mancanti: {missing}"
   print(f"OK: Schema JSON e path validati con successo per {len(data[\"tools\"])} tools!")
   '
   ```

### Fase 5: Validazione Finale e Consolidamento (§13)
1. **Azione**: Esecuzione della suite canonica di validazione rete e rigenerazione del contesto wiki monolitico.
2. **Test di Verifica**:
   ```bash
   python3 scripts/network/validate_network.py && python3 scripts/wiki/build_wiki_context.py
   ```

---

## 5. Piano di Rollback

1. **Ripristino Configurazione `llmwiki`, Concetti e Script**:
   ```bash
   git checkout HEAD -- scripts/ wiki/concepts/ wiki/patterns/script-to-mcp-tool-schema-pattern.md GEMINI.md
   rm -f config.yaml schemas/mcp-tools.schema.json
   ```
2. **Ripristino Indice `wiki/_meta/`**:
   ```bash
   git checkout HEAD -- wiki/_meta/
   ```

---

## 💾 Stato di Ripristino (AI Save-State)
- **Fase Attiva**: Piano Completato con Successo (Fasi 0–5) ✅
- **Ultima Azione Completata**: Esecuzione e verifica al 100% di tutte le fasi: fork esterno `pindaroli/llmwiki-mcp@v0.9.1-k8slab`, bonifica CJK, configurazione `config.yaml` monolingue, riallineamento `mcp_config.json`, hardening script runner, validazione automatica `scripts/mcp_tools.yaml` e suite canonica (§13: `validate_network.py` e `build_wiki_context.py`).
- **Prossimo Passo Operativo**: Nessuno. Piano concluso e archiviato con successo.
- **Blocchi/Decisioni Pendenti**: Nessuno.

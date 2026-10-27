# Contesto Architetturale per Consulto: `llmwiki-mcp-sse-convergence-and-tools-hardening`

## 1. Scheda del Piano
- **Titolo**: Piano: Convergenza Wiki Karpathy `llmwiki`, Delivery Container SSE/StreamableHTTP e Hardening `mcp_tools.yaml`
- **Percorso Piano**: [`wiki/plans/llmwiki-mcp-sse-convergence-and-tools-hardening.md`](file:///Users/olindo/prj/k8s-lab/wiki/plans/llmwiki-mcp-sse-convergence-and-tools-hardening.md)
- **Stato**: `active` (`certified_for_ai: true`)
- **Stack Tecnologico**: Python 3.11+, `llmwiki[all]==0.9.0`, `mcp<2.0.0`, `uv`, `supergateway@4.1.0` (Node 22 Alpine / Debian Slim), Docker Compose (TrueNAS SCALE / OrbStack Failover), Kubernetes (`mcp-system`), Ansible, SOPS + Age.
- **Indice Sezioni del Piano**:
  1. Contesto, Problema e Obiettivi Architetturali (Split-Brain `llmwiki` vs `build_wiki_context.py`, Confronto Opzioni 1A / 1B / 1C, Delivery SSE/StreamableHTTP)
  2. Mappa dei File da Creare o Modificare
  3. Fasi Operative con Protocollo Test-Driven (§12)
  4. Piano di Rollback
  5. Stato di Ripristino (AI Save-State §11)

---

## 2. Nodi, IP e Rete Pertinenti (Estratto Canonico da `rete.json`)

| ID Nodo / Servizio | Hostname / FQDN | Indirizzo IP | VLAN | Ruolo nel Piano |
| :--- | :--- | :--- | :--- | :--- |
| **`truenas`** | `truenas.pindaroli.org` | `10.10.20.50` | VLAN 20 (Client/Services) | Host primario dello stack Docker (`truenas-docker` e `truenas-docker/mcp`, porta `:8100` gateway MCP Traefik, Hermes Agent `:9119`, LiteLLM `:4000`). |
| **`mac-studio`** | `mac-studio` | `10.10.20.100` | VLAN 20 | Workstation di sviluppo e host del failover OrbStack in modalità `lab_mode_off` (`~/.homelab-failover/docker-compose.yaml`). |
| **`lxc-ollama`** | `lxc-ollama.pindaroli.org` | `10.10.20.33` | VLAN 20 | LXC 300 su `pve3`: motore LLM locale Ollama (`:11434`) e llama-server OCR (`:8081`), utilizzabile da `llmwiki` per `kb_ask` / `kb_compile`. |
| **`pve1`, `pve2`, `pve3`** | `pve1/2/3.pindaroli.org` | `10.10.10.11`, `.21`, `.31` | VLAN 10 (Server) | Cluster Proxmox VE gestito via SSH/Ansible dai tool di `mcp_tools.yaml`. |
| **`talos-cp-01..03`** | `k1`, `k2`, `k3` | `10.10.20.141..143` (VIP `.55`) | VLAN 20 | Cluster Kubernetes Talos (namespace `mcp-system`, Ingress VIP Traefik `10.10.20.56`). |
| **`opnsense`** | `firewall.pindaroli.org` | `192.168.2.254` / `192.168.100.1` (OOB) | Transit / VLAN 99 | Firewall e resolver Unbound DNS (`10.10.20.1` / `10.10.20.254`) + Kea DHCP API. |
| **`extreme`** | `switch.pindaroli.org` | `10.10.20.1` / `10.10.10.254` | L3 Core Switch | Switch ExtremeXOS (porta 10 SFP+ gestita dal playbook `exos_port10_boot_recovery.yml`). |

---

## 3. Storage ZFS & Share NFS Pertinenti (Estratto da `storage.json`)

| Pool / Dataset | Percorso Fisico TrueNAS | Utilizzo nel Contesto del Piano |
| :--- | :--- | :--- |
| **`stripe/truenas-docker`** | `/mnt/stripe/truenas-docker` | Ospita i file `docker-compose.yaml` e la sottocartella `/mnt/stripe/truenas-docker/mcp/` della flotta MCP containerizzata. |
| **`stripe/hermesAgent`** | `/mnt/stripe/hermesAgent` | Ospita `HermesMain/` e il workspace condiviso `common/prj/k8s-lab` (sincronizzato bidirezionalmente tra TrueNAS e Mac Studio `/Users/olindo/hermesAgent/common/prj/k8s-lab`). |
| **`oliraid/arrdata`** | `/mnt/oliraid/arrdata/media/movies` | Libreria multimediale ispezionata via SSH dagli script `servarr/*.sh` registrati in `scripts/mcp_tools.yaml`. |

---

## 4. Architettura Interna di `llmwiki==0.9.0` e Vincoli Rilevati

Dall'ispezione del codice sorgente di `llmwiki==0.9.0` (`llmwiki/config.py`, `llmwiki/search.py`, `llmwiki/operations.py`, `llmwiki/mcp_server.py`) emergono i seguenti fatti tecnici oggettivi:
1. **Hardcoding delle Directory di Ricerca e Lettura**:
   - `llmwiki.search.search()` esegue: `for md_file in list(concepts_dir.glob("*.md")) + list(outputs_dir.glob("*.md")):` (non usa `rglob`, quindi non scende nelle sottocartelle e non guarda `entities/`, `patterns/`, `workflows/`, `procedures/`).
   - `llmwiki.operations` (`kb_get`, `kb_list`, `kb_backlinks`, `kb_lint`, `kb_rebuild_index`) risolve ogni articolo cercando esclusivamente `Path(cfg["paths"]["concepts"]) / f"{slug}.md"`.
2. **Profilo Lingua Default (`BUILTIN_LANGUAGES`)**:
   - Se nella root del progetto non esiste un file `config.yaml`, `llmwiki.config._defaults()` applica il profilo `"trilingual"` (`en`, `zh`, `ja`), motivo per cui i 7 file attuali in `wiki/concepts/` contengono sezioni in Cinese (`## 中文`) e Giapponese (`## 日本語`).
   - Tuttavia, `llmwiki.config._normalize_profile()` supporta nativamente un profilo a singola sezione con `header: ""` (`bare_body: true`), configurabile in modo 100% dichiarativo tramite `config.yaml`.
3. **Trasporto MCP (`llmwiki/mcp_server.py`)**:
   - `llmwiki.mcp_server` espone unicamente `stdio_server()` della libreria `mcp` (`mcp<2.0.0`).
   - Non possiede un server HTTP/SSE integrato per MCP (il modulo `llmwiki/web.py` è una UI HTML di ricerca umana sulla porta 5555, non un endpoint MCP SSE/StreamableHTTP).
   - Per esporre `llmwiki` in container remoto via **SSE (`/sse`) o Streamable HTTP (`/mcp`)** secondo gli standard del lab (`[[mcp-registry-package-pattern]]`), il pattern standard adottato in `docker/mcp/registry-package/*` e `docker/mcp/in-house/*` è incapsulare il comando stdio con **`supergateway@4.1.0`**.

---

## 5. Vincoli Architetturali & Golden Rules Applicabili (`GEMINI.md`)

1. **NO UNAUTHORIZED EXTERNAL LIBRARY MODIFICATIONS**: È vietato alterare file dentro site-packages di `llmwiki`. Qualsiasi configurazione o adattamento deve risiedere nel repository (`config.yaml`, `scripts/llmwiki/launcher.py`, `Dockerfile` o script di sync).
2. **MCP REGISTRY PACKAGE & STREAMABLE HTTP / SSE PATTERN**: I container MCP in `docker/mcp/` devono girare come utente non privilegiato (`UID 1000`), avere tag immagine espliciti (mai `:latest`), esporre `/healthz` e utilizzare `supergateway` per tradurre `stdio` in `sse` / `streamableHttp`.
3. **ZERO PLAINTEXT SECRETS (SOPS MANDATE)**: Nessuno script in `scripts/` o `mcp_tools.yaml` può dipendere da file di credenziali non tracciati come `ansible/OPNsense.internal_root_apikey.txt`; deve decifrare da `secrets-sops/*.enc.yaml` tramite `sops` o leggere variabili d'ambiente iniettate.
4. **CWD & LOCATION INDEPENDENCE (`[[go-launcher-script-pattern]]`)**: Ogni script invocato da `go.py` o `mcp_tools.yaml` deve risolvere `ROOT_DIR` dinamicamente e funzionare identicamente sul Mac Studio e dentro il container Linux.

---

## 6. Quesiti Specifici per il Consulto Architetturale

Si richiede al Revisore di esprimersi in modo particolare su:
1. **Scelta tra Opzione 1A, 1B e 1C per il Corpus Unificato di `llmwiki`**:
   - Qual è il pattern più pulito, resiliente agli aggiornamenti e portabile in un container Docker GitOps per far sì che `llmwiki` (`kb_search`, `kb_get`, `kb_list`, `kb_ask`, `kb_backlinks`) indicizzi anche `wiki/entities/`, `wiki/patterns/`, `wiki/workflows/` e `wiki/procedures/` senza rompere la struttura semantica del repository né `build_wiki_context.py`?
   - **Sub-variante 1A-bis (Build-time / Sync Projection)**: È preferibile uno script deterministico (integrato in `build_wiki_context.py` e nel `Dockerfile`) che sincronizza/proietta i file attivi in `wiki/concepts/` (o in una directory `wiki/_compiled_concepts/` puntata da `config.yaml -> paths.concepts`) e rigenera `wiki/_meta/index.json`?
2. **Architettura di Delivery Container SSE / Streamable HTTP per `llmwiki`**:
   - Validazione del `Dockerfile` basato su `supergateway@4.1.0` (supporto duale SSE / Streamable HTTP) e strategia di aggiornamento della Knowledge Base nel container (immagine immutabile ricostruita via GitOps al push vs bind-mount del working tree `/mnt/stripe/hermesAgent/common/prj/k8s-lab` su TrueNAS/OrbStack).
3. **Completezza e Sicurezza di `scripts/mcp_tools.yaml`**:
   - Verifica dei fix proposti per i 3 tool rotti (`audit_proxmox_smart_disks`, `audit_movie_duplicates`, `exos_bounce_sfp_port10`) e per gli script `test_dhcp.sh`, `ingestion_stats.sh` e `check-sops-encrypted.sh`.

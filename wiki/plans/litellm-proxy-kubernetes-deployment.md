---
title: "Piano: Installazione LiteLLM Proxy su Kubernetes con Routing Mac Studio / lxc-ollama e Integrazione Hermes"
type: plan
status: archived
certified_for_ai: false
created_at: 2026-10-21
completed_at: 2026-10-21
tags:
  - "#litellm"
  - "#ollama"
  - "#kubernetes"
  - "#helm"
  - "#hermes"
---

# Piano: Installazione LiteLLM Proxy su Kubernetes con Routing Mac Studio / lxc-ollama e Integrazione Hermes

Installazione dichiarativa (Helm) di un **LiteLLM Proxy** come gateway di inferenza LLM del lab, con routing tra Ollama su Mac Studio (`olindo-macstudio`, Metal, 64 GB unified) e `lxc-ollama` (PVE3, Radeon 890M), e integrazione dell'istanza Hermes Agent. **RAGFlow resta invariato** (decisione utente).

## 🗺️ Mappe Concettuali e Relazioni
- [[SCHEMA]] (Regole di governance del Wiki)
- [[Network_Registry]] (`rete.json`: Mac Studio `10.10.20.100:11434`, `lxc-ollama` `10.10.20.33:11434`)
- [[Ollama]] (Servizi di inferenza)
- [[ollama-rete-registry-integration]] (Registrazione servizi Ollama in `rete.json`)
- [[lxc-ollama-llama-ocr-qwen25-sidecar]] (sidecar `llama-server` Qwen2.5-VL su `:8081`, fuori dal routing)
- [[mcp-secret-projection-pattern]] (Proiezione segreti)

---

## 🎯 Decisioni di Design (concordate con l'utente)

| Area | Decisione |
|---|---|
| Deploy | Namespace `litellm`; chart upstream `oci://ghcr.io/berriai/litellm-helm` (confermato; Project Chart solo se `extraResources` non basta); values in `litellm/litellm-values.yaml`; pod fissato su `talos-cp-01` o `talos-cp-02` via `affinity` (`talos-cp-03` escluso: 4 GB RAM, 66% usata) |
| Esposizione | Traefik IngressRoute su `litellm-internal.pindaroli.org` (trusted, no OAuth2); traffico intra-cluster via K8s DNS |
| Database | Database e ruolo dedicati `litellm` su `postgres-main` (CNPG, `postgres-main-rw.cnpg-system.svc.cluster.local`); credenziali e master key in SOPS |
| Routing >12B | Mac primario, `lxc-ollama` in subordine; fallback solo se il modello esiste sull'altro backend, altrimenti errore esplicito |
| Mac spento | Health check attivo con cooldown per escludere il Mac ed evitare timeout ripetuti |
| Embedding | Alias `embed` (`bge-m3`) instradato solo su `lxc-ollama` (mantenuto disponibile per usi futuri; RAGFlow invariato) |
| Vision | Mac primario; fallback sullo stesso modello Ollama di `lxc-ollama`; il sidecar `llama-server` `:8081` non è nel routing |
| Backend | Hostname DNS (Unbound/OPNsense), niente IP hardcoded |
| Hermes | Usa **esclusivamente** LiteLLM (provider `litellm` via K8s DNS; DeepSeek rimosso da Hermes); virtual key riproducibile (valore in SOPS + Job idempotente); values dichiarativi |
| RAGFlow | **Nessuna modifica**: resta su Ollama/Mac (DB `rag_flow`) e DeepSeek; i modelli che usa non vanno cancellati |
| Console | Admin UI su `/ui` solo per consumi/log e chiavi non critiche; `model_list`, alias e fallback solo nei `values` Helm; nessuna protezione extra (dominio `-internal`, credenziale in SOPS) |

## 🔀 Alias (validati dall'utente)

Insieme di modelli identico su entrambi i backend: `qwen2.5:32b-instruct-q5_K_M`, `gemma4:31b`, `qwen3-vl:32b`, `qwen2.5vl:7b-q4_K_M`, `bge-m3`.

| Alias | Primario (Mac) | Fallback (`lxc-ollama`) |
|---|---|---|
| `big-chat` | `qwen2.5:32b-instruct-q5_K_M` | `qwen2.5:32b-instruct-q5_K_M` |
| `big-alt` | `gemma4:31b` | `gemma4:31b` |
| `vision` | `qwen3-vl:32b` | `qwen3-vl:32b` |
| `vision-light` | `qwen2.5vl:7b-q4_K_M` | `qwen2.5vl:7b-q4_K_M` |
| `embed` | – | `bge-m3` (routing solo `lxc-ollama`) |

> [!NOTE]
> Stato rilevato il 2026-10-21 (da ri-verificare in Fase 1): sul Mac manca `gemma4:31b`; su `lxc-ollama` manca il tag Ollama `qwen2.5vl:7b-q4_K_M` (esiste solo il sidecar `llama-server` su `:8081`). Entrambi vanno scaricati in Fase 1b.

> [!NOTE]
> L'alias `big-chat-xl` (`qwen2.5:72b-instruct-q4_K_M`, solo Mac, senza fallback) è stato **eliminato** per decisione dell'utente; il modello viene rimosso dal Mac in Fase 9.

## 🔎 Stato RAGFlow rilevato (sola lettura, 2026-10-21)
RAGFlow `v0.27.1` salva provider/istanze/modelli nel DB `rag_flow` (`tenant_model_provider`, `tenant_model_instance`, `tenant_model`), gestiti da UI, non nei `values` Helm.

| Provider / istanza | Modello | Tipo | Note |
|---|---|---|---|
| Ollama / `mac` (`http://10.10.20.100:11434`) | `bge-m3:latest` | embedding | usato da 5 knowledge base |
| Ollama / `mac` | `gpt-4o:latest` | chat | **in uso: da NON cancellare** |
| Ollama / `mac` | `qwen2.5vl:32b` | img2txt | tag già assente sul Mac (problema preesistente, fuori scope) |
| DeepSeek / `deepserach` | `deepseek-v4-flash`, `deepseek-v4-pro`, `deepseek-v4-flash-vision-exp` | chat / img2txt | cloud |

> [!IMPORTANT]
> `gpt-4o:latest`, `gpt-4o-mini:latest` e `deepseek-r1:32b` condividono lo stesso digest (19,9 GB). Poiché `gpt-4o:latest` serve a RAGFlow, cancellare gli altri due tag NON libera spazio (il file resta usato da `gpt-4o`).

## ⚠️ Specifiche Tecniche Anti-Errore (Obbligatorie per l'Esecutore)

Per evitare errori di esecuzione, ogni fase DEVE attenersi tassativamente a queste specifiche verificate sul cluster:

1. **Indirizzi DNS e VIP Traefik (NON confondere con il VIP API K8s)**:
   - Dai pod K8s i due backend risolvono già via FQDN: `olindo-macstudio.pindaroli.org` (`10.10.20.100`) e `lxc-ollama.pindaroli.org` (`10.10.20.33`). Usare sempre i FQDN nelle URL (`http://olindo-macstudio.pindaroli.org:11434` e `http://lxc-ollama.pindaroli.org:11434`).
   - Il VIP LoadBalancer di Traefik per tutti i domini `*-internal.pindaroli.org` su Unbound OPNsense è **`10.10.20.56`** (NON `10.10.20.55`, che è il VIP del control plane K8s).

2. **Tag Immagine e Chart Upstream (`berriai/litellm-helm`)**:
   - Chart: `oci://ghcr.io/berriai/litellm-helm` versione **`1.106.2`**.
   - Immagine: `ghcr.io/berriai/litellm:1.106.2` (verificata esistente su GHCR con `appVersion: 1.106.2`; impostare `image.tag: "1.106.2"` e `image.pullPolicy: IfNotPresent`). Non usare tag inesistenti come `main-v1.106.2-stable`.

3. **Sintassi Esatta LiteLLM (`ollama_chat/` + Priorità `order` + Cooldown)**:
   - **Prefisso provider**: per i modelli di chat, tool-calling e vision (`big-chat`, `big-alt`, `vision`, `vision-light`) usare **tassativamente** `ollama_chat/<modello>` (NON `ollama/<modello>`, che usa l'endpoint legacy `/api/generate` e rompe tool calling e immagini). Per l'embedding (`embed`) usare `ollama/bge-m3:latest`.
   - **Priorità primario/fallback**: nel `model_list` di LiteLLM, definire per ciascuno dei 4 alias due voci con lo **stesso** `model_name` (così `/v1/models` espone un solo nome pulito per `discover_models: true` di Hermes), impostando dentro `litellm_params`:
     - `order: 1` (e `timeout: 5`, `stream_timeout: 10`) sulla voce del **Mac Studio** (`http://olindo-macstudio.pindaroli.org:11434`);
     - `order: 2` sulla voce di **`lxc-ollama`** (`http://lxc-ollama.pindaroli.org:11434`).
   - Abilitare obbligatoriamente in `proxy_config.router_settings`:
     ```yaml
     router_settings:
       enable_pre_call_checks: true
       routing_strategy: simple-shuffle
       num_retries: 2
       allowed_fails: 1
       cooldown_time: 60
     ```
     *(Senza `enable_pre_call_checks: true`, LiteLLM ignora `order: 1 / 2` e bilancia 50/50 tra Mac e `lxc-ollama`!)*

4. **Separazione Segreti per Namespace (`cnpg-system` vs `litellm` vs `hermes`)**:
   - In **`cnpg-system`**: Secret `litellm-db-password` (`type: Opaque`, con chiavi `username: litellm` e `password: <DB_PASSWORD>`) richiesto da `postgres-main` (`spec.managed.roles`).
   - In **`litellm`**: Secret `litellm-secrets` con `username: litellm`, `password: <DB_PASSWORD>`, `PROXY_MASTER_KEY: sk-litellm-master-...`, `LITELLM_SALT_KEY: sk-litellm-salt-...`, `UI_USERNAME: admin`, `UI_PASSWORD: <UI_PASSWORD>`, `HERMES_VIRTUAL_KEY: sk-hermes-...`.
   - In **`hermes`**: aggiungere `LITELLM_API_KEY: sk-hermes-...` a `secrets-sops/hermes-secrets.enc.yaml` (NON usare il nome `OPENAI_API_KEY` perché il chart `hermes-agent` monta per primo il Secret `hermes-hermes-agent-env` che definisce `OPENAI_API_KEY: ""`!).

5. **Creazione Database CNPG e Certificato TLS in `litellm`**:
   - La CRD `databases.postgresql.cnpg.io/v1` deve risiedere nel namespace `cnpg-system` (`cluster: { name: postgres-main }`, `name: litellm`, `owner: litellm`).
   - Nel namespace `litellm` deve essere presente la risorsa `Certificate` (`cert-manager.io/v1`, `secretName: pindaroli-wildcard-tls`, `issuerRef: letsencrypt-cloudflare`, identica a `hermes-agent/wildcard-cert.yaml`), altrimenti la `IngressRoute` Traefik non trova il Secret TLS nel namespace `litellm`.

6. **Particolarità Deploy di Hermes (`kustomize build --enable-helm` e `config.model.default`)**:
   - Hermes usa `helmCharts:` dentro `hermes-agent/kustomization.yaml` con `bootstrap.overwrite: true` (di default nel chart) che sovrascrive `/opt/data/config.yaml` ad ogni riavvio del pod.
   - In `hermes-agent/values.yaml` è **obbligatorio** specificare sia `config.model.provider: litellm` sia `config.model.default: big-chat` (altrimenti il chart eredita il default `gpt-4o-mini` dal `values.yaml` interno del chart!).
   - Per applicare le modifiche a Hermes NON usare `kubectl apply -k` (fallisce perché `kubectl` non abilita `--enable-helm`): usare sempre:
     ```bash
     kustomize build --enable-helm hermes-agent/ | kubectl apply -f -
     ```

---

## 🛠️ Fasi Operative

> [!IMPORTANT]
> Ogni fase segue l'Execution Protocol: spiegare cosa/perché, attendere approvazione, eseguire, verificare, attendere il via libera per la fase successiva.

### Fase 1: Raccolta dati e prerequisiti
- Verificare risorse libere su `talos-cp-01`/`cp-02` e modelli presenti sui due backend.
- Verificare i record DNS Unbound per `olindo-macstudio` e `lxc-ollama` raggiungibili dal cluster.
- Chart upstream confermato: fissare la versione (rilevata `1.106.2`) e verificare con `helm template` che IngressRoute, `Database` e Job chiavi entrino in `extraResources`, altrimenti ripiegare su Project Chart.

### Fase 1b: Allineamento modelli sui due backend
- **Obiettivo**: lo stesso insieme di 5 modelli (vedi Alias) su Mac Studio (`10.10.20.100:11434`) e `lxc-ollama` (`10.10.20.33:11434`).
- **Pre-check**: confrontare `/api/tags` dei due backend con la lista attesa e calcolare i mancanti per nodo; verificare spazio libero (Mac: disco; `lxc-ollama`: NFS `stripe/ollama`).
- **Download solo dei mancanti** (un comando alla volta, dopo approvazione). Mancanti attesi: `gemma4:31b` sul Mac, `qwen2.5vl:7b-q4_K_M` su `lxc-ollama`:
  ```bash
  curl -s http://10.10.20.100:11434/api/pull -d '{"model":"gemma4:31b","stream":false}'
  ```
  ```bash
  curl -s http://10.10.20.33:11434/api/pull -d '{"model":"qwen2.5vl:7b-q4_K_M","stream":false}'
  ```
- **Verifica**: `/api/tags` di entrambi elenca i 5 modelli; digest coincidenti tra i nodi; test di generazione/embedding per ciascun modello scaricato.
- **Nota**: per `gemma4:31b` il riferimento su `lxc-ollama` è `dhiltgen/gemma4:31b-it-mtp-q4_K_M-llamacpp`; verificare lo stesso digest sul Mac.
- **Nota**: `lxc-ollama` ha `OLLAMA_MAX_LOADED_MODELS=1` e `KEEP_ALIVE=-1`: il fallback tra modelli diversi provoca scaricamento/ricaricamento (latenza).

### Fase 2: Segreti (SOPS)
- Creare in `secrets-sops/` il segreto con master key LiteLLM, salt key, password DB e il valore pre-generato della virtual key `hermes`.
- Verifica: decifratura `sops -d` e applicazione dry-run.

### Fase 3: Database su `postgres-main`
- **Ruolo**: aggiungere `litellm` a `spec.managed.roles` in `postgres/cluster.yaml` (come già `n8n` e `ragflow`), con `passwordSecret: litellm-db-password` (Secret in `cnpg-system`, sorgente SOPS). Modifica additiva.
- **Database**: risorsa CNPG `Database` (CRD presente) con `owner: litellm`, inclusa in `extraResources` del release LiteLLM con `metadata.namespace: cnpg-system` (nessun YAML sciolto).
- **Verifica**: ruolo e database presenti, connessione dal namespace `litellm` con il ruolo dedicato.

### Fase 4: Chart e values LiteLLM
- Chart upstream, versione e immagine fissate, mai `:latest`.
- Scrivere `litellm/litellm-values.yaml` (model_list con alias, router con fallback, health check/cooldown, `db.useExisting`, `masterkeySecretName`, `affinity`, `resources` 1–2 GiB, `extraResources` per IngressRoute/Database/Job chiave).
- Verifica: `helm lint`, `helm template`, dry-run.

### Fase 5: Deploy, DNS e IngressRoute
- `helm upgrade --install litellm oci://ghcr.io/berriai/litellm-helm --version 1.106.2 -n litellm --create-namespace -f litellm/litellm-values.yaml`.
- Certificato `Certificate` (`pindaroli-wildcard-tls` via `letsencrypt-cloudflare`) e IngressRoute Traefik su `litellm-internal.pindaroli.org` (websecure, `pindaroli-wildcard-tls`, nessun OAuth2) in `extraResources`.
- Record Unbound su OPNsense: `litellm-internal.pindaroli.org` → **`10.10.20.56`** (Traefik VIP).
- Verifica: pod Ready su `talos-cp-01` o `talos-cp-02`, `/health/liveliness`, `/v1/models`.

### Fase 6: Virtual key riproducibile di Hermes e test di routing
- **Principio**: la chiave `hermes` NON si crea a mano dalla UI. Il valore (`sk-hermes-...`) è generato in anticipo e conservato in SOPS, ricostruibile anche ricreando il database.
- **Meccanismo**: Helm hook `post-install,post-upgrade` (Job idempotente in `extraResources`) che attende `/health/liveliness` e chiama `POST http://litellm.litellm.svc.cluster.local:4000/key/generate` con header `Authorization: Bearer $PROXY_MASTER_KEY` e payload `{"key": "$HERMES_VIRTUAL_KEY", "key_alias": "hermes", "models": ["big-chat", "big-alt", "vision", "vision-light", "embed"]}` (se l'alias esiste già, chiama `/key/update` o ignora).
- **Gestione UI**: modelli, alias e fallback solo nei `values`; la UI per consumi/log.
- **Verifica**: ricreando il Job la chiave resta valida; test di routing su `big-chat` (Mac acceso → Mac; Mac spento → `lxc-ollama` senza timeout ripetuti), `big-alt`, `vision`, `vision-light`, `embed` (solo `lxc-ollama`).

### Fase 7: Integrazione Hermes (esclusivamente su LiteLLM, rimozione DeepSeek)
- **Stato rilevato**: Hermes è deployato via Kustomize `helmCharts` (`hermes-agent/kustomization.yaml`, chart `jyje/hermes-agent-helm` 1.0.0, release `hermes`, ns `hermes`) con `hermes-agent/values.yaml`; segreti dal Secret `hermes-secrets` (SOPS). L'initContainer `seed-config` ha `bootstrap.overwrite: true` e copia la ConfigMap in `/opt/data/config.yaml` ad ogni avvio.
- **Modifica a `hermes-agent/values.yaml`**:
  ```yaml
  config:
    providers:
      litellm:
        base_url: http://litellm.litellm.svc.cluster.local:4000/v1
        key_env: LITELLM_API_KEY
        discover_models: true
    model:
      provider: litellm
      default: big-chat
    terminal:
      backend: local
  ```
- **Applicazione e rollout**:
  ```bash
  kustomize build --enable-helm hermes-agent/ | kubectl apply -f -
  ```
- **Verifica**: rollout completato, `/opt/data/config.yaml` aggiornato nel pod, chiamata di test dall'agente.

### Fase 8: RAGFlow — nessuna modifica
- **Decisione utente**: RAGFlow resta com'è (Ollama/`mac` + DeepSeek, config nel DB `rag_flow`). Nessun intervento, nessuna virtual key `ragflow`.
- **Verifica di non regressione**: dopo ogni fase che tocca i modelli del Mac, controllare che `bge-m3:latest` e `gpt-4o:latest` siano ancora presenti e che un retrieval su una knowledge base esistente funzioni.
- Fuori scope (segnalato): `qwen2.5vl:32b` registrato in RAGFlow ma assente sul Mac.

### Fase 8b: Voci Homepage per la console di gestione LiteLLM
> [!IMPORTANT]
> Obbligatorio attivare e seguire la skill `.agents/skills/homepage-manager/` (allineamento simmetrico, verifica icone a 7 livelli, fallback MDI, rollout K8s).

- **Target**: `homepage/homepage.yaml` e `homepage/homepage-local.yaml` (le due istanze K8s). **Esclusa** l'istanza Homepage di TrueNAS.
- **Voce**: servizio "LiteLLM" con link alla console (`https://litellm-internal.pindaroli.org/ui`), simmetrica nelle due pagine.
- **Verifica**: raggiungibilità dell'icona, rollout K8s completato, voce visibile e link funzionante su entrambe le istanze.

### Fase 9: Documentazione e sync wiki
- Entità wiki (inclusa la nota sull'eccezione GitOps di RAGFlow), `todo.md`, aggiornamento `GEMINI.md`.
- `python3 scripts/network/validate_network.py && python3 scripts/wiki/build_wiki_context.py`.

### Fase 10: Rimozione `qwen2.5:72b-instruct-q4_K_M` dal Mac Studio
> [!CAUTION]
> Operazione irreversibile (47,4 GB da riscaricare). Eseguire solo a deploy completato e validato, con conferma esplicita dell'utente sul comando.

- **Precondizioni**: Fasi precedenti verificate; nessun client usa il modello (nessuna route LiteLLM, nessun consumer attivo, non presente in RAGFlow).
- **Pre-check**: confermare presenza e dimensione con `/api/tags` su `10.10.20.100:11434`.
- **Comando** (dopo approvazione):
  ```bash
  curl -s -X DELETE http://10.10.20.100:11434/api/delete -d '{"model":"qwen2.5:72b-instruct-q4_K_M"}'
  ```
- **Verifica**: `/api/tags` non elenca più il modello; spazio disco liberato ~47,4 GB.

### Fase 11 (ultima): Rimozione dei tag `deepseek-r1:32b` e `gpt-4o-mini:latest` dal Mac Studio
> [!CAUTION]
> Operazione irreversibile sui tag. **NON libera spazio**: il blob sottostante (digest `edba8017…`, 19,9 GB) resta referenziato da `gpt-4o:latest` (necessario a RAGFlow).

- **Cosa NON si cancella**: `gpt-4o:latest` (in uso da RAGFlow) e `bge-m3:latest` (embedding RAGFlow).
- **Precondizioni**: Fasi 1–10 verificate; nessun client usa `deepseek-r1:32b` o `gpt-4o-mini:latest` (Hermes migrato a LiteLLM, n8n, MCP, benchmark); conferma esplicita dell'utente per ciascun comando.
- **Comandi** (uno alla volta, dopo approvazione):
  ```bash
  curl -s -X DELETE http://10.10.20.100:11434/api/delete -d '{"model":"deepseek-r1:32b"}'
  ```
  ```bash
  curl -s -X DELETE http://10.10.20.100:11434/api/delete -d '{"model":"gpt-4o-mini:latest"}'
  ```
- **Verifica**: `/api/tags` non elenca più `deepseek-r1:32b` né `gpt-4o-mini:latest`; `gpt-4o:latest` e `bge-m3:latest` ancora presenti; retrieval RAGFlow funzionante.

---

## 💾 Stato di Ripristino (AI Save-State)
- **Fase Attiva**: Piano Completato con Successo ✅
- **Ultima Azione Completata**: Fasi 10 & 11 completate: rimozione di `qwen2.5:72b-instruct-q4_K_M` (~44 GB liberati su Mac Studio) e rimozione dei tag obsoleti `deepseek-r1:32b` e `gpt-4o-mini:latest`. Verifica non-regressione di `gpt-4o:latest` (PONG) e `bge-m3:latest` (dimensione 1024) su Ollama Mac Studio con esito positivo.
- **Prossimo Passo Operativo**: Nessuno, piano concluso e archiviato.
- **Blocchi/Decisioni Pendenti**: Nessuno.

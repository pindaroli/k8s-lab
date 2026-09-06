# Regole di Progetto (Workspace Rules)

- **Priorità Homebrew (brew)**: Prima di installare o compilare qualsiasi pacchetto o tool software scaricandolo direttamente (es. tramite script `curl`, pacchetti tar.gz o compilazione manuale), l'agente deve verificare preventivamente se tale pacchetto è disponibile tramite il gestore di pacchetti **Homebrew** (`brew`). Se disponibile, l'installazione deve essere eseguita nativamente tramite `brew`.

- **Protocollo di Verifica Test-Driven (Rif: wiki/SCHEMA.md#12)**: Ogni singolo comando di modifica (es. modifiche file, script, comandi ZFS, kubectl, Ansible) deve essere obbligatoriamente seguito da un'operazione di verifica reale (es. ispezione di stato, query, curl, log audit, test di porta) per validare e dimostrare l'esito positivo prima di procedere. È vietato passare all'azione successiva se il test del passo corrente non ha avuto esito positivo al 100%.

- **Obbligo di Validazione e Rigenerazione (Rif: wiki/SCHEMA.md#13)**: Ogni volta che l'agente modifica la configurazione del network o lavora sulla wiki, è obbligatorio eseguire lo script di validazione e poi lo script di rigenerazione al termine della sessione prima di effettuare il commit:
  `python3 scripts/network/validate_network.py && python3 scripts/wiki/build_wiki_context.py`

- **Sezione Save-State nei Piani (Rif: wiki/SCHEMA.md#11)**: Ogni piano operativo in corso di redazione o esecuzione deve terminare con la sezione strutturata per la ripresa della sessione:
  ```markdown
  ## 💾 Stato di Ripristino (AI Save-State)
  - **Fase Attiva**: [Fase X / Nome Fase]
  - **Ultima Azione Completata**: [Descrizione sintetica del comando/azione eseguita con successo]
  - **Prossimo Passo Operativo**: [Comando esatto o modifica da fare successivamente]
  - **Blocchi/Decisioni Pendenti**: [Attesa via libera, info mancanti o discussioni aperte]
- **Obbligo di Rollout Automatico Homepage**: Ogni volta che viene modificata la configurazione della dashboard Homepage (in `homepage/homepage.yaml` o `homepage/homepage-local.yaml`), è **obbligatorio** ed automatico eseguire immediatamente l'apply dei manifesti ed il rollout restart dei deployment nel namespace `default`:
  `kubectl apply -f homepage/homepage.yaml && kubectl apply -f homepage/homepage-local.yaml && kubectl rollout restart deployment/homepage deployment/homepage-local -n default`

- **Gestione Switch Extreme via Ansible (Ansible Mandate)**: Per lo switch Extreme Networks, i comandi CLI/SSH di sola lettura (es. `show vlan`, `show configuration`, ispezioni di stato) sono liberamente consentiti per la diagnostica. Qualsiasi operazione di modifica della configurazione DEVE essere obbligatoriamente automatizzata tramite Playbook Ansible permanenti salvati nel repository.

- **Mandato Autenticazione Passwordless SSH**: È vietato l'uso di password hardcoded o trasmesse in qualsiasi script Python, script Shell (`.sh`) o playbook Ansible. Tutte le connessioni automatizzate DEVONO basarsi sull'autenticazione a chiavi SSH (`ssh -o BatchMode=yes`).

- **Mandato Gestione Server MCP (mcp_config.json)**: Ogni volta che l'utente richiede di installare o configurare un nuovo server MCP, la configurazione **DEVE essere eseguita tassativamente in modo centralizzato all'interno di `~/.gemini/antigravity/mcp_config.json`**, evitando l'uso di plugin o directory nascoste. Eventuali script Python, monkeypatch o wrapper personalizzati devono essere salvati nella repository in `scripts/<mcp-name>/`. L'AI deve segnalare all'utente esclusivamente eventuali impedimenti tecnici oggettivi che impediscano questo approccio centralizzato.

- **Policy Port-Forward (Solo Debug)**: Il comando `kubectl port-forward` è consentito ESCLUSIVAMENTE per attività temporanee di debug e diagnostica estemporanea. È tassativamente proibito utilizzarlo o proporlo come soluzione definitiva, architetturale o workaround permanente per collegare carichi di lavoro o server MCP. Qualsiasi accesso stabile deve avvenire tramite Ingress/IngressRoute o K8s DNS.

- **ANTI-LOOSE-YAML GUARD (Strict Helm-First Mandate)**: It is strictly forbidden to create, propose, or execute standalone/loose `.yaml` manifest files in arbitrary directories (e.g. `mcp-servers/`, `manifests/`, or ad-hoc Ingress/Service/Deployment files) via manual `kubectl apply -f`. Every workload, service, and routing entity MUST be managed by a Helm release via an upstream registry chart or a Project Chart located in `helm-charts/<app-name>/`. All configuration changes MUST be expressed strictly through declarative value overrides in `<app-name>/<app-name>-values.yaml` and parameterized Helm templates in `helm-charts/<app-name>/templates/`. If an AI agent contemplates writing a standalone YAML file for Kubernetes: **STOP IMMEDIATELY**. Locate or create the corresponding Helm Project Chart and extend its values and templates instead.

- **RAGFlow Knowledge Base Policy (`opnsense`, `truenas`, `k8s-lab` Datasets)**:
  - **Scope & Purpose**: The RAGFlow knowledge bases (`https://ragflow-internal.pindaroli.org`) are the authoritative source for homelab technical and hardware documentation:
    1. **`opnsense`**: Official OPNsense 26.1 ("Witty Woodpecker") documentation (firewall rules, NAT, policy routing, Kea DHCP, Unbound DNS, WireGuard, MVC APIs, plugins).
    2. **`truenas`**: Official TrueNAS SCALE 25.10 documentation (ZFS storage pools, datasets, quotas, NFS/SMB shares & ACL permissions, replication tasks, snapshot retention).
    3. **`k8s-lab`**: Homelab physical hardware documentation (vendor manuals, component datasheets, motherboard pinouts, PCIe bifurcation, Extreme switch port matrices, BIOS/UEFI/IPMI settings, UPS/NUT power specs).
  - **Intelligent Trigger Conditions (MUST query RAGFlow via `ragflow_retrieval_by_name`)**:
    1. **OPNsense Procedures & Parameters**: Queries regarding firewall rules, routing policies, NAT rules, VPN tunnels, or Unbound/Kea settings.
    2. **TrueNAS Procedures & Storage Best Practices**: Queries regarding recommended ZFS dataset properties (recordsize, sync), NFS/SMB permission schemes, or replication setups.
    3. **Hardware Specifications & Datasheets**: Queries regarding physical component specs, power consumption, connector types, jumper settings, or hardware limits.
    4. **Vendor Model Inquiries & Fallback**: Whenever the user references specific hardware or OS features and local repository files (`rete.json`, `storage.json`, `wiki/`) lack detailed technical manuals or official vendor guidelines.
  - **Strict Exclusions (Do NOT query RAGFlow)**:
    - **Live Infrastructure Operations**: Real-time pod status, service health, live ZFS pool states (`zpool status`), Talos cluster events, or OPNsense active firewall states -> Query live system tools directly (`opnsense` MCP, `truenas-master-mcp`, `talos` MCP, `kubernetes` MCP).
    - **Git Workspace Code & Configs**: Helm values (`arr-values.yaml`), Kubernetes manifests, Ansible playbooks, and GitOps logic -> Inspect local repository files.
    - **General Programming / Syntax**: Standard Python, YAML, or bash syntax questions.
  - **Citation Protocol**: Whenever answering based on RAGFlow retrieval, the agent MUST explicitly cite the source document name, the target RAGFlow dataset (`opnsense`, `truenas`, or `k8s-lab`), and the specific section or page referenced.





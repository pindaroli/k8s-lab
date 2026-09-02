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




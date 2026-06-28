# Project GEMINI: Kubernetes Homelab Migration

> [!IMPORTANT]
> **Current Status**: **DNS EXPLICIT MAPPING OPERATIONAL**
> 0.0.0.0 "Black Hole" records removed from Cloudflare; All internal services exclusively managed via OPNsense.
> **Active Goal**: Ingress & External Access (Phase 5).

### 1. Quick Reference & Entry Point
Benvenuti nel Progetto GEMINI. Questa repository utilizza il paradigma **Wiki LLM** per la gestione della conoscenza.

### 🗺️ Mappe Concettuali (Wiki)
- **Governance**: [[purpose]] (Principi Core), [[SCHEMA]] (Regole del Wiki).
- **Infrastruttura**: [[OPNsense]], [[Talos_Cluster]], [[TrueNAS]], [[Traefik]], [[OAuth2_Proxy]].
- **Monitoraggio**: [[Monitoring]], [[Homepage]].
- **Workloads**: [[Servarr]], [[Tdarr]], [[Xray]].
- **Data & Registry**: [[Network_Registry]], [[Storage_Registry]], [[Secret_Registry]].
- **Procedure**: [[Power_Sequence]] (Shutdown/Startup), [[Certificate_Renewal]].
- **Piani**: [[sops-secret-sovereignty]] (Migrazione SOPS + Age), [[recyclarr-anti-spam-automation]] (Automazione Anti-Spam), [[beets-music-rescue-pipeline]] (Bonifica Libreria Musicale), [[dual-pipeline-gitops-integration]] (Integrazione GitOps Duale Classica), [[album-directory-standardization]] (Standardizzazione Cartelle Album), [[plan-out-of-band-service-access]] (Accesso Fisico OOB), [[pve3-10g-migration-recovery]] (Migrazione 10G PVE3 & Ripristino), [[oob-hardening-validation]] (Validazione e Hardening OOB), [[pve1-upgrade-ve9.2]] (Upgrade PVE1 e Spegnimento Safe), [[pve1-hostname-rename]] (Rinomina Hostname PVE1: pve → pve1), [[opnsense-recovery-and-temporary-routing]] (Ripristino OPNsense & Rete Temporanea), [[special-vdev-optimization]] (Ottimizzazione Special VDEV oliraid: 1M → 64K), [[oliraid-expansion-special-vdev-evacuation]] (Espansione oliraid e Evacuazione Special VDEV), [[kubernetes-mcp-server-and-kubeconfig-migration]] (Configurazione Kubernetes MCP & Migrazione Kubeconfig), [[truenas-master-mcp-integration]] (Installazione TrueNAS Master MCP).
- **Incidenti**: [[2026-05-03-dns-split-horizon-conflict]], [[2026-05-03-dnsbl-filtering-failure]], [[2026-05-06-google-oauth2-credential-leak]], [[2026-05-08-qbittorrent-port-forward-outage]], [[2026-05-16-dnsbl-automation-payload-mismatch]], [[2026-06-02-pve3-kernel-hang-nomodeset]], [[2026-06-03-flannel-restart-dns-cascading-failure]], [[2026-06-20-dhcp-relay-outage-symmetric-routing]], [[2026-06-24-special-mirror-degraded-replaced-disk]], [[2026-06-28-mcp-server-connection-failures-and-github-token-expiry]], [[2026-06-28-talos-cluster-quorum-loss-down]], [[2026-06-28-zshrc-kubeconfig-talosconfig-paths-update]].

- **Grafi**: [Core Wiki k8s-lab](obsidian://graph?vault=k8s-lab&filter=path:wiki)


---

## 2. Status & Active Goals
- **Current Status**: **RECYCLARR AUTOMATION OPERATIONAL** (Anti-spam synced).
- **Active Goal**: Ingress & External Access (Phase 5).
- **PVE2 Status**: **ONLINE**
- **Storage Maintenance**: Piano [[oliraid-expansion-special-vdev-evacuation]] COMPLETATO CON SUCCESSO ✅ — (Capacità espansa a 5 dischi e Special VDEV evacuato al 16% ✅).

---

## 3. Security & Operational Policies (The Golden Rules)
> [!CRITICAL]
> **EXTERNAL ACCESS**: TUTTI i servizi esposti via Cloudflare **DEVONO** avere OAuth2 abilitato.
> **INTERNAL ACCESS**: I servizi `-internal.pindaroli.org` sono considerati fidati (No OAuth2).
> **INFRASTRUCTURE**: Ogni modifica deve essere **DICHIARATIVA** (Helm/Talos). Vietati i `kubectl patch` manuali.
> **SECRETS SYNC**: Quando si modifica un segreto in `k8s-lab/secrets-sops/`, è obbligatorio verificare la compatibilità con le chart in `pindaroli-arr-helm` e aggiornare la documentazione DevOps in `wiki/procedures/`.
> **HELM DEPLOYMENT**: È tassativamente proibito installare chart da cartelle locali. Ogni deploy deve passare dal repository ufficiale (Helm Repo) per garantire la coerenza GitOps e la tracciabilità delle versioni, a meno di casi eccezionali esplicitamente approvati.
> **ADDRESSING**: Usare sempre **VIP (Identità Logica)** per Ingress/Accesso Esterno; usare sempre **K8s DNS** per traffico interno. Mai usare IP fisici o hardcoded.
> **EXECUTION PROTOCOL (TEST-DRIVEN)**: Durante l'esecuzione di un piano, per ogni singolo comando/azione: 1. Spiegare COSA sto facendo e PERCHÉ. 2. Aspettare approvazione esplicita. 3. Eseguire ed effettuare OBBLIGATORIAMENTE un test di verifica reale (ispezione di stato, test di connettività, dry-run, log audit) per validare e dimostrare l'esito positivo del comando prima di procedere. 4. Aspettare autorizzazione esplicita per il passo successivo. Senza eccezioni.
> **PLANNING vs EXECUTION**: L'AI deve limitarsi esclusivamente alla documentazione e alla pianificazione. È TASSATIVAMENTE VIETATO eseguire comandi operativi (es. kill, mv, cp, rm) o manipolare processi durante la fase di stesura o aggiornamento di un piano, a meno di autorizzazione esplicita al comando singolo. L'AI non deve mai assumere che un "vai" durante il planning sia un'autorizzazione a eseguire codice o fermare processi.
> **PLANNING**: È tassativamente proibito pianificare o eseguire azioni basate su assunzioni non verificate. Ogni azione deve essere preceduta da una fase di raccolta dati e analisi che ne confermi la necessità.
> **MASS DATA MODIFICATION (ANTI-DISASTER)**: È PERENTORIAMENTE VIETATO eseguire comandi di modifica massiva (es. `beet modify`, `sed`, `find -exec rm`) usando query lasche o basate su testo libero. Prima di OGNI modifica di massa, l'agente DEVE obbligatoriamente eseguire un "dry-run" o un comando di query/listing (es. `beet ls`) per validare il perimetro ESATTO d'azione. Qualsiasi bulk edit non testato preventivamente sul set di dati è una violazione gravissima dei protocolli di sicurezza.
> **NO UNAUTHORIZED EXTERNAL LIBRARY MODIFICATIONS**: È tassativamente proibito all'AI modificare o alterare il codice di librerie esterne o pacchetti installati nel sistema (es. in `.local/pipx/` o in `/usr/`), A MENO CHE l'utente non lo richieda o lo autorizzi espressamente per risolvere bug bloccanti. Qualsiasi altra modifica o fix deve essere implementato esclusivamente all'interno del repository del progetto.
> **COMMAND DELIVERY**: Fornisci sempre i comandi da eseguire all'utente in blocchi di codice (markdown) separati e singolarmente copiabili, comando per comando. Non raggruppare mai comandi multipli nello stesso blocco per facilitare il copia-incolla ed evitare disastri.

## Future Integrations (n8n & Prefect)
### [ ] Transizione a Metodo B (Helm Secrets)
- [ ] Valutare il passaggio dal Metodo A (Apply manuale) al Metodo B (Integrazione atomica Helm + SOPS) per migliorare la coerenza GitOps.
- [ ] Richiede installazione plugin `helm-secrets` in tutti gli ambienti CI/CD.

### [ ] Migrazione Database n8n su postgres-main

---

## 4. Operational Cheatsheet
- **Talos Config**: `export TALOSCONFIG=talos-config/talosconfig`
- **Kube Config**: `export KUBECONFIG=~/.kube/config` (ereditato per impostazione predefinita)
- **Dashboard**: `talosctl dashboard`
- **Backup Manuale**: `velero backup create backup-pre-change-$(date +%F) --wait`

---

## 5. Reference Files
- **Network Source of Truth**: [rete.json](file:///Users/olindo/prj/k8s-lab/rete.json)
- **Ansible Inventory**: `ansible/inventory.ini`
- **Task List**: [todo.md](file:///Users/olindo/prj/k8s-lab/todo.md)

---
## 6. AI Agent Protocol (Wiki-First Architecture)
Per garantire la coerenza della conoscenza e la tracciabilità delle azioni:
1.  **Planning**: Ogni nuovo obiettivo complesso deve essere prima documentato in un piano dedicato in `wiki/plans/[[nome-piano]]`.
2.  **Todo Sync**: I task in `todo.md` devono essere sincronizzati con il Wiki, utilizzando i wikilink `[[nome-piano]]` per ogni riferimento.
3.  **Materialization**: L'agente deve "materializzare" i piani e i manifesti nel repository prima di procedere all'esecuzione.
4.  **Knowledge Persistence**: I risultati delle operazioni devono essere consolidati nelle entità del Wiki (`wiki/entities/`) per mantenere il contesto tra sessioni diverse.

---

## 7. LLM Wiki Schema — Gemini Compiler (Plans & Incidents Edition)
Operi come l'Agente Compilatore per la gestione di piani aziendali e incidenti storici. Devi evitare rigorosamente l'inquinamento del contesto temporale.

<routing_rules>
1. QUERY SULLO STATO CORRENTE (es. "Qual è il piano attivo?", "Ci sono incidenti?"):
   - Cerca esclusivamente nelle directory `wiki/plans/` e `wiki/incidents/`.
   - Filtra i file prendendo SOLO quelli con `status: active` e `certified_for_ai: true`.
   - Ignora totalmente i file con `status: archived` o `certified_for_ai: false`.

2. QUERY DI AUDIT O STORICHE (es. "Che problemi abbiamo avuto sul DB il mese scorso?", "Cosa prevedeva il vecchio piano?"):
   - Sei autorizzato a leggere i file con `status: archived` o `certified_for_ai: false`.
   - Quando rispondi usando file archiviati, inizia la risposta con questo avviso:
     > [!NOTE]
     > Questa informazione fa riferimento a un piano/incidente passato e archiviato: [[nome-file]].
</routing_rules>

<ingest_workflow_plans>
Quando viene inserito un nuovo piano (es. "Piano Q2 2026"):
1. Identifica il piano precedente nella cartella `wiki/plans/`.
2. Aggiorna il frontmatter del vecchio piano:
   - Imposta `status: archived`
   - Imposta `certified_for_ai: false`
   - Aggiungi `superseded_by: [[nuovo-piano]]`
3. Crea il nuovo piano in `wiki/plans/` con `status: active` e `certified_for_ai: true`.
4. Rimuovi i link al vecchio piano da `wiki/index.md` (o `GEMINI.md`) e inserisci il link al nuovo piano.
</ingest_workflow_plans>

<ingest_workflow_incidents>
Quando viene registrato o chiuso un incidente:
1. Se l'incidente è in corso (ongoing):
   - Crea il file in `wiki/incidents/` con `status: active` e `certified_for_ai: true`.
2. Quando l'incidente viene risolto:
   - Modifica il file dell'incidente impostando `status: archived` e `certified_for_ai: false`.
   - Popola i campi `resolved: true` e `resolved_at: [timestamp]`.
</ingest_workflow_incidents>

---
> [!NOTE]
> Per una visione completa dell'infrastruttura, aprire questa cartella in **Obsidian** e attivare la **Graph View** filtrando per `path:wiki`.

   ```

> **EXECUTION PROTOCOL (HARD ENFORCEMENT)**: È assolutamente vietato eseguire comandi di modifica (bash, replace_file_content) senza aver prima concluso il messaggio precedente con la stringa esatta: **go**. Nessuna eccezione, nemmeno per emergenze o per fermare script in corso.

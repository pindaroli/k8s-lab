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
- **Piani**: [[sops-secret-sovereignty]] (Migrazione SOPS + Age), [[recyclarr-anti-spam-automation]] (Automazione Anti-Spam), [[beets-music-rescue-pipeline]] (Bonifica Libreria Musicale).
- **Incidenti**: [[2026-05-03-dns-split-horizon-conflict]], [[2026-05-03-dnsbl-filtering-failure]], [[2026-05-06-google-oauth2-credential-leak]], [[2026-05-08-qbittorrent-port-forward-outage]].

- **Grafi**: [Core Wiki k8s-lab](obsidian://graph?vault=k8s-lab&filter=path:wiki)


---

## 2. Status & Active Goals
- **Current Status**: **RECYCLARR AUTOMATION OPERATIONAL** (Anti-spam synced).
- **Active Goal**: Ingress & External Access (Phase 5).
- **PVE2 Status**: **OFFLINE** (Hardware Pending) - `postgres-main-2` is currently fenced.

---

## 3. Security & Operational Policies (The Golden Rules)
> [!CRITICAL]
> **EXTERNAL ACCESS**: TUTTI i servizi esposti via Cloudflare **DEVONO** avere OAuth2 abilitato.
> **INTERNAL ACCESS**: I servizi `-internal.pindaroli.org` sono considerati fidati (No OAuth2).
> **INFRASTRUCTURE**: Ogni modifica deve essere **DICHIARATIVA** (Helm/Talos). Vietati i `kubectl patch` manuali.
> **SECRETS SYNC**: Quando si modifica un segreto in `k8s-lab/secrets-sops/`, è obbligatorio verificare la compatibilità con le chart in `pindaroli-arr-helm` e aggiornare la documentazione DevOps in `wiki/procedures/`.
> **HELM DEPLOYMENT**: È tassativamente proibito installare chart da cartelle locali. Ogni deploy deve passare dal repository ufficiale (Helm Repo) per garantire la coerenza GitOps e la tracciabilità delle versioni, a meno di casi eccezionali esplicitamente approvati.
> **ADDRESSING**: Usare sempre **VIP (Identità Logica)** per Ingress/Accesso Esterno; usare sempre **K8s DNS** per traffico interno. Mai usare IP fisici o hardcoded.
> **EXECUTION PROTOCOL**: Durante l'esecuzione di un piano, per ogni singolo comando/azione: 1. Spiegare COSA sto facendo e PERCHÉ. 2. Aspettare approvazione esplicita. 3. Eseguire e testare il risultato. 4. Aspettare autorizzazione esplicita per il passo successivo. Senza eccezioni.
> **PLANNING vs EXECUTION**: L'AI deve limitarsi esclusivamente alla documentazione e alla pianificazione. È TASSATIVAMENTE VIETATO eseguire comandi operativi (es. kill, mv, cp, rm) o manipolare processi durante la fase di stesura o aggiornamento di un piano, a meno di autorizzazione esplicita al comando singolo. L'AI non deve mai assumere che un "vai" durante il planning sia un'autorizzazione a eseguire codice o fermare processi.
> **PLANNING**: È tassativamente proibito pianificare o eseguire azioni basate su assunzioni non verificate. Ogni azione deve essere preceduta da una fase di raccolta dati e analisi che ne confermi la necessità.
> **MASS DATA MODIFICATION (ANTI-DISASTER)**: È PERENTORIAMENTE VIETATO eseguire comandi di modifica massiva (es. `beet modify`, `sed`, `find -exec rm`) usando query lasche o basate su testo libero. Prima di OGNI modifica di massa, l'agente DEVE obbligatoriamente eseguire un "dry-run" o un comando di query/listing (es. `beet ls`) per validare il perimetro ESATTO d'azione. Qualsiasi bulk edit non testato preventivamente sul set di dati è una violazione gravissima dei protocolli di sicurezza.

## Future Integrations (n8n & Prefect)
### [ ] Transizione a Metodo B (Helm Secrets)
- [ ] Valutare il passaggio dal Metodo A (Apply manuale) al Metodo B (Integrazione atomica Helm + SOPS) per migliorare la coerenza GitOps.
- [ ] Richiede installazione plugin `helm-secrets` in tutti gli ambienti CI/CD.

### [ ] Migrazione Database n8n su postgres-main

---

## 4. Operational Cheatsheet
- **Talos Config**: `export TALOSCONFIG=talos-config/talosconfig`
- **Kube Config**: `export KUBECONFIG=talos-config/kubeconfig`
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
> [!NOTE]
> Per una visione completa dell'infrastruttura, aprire questa cartella in **Obsidian** e attivare la **Graph View** filtrando per `path:wiki`.

   ```

> **EXECUTION PROTOCOL (HARD ENFORCEMENT)**: È assolutamente vietato eseguire comandi di modifica (bash, replace_file_content) senza aver prima concluso il messaggio precedente con la stringa esatta: **[ATTENDO AUTORIZZAZIONE]**. Nessuna eccezione, nemmeno per emergenze o per fermare script in corso.

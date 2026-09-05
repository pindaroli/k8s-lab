# GEMINI LLM Wiki: Governance Schema

Questo documento definisce le regole strutturali che l'agente (IA) e l'utente devono rispettare per mantenere l'integrità del Wiki.

## 1. Frontmatter Obbligatorio (YAML)
Ogni file all'interno di `wiki/entities/` e `wiki/workflows/` **DEVE** iniziare con il seguente blocco YAML:

```yaml
---
title: "Nome dell'Entità o Evento"
last_updated: "YYYY-MM-DD"
confidence: "High|Medium|Low" # Livello di affidabilità dell'informazione
tags:
  - "#tag1"
  - "#tag2"
provenance: # Riferimenti ai file RAW o incidenti originali
  - "nomefile_raw.md"
---
```

### Piani (`wiki/plans/`)
Ogni piano **DEVE** includere il seguente frontmatter YAML strutturato:
```yaml
---
title: "Nome del Piano"
type: plan
status: active | archived | draft          # active: in vigore; archived: concluso/superato; draft: in fase di stesura
certified_for_ai: true | false           # true solo se active o draft pronto all'uso
created_at: YYYY-MM-DD
archived_at: YYYY-MM-DD                  # Presente solo se status è archived
superseded_by: [[nome-piano-successivo]]  # Link al piano che sostituisce il corrente (opzionale)
tags:
  - "#tag1"
---
```

### Incidenti (`wiki/incidents/`)
Ogni incidente **DEVE** includere il seguente frontmatter YAML strutturato:
```yaml
---
title: "INC-YYYY-MM-DD: Descrizione"
type: incident
status: active | archived                # active: in corso (ongoing); archived: risolto e chiuso
certified_for_ai: true | false           # true solo se status è active
date: YYYY-MM-DD
severity: P1 | P2 | P3 | P4
resolved: true | false
resolved_at: YYYY-MM-DDTHH:MM:SSZ        # Timestamp ISO (se risolto)
post_mortem: [[post-mortem-file]]        # Link all'analisi dell'incidente o post-mortem (opzionale)
tags:
  - "#tag1"
---
```

### Pattern Architetturali (`wiki/patterns/`)
Ogni pattern architetturale definisce una soluzione standardizzata, riutilizzabile e canonica adottata nel lab.
Ogni pattern **DEVE** includere il seguente frontmatter YAML strutturato:
```yaml
---
title: "Nome Descrittivo del Pattern"
type: pattern
status: active | deprecated | draft          # active: in uso nel lab; deprecated: superato; draft: in studio
certified_for_ai: true | false              # true solo se active e pronto all'uso
created_at: YYYY-MM-DD
last_updated: YYYY-MM-DD
superseded_by: [[nuovo-pattern]]            # Link al pattern successore (opzionale se deprecated)
in_use_by:                                  # Mappa dei progetti e directory dove il pattern è applicato
  - project: "k8s-lab"
    paths:
      - "helm-charts/mcp-gateway"
tags:
  - "#pattern"
---
```

<routing_rules_patterns>
1. CONSULTAZIONE E PROPOSTA ALL'UTENTE (Pattern Consultation & Proactive Suggestion):
   - Prima di proporre, progettare o implementare soluzioni architetturali (es. nuovi server MCP, storage NFS, segreti, routing), l'AI DEVE verificare la presenza di pattern in `wiki/patterns/` aventi `status: active` e `certified_for_ai: true`.
   - Se esiste un pattern attivo pertinente all'ambito di intervento, l'AI DEVE **proporlo esplicitamente all'utente**, evidenziandone motivazioni, vantaggi e coerenza con il resto del lab, e **attendere le istruzioni/approvazione dell'utente prima di procedere all'adozione**.
   - I pattern con `status: deprecated` o `certified_for_ai: false` non devono essere proposti per nuovi workload a meno di esplicite richieste di audit o analisi retrospettiva.

2. TRACCIABILITÀ DELL'USO (`in_use_by` Sync):
   - Una volta che l'utente approva l'adozione del pattern su un nuovo carico di lavoro, directory o repository, l'AI DEVE aggiornare l'elenco `in_use_by` nel frontmatter YAML del pattern corrispondente.
</routing_rules_patterns>


## 2. Sintassi di Collegamento (Wikilinks)
- Utilizzare sempre i doppi bracket per collegare le entità: `[[NomeEntita]]`.
- Non utilizzare link Markdown standard per file interni (es. `[testo](file.md)`), ma usare i wikilinks per mantenere la compatibilità con la Graph View di Obsidian.

## 3. Principio di Non-Distruzione (Tensione Dialettica)
- **Mantenimento**: Ogni volta che un'entità cambia (nuovo IP, nuova policy), aggiorna il file corrispondente.

## 4. Cosa NON includere nel Wiki
> [!CAUTION]
> **NO TRANSIENT DATA**: Non inserire nel Wiki dump temporanei, log grezzi o liste di record DNS (es. `pindaroli.org.txt`).
> Il Wiki deve contenere solo **conoscenza curata, universale e strutturata**. I dati transienti devono restare nella root o in cartelle di log/audit dedicate, per non "sporcare" la base di conoscenza degli agenti.

Se nuove informazioni contraddicono il contenuto esistente:
1. NON sovrascrivere o eliminare il vecchio blocco se non si è assolutamente certi che fosse errato.
2. Creare una sezione `## Evoluzione / Tensioni Note`.
3. Annotare: *"Precedentemente configurato in modo X, modificato in modo Y per risolvere il problema Z (Vedi [[Incidente_XYZ]])"*.

## 5. Tassonomia dei Tag
Usare i seguenti tag per standardizzare la ricerca:
- Livello: `#core`, `#app`, `#network`, `#storage`
- Stato: `#active`, `#deprecated`, `#pending_hardware`
- Piattaforma: `#opnsense`, `#talos`, `#truenas`, `#proxmox`
## 6. Infrastructure as Code (IaC) - Implementation
In attuazione alla regola in [[GEMINI]], ogni modifica segue questo protocollo tecnico:

1.  **HELM First**: Ogni modifica alla configurazione delle applicazioni (IP, variabili d'ambiente, volumi) deve essere effettuata aggiornando il corrispondente file `values.yaml` e lanciando un `helm upgrade`.
2.  **Talos Configs**: Utilizzare i file specifici `talos-config/controlplane-cp-XX.yaml` e `talosctl apply-config`.
3.  **Sincronizzazione**: Il cluster deve essere lo specchio fedele del repository Git.

## 7. Network & DNS Standards
Per mantenere la coerenza tra l'inventario `rete.json` e la risoluzione dei nomi:

1.  **DNS Sources**: Solo i campi `id`, `hostname`, `aliases` e `name` (interfacce logiche) sono fonti valide per record DNS.
2.  **Sanitization**: Mai usare descrizioni testuali (es. "Client LAN") o nomi fisici delle interfacce (`en0`, `eth1`) come hostnames.
3.  **Consistency**: Ogni record DNS deve essere riconducibile a un'entrata esplicita in `rete.json`.

## 8. Storage & NFS Standards (TrueNAS)
Ogni export NFS destinato al cluster Kubernetes o a nodi di calcolo (es. Tdarr) deve rispettare questi requisiti:

1.  **Maproot**: Impostare `Maproot User: root`.
2.  **Security**: Abilitare l'opzione `Insecure` per permettere connessioni da porte non privilegiate.
3.  **Access Control**: Autorizzare gli IP specifici o la subnet.

## 9. Manutenzione Helm: Soft Stop vs Uninstall
Se è necessario fermare temporaneamente un'applicazione senza distruggere la release:

1.  **Soft Stop**: `kubectl scale deployment -n <namespace> --all --replicas=0`.
2.  **Ripristino**: `kubectl scale deployment -n <namespace> --all --replicas=1`.

## 10. Strategia di Indirizzamento (Tecnica)
Per garantire l'Alta Affidabilità (HA) definita in [[GEMINI]]:

1.  **Ingress/External**: Puntare i record DNS esterni (Cloudflare) o interni (OPNsense) sempre al **VIP** (es. `10.10.10.100`) o al nome host logico (es. `k1`).
2.  **Pod-to-Pod**: Usare sempre il Service Name `svc.cluster.local`. È vietato usare l'IP del VIP o l'IP fisico del nodo per la comunicazione interna tra container.
3.  **Stateful Awareness**: L'indirizzamento logico non sposta lo storage locale. La resilienza dei dati deve essere gestita a livello applicativo (replicazione DB).

## 11. Ripresa Sessione e Save-State (/resume)
Per garantire la continuità del lavoro e della conoscenza tra sessioni o contesti diversi dell'agente (LLM):

1.  **Il Comando `/resume`**: Quando l'utente inserisce `/resume [[nome-piano]]`, l'agente deve immediatamente:
    - Scansionare il piano specificato in `wiki/plans/`.
    - Leggere la sezione `## 💾 Stato di Ripristino (AI Save-State)` per riprendere il contesto esatto.
    - Controllare i relativi task pendenti in `todo.md`.
    - Proporre la sintesi dello stato e l'azione immediata successiva.
2.  **La sezione "Save-State"**: Ogni piano in corso di elaborazione o esecuzione **DEVE** terminare con un blocco standardizzato aggiornato dall'agente al termine di ogni turno:
    ```markdown
    ## 💾 Stato di Ripristino (AI Save-State)
    - **Fase Attiva**: [Fase X / Nome Fase]
    - **Ultima Azione Completata**: [Descrizione sintetica del comando/azione eseguita con successo]
    - **Prossimo Passo Operativo**: [Comando esatto o modifica da fare successivamente]
    - **Blocchi/Decisioni Pendenti**: [Attesa via libera, info mancanti o discussioni aperte]
    ```

## 12. Test-Driven Verification Protocol (Operational)
Per garantire la stabilità del cluster homelab ed evitare disastri derivanti da configurazioni errate, ogni piano operativo e la relativa esecuzione devono seguire un protocollo rigorosamente **Test-Driven**:

1.  **Test Ad Ogni Passo**: Ogni singolo comando di modifica (Ansible, kubectl, modifiche file, script, comandi ZFS) deve essere seguito da un'operazione di verifica esplicita (es. query SQL, log audit, test di porta, curl, df, mount inspection) per validare l'esito reale.
2.  **Documentazione nel Piano**: Ogni piano di migrazione o manutenzione in `wiki/plans/` deve includere esplicitamente i comandi di test e verifica a corredo di ciascun comando operativo, in modo che l'operatore e l'AI possano validare lo stato passo dopo passo.
3.  **No Assunzioni**: È vietato passare al comando successivo se il test del passo corrente non ha restituito esito positivo al 100%.

## 13. Wiki Context Refresh (LLM Sync Protocol)

> [!IMPORTANT]
> **OBBLIGO DI VALIDAZIONE E RIGENERAZIONE**: Ogni volta che si modifica la configurazione del network o si lavora sulla wiki, è **obbligatorio** validare la congruenza della rete ed eseguire lo script di rigenerazione del contesto **al termine della sessione**:
>
> 1. Validazione Rete:
> ```bash
> python3 scripts/validate_network.py
> ```
> 2. Rigenerazione Contesto:
> ```bash
> python3 scripts/build_wiki_context.py
> ```
>
> Lo script di validazione garantisce che non vi siano conflitti, IP/MAC duplicati o DNS non attivi/non autorizzati in `rete.json`, mentre lo script di rigenerazione produce `wiki/wiki_context.md` per l'allineamento dei modelli LLM.

**Regole operative**:
1. **Quando eseguirlo**: Dopo qualsiasi modifica a file `.md` in `wiki/`, inclusi aggiornamenti di status, nuovi piani, nuove entità o modifica di workflow.
2. **Non committare senza aggiornare**: `wiki_context.md` deve sempre essere in sync con l'ultimo stato della wiki. Se si fa `git commit` di file wiki, includere anche il `wiki_context.md` aggiornato.
3. **Piani Conclusi**: Lo script esclude automaticamente i piani con `status: "Concluso"` o `"Completato"`. Aggiornare lo status del piano nel frontmatter prima di rigenerare.
4. **Incidents**: Lo script esclude sempre la cartella `incidents/`. Non è necessario fare nulla di speciale per i nuovi incident report.
5. **File generato**: `wiki/wiki_context.md` è un file **generato automaticamente**. Non modificarlo a mano: le modifiche verranno sovrascritte alla prossima esecuzione.

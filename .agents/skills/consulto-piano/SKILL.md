---
name: consulto-piano
type: skill
description: "Prepara il materiale completo e produce il prompt strutturato per richiedere un consulto/revisione esperta su un piano architetturale o operativo (<piano>), rigenerando wiki/wiki_context.md ed estraendo tutte le nozioni contestuali in contesto.md."
when_to_use: "Quando l'utente scrive 'chiedo consulto su <piano>', 'consulto su <piano>', 'chiedi consulto sul piano <piano>' o richiede un parere/consulto tecnico specialistico su un piano architetturale o operativo del homelab."
status: active
tags:
  - architecture
  - review
  - plans
  - wiki
  - context
  - prompt-engineering
---

# Consulto Piano Skill (`consulto-piano`)

## 🗣️ Trigger Phrases Riconosciute (Pattern di Attivazione)
La skill si attiva automaticamente quando l'utente richiede una revisione o un consulto su un piano operativo/architetturale, usando espressioni come:
- `chiedo consulto su <piano>`
- `chiedo consulto sul piano <piano>`
- `consulto su <piano>`
- `consulto piano <piano>`
- `chiedi un consulto per <piano>`
- `voglio un consulto su <piano>`
- `revisione del piano <piano>`

> **Nota sui Parametri**: `<piano>` può essere specificato come:
> - Nome file con o senza estensione (es. `orbstack-failover-truenas-services`, `orbstack-failover-truenas-services.md`)
> - Sintassi wikilink (es. `[[orbstack-failover-truenas-services]]`)
> - Percorso relativo o assoluto (es. `wiki/plans/orbstack-failover-truenas-services.md`)
> - Termini di ricerca o nome parziale (lo skill effettua match per prefisso e sottostringa in `wiki/plans/`)

---

## 🎯 Obiettivo
Fornire un processo rigoroso, guidato e completo per preparare il materiale di consulto di qualsiasi piano operativo del lab per la revisione critica da parte dell'utente o di un modello esterno:
1. **Materializzazione da Sessione (se mancante)**: Se il piano non è ancora presente su disco, l'agente lo redige e lo salva in `wiki/plans/<piano>.md` sintetizzando direttamente il contesto cognitivo, i requisiti e l'architettura discussi durante la sessione.
2. **Aggiornamento dello Stato Globale**: Rigenerazione preventiva del contesto unificato `wiki/wiki_context.md` tramite lo script previsto, in modo che includa anche il nuovo piano.
3. **Cristallizzazione del Contesto Specifico**: Generazione del file `contesto.md` nella radice del progetto, contenente tutte le nozioni contestuali, nodi, IP, VLAN, storage ZFS, vincoli e Golden Rules pertinenti al piano.
4. **Produzione e Presentazione del Prompt**: Stampa a video all'utente di un prompt specialistico pronto all'uso in un blocco markdown copiabile, vincolando l'analisi ai tre file fondamentali (`wiki/plans/<piano>.md`, `contesto.md`, `wiki/wiki_context.md`).

> [!CRITICAL]
> **DIVIETO ASSOLUTO DI AVVIO AUTOMATICO SUBAGENTI (NO AUTO-SUBAGENT / NO BACKGROUND EXECUTION)**:
> L'agente **NON DEVE MAI** invocare subagenti (`invoke_subagent`), né avviare processi o task in background per svolgere autonomamente il consulto.
> Il mandato della skill termina tassativamente con la generazione dei file (`contesto.md`, `wiki_context.md`) e la stampa a schermo del prompt formattato per l'utente. Sarà esclusivamente l'utente a decidere se, quando e dove sottoporre il prompt (es. in un modello esterno, un'altra chat o un subagente manuale).

---

## ⚡ Workflow Operativo in 4 Fasi

### Fase 1: Individuazione o Materializzazione del Piano da Sessione
1. **Verifica Esistenza su Disco**:
   - L'agente verifica se esiste il file del piano all'interno di `wiki/plans/<piano>.md` (o match parziale).
2. **Caso A — Il Piano esiste già su disco**:
   - L'agente legge il file e ne estrae titolo, stato, sezioni e stack tecnologico coinvolto.
3. **Caso B — Il Piano NON esiste ancora su disco (Materializzazione da Contesto)**:
   > [!IMPORTANT]
   > Se l'utente richiede un consulto su un piano discusso o proposto durante la sessione corrente ma non ancora salvato su file, **l'agente DEVE redigere e salvare immediatamente il file `wiki/plans/<piano>.md`**.
   - Il piano creato deve seguire fedelmente lo standard architetturale del wiki (`wiki/SCHEMA.md` e `GEMINI.md`):
     - **Frontmatter YAML**:
       ```yaml
       ---
       title: "Piano: <Titolo Descrittivo del Piano>"
       type: plan
       status: active
       certified_for_ai: true
       created_at: YYYY-MM-DD
       tags:
         - "#core" # o tag pertinenti: network, storage, truenas, talos, ecc.
       ---
       ```
     - **Sezione 1**: Contesto, Obiettivo e Decisioni Architetturali concordate nella sessione.
     - **Sezione 2**: Mappa dei File da Creare o Modificare.
     - **Sezione 3**: Fasi Operative con Protocollo Test-Driven (§12) per ogni singolo comando.
     - **Sezione 4**: Piano di Rollback dettagliato.
     - **Sezione 5**: Sezione Save-State (`## 💾 Stato di Ripristino (AI Save-State)` §11).
   - L'agente notifica all'utente la creazione del piano: *"Ho materializzato il piano in `wiki/plans/<piano>.md` estraendo architettura e decisioni dal contesto della sessione corrente."*

### Fase 2: Rigenerazione Vincolante di `wiki/wiki_context.md`
Eseguire lo script di validazione e rigenerazione canonico previsto dall'architettura del repository (Rif: `wiki/SCHEMA.md#13` e `.agents/AGENTS.md`):

```bash
python3 scripts/network/validate_network.py && python3 scripts/wiki/build_wiki_context.py
```

*Verificare che l'operazione si concluda con codice 0. Poiché il piano ha `status: active` e `certified_for_ai: true`, viene automaticamente incluso nel nuovo `wiki/wiki_context.md`.*

### Fase 3: Creazione del File `contesto.md`
Generare e salvare nella radice del workspace (`/Users/olindo/prj/k8s-lab/contesto.md`) il documento strutturato che aggrega le nozioni contestuali pertinenti al piano in esame:
- **1. Scheda del Piano**: Titolo, percorso, stato, tecnologie e indice sezioni.
- **2. Nodi, IP e Rete Pertinenti**: Estrazione mirata da `rete.json` di tutti i server, hypervisor (`pve1`, `pve2`, `pve3`), TrueNAS, OPNsense, Switch, VM, LXC, VIP e VLAN coinvolti.
- **3. Storage ZFS & Share NFS Pertinenti**: Estrazione mirata da `storage.json` dei dataset, mountpoint, share NFS e reti autorizzate toccate dal piano.
- **4. Vincoli Architetturali & Golden Rules**: Estratto delle regole non negoziabili da `GEMINI.md` applicabili al caso d'uso (es. divieto IP hardcoded, NFS schema 777 `olindo:k8s`, Helm-first, OAuth2 Proxy, SSH passwordless, test-driven protocol).
- **5. Aree di Attenzione & Quesiti per il Consulto**: Identificazione di potenziali rischi di continuità di servizio, scenari limite, convergenza e idempotenza.

### Fase 4: Generazione e Presentazione del Prompt a Video (Nessun Subagente)
Formattare e presentare all'utente nella chat il prompt specialistico pronto per essere copiato.
L'agente si ferma qui: **è tassativamente proibito eseguire `invoke_subagent`**.

Il prompt deve tassativamente:
1. Definire il ruolo dell'agente revisore come **Senior Principal Systems Architect & Site Reliability Engineer**.
2. **Citare espressamente e obbligatoriamente come riferimenti di studio i tre file**:
   - `wiki/plans/<piano>.md`
   - `contesto.md`
   - `wiki/wiki_context.md`
3. Articolare i criteri di valutazione (Conformità ai vincoli, Safety & blast radius, Idempotenza, Test-Driven Verification, alternative architetturali).
4. Richiedere una struttura di risposta standardizzata:
   - Verdetto Esecutivo (`[APPROVATO]` / `[APPROVATO CON RISERVE]` / `[RESPINTO]`)
   - Criticità Bloccanti (P0 / P1)
   - Avvertenze, Race Condition & Edge Cases (P2)
   - Ottimizzazioni Proattive & Semplificazioni KISS (P3)
   - Revisione del Piano di Rollback & Test Plan
   - Domande chiarificatrici aperte per l'autore

---

## 📋 Schema del Prompt Generato per l'Agente Revisore

````markdown
Sei un **Senior Principal Systems Architect & Site Reliability Engineer** specializzato in infrastrutture ibride (Kubernetes Talos, TrueNAS SCALE ZFS, Proxmox VE, OPNsense e GitOps).
Sei incaricato di effettuare una **revisione critica, obiettiva, approfondita e costruttiva** del piano operativo homelab indicato di seguito.

---

### 📚 DOCUMENTI DI RIFERIMENTO FORNITI (Fonti di Verità Obbligatorie)
Per svolgere la revisione hai a disposizione e **DEVI CONSULTARE CONGIUNTAMENTE** questi 3 documenti:
1. **Piano Operativo in Esame**: `wiki/plans/<nome-piano>.md`  
   *(Contiene l'architettura proposta, le decisioni tecniche, la sequenza delle fasi, i comandi operativi e i test)*.
2. **Quadro Contestuale e Vincoli Specifici**: `contesto.md`  
   *(Contiene la mappatura puntuale dei nodi, IP, VLAN, storage ZFS, Golden Rules rilevanti e i quesiti critici estratti per questo piano)*.
3. **Contesto Globale Homelab**: `wiki/wiki_context.md`  
   *(Contiene lo stato globale consolidato della wiki: entità, pattern architetturali, workflow attivi, inventario completo `rete.json` e `storage.json`)*.

---

### 🎯 OBIETTIVO DEL CONSULTO
Analizzare criticamente il piano `<nome-piano>.md` (<titolo-piano>) per:
- Validarne la fattibilità tecnica reale e la congruenza con l'infrastruttura descritta in `rete.json` e `storage.json`.
- Rilevare qualsiasi violazione di policy o vincolo di governance del homelab documentati in `contesto.md` e `wiki/wiki_context.md`.
- Identificare potenziali **blind spot**, race condition, rischi di perdita dati, downtime imprevisti o single point of failure (SPOF).
- Verificare la robustezza dell'**idempotenza**, la solidità del **piano di rollback** e la granularità del **protocollo di verifica Test-Driven**.
- Proporre ottimizzazioni concrete, semplificazioni secondo il principio KISS e miglioramenti operativi prima dell'esecuzione reale.

---

### 🔍 CRITERI SPECIFICI DI VALUTAZIONE
1. **Conformità Architetturale**:
   - Rispetto dei mandati homelab (no IP hardcoded, schemi permessi NFS 777 `olindo:k8s`, Helm-first, sicurezza Ingress/OAuth2, SSH passwordless).
   - Coerenza con i ruoli dei nodi (`pve1`, `pve2`, `pve3`, `truenas` 10.10.20.50, `opnsense` 192.168.2.254, Mac Studio 10.10.20.100).
2. **Safety & Blast Radius**:
   - Rischio per dataset ZFS (`oliraid`, `stripe`), database, volumi persistenti e file `.env`.
   - Isolamento degli errori: un'anomalia in uno step compromette l'intero rack o resta confinata?
3. **Idempotenza & Transizioni di Stato**:
   - Se il piano viene rieseguito 2 volte di seguito, converge allo stato target senza duplicazioni o riavvii distruttivi?
   - Cosa accade se la procedura si interrompe a metà (stato sporco/parziale)?
4. **Verifiche Test-Driven**:
   - Ogni comando operativo di modifica (cp, rm, docker compose, zfs, curl, kubectl, uci/api) è immediatamente seguito da un test di verifica oggettivo (ispezione stato, test porta, dry-run, log audit)?
5. **Alternative e Ottimizzazioni**:
   - Esistono pattern già documentati in `wiki/wiki_context.md` che risolvono lo stesso problema in modo più lineare ed elegante?

---

### 📋 FORMATO DEL RESPONSO ATTESO
Struttura la tua perizia tecnica nelle seguenti sezioni chiare:

1. **🚦 Verdetto Esecutivo**:
   - Valutazione sintetica: `[APPROVATO]` / `[APPROVATO CON RISERVE / RACCOMANDAZIONI]` / `[RESPINTO - CRITICITÀ BLOCCANTI]`.
   - Sintesi ad alto livello (3-4 frasi) sulla qualità e affidabilità del piano.

2. **🔴 Criticità Bloccanti (P0 / P1)** *(se presenti)*:
   - Difetti architetturali gravi, incompatibilità di rete/storage, comandi distruttivi senza safety net o violazioni di Golden Rules.

3. **🟡 Avvertenze, Race Condition & Scenari Limite (P2)**:
   - Edge cases, comportamenti asincroni, timeout non gestiti, rischi di mancata convergenza.

4. **🟢 Ottimizzazioni Proattive & Semplificazioni KISS (P3)**:
   - Accorgimenti per rendere il codice/procedura più snella, manutenibile o performante.

5. **🛡️ Revisione del Piano di Rollback & dei Test di Verifica**:
   - Valutazione analitica su come annullare le modifiche in sicurezza e sulla completezza della checklist di test.

6. **❓ Domande Chiarificatrici o Punti Aperti per l'Autore**:
   - Eventuali assunzioni non specificate che richiedono conferma esplicita prima di procedere.
````

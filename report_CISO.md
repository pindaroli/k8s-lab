# Report di Valutazione di Sicurezza e Riservatezza (CISO Perspective)
**Documento di Riferimento:** *Devoteam ServiceNow Investment Strategy — Turn Pricing Pressure into Growth and Stronger Margins* (Amplify ServiceNow · ASN)  
**Struttura delle Fasi di Audit:**
* 🛡️ **Fase 1:** Sicurezza versione PC (*Consultant PC Security & Data Retention*)
* 🧠 **Fase 2:** Cattura dell'Expertise (*Capture Expertise & Tooling Maturity*)  
**Data:** 14 Settembre 2026  

---

## 1. Executive Summary

Il presente report raccoglie le perplessità di sicurezza, conformità e sovranità del dato sollevate in merito all'architettura proposta da Devoteam per la scalabilità dei servizi ServiceNow tramite l'AI (*Amplify ServiceNow - ASN*).

L'indagine è strutturata formalmente su due macro-fasi di valutazione:
1. **Fase 1 — Sicurezza versione PC:** Analisi della sostenibilità tecnica e contrattuale della variante **"Consultant PC"** dell'edizione *ASN Offline Edition*, confrontando le promesse di riservatezza contenute nelle slide strategiche con la realtà operativa della gestione degli endpoint portatili e del rischio *Insider Threat*.
2. **Fase 2 — Cattura dell'Expertise:** Verifica della reale disponibilità di strumenti software definiti e pronti per codificare l'expertise dei senior, eseguire controlli deterministici non-AI anti-allucinazione, guidare la piramide operativa e integrare client AI terzi (es. Claude Code, Cursor, Antigravity).

---

## 2. Registro Audit — Fase 1: "Sicurezza versione PC"

### Prompt 1 (Transito dati verso il motore LLM)
> *"Nel modello ASN Offline Edition, questo approccio risolve il transito dei dati verso il motore di LLM? I dati del cliente escono verso l'esterno?"*

#### Valutazione Tecnica & Risposta
L'approccio del documento affronta la questione separando nettamente due canali:

1. **Risoluzione Totale (100% Air-Gapped On-Premise):**
   * *Slide 14:* `«Airgapped: AI models hosted in the customer datacenter»`
   * Se il cliente adotta modelli open-weights (es. Mistral, Llama) ospitati su server GPU interni al proprio data center o VPC privato, **nessun dato transita su Internet**. Il ciclo tra ServiceNow, ASN/MCP e LLM avviene interamente sulla rete locale del cliente.
2. **Risoluzione Contrattuale / Perimetrale (Cloud Privato del Cliente):**
   * *Slide 12:* `«ASN routes within policy [...] Region EU · Google Vertex AI / Azure OpenAI / AWS Bedrock / Mistral»`
   * *Slide 12:* `«execute only on an approved customer gateway through ASN»`
   * Se si usano modelli di frontiera commerciali, i dati transitano direttamente dal runtime locale verso il **tenant cloud privato del cliente**, coperto dai contratti enterprise di *Zero Data Retention* e confidenzialità stipulati dal cliente stesso con il cloud provider. I dati non transitano né vengono centralizzati sui server di Devoteam.
3. **Esclusione di API Pubbliche / Gateway Centralizzati:**
   * *Slide 12:* Il gateway multimodello **OpenRouter** viene esplicitamente confinato a dati sintetici, pubblici o autorizzati per attività interne di benchmark (`«Synthetic, public or explicitly authorized data»`), e ne viene vietato l'uso su dati reali di produzione.

---

### Prompt 2 (Persistenza e uso illegittimo sul PC del consulente)
> *"Il documento parla di esecuzione sul PC locale (Consultant PC)... in questo caso, anche se in esecuzione dentro l'infrastruttura di rete del cliente, il singolo consulente non può memorizzare dati del cliente sul suo PC? Si può garantire la riservatezza contro l'uso illegittimo da parte del consulente?"*

#### Valutazione Tecnica & Risposta
**No, la versione "Consultant PC" non può tecnicamente garantire l'assoluta riservatezza contro l'uso improprio, la copia o la conservazione non autorizzata da parte del consulente (*Insider Threat*).**

1. **Principio di Controllo dell'Endpoint:**
   Nella sicurezza delle informazioni, chi detiene l'accesso fisico o amministrativo a un dispositivo controlla la memoria RAM, il disco rigido e i flussi applicativi locali. Anche isolando la rete o attestando il PC sulla LAN del cliente:
   * I record estratti dall'istanza ServiceNow (tramite MCP) e i frammenti di codice/contesto inviati al modello atterrano localmente sulla macchina del consulente.
   * Il consulente ha la possibilità tecnica di intercettare i log, conservare cache di file temporanei, catturare schermate o salvare payload su dischi e partizioni non monitorate.
2. **L'isolamento di rete non mitiga l'insider:**
   La segregazione di rete impedisce a dati terzi di uscire su Internet *durante* la sessione, ma non impedisce la persistenza locale sul laptop per un utilizzo successivo (es. una volta disconnesso dalla rete del cliente).
3. **Cosa garantisce il documento vs cosa non può garantire:**
   * **Garantisce:** Che Devoteam come azienda non centralizzi i dati dei clienti in un unico database proprietario (*«Reuse without data centralization»*).
   * **NON garantisce:** Che il singolo professionista sia materialmente impossibilitato a trattenere o riutilizzare frammenti di dati o codice del cliente memorizzati sul proprio hard disk.

---

### Prompt 3 (Verifica letterale sul testo originale in inglese)
> *"Controlla direttamente in inglese se le considerazioni finali enunciate sono contenute nel documento e cita le frasi precise. Separa cosa dice il testo da eventuali deduzioni esterne."*

#### Valutazione Tecnica & Risposta

#### A. Evidenze letterali presenti nel documento (Inglese)
* **Ambiente di esecuzione:**
  * Slide 13 (Box 02): `«Consultant PC · customer cloud · on-premise»`
  * Slide 13 (Footer): `«Proposed ASN Offline Edition · destination and connectivity remain customer-qualified»`
* **Promesse di confinamento locale:**
  * Slide 13 (Box 03): `«execution, evidence and customer data stay local. Qualified endpoint · local policy · local control»`
  * Slide 13 (Banner): `«The value: reuse trusted methods without centralizing customer data.»`
  * Slide 14 (Box Customer Environment): `«Customer data stays local · not shared»`
* **Riconoscimento dei limiti e necessità di hardening:**
  * Slide 16 (Pillar 01): `«Consistent identity controls across multicloud, on-premise and consultant PCs; portable controls still require deployment-specific compliance verification.»`
  * Slide 16 (Common foundation): `«PC installation: both components · customer-hosted AI · security hardening»`

#### B. Elementi NON presenti nel documento (Deduzioni di settore / Best practice)
Nel testo del documento **non sono menzionati**:
* Architetture basate su **VDI, Citrix o Bastion Host**: il documento cita unicamente *"Consultant PC"*.
* Requisiti tecnici di **esecuzione "in-memory / zero-disk persistence"** (il testo promette che i dati restano locali ma non specifica l'architettura di caching su disco).
* Tecnologie endpoint specifiche come **BitLocker, FileVault, EDR o agenti DLP**.
* Distinzioni contrattuali tra ambienti di **Sviluppo/Sub-Production e Produzione**.

---

### Prompt 4 (Valutazione di Overpromising: Promessa vs Realtà)
> *"Il documento promette ciò che la versione Consultant PC non riesce a mantenere? C'è una contraddizione tra i claim principali e i vincoli tecnici?"*

#### Valutazione Tecnica & Risposta
**Sì, c'è un forte attrito (e un oggettivo overpromising) tra i titoli e i claim ad alto livello rispetto alla realtà tecnica del "Consultant PC".** Tuttavia, gli estensori del documento hanno inserito clausole di salvaguardia ("fine print") per mitigare la responsabilità legale.

1. **Le contraddizioni nei Claim principali:**
   * **Contraddizione 1: "Customer-controlled runtime" applicato al "Consultant PC" (Slide 13):**  
     Un PC di proprietà del fornitore non è un runtime sotto il controllo del cliente. Assegnare l'etichetta *"Customer-controlled"* a un laptop del fornitore è una forzatura logica.
   * **Contraddizione 2: "Customer data stays local · not shared" (Slide 14):**  
     Se i dati atterrano sul computer del consulente, per il cliente i dati **sono usciti dal perimetro** e sono stati condivisi con il fornitore. Chiamarli "locali" fa leva su un'ambiguità semantica (locali al processo software, ma esterni all'infrastruttura del cliente).
   * **Contraddizione 3: Assenza di tutela dall'Insider Threat:**  
     La promessa di "sovranità dei dati" (*Sovereignty*, Slide 14) decade nel momento in cui l'asset fisico su cui risiedono i dati è mobile e sottratto alla custodia del cliente.
2. **Le clausole di salvaguardia adottate nel documento:**
   * **La qualifica del cliente (Slide 13 footer):** `«destination and connectivity remain customer-qualified»` — scarica la decisione finale sul CISO del cliente: se il cliente accetta il PC portatile, se ne assume il rischio.
   * **L'eccezione di compliance (Slide 16):** `«portable controls still require deployment-specific compliance verification»` — ammette formalmente che per i portatili i controlli standard non offrono garanzie automatiche e richiedono un'approvazione ad hoc caso per caso.
   * **Lo stato di proposta (Slide 13):** `«Proposed ASN Offline Edition»` — definisce la soluzione come modello architetturale proposto e non come capacità contrattualmente certificata.

---

## 3. Registro Audit — Fase 2: "Cattura dell'Expertise"

### Prompt 5 (Promesse su Senior, controlli non-AI e compiti Junior: bastano MCP e Skill?)
> *"Il documento fa promesse sulla capacità di ASN di catturare l'expertise dei senior, controllare gli output con procedure non-AI based per limitare le allucinazioni e guidare il lavoro di junior e practitioner. Per fare questo propone solo l'uso di MCP Server aziendali e di Skill o c'è dell'altro?"*

#### Valutazione Tecnica & Risposta
Le promesse del documento sono state individuate con precisione, ma **la soluzione non si riduce a semplici "MCP e Skill"**. Nel disegno architetturale delineato, MCP e Skill sono solo strumenti d'interfaccia atomica; il framework per mantenere tali promesse prevede **5 componenti distinti**:

1. **Algoritmi Deterministici NON-AI (`Deterministic algorithms`, Slide 6):**
   * *Citazione:* `«Deterministic algorithms: Non-AI checks over fixed inputs. No-network · calculate · reconcile · check»`
   * *Citazione:* `«Deterministic checks catch defined-rule deviations and unsupported references. Reviewed rules and fixed inputs make checks reproducible.»`
   * Non si tratta di prompt AI o skill, ma di logica di controllo algoritmica classica disconnessa da rete che verifica sintassi, API ufficiali e calcoli prima dell'invio all'utente.
2. **Workflows Strutturati e Requisiti di Evidenza (`Evidence Requirements`, Slide 3, 4, 5):**
   * *Citazione:* `«Skills, workflows, evidence requirements and review criteria»` (Slide 5)
   * Le skill atomiche vengono incapsulate in flussi vincolanti che obbligano l'operatore (junior) a produrre evidenze oggettive prima di procedere.
3. **ASN Core come Esecutore Autoritativo (`ASN Runtime Executor`, Slide 11):**
   * *Citazione:* `«No workflow authoring in clients · ASN runtime remains the executor»` (Slide 11)
   * *Citazione:* `«Approved versions only · ASN authoritative»` (Slide 10)
   * I client AI esterni non hanno il permesso di gestire l'orchestrazione; l'autorità di esecuzione appartiene solo al runtime ASN.
4. **Human-in-the-Loop a Sbarramento (`Experts Decide`, Slide 6, 8):**
   * *Citazione:* `«Experts judge & accept: Human decision at the handoff. Exceptions stay visible.»` (Slide 6)
   * La piramide operativa assegna ai junior compiti guidati e delimitati (*«Junior · bounded work»*) e ai senior la revisione e la gestione esclusiva delle anomalie (*«Senior · exceptions»*).
5. **Disaccoppiamento dei Livelli MCP (Slide 11):**
   * *Application-level MCP:* per esporre i metodi di ASN verso l'esterno.
   * *Devoteam ServiceNow Bridge:* connettore proprietario per l'interazione con l'istanza ServiceNow (in sostituzione di *NowAIKit*).

---

### Prompt 6 (Strumenti definiti vs Astrazione e Roadmap futura)
> *"Il documento espone strumenti ben definiti come MCP e Skill per fare la parte dei controlli deterministici, dei workflow e della guida ai junior? O lascia la loro attuazione e metodi da definire in seguito?"*

#### Valutazione Tecnica & Risposta
**Il documento NON espone strumenti tecnici pronti o definiti.** Trattandosi di un pitch di investimento (*Investment Strategy*), definisce un'architettura di principio ma rimanda interamente l'attuazione e la scelta degli strumenti a una successiva fase di ingegneria da finanziare.

1. **Cosa esiste oggi nel piano:**
   * Il connettore temporaneo di terze parti **NowAIKit** (Slide 11).
   * Il gateway **OpenRouter** per testare modelli AI (Slide 12).
   * L'elenco dei client AI approvati (Claude Code, Cursor, Antigravity, Codex - Slide 10).
2. **Cosa è completamente indefinito e ancora da costruire:**
   * **I controlli deterministici non-AI:** Non viene citato alcun linguaggio, linter, motore di parsing AST per JavaScript/ServiceNow o motore di regole formale.
   * **Il motore dei Workflow:** Non viene definito lo standard (State machine, BPMN, Python, YAML).
   * **Il Devoteam MCP Server:** È un'iniziativa futura (`«Pillar 01: Build a functional replacement for NowAIKit»`, Slide 15, 16).
3. **Le conferme documentali del vuoto operativo:**
   * *Slide 18 (First Tranche):* `«Define scope + owners + capacity — Funding amounts not yet provided.»` *(Si richiede budget proprio per definire perimetro, team e capacità operativa).*
   * *Slide 20 (Priority 02):* `«Build shared engineering capacity: Maintain methods, controls and review capacity.»`

---

### Prompt 7 (Decodifica di Slide 10 — "Proposed external exposure · no universal client compatibility")
> *"Cosa intende dire esattamente la Slide 10 nel footer con la frase: «Status: proposed external exposure · no universal client compatibility»?"*

#### Valutazione Tecnica & Risposta
Questa dicitura a piè di pagina costituisce il **disclaimer tecnico formale** che smentisce la pronta disponibilità dell'integrazione mostrata graficamente nella slide:

1. **`«proposed external exposure»` (Esposizione esterna solo proposta):**
   * "External exposure" significa rendere le skill e i workflow di ASN richiamabili all'esterno dell'applicazione proprietaria, direttamente dentro gli IDE di sviluppo dei consulenti (*Claude Code, Cursor, Antigravity*).
   * Il termine **"proposed"** certifica che questa integrazione **non è attualmente in produzione**, ma rappresenta una proposta architetturale in cerca di sponsorizzazione e sviluppo.
2. **`«no universal client compatibility»` (Nessuna compatibilità universale):**
   * Riconosce che il mercato dei client AI è profondamente frammentato: ciascun client gestisce il contesto, i token e le chiamate MCP in modo differente.
   * Ammette che ASN non può garantire che un workflow si comporti in modo identico e deterministico su strumenti diversi, confermando l'impossibilità di affidare l'orchestrazione dei processi ai client terzi.

---

## 4. Matrice Sinottica di Conformità e Maturità (Fase 1 & Fase 2)

| Requisito / Ambito di Verifica | Fase di Riferimento | Promessa del Documento | Stato Reale nel Documento | Valutazione CISO |
| :--- | :---: | :--- | :--- | :--- |
| **Riservatezza Dati (Cloud / On-Prem)** | **Fase 1** | Isolamento dati e modelli dedicati | Pienamente specificato (Slide 12, 14) | ✅ **Conforme** (su infra cliente) |
| **Riservatezza Dati (Consultant PC)** | **Fase 1** | *"Customer data stays local · not shared"* | Dati residenti su hardware fornitore | ❌ **Non Conforme** (Rischio Leak) |
| **Mitigazione Insider Threat** | **Fase 1** | Runtime sotto controllo cliente | Nessun controllo d'endpoint portatile | ❌ **Non Garantito** su PC |
| **Controlli Deterministici Non-AI** | **Fase 2** | Algoritmi anti-allucinazione | Solo principio astratto (Slide 6) | ⚠️ **Non Valutabile** (Manca tool) |
| **Workflow Engine & Evidence** | **Fase 2** | Percorsi guidati per junior | Nessun engine/schema codificato | ⚠️ **Assente** (Da ingegnerizzare) |
| **Integrazione Client Terzi (IDE)** | **Fase 2** | Utilizzo su Cursor, Claude, ecc. | Solo proposta (*proposed*, Slide 10) | ⚠️ **Non Pronto** (Incompatibilità) |
| **Bridge ServiceNow Proprietario** | **Fase 2** | Devoteam Bridge MCP autonomo | Sostituto futuro di NowAIKit (Slide 15) | ⏳ **In Roadmap** (Da costruire) |

---

## 5. Posizione Ufficiale e Raccomandazioni del CISO

Sulla base delle risultanze emerse dall'audit documentale congiunto (Fase 1 & Fase 2), la posizione raccomandata per il CISO in sede di negoziazione con Devoteam è articolata in 4 prescrizioni tassative:

1. **Negazione dell'Opzione "Consultant PC" (Fase 1):**
   * Esercitare la facoltà di qualifica (`«customer-qualified»`, Slide 13) imponendo il **divieto assoluto** di esecuzione di ASN su laptop fisici dei consulenti qualora siano trattati dati reali di configurazione, sicurezza o business logic.
2. **Prescrizione di Deployment Interno o VDI Blindata (Fase 1):**
   * Autorizzare l'adozione di ASN esclusivamente se erogato come **workload interno al VPC/datacenter del cliente** (*customer cloud / on-premise*), oppure via **VDI aziendale controllata dal cliente** con inibizione di clipboard, storage locale e redirect USB.
3. **Verifica della Maturità dei Controlli Deterministici (Fase 2):**
   * Richiedere a Devoteam l'audit del codice sorgente e la documentazione tecnica del presunto modulo di verifica deterministica non-AI (*Slide 6*), per scongiurare che l'affidabilità sia invece demandata a semplici prompt di secondo livello.
4. **Governo dei Client di Sviluppo ed Esposizione Esterna (Fase 2):**
   * Vietare l'uso estemporaneo di client AI non governati (Cursor, Claude Code) fino a quando non sia formalmente certificato il connettore con supporto OAuth 2.0 PKCE nominativo (*Slide 16*) e validata la perfetta aderenza alle ACL di ServiceNow.

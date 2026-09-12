---
name: nowaikit-itsm-assessment
description: Produces a complete ITIL/ServiceNow ITSM Assessment report by interactively requesting questionnaire responses via an upload widget and combining them with live instance data extracted via the nowaikit MCP server.
---

# NowAIKit ITSM Assessment Skill

Questa skill permette di generare automaticamente un documento di Assessment ITSM completo, offrendo un widget interattivo di upload per il questionario e incrociando i dati qualitativi con le evidenze tecniche estratte in tempo reale dall'istanza ServiceNow tramite il server MCP `nowaikit`.

## 🎯 Trigger
Attivati quando l'utente richiede di generare un "ITSM Assessment", "Report ITSM" o fa riferimento esplicito a questa skill (es. *"esegui la skill nowaikit-itsm-assessment"*), anche se non ha ancora fornito o allegato alcun file.

## 🗂️ File Interni della Skill
Utilizza esclusivamente i due file interni della skill memorizzati nella directory locale `.agents/skills/nowaikit-itsm-assessment/`:
1. **Istruzioni di Estrazione**: `istruzioni.json` (catalogo dei comandi/query MCP da eseguire su ServiceNow). Leggilo con `view_file`.
2. **Template Documentale**: `template.md` (struttura Markdown rigorosa del report finale). Leggilo con `view_file`.

---

## 🚀 Workflow Operativo Rigoroso

### Passo 1: Verifica Interattiva dell'Input Utente con Widget
1. **Controllo Presenza Dati**:
   - Verifica se l'utente ha già fornito nel messaggio:
     - Il percorso locale del file JSON (es. `/path/to/risposte-questionario.json`), OPPURE
     - Il contenuto JSON incollato direttamente.
2. **Richiesta Interattiva con Widget UI (se il file manca)**:
   - Se l'utente **NON** ha ancora fornito né il percorso né il contenuto JSON:
     - Crea/aggiorna l'artifact HTML dell'uploader (con dropzone, validazione client-side e pulsante di selezione) all'interno della directory degli artifact.
     - Mostra l'interfaccia all'utente incorporandola tramite il tag `<agent-embed src="file:///<artifact_path>/uploader.html"></agent-embed>`.
     - Ricorda inoltre all'utente che può utilizzare l'icona graffetta/**+** nativa della barra di chat per allegare il file.
     - **FERMATI SUBITO** e attendi l'input dell'utente prima di procedere.
3. **Acquisizione del Contenuto**:
   - Quando l'utente risponde con il path del file, leggilo con `view_file`.
   - Se ha incollato il JSON, parsalo direttamente dal contesto.

---

### Passo 2: Lettura File Interni della Skill
1. Leggi `istruzioni.json` dalla cartella `.agents/skills/nowaikit-itsm-assessment/` usando `view_file`.
2. Leggi `template.md` dalla cartella `.agents/skills/nowaikit-itsm-assessment/` usando `view_file`.

---

### Passo 3: Estrazione Dati Live via MCP (`nowaikit`)
Per ogni voce presente in `istruzioni.json`:
- Esegui il tool indicato nel campo `"tool"` (es. `query_records`, `get_system_property`) indirizzato al server MCP `nowaikit`.
- Passa esattamente i parametri specificati nel blocco `"parameters"`.
- Raccogli i risultati tecnici restituiti da ServiceNow.

---

### Passo 4: Integrazione Dati e Redazione Contenuti
Utilizza rigorosamente `template.md` come base:
1. Sostituisci variabili come `{{metadata.cliente}}`, `{{metadata.versione}}`, `{{metadata.data_riferimento_documento}}` con i valori reali del questionario.
2. Per ogni tabella delle sezioni 3, 4, 5 e 6:
   - **Stato attuale**: Sintetizza la situazione incrociando risposta al questionario ed evidenza tecnica ServiceNow.
   - **Suggerimenti**: Se la risposta indica `"No si chiede a Devoteam di fare una proposta"`, formula una proposta consulenziale autorevole basata sulle best practice ITIL e gli standard architetturali ServiceNow (CSDM 4.0, OOTB first, CAB, ecc.).
   - **Benefici**: Specifica i vantaggi concreti.
   - **Score**: Assegna punteggi (1-5) *Attuale* e *Atteso*.
   - **Priorità**: Assegna ALTA, MEDIA o BASSA.

---

### Passo 5: Sintesi e Roadmap (Sezioni 7 e 8)
- Compila la tabella riassuntiva dei punteggi (Sezione 7).
- Raggruppa tutte le azioni nei 3 orizzonti temporali (Sezione 8).

---

### Passo 6: Output Finale
- Restituisci ESCLUSIVAMENTE il documento Markdown finale completo a partire dal titolo `# ServiceNow Assessment - Modulo ITSM`.

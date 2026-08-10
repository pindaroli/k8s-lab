# Guida alla Esportazione e Migrazione Istanze ServiceNow (SN)

## 📌 Panoramica
Questa guida racchiude le terminologie ufficiali, i tre metodi principali per esportare/migrare le configurazioni di un'istanza ServiceNow verso una nuova istanza pulita e i relativi prompt pronti all'uso per l'AI Agent (NowAIKit / MCP).

---

## 📖 Gergo ServiceNow (SN Terms)

Quando si vuole trasferire la configurazione o duplicare un'istanza in ServiceNow, si utilizzano i seguenti termini specifici:

1. **Update Set** (o *Remote Update Set*): Il pacchetto XML contenente le personalizzazioni di codice, tabelle e form.
2. **Scoped Application / App Package**: L'applicazione impacchettata (in *Studio*) integrata con *Git* o l'*App Repository*.
3. **Instance Clone** (o *System Clone*): Il processo nativo per duplicare l'intero database di un'istanza (dati + configurazioni).
4. **Data Preservers / Exclusions**: Le regole applicate durante un Clone per conservare i dati specifici dell'istanza di destinazione (es. System Properties di DEV).

---

## 🛠️ I 3 Metodi di Migrazione in Dettaglio

### 1. Update Set (Remote Update Set) — *Metodo Granulare*
* **Cos'è**: Registro nativo che traccia i metadata (`sys_update_xml`).
* **Cosa include**: Tabelle, campi, form layout, Business Rules, Script Include, Client Script, UI Policy, Flow Designer, Ruoli, ACL.
* **Cosa esclude**: Dati applicativi, Utenti, Gruppi e System Properties (richiedono export dedicato).
* **Procedura**:
  1. Istanza Sorgente: Impostare l'Update Set su `State = Complete`.
  2. Esportare in XML via link *Export to XML*.
  3. Istanza Target: Importare in *Retrieved Update Sets*, eseguire il *Preview* e infine il *Commit*.

### 2. Scoped Application (Integrazione Git / App Repo) — *Metodo SDLC Moderno*
* **Cos'è**: Sviluppo in un namespace applicativo dedicato (`x_company_app`) integrato con repository Git (GitHub/GitLab) o App Repository privato.
* **Cosa include**: Tutti i file e script compresi nello Scope dell'app, inclusi eventuali dati demo definiti.
* **Cosa esclude**: Modifiche apportate in ambiente Global al di fuori dello Scope.
* **Procedura**:
  1. Istanza Sorgente: In *Studio*, eseguire Commit & Push delle modifiche sul repo Git.
  2. Istanza Target: In *Studio*, selezionare *Import From Source Control* fornendo URL del repo e credenziali.

### 3. Instance Clone (System Clone) — *Metodo Duplicazione Totale*
* **Cos'è**: Duplicazione totale del database gestita dall'infrastruttura Cloud di ServiceNow.
* **Cosa include**: **TUTTO** (dati, utenti, incidenti, log, personalizzazioni).
* **Procedura**:
  1. In *System Clone > Clone Targets*, aggiungere l'istanza target.
  2. Richiedere il clone via *Request Clone* definendo Data Preservers ed Exclusions.
  3. L'engine di ServiceNow esegue la duplicazione in background.

---

## 📊 Tabella Comparativa

| Caratteristica | 1. Update Set | 2. Scoped App (Git) | 3. Instance Clone |
| :--- | :--- | :--- | :--- |
| **Cosa sposta** | Personalizzazioni e codice | Soluzione / App isolata | L'intera istanza (Codice + Dati) |
| **Sposta i dati/record?** | ❌ No | ⚠️ Solo dati demo dichiarati | ✅ Sì (Tutti i dati) |
| **Destinazione** | Nuova o Esistente | Nuova o Esistente | Sovrascrive l'istanza target |
| **Strumento** | File XML nativi | Studio / Git / App Repo | Engine System Clone di SN |

---

## 🤖 Vibe Prompts per l'AI Agent (NowAIKit)

### 📦 Prompt 1 — Update Set & Config Export
```text
"Senti, dobbiamo impacchettare tutte le customizzazioni per portarle su una nuova istanza. Prendi l'Update Set attivo su cui abbiamo lavorato, impostalo nello stato 'Complete' ed esporta il file XML. Già che ci sei, usa export_properties per fare uno snapshot JSON di tutte le System Properties dell'istanza corrente e salvami tutto il pacchetto di configurazione in locale."
```

### 🚀 Prompt 2 — Scoped Application & Git Push
```text
"Dobbiamo trasferire l'applicazione '[Nome_App]' sulla nuova istanza passando da Git. Fai un check dello stato dell'app nello Studio, esegui il commit di tutte le modifiche pendenti con messaggio 'Release v1.0 - Ready for migration' e fai il push sul repository Git. Subito dopo, passa alla nuova istanza e avvia l'importazione dell'applicazione direttamente dal repo Git."
```

### 🔄 Prompt 3 — Instance Clone & Drift Check
```text
"Voglio duplicare l'intera istanza sorgente '[Istanza_Prod]' sulla nuova istanza target '[Istanza_Dev]'. Controlla che le due istanze siano raggiungibili, imposta i Data Preservers per non sovrascrivere le credenziali di dev e lancia la richiesta di System Clone. Non appena il clone è completato, esegui un compare_instances per confermarmi che tabelle e proprietà siano perfettamente allineate."
```

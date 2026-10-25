---
title: Integrazione Locale MCP Microsoft Office (office_mac + macos_automator) e Skill macos-office-automation
status: active
certified_for_ai: true
author: Gemini
created_at: 2026-10-25
category: operational_plan
tags:
  - mcp
  - macos
  - office365
  - applescript
  - automator
  - skill
---

# Piano Operativo: Integrazione Locale MCP Microsoft Office (`office_mac` + `macos_automator`) e Skill `macos-office-automation`

> [!IMPORTANT]
> **Current Status**: **IN ATTESA DI DECISIONI ARCHITETTURALI E AVVIO FASE 1**
> **Contesto**: Automazione 100% locale su macOS di Microsoft Word, Excel e PowerPoint tramite accoppiata di server MCP (`office_mac` per motore OOXML + session check; `macos_automator` per AppleScript/JXA nativo e controllo GUI) governati dalla skill dedicata `macos-office-automation`.

---

## 🗺️ Mappe Concettuali e Relazioni
- [[MCP_Platform]] (Piattaforma e client MCP del lab)
- [[zero-install-executable-package-pattern]] (Esecuzione effimera `uv` / `npx` senza inquinare l'ambiente globale)
- [[SCHEMA]] (Regole di governance e catalogazione del Wiki)

---

## 1. Obiettivo e Architettura della Soluzione

L'obiettivo è dotare l'ambiente macOS locale di capacità complete e ad alta efficienza per creare, leggere, modificare, formattare ed esportare documenti **Microsoft Office (Word, Excel, PowerPoint)** operando esclusivamente sul file system locale del Mac e sui processi desktop, **senza** coinvolgere Outlook, account cloud OneDrive/SharePoint o API Microsoft Graph remote.

L'architettura si fonda sulla ripartizione rigorosa dei compiti tra due server MCP configurati centralmente in [`~/.gemini/antigravity/mcp_config.json`](file:///Users/olindo/.gemini/antigravity/mcp_config.json):

1. **`office_mac` (`vAirpower/macos-office365-mcp-server`)**:
   - **Ruolo**: Motore documentale OOXML (`python-docx`, `openpyxl`, `python-pptx`) per operazioni strutturali ad alta velocità su disco + bridge PyObjC/AppleScript per l'ispezione delle sessioni aperte (`check_office_status`, `list_active_documents`, `list_active_workbooks`, `list_active_presentations`).
   - **Modalità di esecuzione**: Clonazione del codice in `scripts/office-mac-mcp/` ed esecuzione effimera tramite `/opt/homebrew/bin/uv run` con dipendenze iniettate al volo (`mcp<2.0.0`, `python-pptx`, `python-docx`, `openpyxl`, `aiofiles`), zero `.venv` manuali e zero `pip install` globali.
2. **`macos_automator` (`@steipete/macos-automator-mcp`)**:
   - **Ruolo**: Runtime nativo AppleScript e JXA (`execute_script`) corredato da knowledge base SDEF (`get_scripting_tips`) per le azioni non coperte dal motore OOXML (focus finestre, editing live su finestra aperta, esecuzione macro VBA, esportazione PDF nativa Quartz, UI scripting via `System Events`).
   - **Modalità di esecuzione**: Zero-install pura tramite `npx -y @steipete/macos-automator-mcp@latest`.

---

## 2. Configurazione Dichiarativa Target (`~/.gemini/antigravity/mcp_config.json`)

```json
    "office_mac": {
      "command": "/opt/homebrew/bin/uv",
      "args": [
        "run",
        "--with",
        "mcp<2.0.0",
        "--with",
        "python-pptx",
        "--with",
        "python-docx",
        "--with",
        "openpyxl",
        "--with",
        "aiofiles",
        "python",
        "/Users/olindo/prj/k8s-lab/scripts/office-mac-mcp/src/office365_mcp_server.py"
      ]
    },
    "macos_automator": {
      "command": "npx",
      "args": [
        "-y",
        "@steipete/macos-automator-mcp@latest"
      ]
    }
```

---

## 3. Specifica Completa della Skill (`macos-office-automation`)

Il file `SKILL.md` (da collocare in `.agents/skills/macos-office-automation/SKILL.md` o globalmente in `~/.gemini/config/skills/macos-office-automation/SKILL.md`) conterrà la seguente definizione:

```markdown
---
name: macos-office-automation
description: Automazione e gestione avanzata in locale su macOS di Microsoft Office (Word, Excel, PowerPoint) tramite i server MCP office_mac (OOXML + AppleScript bridge) e macos_automator (AppleScript/JXA nativo). Attivare ogni volta che l'utente chiede di creare, leggere, modificare, formattare, esportare in PDF o automatizzare file .docx, .xlsx, .pptx o controllare le applicazioni desktop Word, Excel e PowerPoint sul Mac.
---

# macOS Microsoft Office Automation Skill

Sei uno specialista nell'automazione e gestione avanzata di **Microsoft Office (Word, Excel, PowerPoint)** su ambiente locale macOS.
Operi al **100% in locale** sul file system e sui processi desktop del Mac tramite due server MCP complementari:
1. **`office_mac`** (`macos-office365-mcp-server`): motore documentale OOXML (`python-docx`, `openpyxl`, `python-pptx`) + bridge applicativo AppleScript.
2. **`macos_automator`** (`macos-automator-mcp`): runtime nativo per AppleScript e JXA con knowledge base di script di sistema (`execute_script`, `get_scripting_tips`).

> [!IMPORTANT]
> **Perimetro di Esclusione**: NON gestire mai Outlook, account cloud OneDrive/SharePoint o API Microsoft Graph/365 remote. Tutte le operazioni devono avvenire localmente sui file POSIX del Mac e sulle istanze desktop.

---

## 🧭 Regole di Routing e Scelta degli Strumenti

Per garantire la massima velocità (efficienza di token e tempo di esecuzione) e zero errori di sintassi, applica rigidamente questa matrice decisionale:

### 1. Consapevolezza Preliminare della Sessione (Pre-Flight Check) -> USA `office_mac`
Prima di manipolare o sovrascrivere qualsiasi file esistente su disco:
1. Esegui `check_office_status` per verificare che le app Office siano installate e accessibili.
2. Interroga `list_active_documents`, `list_active_workbooks` o `list_active_presentations` per verificare se il documento target è **attualmente aperto a schermo** dall'utente:
   - **Se il file è CHIUSO**: procedi con i tool OOXML di `office_mac` (veloci e atomici su disco).
   - **Se il file è APERTO**: **FERMATI / ATTENZIONE** (vedi Gestione Conflitti Lock & Dirty State sotto). Modificare il file su disco con `office_mac` mentre è aperto nell'app GUI non aggiornerà la finestra aperta e rischierà di essere sovrascritto quando l'utente salverà dalla GUI!

### 2. Operazioni Documentali Ordinarie (File Chiusi o Nuovi) -> USA SEMPRE `office_mac`
Utilizza prioritariamente i tool predefiniti ad alto livello per la creazione e manipolazione strutturale dei contenuti:
- **Excel**: `create_workbook`, `add_worksheet`, `write_cell`, `write_range`, `add_formula`, `create_chart`, `save_workbook`.
- **Word**: `create_document`, `add_heading`, `add_paragraph`, `add_list`, `add_table`, `save_document`.
- **PowerPoint**: `create_presentation`, `add_slide`, `add_text_to_slide`, `add_image_to_slide`, `add_speaker_notes`, `save_presentation`.

**Regola di efficienza**: È vietato generare script AppleScript/JXA con `macos_automator` per operazioni di scrittura dati, formattazione celle o aggiunta slide se il file non è bloccato in GUI ed esiste già il tool atomico in `office_mac`.

### 3. Controllo Nativo del Sistema, Live GUI Editing e Azioni di Menu -> USA `macos_automator`
Ricorri a `execute_script` (AppleScript / JXA) **esclusivamente** nei seguenti casi:
- **Manipolazione Live in Finestra Aperta**: L'utente sta guardando il documento aperto in Word/Excel/PowerPoint e vuole vedere le modifiche applicate in tempo reale senza chiudere il file.
- **Focus e Gestione Finestre**: Portare in primo piano un documento o applicazione (`tell application "Microsoft Word" to activate`).
- **Esecuzione di Macro VBA**: Richiamare routine macro già presenti nelle cartelle di lavoro (`run VB macro`).
- **Esportazioni Grafiche e Stampa PDF**: Salvare o esportare in PDF tramite il motore di rendering nativo di Office/macOS Quartz (`save as ... file format format PDF`).
- **UI Scripting**: Manipolazione di menu contestuali o finestre di dialogo modali tramite `System Events`.

**Regola di Best-Practice AppleScript**: Prima di compilare AppleScript complessi, interroga `get_scripting_tips` di `macos_automator` per reperire la sintassi SDEF corretta ed evitare timeout o comandi deprecati.

---

## 📂 Gestione Percorsi, Lock e Permessi macOS

1. **Percorsi POSIX Assoluti**: Usa **sempre** percorsi assoluti POSIX (es. `/Users/olindo/Documents/report.xlsx`). Mai usare percorsi relativi (`./`), `~` non espansa o backslash Windows.
2. **Verifica Esistenza e Lock File (`~$`)**:
   - Prima di leggere/scrivere, verifica l'esistenza della directory/file target.
   - Se nella stessa directory esiste un file di lock `~$<nomefile>.docx/xlsx/pptx` (o il file compare in `list_active_*`), avvisa l'utente o chiedi se salvare su un nuovo file / operare via AppleScript live prima di sovrascrivere su disco.
3. **Diagnostica Errori Permessi macOS (TCC)**:
   - Se un comando AppleScript restituisce l'errore **`-1743` (`errAEEventNotPermitted`)**, interrompi i tentativi e istruisci l'utente ad abilitare i permessi in:
     `Impostazioni di Sistema -> Privacy e Sicurezza -> Automazione` (abilitando i toggle per Microsoft Word, Excel, PowerPoint sotto l'app host).
   - Se un comando UI Scripting (`System Events`) restituisce errore **`-1719` / `-25211`**, istruisci l'utente ad abilitare l'app host in:
     `Impostazioni di Sistema -> Privacy e Sicurezza -> Accessibilità`.
```

---

## 4. ⚠️ Punti Critici e Decisioni da Vagliare Prima dell'Esecuzione

1. **Criticità Split-Brain (File su Disco vs Finestra GUI Aperta)**:
   - `office_mac` scrive i file OOXML direttamente su disco tramite `openpyxl`/`python-docx`/`python-pptx`, bypassando la RAM di Word/Excel/PowerPoint.
   - Se il file è aperto in GUI, le modifiche su disco di `office_mac` non compaiono a schermo e vengono perse se l'utente preme `Cmd+S`. La Skill mitiga questo rischio imponendo il check preventivo `list_active_*` e deviando su `macos_automator` (AppleScript in-memory) o chiedendo la chiusura del file quando il documento è già aperto.
2. **Stato Upstream di `vAirpower/macos-office365-mcp-server`**:
   - Il server upstream lavora prevalentemente per sessioni in-memory (`create_workbook` -> `workbook_id` -> `save_workbook`) e potrebbe avere capacità limitate nella modifica in-place di file `.xlsx`/`.docx` preesistenti complessi. Essendo clonato in `scripts/office-mac-mcp/`, potremo ispezionare ed eventualmente estendere i controller Python locali durante la Fase 2.
3. **Ambito di Installazione della Skill**:
   - Decidere se installare `macos-office-automation` a livello **Workspace** (`/Users/olindo/prj/k8s-lab/.agents/skills/macos-office-automation/SKILL.md`) o **Globale** (`/Users/olindo/.gemini/config/skills/macos-office-automation/SKILL.md`).
4. **Permessi macOS TCC (`macos_automator`)**:
   - `execute_script` ha accesso completo a AppleScript/JXA con i privilegi dell'utente locale. Richiederà l'approvazione esplicita dei popup macOS per `Automazione` (Word, Excel, PowerPoint) ed eventualmente `Accessibilità` (`System Events`).

---

## 5. Fasi Operative di Implementazione (Protocollo Test-Driven)

### [ ] Fase 1: Verifica Prerequisiti Desktop & Acquisizione `office_mac`
- Verifica presenza di `Microsoft Word.app`, `Microsoft Excel.app` e `Microsoft PowerPoint.app` in `/Applications`.
- Clone del repository `https://github.com/vAirpower/macos-office365-mcp-server.git` in `/Users/olindo/prj/k8s-lab/scripts/office-mac-mcp/` (rimuovendo `.git` nidificato).
- Ispezione dei tool esposti in `src/office365_mcp_server.py` e test di avvio CLI tramite `/opt/homebrew/bin/uv run`.

### [ ] Fase 2: Registrazione Dichiarativa in `~/.gemini/antigravity/mcp_config.json`
- Aggiunta delle voci `office_mac` e `macos_automator` in `~/.gemini/antigravity/mcp_config.json`.
- Verifica caricamento schemi MCP in Antigravity.

### [ ] Fase 3: Creazione della Skill `macos-office-automation`
- Scrittura del file `SKILL.md` nel percorso scelto dall'utente (Workspace `.agents/skills/` o Globale `~/.gemini/config/skills/`).
- Eventuale registrazione della regola di attivazione in `.agents/AGENTS.md` (se di workspace).

### [ ] Fase 4: Collaudo End-to-End e Onboarding Permessi TCC macOS
- Esecuzione di `check_office_status` e `list_active_*` su `office_mac`.
- Creazione di test in `/tmp` di un file `.xlsx`, `.docx` e `.pptx` via `office_mac`.
- Test di attivazione finestra ed esportazione PDF via `macos_automator` (`execute_script`) con verifica dei permessi macOS `Automazione`.

---

## 💾 Stato di Ripristino (AI Save-State)
- **Fase Attiva**: Fase 0 (Pianificazione completata e persistita su Wiki)
- **Ultima Azione Completata**: Redazione e salvataggio del piano `wiki/plans/macos-office-mcp-and-skill-integration.md` e sincronizzazione con `todo.md` e `GEMINI.md`.
- **Prossimo Passo Operativo**: Attendere le decisioni dell'utente sui punti critici (in particolare: collocazione della Skill Globale vs Workspace) e l'autorizzazione per avviare la **Fase 1** (verifica app in `/Applications` e clone di `macos-office365-mcp-server` in `scripts/office-mac-mcp/`).
- **Blocchi/Decisioni Pendenti**: Scelta percorso Skill (`~/.gemini/config/skills/` vs `.agents/skills/`) e via libera esplicito dell'utente per l'esecuzione della Fase 1.

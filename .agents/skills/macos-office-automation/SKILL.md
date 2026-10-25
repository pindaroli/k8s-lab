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
1. Esegui `check_office_status` per verificare che le app Office siano installate e se sono attualmente in esecuzione (`*_running`).
2. Interroga `list_active_documents`, `list_active_workbooks` o `list_active_presentations` per verificare se il documento target è **attualmente aperto a schermo** dall'utente (`source: "macos_gui"`):
   - **Se il file è CHIUSO**: procedi con i tool OOXML di `office_mac` (veloci e atomici su disco).
   - **Se il file è APERTO**: **FERMATI / ATTENZIONE** (vedi Gestione Conflitti Lock & Dirty State sotto). Modificare il file su disco con `office_mac` mentre è aperto nell'app GUI non aggiornerà la finestra aperta e rischierà di essere sovrascritto quando l'utente salverà dalla GUI!

### 2. Operazioni Documentali Ordinarie (File Chiusi o Nuovi) -> USA SEMPRE `office_mac`
Utilizza prioritariamente i tool predefiniti ad alto livello per la creazione e manipolazione strutturale dei contenuti:
- **Excel**: `create_workbook`, `add_worksheet`, `write_cell`, `write_range`, `add_formula`, `create_chart`, `save_workbook`, `list_worksheets`.
- **Word**: `create_document`, `add_heading`, `add_paragraph`, `add_list`, `add_table`, `save_document`.
- **PowerPoint**: `create_presentation`, `add_slide`, `add_text_to_slide`, `add_image_to_slide`, `add_speaker_notes`, `save_presentation`.

**Regola di efficienza**: È vietato generare script AppleScript/JXA con `macos_automator` per operazioni di scrittura dati, formattazione celle o aggiunta slide se il file non è bloccato in GUI ed esiste già il tool atomico in `office_mac`.

### 3. Controllo Nativo del Sistema, Live GUI Editing e Azioni di Menu -> USA `macos_automator`
Ricorri a `execute_script` (AppleScript / JXA) **esclusivamente** nei seguenti casi:
- **Manipolazione Live in Finestra Aperta**: L'utente sta guardando il documento aperto in Word/Excel/PowerPoint e vuole vedere le modifiche applicate in tempo reale senza chiudere il file.
- **Focus e Gestione Finestre**: Portare in primo piano un documento o applicazione (`tell application "Microsoft Word" to activate`).
- **Esecuzione di Macro VBA**: Richiamare routine macro già presenti nelle cartelle di lavoro (`run VB macro`).
- **Esportazioni Grafiche e Stampa PDF**: Salvare o esportare in PDF tramite il motore di rendering nativo di Office/macOS Quartz (`save as activeDoc file name POSIX file "/Users/olindo/Library/Containers/com.microsoft.Word/Data/Documents/out.pdf" file format format PDF`, usando sempre `POSIX file` e preferibilmente la directory `Data/Documents` del container sandbox dell'app per evitare popup modali "Grant Access" di macOS App Sandbox, spostando poi il PDF nella destinazione finale).
- **UI Scripting**: Manipolazione di menu contestuali o finestre di dialogo modali tramite `System Events`.

**Regola di Best-Practice AppleScript**: Prima di compilare AppleScript complessi, interroga `get_scripting_tips` di `macos_automator` per reperire la sintassi SDEF corretta ed evitare timeout o comandi deprecati.

---

## 📂 Gestione Percorsi, Lock e Permessi macOS

1. **Percorsi POSIX Assoluti**: Usa **sempre** percorsi assoluti POSIX (es. `/Users/olindo/Documents/report.xlsx`). Mai usare percorsi relativi (`./`), `~` non espansa o backslash Windows.
2. **Verifica Esistenza e Lock File (`~$`)**:
   - Prima di leggere/scrivere, verifica l'esistenza della directory/file target.
   - Se nella stessa directory esiste un file di lock `~$<nomefile>.docx/xlsx/pptx` (o il file compare in `list_active_*` con `source: "macos_gui"`), avvisa l'utente o chiedi se salvare su un nuovo file / operare via AppleScript live prima di sovrascrivere su disco.
3. **Diagnostica Errori Permessi macOS (TCC)**:
   - Se un comando AppleScript restituisce l'errore **`-1743` (`errAEEventNotPermitted`)**, interrompi i tentativi e istruisci l'utente ad abilitare i permessi in:
     `Impostazioni di Sistema -> Privacy e Sicurezza -> Automazione` (abilitando i toggle per Microsoft Word, Excel, PowerPoint sotto l'app host).
   - Se un comando UI Scripting (`System Events`) restituisce errore **`-1719` / `-25211`**, istruisci l'utente ad abilitare l'app host in:
     `Impostazioni di Sistema -> Privacy e Sicurezza -> Accessibilità`.

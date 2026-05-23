---
title: "Workaround Sicurezza Ghostty: Avvio Automatico Tdarr Node"
last_updated: "2026-05-23"
confidence: "High"
tags:
  - "#ghostty"
  - "#tdarr"
  - "#macos"
provenance:
  - "manual_launcher"
---

# Workaround Sicurezza Ghostty: Avvio Automatico Tdarr Node

## Problematica
A partire dalla versione 1.2.0 di Ghostty, l'esecuzione di script locali da sorgenti esterne (es. Finder, Alfred, lanciatori grafici) innesca sistematicamente il popup di sicurezza:

"Allow Ghostty to execute '/Users/olindo/prj/k8s-lab/tdarr/node/start_node.sh'?"

Questo comportamento è legato alla vulnerabilità GHSA-q9fg-cpmh-c78x (escalation dei privilegi tramite ereditarietà delle autorizzazioni TCC del terminale). Mitchell Hashimoto (il manutentore principale) ha confermato che non verranno introdotte opzioni di whitelist o parametri per disattivare questo avviso nei file di configurazione per evitare che malware non privilegiati possano manipolare il file di testo `~/.config/ghostty/config`.

## Soluzione Applicata
Per ovviare al problema è stata creata un'applicazione AppleScript nativa (`Avvia-Tdarr-Node.app`) posizionata sulla Scrivania.

L'AppleScript sfrutta l'API di scripting di Ghostty per inviare il comando come stringa di testo (`input text`) all'interno di una shell già inizializzata. Poiché l'input simula l'interazione diretta della tastiera, Ghostty considera l'azione fidata e non mostra alcun popup di sicurezza.

### Codice Sorgente del Lanciatore
Il codice sorgente è memorizzato in modo permanente nel repository in [tadarr-script.applescript](file:///Users/olindo/prj/k8s-lab/tdarr/tadarr-script.applescript):
```applescript
tell application "Ghostty"
	activate
	set cfg to new surface configuration
	set initial working directory of cfg to "/Users/olindo/prj/k8s-lab/tdarr/node/"
	set win to new window with configuration cfg
	set term to focused terminal of selected tab of win
	input text "./start_node.sh" & return to term
end tell
```

### Come Rigenerare l'App in Futuro
In caso di modifiche ai percorsi o se l'app dovesse essere cancellata, è possibile ricompilarla eseguendo da terminale:
```bash
osacompile -o ~/Desktop/Avvia-Tdarr-Node.app /Users/olindo/prj/k8s-lab/tdarr/tadarr-script.applescript
```

### Come Registrare l'App tra gli Elementi del Login (Login Items)
Una volta compilata l'applicazione sulla Scrivania, questa deve essere registrata tra gli Elementi del Login di macOS affinché parta all'avvio.

#### Metodo 1: Tramite Terminale (Consigliato)
Esegui il seguente comando per registrare programmaticamente l'applicazione nei Login Items:
```bash
osascript -e 'tell application "System Events" to make new login item at end with properties {path:"/Users/olindo/Desktop/Avvia-Tdarr-Node.app", name:"Avvia-Tdarr-Node", hidden:false}'
```

#### Metodo 2: Tramite Interfaccia Grafica
1. Apri **Impostazioni di Sistema** su macOS.
2. Naviga su **Generali > Elementi Login**.
3. Sotto la sezione **Apri all'accesso**, clicca sul pulsante **`+`**.
4. Sfoglia e seleziona `Avvia-Tdarr-Node.app` dalla tua **Scrivania** (Desktop).

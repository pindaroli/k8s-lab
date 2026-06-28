# Regole di Progetto (Workspace Rules)

- **Priorità Homebrew (brew)**: Prima di installare o compilare qualsiasi pacchetto o tool software scaricandolo direttamente (es. tramite script `curl`, pacchetti tar.gz o compilazione manuale), l'agente deve verificare preventivamente se tale pacchetto è disponibile tramite il gestore di pacchetti **Homebrew** (`brew`). Se disponibile, l'installazione deve essere eseguita nativamente tramite `brew`.

- **Visualizzazione Log di Antigravity (Scorciatoia Terminale)**: Se l'utente chiede di vedere i log di Antigravity (es. "fammi vedere i log di antigravity", "apri i log di antigravity" o simili), l'agente deve proporre ed eseguire direttamente (previo assenso dell'utente) un comando per aprire una nuova finestra di terminale che esegua il `tail -f` del file di log del language server (`~/Library/Logs/Antigravity/language_server.log`).
  - L'agente deve tentare prima di aprire una nuova finestra in **Ghostty** con il comando:
    `ghostty -e "tail -f ~/Library/Logs/Antigravity/language_server.log" &`
  - Se Ghostty non è installato o il comando fallisce, l'agente deve effettuare il fallback sull'app **Terminale** nativa di macOS usando AppleScript:
    `osascript -e 'tell application "Terminal" to do script "tail -f ~/Library/Logs/Antigravity/language_server.log"' &`

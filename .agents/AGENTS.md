# Regole di Progetto (Workspace Rules)

- **Priorità Homebrew (brew)**: Prima di installare o compilare qualsiasi pacchetto o tool software scaricandolo direttamente (es. tramite script `curl`, pacchetti tar.gz o compilazione manuale), l'agente deve verificare preventivamente se tale pacchetto è disponibile tramite il gestore di pacchetti **Homebrew** (`brew`). Se disponibile, l'installazione deve essere eseguita nativamente tramite `brew`.

---
compiled: true
compiled_at: '2026-08-27T04:15:00.808725+00:00'
ingested_at: '2026-08-27T04:05:58.783382+00:00'
title: opnsens-action-cron-guide
type: local_file
---

```python
md_content = """# Guida Tecnica: Creazione di Action Personalizzate in OPNsense (configd)

Questa guida spiega come estendere in modo nativo le funzionalità di OPNsense utilizzando il sottosistema **configd**. Questo meccanismo permette di registrare script personalizzati eseguiti via riga di comando (CLI) e di renderli disponibili automaticamente all'interno dell'interfaccia grafica (WebGUI), specificamente nel menu a tendina del modulo **Cron**, garantendo la persistenza agli aggiornamenti di sistema.

Utilizzeremo come esempio pratico lo script `sync_ping`, progettato per verificare la connettività WAN ed eseguire un reset dell'interfaccia in caso di disconnessione stabile.

---

## Architettura di configd

L'integrazione tra la riga di comando e la WebGUI in OPNsense si basa su tre componenti:
1. **Lo Script Eseguibile**: Il codice effettivo (Shell, Python, ecc.) che compie l'azione.
2. **Il File di Configurazione della Action (`.conf`)**: Un file che mappa l'azione, definisce i permessi, il messaggio di log e la descrizione per la WebGUI.
3. **Il Demone configd**: Il servizio di backend che legge le configurazioni e ne permette l'esecuzione sicura tramite il comando `configctl`.

---

## Passo 1: Creazione dello Script Shell

I file eseguibili personalizzati devono risiedere in una directory logica dedicata agli script.

1. Accedi alla shell di OPNsense (opzione `8` dal menu console).
2. Crea e apri il file dello script:

```

```text
File generated successfully.

```bash
   nano /usr/local/opnsense/scripts/sync-ping.sh

```

3. Incolla il seguente codice (assicurati che non ci siano ritorni a capo in formato Windows/DOS):
```bash
#!/bin/sh

# Configurazione
TARGET="8.8.8.8"
INTERFACE="wan"
MAX_ATTEMPTS=3
SLEEP_TIME=15

# Ciclo di verifica connettività
for i in 1 2 3; do
    if /sbin/ping -c 3 -q "$TARGET" > /dev/null 2>&1; then
        # Connessione presente, esce con successo
        exit 0
    fi
    sleep "$SLEEP_TIME"
done

# Se arriva qui, la connessione è stabilmente interrotta
/usr/bin/logger -t check_wan "Connettività WAN assente. Avvio reset di $INTERFACE..."
/usr/local/sbin/configctl interface reconfigure "$INTERFACE"

```


4. Salva il file (`Ctrl+O`, `Invio`) ed esci (`Ctrl+X`).
5. **Fondamentale**: Rendi lo script eseguibile dal sistema:
```bash
chmod +x /usr/local/opnsense/scripts/sync-ping.sh

```



---

## Passo 2: Definizione dell'Azione in actions.d

Per fare in modo che il motore di OPNsense veda lo script, dobbiamo creare un file di configurazione all'interno della directory `actions.d`. Il nome del file deve seguire tassativamente la sintassi `actions_<nome_servizio>.conf`.

1. Crea il file dell'azione:
```bash
nano /usr/local/opnsense/service/conf/actions.d/actions_sync_ping.conf

```


2. Incolla la struttura di configurazione:
```ini
[run]
command:/usr/local/opnsense/scripts/sync-ping.sh
parameters:
type:script
message:SyncPing Connectivity Check
description:SyncPing Connectivity Check

```



### Anatomia del file `.conf`:

* `[run]`: Rappresenta il sotto-comando dell'azione. Determina la sintassi CLI finale (`configctl sync_ping run`).
* `command`: Il percorso assoluto dello script da eseguire.
* `type`: Tipo di esecuzione (`script` per script tradizionali).
* `message`: Il messaggio inviato ai log di sistema interni (`/var/log/system/latest.log`) quando l'azione viene invocata.
* `description`: **La stringa visualizzata nel menu a tendina della WebGUI (es. nel modulo Cron).**

3. Salva e chiudi l'editor.
4. Imposta i giusti permessi di lettura per il file di configurazione:
```bash
chmod 644 /usr/local/opnsense/service/conf/actions.d/actions_sync_ping.conf

```



---

## Passo 3: Registrazione e Test da Riga di Comando

Il demone `configd` memorizza le azioni all'avvio. Ogni volta che si modifica o si aggiunge un file in `actions.d`, il servizio va riavviato.

1. Riavvia il demone `configd`:
```bash
service configd restart

```


2. Esegui il test dell'azione tramite lo strumento nativo `configctl`:
```bash
configctl sync_ping run

```



### Analisi dei risultati del Test:

* **Il terminale torna a capo vuoto**: L'azione è corretta. Lo script è stato eseguito, ha riscontrato che il ping funziona ed è terminato correttamente.
* **Error (127)**: Significa *Command not found*. Verifica che il percorso specificato nella riga `command:` del file `.conf` sia identico a quello dello script sul disco, che lo script sia eseguibile (`chmod +x`) e che la prima riga dello script sia esattamente `#!/bin/sh` (senza caratteri speciali invisibili `\r` dovuti a copia-incolla da Windows).
* **Action not allowed or missing**: `configd` ha scartato il file `.conf` a causa di un errore di sintassi o permessi errati sul file `.conf`.

---

## Passo 4: Schedulazione tramite la WebGUI (Cron)

Una volta che il comando `configctl sync_ping run` risponde con successo in CLI, la WebGUI è pronta per mostrarlo nativamente.

1. Apri il browser e accedi alla WebGUI di OPNsense.
2. Naviga su **System ➔ Settings ➔ Cron**.
3. **Importante**: Svuota la cache del browser per forzare il ricaricamento dei comandi eseguendo un *Hard Refresh* (`Ctrl + F5` su Windows/Linux o `Cmd + Shift + R` su Mac).
4. Clicca sul pulsante **+** (Aggiungi) in basso a destra per creare un nuovo Job.
5. Configura i parametri temporali (es. inserisci `*/5` in *Minutes* per eseguirlo ogni 5 minuti).
6. Apri il menu a tendina del campo **Command**: troverai la voce **`SyncPing Connectivity Check`** (generata dal campo `description` del file `.conf`). Selezionala.
7. Clicca su **Save** e poi sul pulsante **Apply** in alto nella pagina per rendere effettiva la pianificazione.

Da questo momento, il sistema eseguirà in background il controllo in modo nativo e pulito.
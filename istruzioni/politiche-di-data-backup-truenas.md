# Politiche di Data Backup su TrueNAS

Questo documento descrive la policy ufficiale di protezione dei dati (Data Protection) del Lab tramite Snapshots ZFS e Replication Tasks. L'obiettivo è garantire il disaster recovery riducendo al minimo l'accumulo di "spazzatura" (snapshot orfani).

---

## 1. Periodic Snapshot Tasks (Le "Fotografie")
Il *Periodic Snapshot Task* è il sistema con cui TrueNAS scatta una foto istantanea (in sola lettura) dello stato del file system in un preciso istante temporale. Questi dati risiedono fisicamente sullo stesso disco dei dati originali.

### Regole d'Oro di Configurazione:
*   **Snapshot Lifetime (Ritenzione):** **DEVE SEMPRE ESSERE IMPOSTATA** (es. `1 WEEK` o `2 WEEKS`). Mai lasciare il campo illimitato, altrimenti TrueNAS conserverà gli snapshot per l'eternità, finendo per riempire totalmente il pool.
*   **Schedule (Frequenza):** Evitare l'impostazione `Hourly` su macro-dataset di radice che ospitano container o K3s (`.ix-virt`, `ix-apps`).
    *   *Consigliato:* `Daily` (una volta al giorno di notte).
    *   *Se necessario un RPO più stretto:* usare "Custom" per eseguire ogni 12 ore impostando `Minute: 0`, `Hour: */12`.
*   **Recursive (Ricorsione):** Se si spunta questa casella puntando alla radice di un pool (es. `stripe`), TrueNAS creerà contemporaneamente uno snapshot distinto per *ogni singolo micro-dataset figlio*. Moltiplicato per una frequenza oraria, genera decine di migliaia di snapshot morti nel giro di poche settimane.
    *   *Best Practice:* Disabilitarlo se si vuole backuppare selettivamente (creando task separati solo per `games` o cartelle K8s vitali). Se tenuto abilitato, compensare abbassando le frequenze a `Daily` o abbassando la Lifetime.
*   **Allow Taking Empty Snapshots ❌:** **Sempre senza spunta.** Insegna a TrueNAS a saltare il turno se nessun disco o file ha subìto la minima alterazione dal turno di backup precedente. Impedisce l'intasamento dell'interfaccia con centinaia di snapshot vuoti (0 byte).

---

## 2. Replication Tasks (Il vero Backup Fisico)
Il *Replication Task* è il "motore" di TrueNAS. Risoluta l'impossibilità di usare uno snapshot interno in caso di morte hardware del disco SSD. Questo task copia fisicamente blocco-per-blocco i dati dal disco veloce (`stripe`) al disco meccanico di archiviazione protetto (`oliraid/backup-stripe`).

### Regole d'Oro di Configurazione:
*   **Sorgente ("Grilletto"):** Non deve basarsi su uno schedule a tempo, ma ascoltare passivamente lo snapshot. Sotto *Periodic Snapshot Tasks*, selezionare l'esatto task configurato nel Capitolo 1. Quando il Capitolo 1 finisce, questo task si sveglia e copia i dati differenziali.
*   **Snapshot Retention Policy:** Usare sempre l'opzione magica **`Same as Source`**. Questa impostazione permette a TrueNAS di sincronizzare automaticamente l'eliminazione dei vecchi snapshot. Quando il task originario scarta uno snapshot scaduto da 1 settimana, il comando viene propagato sul disco di backup, mantenendoli dimensionalmente speculari e leggeri.

---

## 3. Gestione Emergenze ZFS (Lo "Spazzaneve")
In caso di errata configurazione passata del *Periodic Snapshot Task* (es. assenza di *Lifetime*), l'accumulo supera rapidamente le decine di migliaia di istantanee. L'interfaccia WebUI Web di TrueNAS (`Data Protection > Snapshots`) si impallerà nel tentativo di caricarli.

La pulizia deve essere fatta via Terminale (SSH) o Shell di sistema usando l'utente `root` o tramite `sudo`.

### Script di Puzilia (`prune.sh`)
Questo semplice ma potentissimo script cerca e distrugge automaticamente tutto ciò che è più vecchio dei giorni specificati, saltando inteligentemente quegli snapshot che sono attivamente "clonati" (in uso da VM Live).

```bash
#!/bin/bash
# Impostiamo quanti giorni VOGLIAMO conservare. Tutti quelli creati PRIMA verranno disintegrati.
DAYS_TO_KEEP=7

# UNIX Timestamp Date calculation
LIMIT=$(date -d "-$DAYS_TO_KEEP days" +%s)

# Elenca in formato pulito e UNIX-Stamp per permettere controlli matematici sul tempo
zfs list -H -t snapshot -o name,creation -p | while read -r SNAP_NAME CREATION_TIME; do
    if [ "$CREATION_TIME" -lt "$LIMIT" ]; then
        echo "Distruggo snapshot orfano: $SNAP_NAME"
        zfs destroy "$SNAP_NAME"
    fi
done
```

Esecuzione:
1. `nano prune.sh` (Incolla il codice e salva).
2. `chmod +x prune.sh` (Lo rende eseguibile).
3. `sudo ./prune.sh` (Esegue da Amministratore ZFS).
4. `zfs list -H -t snapshot | wc -l` (Verifica l'abbassamento netto del totale file superstiti).

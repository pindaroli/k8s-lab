# Gestione Log Ollama (Mac Studio)

Questa documentazione riassume la strategia e le scelte tecniche effettuate per la gestione dei log di Ollama e del suo monitoraggio.

## Strategia
Abbiamo scelto di seguire le **Best Practice di macOS** (Apple Developer Guidelines) per garantire ordine, facilità di debugging e protezione del disco fisso (evitando che i log crescano all'infinito).

### Scelte Chiave:

1. **Percorso Standard**: I log risiedono in `~/Library/Logs/ollama-monitoring/`. Questa è la cartella utente standard in cui i processi su macOS dovrebbero scrivere, rendendoli facilmente individuabili tramite l'app *Console* o il terminale.
2. **Separazione dei Log**:
    - `ollama.log`: Contiene esclusivamente l'activity del motore Ollama (caricamento modelli, errori GPU, inferenza).
    - `ollama-metrics.log`: Contiene i log del proxy di monitoraggio (errori di scraping, comunicazione con VictoriaMetrics).
    *Razionale*: In caso di malfunzionamento, è possibile distinguere immediatamente se il problema è nell'IA o nel monitoraggio.

## Rotazione Automatica (`newsyslog`)
Per evitare che i log consumino tutto lo spazio disco (importante su un server AI con 64GB di RAM ma disco finito), abbiamo configurato il tool di sistema `newsyslog`.

**Configurazione (`/etc/newsyslog.d/ollama.conf`):**
- **Soglia di Rotazione**: 10 MegaByte (`10240 KB`).
- **Ritenzione**: Mantenimento degli ultimi **5 log** storici.
- **Compressione**: I log vecchi vengono compressi in formato `.gz` per risparmiare spazio.
- **Frequenza**: Controllo ogni 7 giorni (se la soglia di 10MB non viene raggiunta prima).

## Manutenzione e Debug

### Vedere i log in tempo reale:
```bash
tail -f ~/Library/Logs/ollama-monitoring/*.log
```

### Controllare lo stato della rotazione:
```bash
# Simula la rotazione per vedere se la configurazione è valida
sudo newsyslog -nv /Users/olindo/Library/Logs/ollama-monitoring/ollama.log
```

## Riferimenti
- **LaunchAgent Engine**: `~/Library/LaunchAgents/homebrew.mxcl.ollama.plist`
- **LaunchAgent Exporter**: `~/Library/LaunchAgents/org.norskhelsenett.ollama-metrics.plist`
- **Configurazione Rete**: [rete.json](file:///Users/olindo/prj/k8s-lab/rete.json)

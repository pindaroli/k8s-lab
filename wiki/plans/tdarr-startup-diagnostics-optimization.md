---
title: "Piano: Ottimizzazione Diagnostica Avvio Tdarr Node"
type: plan
status: archived
certified_for_ai: false
created_at: 2026-06-27
archived_at: 2026-06-27
---

# Piano: Ottimizzazione Diagnostica Avvio Tdarr Node

> [!NOTE]
> **Stato**: ✅ **CONCLUSO & OPERATIVO (2026-05-23)**
> **Obiettivo**: Impedire al binario `Tdarr_Node` di avviarsi se il server Tdarr (`tdarr-api.pindaroli.org:8266`) non è raggiungibile. Questo evita lo spam di log Axios (AxiosError) chilometrici se l'avvio del nodo avviene quando il server non è ancora pronto o raggiungibile, limitando la diagnostica verbosa ai soli casi in cui l'avvio viene abortito definitivamente.

## 1. Analisi del Problema
Quando il Mac Studio si avvia o la rete non è stabilizzata, lo script di avvio `start_node.sh` verifica la connettività NFS e procede ad avviare il binario `Tdarr_Node`.
Se il Tdarr Server (`10.10.20.61:8266`) è momentaneamente giù o in fase di avvio:
- Il binario `Tdarr_Node` tenta continuamente di connettersi a `/api/v2/nodes/version-check`.
- Ad ogni fallimento, il logger interno di Tdarr serializza l'intero oggetto `AxiosError`, producendo un output log chilometrico contenente configurazione della richiesta, header, payload e stacktrace completo.
- Questo log viene mostrato a terminale via `tail -f` e salvato in `/Users/olindo/Library/Logs/tdarr-node.log`, rendendo difficile notare se si tratta di un'interruzione temporanea o di un problema di rete permanente.

## 2. Modifiche Proposte

### Script di Avvio: [start_node.sh](file:///Users/olindo/prj/k8s-lab/tdarr/node/start_node.sh)
Introdurremo un controllo preventivo di connettività TCP sulla porta `8266` di `tdarr-api.pindaroli.org` analogo a quello del server NFS.
- **Ciclo di Retry Sintetico**: Eseguirà fino a 12 tentativi distanziati di 5 secondi l'uno (60 secondi totali). Ad ogni tentativo fallito stamperà una singola riga di avviso:
  `⚠️ Server Tdarr (tdarr-api.pindaroli.org:8266) non raggiungibile. Riprovo in 5s...`
- **Avvio Solo se Connesso**: Se il server risponde, lo script procede ad avviare `Tdarr_Node`.
- **Abort & Diagnostica Dettagliata**: Se dopo 60 secondi il server continua ad essere irraggiungibile, lo script interrompe l'esecuzione (`exit 1`) e **solo allora** stampa la diagnostica dettagliata di rete:
  - Test ping verso `tdarr-api.pindaroli.org`
  - Stato dettagliato della porta `8266` via `nc`
  - Routing di rete per l'IP del server.

## 3. Piano di Verifica
1. **Test Connettività Normale**: Con il cluster K8s e il pod Tdarr attivi, avviare lo script e verificare che rilevi istantaneamente il server ed esegua `Tdarr_Node` regolarmente.
2. **Test Connettività in Errore (Dry-Run / Server Spento)**: Simulare il fallimento puntando temporaneamente a un IP o porta errati (es. `8269`) nello script. Verificare che:
   - Stampe solo gli avvisi sintetici ogni 5 secondi.
   - Al termine dei 12 tentativi, esca con errore (`exit 1`) stampando la diagnostica dettagliata completa.

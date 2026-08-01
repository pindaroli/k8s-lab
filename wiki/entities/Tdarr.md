---
title: "Tdarr (Distributed Transcoding)"
last_updated: "2026-05-23"
confidence: "High"
tags:
  - "#app"
  - "#media"
  - "#transcoding"
provenance:
  - "tdarr/configs/Tdarr_Node_Config.json"
---

# Tdarr (Distributed Media Processing)

Tdarr è il sistema di transcodifica distribuito utilizzato per convertire la libreria media in formato HEVC (H265) in modo automatizzato.

## 1. Architettura
Il sistema è diviso in due componenti principali:
1.  **Tdarr Server & Internal Node**: Gira come container nel [[Talos_Cluster]] (Namespace `arr`). Gestisce il database e la dashboard.
2.  **External Node (Mac Studio)**: Un nodo esterno ad alte prestazioni (`10.10.20.100`) che utilizza la potenza della GPU/VideoToolbox del Mac Studio M2 Ultra.

## 2. Configurazione Nodo Mac Studio
- **Script di Avvio**: `tdarr/node/start_node.sh`.
- **Lancio allo Startup**: Gestito tramite il launcher AppleScript nativo (`Avvia-Tdarr-Node.app`) posizionato sulla Scrivania per aggirare le restrizioni di sicurezza di Ghostty (Vedi dettagli completi in [[Ghostty_Workaround]]).
- **Path Translators**: Mappa i percorsi interni del server (`/media`, `/temp`) con quelli locali del Mac (`/Volumes/arrdata/media`, `/tmp/tdarr-cache`).
- **Automazione Mount**: Utilizza `sudoers` per montare le share NFS senza password (Vedi [[TrueNAS]]).

## 3. Modello di Esecuzione in Background (Nohup & Tail)
Per consentire l'avvio automatico all'accesso GUI ma evitare che la chiusura manuale del terminale interrompa il nodo (causando crash da `SIGHUP` o `SIGPIPE`), lo script `start_node.sh` adotta una strategia robusta di distacco del processo:

1. **Verifica Rete & Mount Automontati (Sequenziale)**:
   * **Verifica 1 (NFS/Rete Generale)**: Effettua un controllo preventivo di ping verso il server NFS (`10.10.10.50`) con un retry loop di sicurezza (fino a 60 secondi) per attendere la prontezza della rete o l'avvio del server storage.
   * **Verifica 2 (Tdarr Server)**: Effettua una verifica TCP sulla porta `8266` di `tdarr-api.pindaroli.org` con attese sintetiche a riga singola (fino a 60 secondi). Questo impedisce l'avvio del binario Tdarr Node e i conseguenti cicli di crash con log Axios verbosi se il Tdarr Server è momentaneamente offline, mostrando una diagnostica dettagliata di rete solo in caso di aborto definitivo.
   * **Mount NFS**: Successivamente, verifica ed esegue il mount della share NFS (`/Volumes/arrdata/media`) sfruttando i permessi `sudoers` passwordless dell'utente.
2. **Esecuzione Detached (`nohup`)**:
   Il binario viene lanciato in background separato dalla shell:
   ```bash
   nohup ./Tdarr_Node > /Users/olindo/Library/Logs/tdarr-node.log 2>&1 &
   ```
   Questo reindirizzamento previene il crash del processo per `SIGPIPE` quando il terminale di avvio viene chiuso.
3. **Live Stream dei Log (`tail -f`)**:
   Subito dopo il lancio, lo script esegue:
   ```bash
   tail -f /Users/olindo/Library/Logs/tdarr-node.log
   ```
   Questo mostra i log in tempo reale all'apertura del terminale. Quando l'utente chiude la finestra, `tail` viene arrestato, ma il processo `Tdarr_Node` continua a funzionare perfettamente in background.

## 4. Storage e Cache
- **Libreria**: `/Volumes/arrdata/media` (NFS su TrueNAS).
- **Cache (Local SSD macOS)**: `/tmp/tdarr-cache`. Sfrutta l'SSD NVMe ad alte prestazioni del Mac Studio per transcodificare a banda ultra-larga. Viene ripulita automaticamente da macOS ad ogni riavvio del sistema.

## 5. Logica di Transcodifica (Flows)
- Si utilizzano i **Tdarr Flows** invece dei plugin classici per una gestione più granulare.
- Workflow: `Check Health` -> `Backup` -> `HEVC Transcode` -> `Verify` -> `Replace`.

## 6. Gestione e Monitoraggio (Cheatsheet)
### Vedere i log in tempo reale
Per ispezionare l'output di transcodifica:
```bash
tail -f ~/Library/Logs/tdarr-node.log
```

### Controllare se il processo è attivo
```bash
ps aux | grep Tdarr_Node
```

### Arrestare il nodo manualmente
```bash
killall Tdarr_Node
```

## 7. Ottimizzazione Log (Axios Error Patch)
Per evitare che gli errori di connessione Axios (ad esempio se il server Tdarr è momentaneamente irraggiungibile all'avvio) generino dump JSON chilometrici ("teatrali") che intasano inutilmente i log, viene applicata una patch dinamica a runtime:

- **File Patch**: `tdarr/node/patch_axios_errors.js`.
- **Iniezione**: Caricata tramite la variabile `NODE_OPTIONS="--require ..."` all'interno di `start_node.sh`.
- **Comportamento (Soluzione 2)**: Durante i primi **120 secondi** (fase critica di avvio), intercetta `AxiosError` per renderne non enumerabili le proprietà pesanti (`config`, `request`, `response`) e compattarne drasticamente il metodo `.toJSON()`. Trascorsi 2 minuti, la patch si disattiva automaticamente ripristinando il comportamento diagnostico di default.

## Relazioni
- Dashboard accessibile via: [[Traefik]] (`tdarr-internal.pindaroli.org`).
- Dipende da: [[TrueNAS]] per i file sorgente.
- Comunica con: API Server su `tdarr-api.pindaroli.org` (Porta 8266).

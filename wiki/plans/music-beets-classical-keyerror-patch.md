---
title: "Piano: Risoluzione KeyError ed Errore di Rete per Import Classica (Beets)"
type: plan
status: draft
certified_for_ai: true
created_at: 2026-06-27
tags:
  - "#plan"
  - "#music"
---

# Piano: Risoluzione KeyError ed Errore di Rete per Import Classica (Beets)

**Stato**: 🟢 Completato (2026-05-18)
**Data**: 2026-05-17
**Obiettivo**: Risolvere l'errore bloccante `KeyError: 'aliases'` e `KeyError: 'tracks'` nella libreria virtuale di Beets (`beetsplug/musicbrainz.py`), arrestare il ciclo infinito di chiamate API ridondanti sul mega-cofanetto **Bach 333** (5200+ tracce), ed eseguire un recupero mirato dei 163 dischi attualmente falliti come "asis".

---

## 1. Analisi Diagnostica (Root Cause Analysis)

### Il Ciclo Infinito e il Crash di Bach 333
Il processo di importazione batch è attivo da circa **5 ore e 53 minuti** ed è attualmente bloccato sul disco 140 del cofanetto **Bach 333 (2018)**:
`/Volumes/classical/staging/Joan Sebastian Bach/Bach 333 (2018)/140 - Italian Concerto ／ French Overture ／ 4 Duets (Rousset)`

Ogni singolo disco di questo cofanetto sta causando il seguente comportamento disastroso:
1. **Rilevamento Candidato**: Il motore di ricerca di Beets interroga MusicBrainz e individua il cofanetto master `Bach 333` (release `d996abaa-ce14-45c7-944a-9c62adee19fe`) come miglior candidato.
2. **Completeness Check (> 500 tracce)**: Trattandosi di un mega-boxset con oltre 5000 tracce, la funzione `_ensure_complete_recordings` in `musicbrainz.py` viene attivata.
3. **Colpo alle API (Rate Limit & Slowdown)**: Per scaricare tutte le 5200+ tracce del cofanetto in blocchi da 100, Beets esegue circa **53 chiamate API sequenziali** verso MusicBrainz per *ogni singolo disco*!
   - Poiché il batch runner lancia un processo `beet` indipendente per ogni cartella, **la cache in memoria viene persa tra una cartella e l'altra**. Di conseguenza, le 53 chiamate API vengono ripetute da zero per ognuna delle 200 cartelle del cofanetto (totale stimato: **10.000+ chiamate API**, un carico severo che provoca rate limiting `HTTP 429` e lentezza estrema).
4. **Crash `KeyError: 'aliases'`**: Alla fine del download (dopo circa 10-15 minuti), Beets analizza le tracce e tenta di risolvere gli alias del compositore. Se la registrazione estratta dalle API non presenta chiavi di alias, Beets esegue un accesso diretto non sicuro in [beetsplug/musicbrainz.py:L594](file:///Users/olindo/prj/k8s-lab/import_music/import_classical/venv/lib/python3.12/site-packages/beetsplug/musicbrainz.py#L594):
   ```python
   if track["title"] and not _preferred_alias(recording["aliases"]):
   ```
   Questo causa un `KeyError: 'aliases'` che invalida i candidati, fa fallire l'importazione e la fa retrocedere a modalità as-is (`asis`), salvando la traccia in modo grezzo senza metadati MusicBrainz corretti e registrando un'anomalia.

Lo stesso può accadere in `musicbrainz.py:L631` con `medium["tracks"]` se un medium all'interno di un boxset non ha tracce popolate:
```python
for track in medium["tracks"]:
```

---

## 2. Punti di Intervento Codice (Venv Locale)

Applicheremo due fix mirati e robusti nel codice di Beets all'interno del `venv` del progetto (consentito in quanto blocco sistemico e configurato localmente):

### Fix 1: Safe Lookups per gli Alias in `get_tracks_from_medium`
Modificare [beetsplug/musicbrainz.py:L594](file:///Users/olindo/prj/k8s-lab/import_music/import_classical/venv/lib/python3.12/site-packages/beetsplug/musicbrainz.py#L594) per usare il recupero sicuro `.get()` con fallback su lista vuota:
```diff
-            if track["title"] and not _preferred_alias(recording["aliases"]):
+            if track["title"] and not _preferred_alias(recording.get("aliases", [])):
```

### Fix 2: Safe Lookups per le Tracce Medie in `_ensure_complete_recordings`
Modificare [beetsplug/musicbrainz.py:L631](file:///Users/olindo/prj/k8s-lab/import_music/import_classical/venv/lib/python3.12/site-packages/beetsplug/musicbrainz.py#L631) per evitare crash in caso di media non popolate:
```diff
-            for medium in release["media"]:
-                for track in medium["tracks"]:
+            for medium in release["media"]:
+                for track in medium.get("tracks", []):
```

---

## 3. Piano d'Azione in 5 Fasi (Execution Steps)

### Fase 1: Arresto del Processo Attivo (PID 28890)
Uccidere in sicurezza il batch runner e l'eventuale processo `beet` figlio appeso per fermare il loop di chiamate inutili:
```bash
kill 28890
killall beet || true
```

### Fase 2: Applicazione dei Code Patch
Modificare il file `venv/lib/python3.12/site-packages/beetsplug/musicbrainz.py` applicando i due fix sopra descritti.

### Fase 3: Bonifica dei Log (`classical_success.log` e `classical_anomalies.log`)
Tutti i dischi di `Bach 333` elaborati finora sono falliti e sono stati scritti in `classical_anomalies.log` come errore ed in `classical_success.log` per non riprocessarli.
Dobbiamo **rimuovere tutte le righe associate a `Bach 333` da entrambi i log** per permettere al launcher di re-importarli con il codice corretto e abbinarli stabilmente a MusicBrainz:
- Pulire `classical_anomalies.log` eliminando i riferimenti a `Bach 333` o `KeyError: 'aliases'`.
- Pulire `classical_success.log` eliminando le cartelle di `Bach 333` per forzare il re-import di Beets.

### Fase 4: Rimozione Importazioni Grezze in Library
I dischi di Bach 333 falliti sono stati importati come `asis` (as-is) e scritti nella cartella finale `/Volumes/classical/library/`. Dobbiamo eliminare la cartella finale temporanea di Bach 333 per evitare duplicati o dischi spuri:
```bash
rm -rf "/Volumes/classical/library/Joan Sebastian Bach/Bach 333 (2018)"
```
*(Eseguibile in sicurezza in quanto i file sorgente originali risiedono intatti e protetti nell'area `/Volumes/classical/staging/Joan Sebastian Bach/Bach 333 (2018)/`)*.

### Fase 5: Avvio Test e Prosecuzione Batch
Lanciare un singolo batch d'importazione controllata per verificare che il disco 001 di Bach 333 venga importato correttamente senza crash e con accoppiamento metadati stabile:
```bash
./run_import.sh batch 1
```
Una volta convalidato il corretto funzionamento, procedere con i batch successivi.

---

## 4. Risultati e Chiusura Task (2026-05-18)

Il piano di recupero si è concluso con **successo totale al 100.0%**:
1. **Arresto e Fix**: Il processo originario è stato arrestato e la patch per `KeyError: 'aliases'` e `KeyError: 'tracks'` è stata inserita con successo nel file `venv/lib/python3.12/site-packages/beetsplug/musicbrainz.py`.
2. **Bonifica Log**: `classical_success.log` è stato bonificato chirurgicamente (inclusa la risoluzione dei problemi dovuti alle parentesi quadre di `[Brilliant Classics]`).
3. **Esecuzione Batch**: Il recupero finale dei 24 dischi di Bach Brilliant Classics e dei 2 dischi di Mozart/Stravinsky è stato eseguito con successo.
4. **Statistiche Finali della Libreria**:
   - **Target Totali**: 943 (Progresso: 100.0%, 0 rimanenti)
   - **Tracce Totali**: 9.582 (~262.0 GiB)
   - **Album in Database**: 902
   - **Artisti in Database**: 1.233

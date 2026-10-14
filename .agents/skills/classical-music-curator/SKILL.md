---
name: classical-music-curator
type: skill
description: "Ricerca critica, curatela discografica e download assistito di musica classica tramite arrstack-mcp (Prowlarr e qBittorrent). Presenta comparativamente le 7 migliori incisioni per qualità artistica e tecnica, con tracker/indexer opzionale e gate di scelta vincolante prima del download con categoria lidarr-classical."
when_to_use: "Quando l'utente richiede di cercare o scaricare brani, opere, sinfonie, concerti o quartetti di musica classica indicando autore e opera (con tracker opzionale)."
status: active
tags:
  - servarr
  - classical
  - music
  - prowlarr
  - qbittorrent
---

# Classical Music Curator Skill (`classical-music-curator`)

## 🗣️ Trigger Phrases Riconosciute
Lo skill si attiva automaticamente quando l'utente usa formule come:
- `scarica classica <autore> <opera> [su <tracker>]`
- `cerca <opera> di <autore> [su <tracker>]`
- `trova esecuzioni di <opera> [su <tracker>]`
- `curatore classica <autore> <opera>`
- `scarica con categoria lidarr-classical <opera>`

---

## 🎯 Parametri di Input
* `<autore>` / `<compositore>` (**Obbligatorio**): es. *Shostakovich*, *Mahler*, *Bach*, *Beethoven*, *Brahms*.
* `<opera>` (**Obbligatorio**): es. *Sinfonia n. 5*, *Variazioni Goldberg*, *Quartetto op. 110*.
* `[tracker / indexer]` (**Opzionale**):
  - Se specificato (es. *RuTracker*, *LimeTorrents*, *The Pirate Bay*): risolve l'ID corrispondente e filtra la ricerca.
  - Se non specificato: interroga **tutti gli indexer disponibili** (`indexer_ids=""`).
  - *Resilienza*: se la ricerca globale su tutti gli indexer va in timeout (>30s a causa di tracker lenti o non reattivi), ritenta automaticamente su RuTracker (`13`) e LimeTorrents (`6`), informando l'utente.

---

## 🎯 Obiettivo & Filosofia Operativa
Fornire all'ascoltatore un servizio di curatela discografica di alto livello per la musica classica:
1. **Ricerca mirata e flessibile**: Interrogazione di tutti gli indexer attivi o del tracker specifico richiesto.
2. **Valutazione critica a 7 opzioni**: Selezione delle 7 migliori incisioni bilanciando qualità artistica (premi, direttori storici, orchestre di riferimento) e fedeltà tecnica audiofila (Studio Master 24-Bit `[TR24][OF]`, SACD DSD o CD RedBook EAC/AccurateRip da etichette di pregio come DG, Decca, Philips, BIS, Reference Recordings, Supraphon, Chandos, Harmonia Mundi).
3. **User Decision Sovereignty (GATE DI STOP)**: L'AI NON scarica MAI in autonomia. Mostra la tabella comparativa e si ferma, attendendo la decisione dell'utente.
4. **Instradamento Corretto**: Invio su qBittorrent esclusivamente con categoria `lidarr-classical` verso lo staging dedicato (`/media/downloads/lidarr-classical`).

---

## ⚡ Workflow Operativo in 3 Fasi

### Fase 1: Ricerca & Curatela (I 7 Candidati)
1. **Risoluzione Tracker (Opzionale)**:
   - Se specificato:
     - `RuTracker` -> ID `13`
     - `LimeTorrents` -> ID `6`
     - `The Pirate Bay` -> ID `10`
     - `FileMood` -> ID `4`
     - Altri indexer: consultare `prowlarr_list_indexers` se necessario.
   - Se non specificato:
     - Impostare `indexer_ids=""` (tutti gli indexer).
2. **Esecuzione Ricerca**:
   - Invocare `prowlarr_search(query="<Autore> <Opera>", indexer_ids="<ID_OPZIONALE>")`.
   - Se la query globale restituisce timeout (>30s), eseguire il fallback automatico con `indexer_ids="13,6"`.
3. **Selezione delle 7 Migliori Incisioni**:
   - **[1] Riferimento Moderno Audiofilo**: Master recente 24-Bit / 96-192 kHz FLAC `[TR24][OF]`, massima trasparenza acustica.
   - **[2] Benchmark Storico Ineludibile**: Registrazione storica epocale (es. Bernstein, Mravinsky, Karajan, Walter, Kleiber, Furtwängler).
   - **[3] Lettura Filologica / HIP**: Su strumenti originali d'epoca e prassi storicamente informata (Harnoncourt, Gardiner, Herreweghe, Savall).
   - **[4] Vincitore Premi della Critica**: *Gramophone Award*, *Diapason d'Or*, *BBC Music Magazine*, *Choc de Classica*, *Grammy*.
   - **[5] Ensemble / Solista Specialista**: Affinità elettiva con l'autore (es. Borodin per Shostakovich, Quartetto Italiano per Beethoven).
   - **[6] Alternativa Audiofila Specialistica**: Incisione da etichetta audiophile (Reference Recordings, BIS, PentaTone SACD, Chandos).
   - **[7] Pathos Teatrale / Live Esclusivo**: Registrazione dal vivo memorabile per tensione interpretativa e impeto espressivo.

4. **Presentazione all'Utente**:
   Tabella Markdown strutturata:
   | # | Opera & Interpreti | Anno & Etichetta | Formato Audio | Dimensioni & Seeds | Tracker | Valore Critico / Note |
   |---|-------------------|------------------|---------------|-------------------|---------|-----------------------|
   | [1] | ... | ... | FLAC 24-192 | 1.8 GB (6 seeds) | RuTracker | ... |
   | ... | ... | ... | ... | ... | ... | ... |

---

### Fase 2: GATE DI STOP INVALICABILE (Attesa Scelta Utente)
> [!CRITICAL]
> **DIVIETO ASSOLUTO DI DOWNLOAD AUTOMATICO**
> Durante la Fase 1 è TASSATIVAMENTE PROIBITO invocare `prowlarr_grab`, `qbt_add`, `qbt_add_magnet` o qualsiasi tool di download.
> L'agente DEVE terminare il messaggio con la richiesta esplicita all'utente:
> *"Quale di queste 7 edizioni preferisci scaricare? (indica il numero da [1] a [7] o l'interprete)"*
> e attendere la risposta.

---

### Fase 3: Download & Verifica Test-Driven (Post-Scelta)
1. Ricevuta la scelta dell'utente:
   - Invocare `prowlarr_grab(index=<N>, category="lidarr-classical")`.
2. Eseguire la verifica reale con `qbt_torrent_details`:
   - Verificare che il torrent sia attivo e che `save_path` contenga `/media/downloads/lidarr-classical`.
3. Notificare l'utente con il riepilogo del torrent avviato.

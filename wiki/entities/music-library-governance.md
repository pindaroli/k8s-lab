# Music Library Governance

Questo documento definisce gli standard e le convenzioni per la gestione della libreria musicale nel progetto GEMINI.

## 📂 Struttura del File System

La libreria è organizzata per garantire la massima compatibilità con **Lidarr** e **Jellyfin**.

### Album Standard
- **Percorso**: `{Artista}/{Album} ({Anno})/{Artista} - {Album} - {Traccia} - {Titolo}`
- **Esempio**: `Akon/Freedom (2008)/Akon - Freedom - 01 - Right Now (Na Na Na).mp3`

### Compilation e Colonne Sonore (OST)
- **Percorso**: `Compilations/{Album} ({Anno})/{Traccia} - {Titolo}`
- **Regola**: L'album deve avere il flag `compilation: True` e l'artista dell'album impostato su `Various Artists`.
- **Esempio**: `Compilations/School of Rock (2003)/01 - School of Rock.mp3`

### Singoli e Brani Sparsi
- **Percorso**: `Non-Album/{Artista}/{Titolo}`

---

## 🏷️ Standard di Metadati

### Naming Convention
- Tutti i file utilizzano il **Leading Zero** per le tracce (es. `01`, `02`) per mantenere l'ordine alfabetico corretto nel file system.
- L'anno dell'album è sempre incluso nel nome della cartella tra parentesi tonde.

### Qualità e Formati
- **FLAC**: Formato preferito per l'archiviazione (Lossless).
- **MP3/AAC**: Accettati per materiale raro o in attesa di upgrade via Lidarr.
- **Note**: Gli album non-FLAC pubblicati negli ultimi 15 anni sono considerati candidati prioritari per il rimpiazzo con versioni ad alta qualità.

---

## 🛠️ Strumenti e Plugin (Beets)

La bonifica e la gestione sono affidate a **Beets** con i seguenti plugin critici:

| Plugin | Scopo |
| :--- | :--- |
| `chroma` | Fingerprinting audio (AcoustID) per identificare brani con metadati errati. |
| `lastgenre` | Recupero automatico dei generi musicali da Last.fm. |
| `ihate` | Filtro automatico per escludere bootleg, video o formati indesiderati. |
| `zero` | Pulizia di tag superflui o commenti inseriti dai cracker/ripper. |
| `scrub` | Rimozione di tutti i tag non standard prima della riscrittura. |

---

## 📜 Procedure Operative

### Aggiunta di Nuova Musica
La musica scaricata deve passare per la "Landing Zone" (`music_backup`) tramite il comando `beet import` prima di essere esposta ai media server.

### Unificazione Artisti
In caso di nomi duplicati (es. `Us3` vs `US3`), utilizzare `beet modify` per uniformare al nome ufficiale presente su MusicBrainz.

### Modifica Massiva dei Dati (Regola di Sopravvivenza)
> [!CAUTION]
> **MAI eseguire `beet modify` usando query generiche o parziali (es. `album="Nome Album"`).** Questo può causare match collaterali distruttivi sull'intera libreria.
> - Usare SEMPRE query esatte se basate su testo (es. `album::^Nome Esatto$`) o, preferibilmente, identificatori univoci e percorsi assoluti.
> - Prima di eseguire un `modify`, si DEVE SEMPRE fare un `beet ls` con la stessa identica query per verificare preventivamente la lista dei file interessati.

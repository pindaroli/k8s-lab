---
title: "Piano: Tool CLI Interattivo per Pulizia Selettiva Torrent su qBittorrent"
type: plan
status: completed
certified_for_ai: true
created_at: 2026-10-16
tags:
  - "#servarr"
  - "#qbittorrent"
  - "#automation"
  - "#scripting"
  - "#storage"
---

# Piano: Tool CLI Interattivo per Pulizia Selettiva Torrent su qBittorrent

Il presente piano operativo definisce l'architettura, la progettazione e l'implementazione di uno strumento CLI interattivo e modulare (`scripts/servarr/cleanup_torrents.sh` e motore `cleanup_torrents.py`) per consentire la ricerca, il filtraggio avanzato temporale, percentuale e per categoria, la gestione flessibile delle eccezioni e la cancellazione atomica (compresi i file scaricati su disco) dei torrent gestiti da qBittorrent via REST API native.

Lo strumento adotta rigorosamente il protocollo REST con client HTTP nativo standard (zero dipendenze pip), integrando il supporto per la gestione sessione di qBittorrent v5.2.x (`QBT_SID_*` e status code 204), la decifratura trasparente delle credenziali tramite SOPS e la piena conformità allo standard [[go-launcher-script-pattern]] per l'integrazione immediata in `scripts/go.py`.

---

## 🗺️ Mappe Concettuali e Relazioni
- [[SCHEMA]] (Regole del Wiki, Governance e Protocollo Test-Driven)
- [[go-launcher-script-pattern]] (Standard per script auto-documentanti, CWD-independent ed eseguibili da `scripts/go.py`)
- [[Servarr]] (Architettura dello stack media e storage torrent su TrueNAS SCALE)
- [[2026-09-02-qbittorrent-5.2-auth-cookie-breaking-change]] (Specifiche autenticazione qBittorrent 5.2.x e gestione cookie di sessione)

---

## 1. Analisi dei Requisiti Funzionali

1. **Finestra Temporale Dinamica (`<data start>` e `<data end>`)**:
   - **Data Inizio (`<data start>`)**: Richiesta in input (formati accettati: `YYYY-MM-DD`, `YYYY-MM-DD HH:MM:SS` o alias come `today`, `yesterday`, `7d`, `30d`). Se viene fornita solo la data, l'orario viene impostato automaticamente a `00:00:00`.
   - **Data Fine (`<data end>`)**: Richiesta in input (stessi formati, default orario `23:59:59` per includere l'intera giornata).
   - **Validazione Cronologica**: Lo script verifica tassativamente che `<data end> >= <data start>`. In caso contrario, segnala l'errore a video e richiede nuovamente l'inserimento.
2. **Filtro Percentuale di Scaricamento (`<perc>`)**:
   - Richiesta in input della soglia percentuale massima di completamento (valore numerico tra 0 e 100, default 100%).
   - Criterio di selezione: percentuale di scaricamento del torrent minore o uguale a `<perc>` (`progress * 100 <= perc`).
3. **Selezione Categoria Dinamica**:
   - Interrogazione live delle categorie configurate su qBittorrent tramite endpoint `GET /api/v2/torrents/categories`.
   - Presentazione di un menu numerato interattivo:
     - `[0] Tutte (nessun filtro di categoria) [DEFAULT]`
     - `[1] autobrr-classical`
     - `[2] books`
     - `[3] lidarr`
     - `...`
   - Se l'utente preme Invio o sceglie `0`, vengono inclusi i torrent di qualsiasi categoria (inclusi quelli senza categoria). Se sceglie una categoria specifica, la ricerca matcha rigorosamente tale categoria.
4. **Ricerca, Estrazione e Tabella Risultati**:
   - Interrogazione dell'endpoint REST `GET /api/v2/torrents/info`.
   - Filtraggio in memoria dei torrent che soddisfano simultaneamente:
     - `added_on >= timestamp(data start)`
     - `added_on <= timestamp(data end)`
     - `progress * 100 <= perc`
     - Categoria corrispondente (se diversa da "Tutte").
   - Presentazione a video di una tabella formattata con colonne fisse:
     - **# (Indice identificativo numerico progressivo: 1, 2, ... N)**
     - **Nome del Torrent**
     - **Categoria**
     - **Percentuale di Completamento** (es. `45.2%`)
     - **Data di Inserimento** (formato leggibile `YYYY-MM-DD HH:MM:SS`)
     - **Spazio Occupato / Scaricato** (es. `1.25 GB / 5.40 GB`)
   - Riepilogo complessivo del numero di elementi trovati e dello storage totale scaricato su disco.
5. **Gestione Esclusioni (`<elenco esclusioni>`)**:
   - Prompt: `Ci sono esclusioni da non cancellare? (y/N): `
   - In caso negativo (`n`, `no` o Invio): `<elenco esclusioni>` rimane vuoto.
   - In caso affermativo (`y`, `yes`, `s`, `si`):
     - Richiesta in input degli indici separati da virgola o intervalli (es: `1, 3, 5-8`).
     - Parsing e validazione degli indici inseriti.
     - Mostra l'elenco esplicito dei torrent salvati ed esclusi.
     - Ricalcolo e visualizzazione della lista netta dei torrent candidati all'eliminazione.
6. **Conferma di Sicurezza e Cancellazione Definitiva**:
   - Se la lista netta è vuota, lo script segnala che non vi è nulla da eliminare ed esce.
   - In presenza di torrent da cancellare, presenta un avviso chiaro in rosso:
     `⚠️  ATTENZIONE: Verranno eliminati definitivamente M torrent e TUTTI i relativi file dal disco!`
   - Prompt di conferma: `Confermi l'eliminazione definitiva con cancellazione dei file? (yes/no): `
   - Se l'utente digita `yes`: procede all'eliminazione via REST API `POST /api/v2/torrents/delete` con payload `hashes=<hash1>|<hash2>...` e `deleteFiles=true`.
   - Se l'utente digita `no` o qualsiasi altro valore: abortisce immediatamente l'operazione senza toccare alcun file né record (`Operazione annullata.`).
7. **Reportistica Finale e Statistiche**:
   - Stampa del numero esatto di torrent eliminati con successo.
   - Stampa della quantità complessiva di storage liberato espressa in GB (`completed_bytes / 1024^3`).

---

## 2. Architettura Tecnica e REST API qBittorrent

### 2.1 Connettività e Parametri di Connessione
- **Host / URL**:
  - Default: `http://10.10.20.50:8080` (TrueNAS SCALE Docker Bare Metal su VLAN 20) o via variabile d'ambiente `QBT_URL` / parametro CLI `--url`.
- **Credenziali**:
  - `QBT_USER`: default `admin` (o env / flag `--user`).
  - `QBT_PASS`: recuperato automaticamente da `secrets-sops/servarr-api-keys.enc.yaml` tramite comando `sops -d` o da variabile d'ambiente `QBT_PASS` / flag `--pass`.

### 2.2 Gestione Sessione REST API qBittorrent 5.2.x
L'autenticazione a qBittorrent 5.2.x non restituisce `HTTP 200 OK` con corpo `Ok.`, ma un codice `HTTP 204 No Content` impostando un cookie di sessione con naming dinamico `QBT_SID_<PORT>` (es. `QBT_SID_8080`) o `SID`.
Il modulo Python adotta un gestore di cookie nativo `http.cookiejar.CookieJar` abbinato a `urllib.request.build_opener`, garantendo:
1. Zero dipendenze esterne (solo libreria standard di Python 3).
2. Conservazione automatica e invio trasparente del cookie di sessione su tutte le chiamate successive.
3. Riconoscimento dello stato 200/204 come autenticazione riuscita.

### 2.3 Endpoint Coinvolti
| Azione | Metodo | Endpoint | Parametri / Payload |
| :--- | :--- | :--- | :--- |
| **Login** | `POST` | `/api/v2/auth/login` | `username=<user>&password=<pass>` |
| **Categorie** | `GET` | `/api/v2/torrents/categories` | - |
| **Elenco Torrent** | `GET` | `/api/v2/torrents/info` | (opzionale `category=<cat>`) |
| **Cancellazione** | `POST` | `/api/v2/torrents/delete` | `hashes=<hash1>\|<hash2>&deleteFiles=true` |

---

## 3. Struttura dei Componenti nel Repository

```text
scripts/servarr/
├── cleanup_torrents.sh    # Entrypoint wrapper Bash conforme a go-launcher-script-pattern
└── cleanup_torrents.py    # Motore logico Python (CLI interattiva, REST API, parsing e report)
```

### 3.1 Wrapper Shell (`scripts/servarr/cleanup_torrents.sh`)
- Rispetta il pattern architetturale [[go-launcher-script-pattern]]:
  - Riga 1: Shebang `#!/usr/bin/env bash`
  - Riga 2: Descrizione chiara per il menu `go.py`: `# Pulizia selettiva torrent su qBittorrent per data, percentuale e categoria`
  - Risoluzione dinamica di `SCRIPT_DIR` e `ROOT_DIR`.
  - Verifica automatica della disponibilità di `python3`.
  - Esportazione opzionale di `QBT_PASS` tramite `sops -d` se non già presente nell'ambiente.
  - Invocazione del motore Python passando tutti gli argomenti (`"$@"`).

---

## 4. Fasi Operative di Implementazione

### Fase 1: Creazione del Motore Core Python (`scripts/servarr/cleanup_torrents.py`)
- Implementazione della classe `QBittorrentClient`:
  - Metodi: `login()`, `get_categories()`, `get_torrents()`, `delete_torrents()`.
  - Gestione cookie `http.cookiejar`, gestione codici 200/204 e timeout di rete.
- Implementazione delle funzioni di utilità:
  - `parse_flexible_date(input_str, is_end_date)`
  - `parse_index_list(input_str, max_index)`
  - Formattatori per bytes (GB) e date.
- Implementazione del flusso interattivo da terminale (Wizard a 7 step).
- Supporto flag CLI per modalità non interattiva o di test:
  - `--dry-run`: Esegue tutta la ricerca, visualizza la tabella e simula la cancellazione senza inviare chiamate distruttive alle API.
  - `--url`, `--user`, `--pass`: Override parametri di connessione.

### Fase 2: Creazione del Wrapper Shell Eseguibile (`scripts/servarr/cleanup_torrents.sh`)
- Scrittura del file conforme a [[go-launcher-script-pattern]].
- Assegnazione dei permessi di esecuzione: `chmod +x scripts/servarr/cleanup_torrents.sh scripts/servarr/cleanup_torrents.py`.

### Fase 3: Validazione Test-Driven End-to-End
1. **Test Connessione & Autenticazione**: Verifica del login e recupero categorie live tramite script Python.
2. **Test Dry-Run con Filtri**:
   - Esecuzione di `scripts/servarr/cleanup_torrents.sh --dry-run` specificando intervallo temporale reale, percentuale e categoria.
   - Verifica della corretta renderizzazione della tabella e del calcolo dei GB.
   - Test del parsing delle esclusioni (singole e a intervallo: es. `1, 3`).
   - Verifica che in `--dry-run` nessuna richiesta di eliminazione venga inoltrata al demone.
3. **Verifica Integrazione Launcher**:
   - Esecuzione di `python3 scripts/go.py` per verificare che lo script appaia correttamente indicizzato nel menu interattivo.

### Fase 4: Consolidamento Documentale & Chiusura Piano
- Aggiornamento di `wiki/patterns/go-launcher-script-pattern.md` includendo lo script nel campo `in_use_by`.
- Aggiornamento di `todo.md` e delle mappe concettuali in `GEMINI.md`.
- Esecuzione degli script di validazione e rigenerazione:
  `python3 scripts/network/validate_network.py && python3 scripts/wiki/build_wiki_context.py`

---

## 💾 Stato di Ripristino (AI Save-State)
- **Fase Attiva**: Piano Concluso
- **Ultima Azione Completata**: Implementazione di cleanup_torrents.py, wrapper cleanup_torrents.sh, collaudo helper functions e test integrazione go.py completati al 100%.
- **Prossimo Passo Operativo**: Nessuno; il tool è pronto all'uso sia via `./scripts/servarr/cleanup_torrents.sh` sia tramite `./scripts/go.py`.
- **Blocchi/Decisioni Pendenti**: Nessuno.

---
title: "Incidente: Conflitto Metadati NFO, Locandine Multiple e Dumps DVD su Jellyfin"
type: incident
status: archived
certified_for_ai: false
date: 2026-09-13
severity: Medium
resolved: true
resolved_at: 2026-09-13T20:04:00Z
---

# Incident Report: Conflitto Metadati NFO, Locandine Multiple e Dumps DVD su Jellyfin (2026-09-13)

## Executive Summary
Durante l'audit della libreria multimediale su `/media/movies/` (pool ZFS `oliraid`), sono state riscontrate gravi anomalie visive nell'interfaccia di Jellyfin (schede film duplicate o triplicate, es. *La mala educación*) e un consistente spreco di spazio su storage TrueNAS.
L'indagine tecnica ha evidenziato due cause radice:
1. **Conflitto e proliferazione di file `.nfo`**: 352 cartelle presentavano file `.nfo` discordanti (conflitto tra `movie.nfo` in italiano generato automaticamente da FileBot AMC e file `<titolo>.nfo` storici o in lingua inglese ereditati dai torrent). Jellyfin, leggendo entrambi i metadati locali, generava schede multiple e dati incoerenti.
2. **Coesistenza di Dumps DVD (`VIDEO_TS`) e File Master `.iso`**: 10 cartelle film contenevano sia il file `.iso` master integro che una sotto-cartella estratta con file `.VOB` grezzi, inducendo Jellyfin a catalogare due volte lo stesso titolo e occupando circa 46.5 GB di spazio ridondante.

L'incidente è stato risolto ridefinendo la strategia dichiarativa dei metadati (adozione del pattern [[movie-metadata-and-artwork-architecture]]), disabilitando la creazione di file `.nfo` sia su Radarr che sul normalizzatore FileBot, bonificando 971 file `.nfo` e rimuovendo i 10 sotto-alberi `VIDEO_TS` duplicati, recuperando **158.90 GB** complessivi nella sessione.

---

## 1. Root Cause Analysis (RCA)

### 1.1 Conflitto dei Metadati Locali (.nfo) e Precedenza Jellyfin
- **Comportamento Jellyfin**: Jellyfin ha i *Metadata Readers* abilitati per default; quando scansiona una cartella film, i metadati letti dai file `.nfo` locali hanno priorità rispetto allo scraping online via API TheMovieDb (TMDb).
- **Collisione di Nomenclatura**:
  - FileBot AMC operava con `--def artwork=y`, scaricando locandine e generando obbligatoriamente `movie.nfo` con titolo e trama in italiano.
  - Molti download pregressi contenevano già un file `.nfo` nominato con il titolo del file video (es. `Nome Del Film (Anno).nfo`) o generato da vecchie configurazioni Kodi.
  - La presenza simultanea di due file XML con metadati e ID leggermente divergenti portava Jellyfin a frammentare la scheda del film, creando duplicati nell'interfaccia utente.

### 1.2 Dumps DVD Annidati (Doppia Entità per lo Scanner)
- In 10 titoli (tra cui *La mala educación*, *Il dottor Stranamore*, *Beetlejuice*, *Match Point*), coesisteva il file `.iso` e una cartella annidata `VIDEO_TS`.
- Lo scanner di Jellyfin supporta sia le immagini disco (`.iso`) che le directory DVD scompattate (`VIDEO_TS` contenente `VTS_01_1.VOB`, ecc.).
- Entrambi venivano processati come entità separate, raddoppiando l'impronta disco e visualizzando locandine multiple.

---

## 2. Azioni Correttive e Risoluzione

### 2.1 Allineamento Dichiarativo Ingestion Radarr
- Configurato dichiarativamente tramite REST API il consumer metadati `Kodi (XBMC) / Emby` (`id: 1`) su Radarr:
  - `enable`: `true`
  - `movieMetadata` (.nfo): `false` *(Divieto categorico di scrittura .nfo)*
  - `movieImages` (`poster.jpg`, `fanart.jpg`): `true` *(Salvataggio delle copertine grafiche locali sul NAS)*

### 2.2 Aggiornamento Normalizzatore Video FileBot (`pindaroli-arr-helm`)
- Modificato lo script [`normalize-video.sh`](file:///Users/olindo/prj/pindaroli-arr-helm/custom-docker-images/custom-normalizer/normalize-video.sh):
  - Mantenuto `--def artwork=y` per il download degli artwork fisici (`poster.jpg`, `fanart.jpg`, loghi).
  - Introdotta la pulizia automatica post-processo immediata:
    ```bash
    find "$TARGET_DIR" -maxdepth 2 -type f -name "*.nfo" -delete
    ```
- Eseguito il bump a `custom-normalizer:1.5.0` e chart Helm `servarr:1.9.9` (Revisione 174).
- Ricompilata e pubblicata l'immagine su GHCR ed eseguito il rollout restart di `servarr-qbittorrent`.

### 2.3 Bonifica Controllata su Storage TrueNAS (ZFS `oliraid`)
1. **Eliminazione 971 File `.nfo`**:
   - Eseguito dry-run di verifica preventiva: confermati 546 `movie.nfo` e 425 NFO specifici di release.
   - Rimossi tutti i 971 file `.nfo`. Preservati intatti tutti i 534 `folder.jpg`, 514 `backdrop.jpg` e i 433 file video.
2. **Eliminazione 10 Dump `VIDEO_TS` Ridondanti**:
   - Audit di sicurezza: verificata l'integrità del master `.iso` per 10 cartelle su 11. Esclusa e preservata la cartella *Le streghe di Salem* (in quanto priva di file ISO alternativo).
   - Rimossi i 10 sotto-alberi duplicati, liberando **46.54 GB** netti su ZFS.
   - Totale spazio recuperato nella sessione di manutenzione: **~158.90 GB**.

---

## 3. Validazione Post-Implementazione
1. **Verifica Audit Script (`audit_movie_duplicates.py`)**:
   - Sezione `CARTELLE PROBLEMI DI .NFO`: **Nessuna anomalia (0)**.
   - Sezione `CARTELLE DIVERSE CHE CONTENGONO LO STESSO FILM`: **Nessuna anomalia (0)**.
   - Sezione `CARTELLE CON VIDEO_TS O .ISO SDOPPIATI`: **0 duplicati** (solo il titolo non duplicato preservato).
2. **Verifica Jellyfin**:
   - Eliminati i conflitti di metadati; schede e locandine allineate e prive di sdoppiamenti.

# Contesto di Ripresa: Bonifica & Normalizzazione Mozart 225

Questo documento riassume lo stato dell'attività di ottimizzazione della tassonomia per la musica classica (in particolare per l'edizione monumentale **Mozart 225**), il problema bloccante riscontrato e la strategia di risoluzione approvata per la ripresa del lavoro.

---

## 📌 Stato dell'Arte & Lavori Completati
1. **Risoluzione Bug Routing Beets**:
   * Modificato `beets_classical_config.yaml` correggendo il condizionale da `%if{is_recital,...}` a `%if{$is_recital,...}` per forzare l'instradamento in `Monographs/` degli album monografici.
2. **Aggiornamento Database Beets per 29 CD Esclusi**:
   * Modificato ed eseguito lo script `standardize_complete_editions.py` che ha correttamente riconosciuto e aggiornato a database tutti i 29 CD mancanti con i metadati normalizzati e l'associazione al parentwork `Mozart 225 - 04 Theatre`, ecc.
3. **Il Blocco**:
   * Durante l'esecuzione reale di `/Users/olindo/prj/k8s-lab/import_music/import_classical/venv/bin/beet -c beets_classical_config.yaml move "Mozart 225"`, Beets è andato in crash con `FileNotFoundError` su:
     `/Volumes/classical/library/03 - Theatre (102-152)/CD-134 - Theatre - Così fan tutte.../134-25...flac`
   * I 29 CD recuperati non erano mai stati spostati da Beets prima d'ora. Poiché sono state rimosse le vecchie cartelle orfane dalla library e la cartella fisica in staging è stata rimossa, Beets non trova più i vecchi symlink fisici per poterli spostare.

---

## 🔍 Diagnosi Tecnica & Analisi Filesystem
* **NFS Mount**: `/Volumes/classical` punta al dataset ZFS `10.10.10.50:/mnt/oliraid/arrdata/classical` su TrueNAS.
* **Staging vuoto**: La cartella fisica reale `Wolfgang Amadeus Mozart` in `/Volumes/classical/staging/` risulta assente (ci sono solo Paisiello e Verdi).
* **ZFS Snapshots Rilevati**:
  Sotto `/Volumes/classical/.zfs/snapshot/` sono stati individuati due snapshot:
  1. `manual-prima-gestione-tassonomia-tipologia-2026-05-20_00-38` (fatto prima dell'inizio dell'attività)
  2. `manual-proma-reiorganizzazione-howrowitz-2026-05-19_23-27`
* **Errore Cache Client macOS**:
  Il client macOS riscontra un errore di `Stale NFS file handle` provando ad accedere allo snapshot `manual-prima-gestione-tassonomia-tipologia-2026-05-20_00-38` (a causa della cache degli inode NFS non allineata su macOS).

---

## 🚀 Strategia di Ripristino e Prossimi Passi (Domani)
La strategia ottimale, pulita e sicura per ripartire da uno stato coerente sul filesystem è la seguente:

1. **Rollback su TrueNAS**:
   * Eseguire il rollback del dataset `/mnt/oliraid/arrdata/classical` allo snapshot:
     👉 **`manual-prima-gestione-tassonomia-tipologia-2026-05-20_00-38`**
   * *Questo ripristinerà istantaneamente sia la cartella fisica in staging, sia i vecchi symlink orfani in library, azzerando gli errori NFS stale.*

2. **Riesecuzione di Beets Move**:
   * Lanciare il comando di spostamento definitivo di Mozart 225 sotto `Monographs/`:
     ```bash
     /Users/olindo/prj/k8s-lab/import_music/import_classical/venv/bin/beet -c /Users/olindo/prj/k8s-lab/import_music/import_classical/beets_classical_config.yaml move "Mozart 225"
     ```
   * *Beets troverà tutti i file fisici e i symlink originari e li sposterà ordinatamente sotto `library/Monographs/Wolfgang Amadeus Mozart/...` secondo le regole normalizzate.*

3. **Pulizia Finale**:
   * Eseguire la bonifica delle cartelle rimaste vuote e dei file nascosti `.DS_Store` / `._*` orfani in library.

---

## 🔮 PROMPT DI RIPRESA PER L'AI (Da incollare nella nuova chat)
> Ciao! Dobbiamo completare l'attività di bonifica e normalizzazione di "Mozart 225" nella libreria classica di Beets.
> Il contesto completo e i dettagli tecnici dell'attività si trovano salvati nel file markdown:
> `/Users/olindo/prj/k8s-lab/import_music/import_classical/context_resume_mozart225.md`
>
> **Aggiornamento di stato prima di iniziare**:
> Ho appena eseguito con successo su TrueNAS il rollback del dataset `/mnt/oliraid/arrdata/classical` allo snapshot `manual-prima-gestione-tassonomia-tipologia-2026-05-20_00-38`. Ora il filesystem è tornato allo stato integro originario, con tutti i vecchi symlink e la directory di staging al loro posto.
>
> Procediamo con i prossimi passi del piano:
> 1. Spiegami cosa intendi fare per verificare che il filesystem sia tornato online e corretto (senza errori stale NFS).
> 2. Esegui la verifica e poi procedi con lo spostamento reale via `beet move "Mozart 225"`.
>
> Ricorda di rispettare rigorosamente il protocollo operativo di autorizzazione preventiva (`[ATTENDO AUTORIZZAZIONE]`) prima di ogni comando di modifica.

---

## 🏁 Conclusione Attività (2026-05-21) — Consolidamento Perdita e Pulizia
A seguito di approfonditi controlli nei backup e negli snapshot di TrueNAS, si è riscontrato che i file fisici sorgenti di *Mozart 225* nello staging erano irrimediabilmente perduti.

Per ripristinare la coerenza assoluta della libreria classica, si è deciso di **accettare e consolidare la perdita**, procedendo con una pulizia totale sia del DB che del filesystem:
1. **Rimozione DB Beets Classica**: Eseguita la rimozione forzata di tutte le 3.323 tracce relative all'album `Mozart 225` (`beet remove -f album:"Mozart 225"`).
2. **Pulizia Filesystem**: Rimosse tutte le cartelle fisiche e i symlink orfani relativi a `Mozart 225` sotto `/Volumes/classical/library/`.
3. **Consolidamento Directory**: Eliminate le cartelle d'artista ormai vuote (`Wolfgang Amadeus Mozart`) in `Monographs/` e `Recitals/`.

Il sistema e la libreria classica sono ora in uno stato **coerente, pulito e privo di riferimenti orfani**.

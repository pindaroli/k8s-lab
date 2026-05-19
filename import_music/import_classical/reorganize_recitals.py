#!/usr/bin/env python3
import os
import sys
import argparse
import pathlib
import unicodedata
import json

# Tentativo di importazione delle librerie core di Beets per la manipolazione sicura del database
try:
    from beets.library import Library
    from beets.util import bytestring_path, syspath
except ImportError:
    print("[-] Errore: Le librerie di Beets non sono installate nell'ambiente Python corrente.")
    print("[*] Eseguire lo script all'interno del container Kubernetes o dell'ambiente in cui Beets è configurato.")
    sys.exit(1)

# Configurazione dei percorsi di default per l'ambiente TrueNAS/macOS
DEFAULT_DB = "/Users/olindo/prj/k8s-lab/import_music/import_classical/classical_musiclibrary.db"
DEFAULT_LIB = "/Volumes/classical/library"
NORMALIZATION_JSON = "/Users/olindo/prj/k8s-lab/import_music/import_classical/artist_normalization.json"

def normalize_artist_name(raw_name, json_path=NORMALIZATION_JSON):
    """
    Normalizza e traslittera i nomi degli artisti per la scrittura nel file system.
    Supporta 3 livelli:
      1. Mapping esplicito in JSON (con fallback tra Volumes e percorso locale).
      2. Traslitterazione fonetica cirillica.
      3. Rimozione diacritici Unicode NFD / unidecode.
    """
    if not raw_name:
        return "Unknown Artist"

    string_val = str(raw_name).strip()

    # Rimozione preventiva delle date di nascita/morte tra parentesi (es. "(1756-1791)")
    # molto frequenti in database come MusicBrainz/Discogs per evitare falsi positivi
    import re
    string_val = re.sub(r'\s*\(\d{4}[-–—]\d{4}\)', '', string_val)
    string_val = re.sub(r'\s*\([*†]?\d{4}\)', '', string_val)
    string_val = string_val.strip()

    # Inizializzazione della cache in memoria all'interno del contesto globale di Beets
    global _normalization_cache
    if '_normalization_cache' not in globals():
        globals()['_normalization_cache'] = {}
        possible_paths = ["/Volumes/classical/artist_normalization.json", json_path]
        loaded = False
        for p in possible_paths:
            if os.path.exists(p):
                try:
                    with open(p, 'r', encoding='utf-8') as f:
                        globals()['_normalization_cache'] = json.load(f)
                        loaded = True
                        break
                except Exception:
                    pass
        if not loaded:
            globals()['_normalization_cache'] = {}

    cache = globals()['_normalization_cache']

    # Livello 1: Corrispondenza esatta nel dizionario di normalizzazione
    if string_val in cache:
        return cache[string_val]

    # Livello 2: Rilevamento alfabeto cirillico e traslitterazione russa
    # Intervallo Unicode per i caratteri cirillici: U+0400 - U+04FF
    if any('\u0400' <= char <= '\u04FF' for char in string_val):
        try:
            import cyrtranslit
            return cyrtranslit.to_latin(string_val, "ru").strip()
        except ImportError:
            try:
                from transliterate import translit
                return translit(string_val, reversed=True).strip()
            except ImportError:
                pass

    # Livello 3: Rimozione dei diacritici mediante scomposizione NFD o modulo unidecode
    try:
        import unidecode
        return unidecode.unidecode(string_val).strip()
    except ImportError:
        nfd_form = unicodedata.normalize('NFD', string_val)
        return "".join(char for char in nfd_form if unicodedata.category(char) != 'Mn').strip()

def clean_name(val, mapping_path=NORMALIZATION_JSON):
    """
    Esegue la normalizzazione linguistica del nome del compositore o dell'esecutore.
    """
    return normalize_artist_name(val, json_path=mapping_path)

def sanitize_path_part(part):
    """
    Rimuove o sostituisce i caratteri vietati nei nomi di file e cartelle
    (in particolare la barra '/' e i due punti ':').
    """
    if not part:
        return ""
    # Sostituisce la barra '/' e i due punti ':' con un underscore per evitare di spezzare il percorso
    return str(part).replace('/', '_').replace(':', '_').strip()

def get_track_composers(track):
    """
    Estrae in modo robusto i compositori da una traccia, supportando sia 'composers' (lista o stringa)
    sia 'composer' (singolare) ed eventuali separatori multivalore.
    """
    comps = track.get('composers')
    if comps:
        if isinstance(comps, list):
            return [str(c).strip() for c in comps if c]
        elif isinstance(comps, str):
            return [c.strip() for c in comps.replace(';', ',').split(',') if c.strip()]

    comp = track.get('composer')
    if comp:
        if isinstance(comp, list):
            return [str(c).strip() for c in comp if c]
        elif isinstance(comp, str):
            return [c.strip() for c in comp.replace(';', ',').split(',') if c.strip()]

    return []

def process_recitals(db_path, library_root, dry_run=True):
    """
    Scansiona il database Beets per individuare e riorganizzare gli album Recital multi-compositore.
    """
    if not os.path.exists(db_path):
        print(f"[-] Errore: Il database di Beets {db_path} non esiste.")
        sys.exit(1)

    print(f"[*] Inizializzazione della libreria Beets dal database: {db_path}")
    lib = Library(db_path)

    # Estrae tutti gli album presenti nella libreria
    all_albums = lib.albums()
    total_files_moved = 0
    directories_to_check = set()

    print(f"[*] Scansione in corso su {len(all_albums)} album registrati...")

    for album in all_albums:
        album_id = album.id
        album_artist = album.albumartist
        album_title = album.album
        album_year = album.year

        # Recupera tutte le tracce associate all'album corrente
        tracks = list(album.items())

        # Analizza i compositori unici presenti nell'album per verificare se si tratta di un recital
        unique_composers = set()
        for t in tracks:
            for c in get_track_composers(t):
                unique_composers.add(clean_name(c).lower().strip())

        if len(unique_composers) <= 1:
            # L'album è monografico; non richiede l'applicazione della tassonomia dei recital
            continue

        print(f"\n[!] Recital Rilevato (ID: {album_id}): '{album_title}' di {album_artist}")
        print(f"    Compositori totali: {len(unique_composers)} ({', '.join(sorted(list(unique_composers)))})")

        # Generazione dei percorsi e delle cartelle di destinazione normalizzati e sanificati
        clean_performer = sanitize_path_part(clean_name(album_artist))
        clean_album_title = sanitize_path_part(clean_name(album_title))
        clean_album_folder = f"[{album_year}] {clean_album_title}" if album_year else clean_album_title
        new_album_dir = os.path.join(library_root, "Recitals", clean_performer, clean_album_folder)

        for track in tracks:
            # Ottiene il percorso assoluto corrente registrato nel database di Beets
            old_path = track.path.decode('utf-8') if isinstance(track.path, bytes) else track.path

            # Se il percorso nel database fa riferimento alla vecchia cartella /Users/olindo/Music
            # ma la libreria è in library_root (/Volumes/classical/library), proviamo la mappatura automatica.
            if old_path.startswith("/Users/olindo/Music/"):
                mapped_path = old_path.replace("/Users/olindo/Music/", library_root.rstrip("/") + "/")
                if os.path.exists(mapped_path) or os.path.islink(mapped_path):
                    old_path = mapped_path

            if not os.path.exists(old_path) and not os.path.islink(old_path):
                print(f"    [-] File non trovato sul disco (saltato): {old_path}")
                continue

            file_ext = pathlib.Path(old_path).suffix

            # Formattazione del nome del file per il recital
            track_num = f"{track.track:02d}"
            if track.disc and track.disctotal > 1:
                track_num = f"{track.disc:02d}-{track.track:02d}"

            track_comps = get_track_composers(track)
            track_comp = track_comps[0] if track_comps else "Unknown Composer"
            clean_track_composer = sanitize_path_part(clean_name(track_comp))
            clean_track_title = sanitize_path_part(clean_name(track.get('title') or ''))

            new_filename = f"{track_num} - {clean_track_composer} - {clean_track_title}{file_ext}"
            new_path = os.path.join(new_album_dir, new_filename)

            if old_path == new_path:
                print(f"    [=] File già allineato correttamente: {new_filename}")
                continue

            if os.path.islink(old_path):
                # Legge il percorso di staging a cui punta il symlink
                staging_target = os.readlink(old_path)
                # Se è relativo, lo risolve a percorso assoluto reale rispetto alla vecchia directory del symlink
                if not os.path.isabs(staging_target):
                    staging_target = os.path.normpath(os.path.join(os.path.dirname(old_path), staging_target))

                # Calcola il cammino relativo dalla nuova directory padre del symlink a staging_target
                target_parent_dir = os.path.dirname(new_path)
                relative_staging_target = os.path.relpath(staging_target, target_parent_dir)

                print(f"    [->] Pianificato spostamento symlink (NFS Relativo):")
                print(f"         DA: {old_path}")
                print(f"         A : {new_path}")
                print(f"         Puntando a: {relative_staging_target}")
            else:
                print(f"    [->] Pianificato spostamento file fisico:")
                print(f"         DA: {old_path}")
                print(f"         A : {new_path}")

            # Traccia la vecchia directory padre per la successiva rimozione in sicurezza
            directories_to_check.add(os.path.dirname(old_path))
            total_files_moved += 1

            if not dry_run:
                # Crea la directory di destinazione se non esiste
                os.makedirs(new_album_dir, exist_ok=True)

                # Verifica se l'elemento è un collegamento simbolico
                if os.path.islink(old_path):
                    # Rimuove l'eventuale file preesistente nella nuova destinazione
                    if os.path.exists(new_path) or os.path.islink(new_path):
                        os.unlink(new_path)

                    # Crea il nuovo collegamento simbolico relativo portabile
                    os.symlink(relative_staging_target, new_path)

                    # Rimuove il vecchio collegamento simbolico
                    os.unlink(old_path)
                else:
                    # Se si tratta di un file fisico reale (non consigliato in questo setup, ma implementato per sicurezza)
                    if os.path.exists(new_path):
                        os.remove(new_path)
                    os.rename(old_path, new_path)

                # Aggiorna il percorso dell'item nel database Beets tramite API nativa
                # L'API gestisce in modo trasparente la relativa conversione per la portabilità v2.x
                track.path = bytestring_path(new_path)
                track.store()

        # Allineamento e spostamento dell'album art associato
        if album.artpath:
            old_art = album.artpath.decode('utf-8') if isinstance(album.artpath, bytes) else album.artpath

            # Applica lo stesso risanamento all'album art
            if old_art.startswith("/Users/olindo/Music/"):
                mapped_art = old_art.replace("/Users/olindo/Music/", library_root.rstrip("/") + "/")
                if os.path.exists(mapped_art) or os.path.islink(mapped_art):
                    old_art = mapped_art

            if os.path.exists(old_art) or os.path.islink(old_art):
                art_ext = pathlib.Path(old_art).suffix
                new_art = os.path.join(new_album_dir, f"cover{art_ext}")

                if old_art != new_art:
                    is_art_link = os.path.islink(old_art)
                    if is_art_link:
                        staging_art_target = os.readlink(old_art)
                        if not os.path.isabs(staging_art_target):
                            staging_art_target = os.path.normpath(os.path.join(os.path.dirname(old_art), staging_art_target))

                        target_art_parent_dir = os.path.dirname(new_art)
                        relative_staging_art_target = os.path.relpath(staging_art_target, target_art_parent_dir)

                        print(f"    [->] Spostamento copertina (NFS Relativo): \n         DA: {old_art} \n         A : {new_art} \n         Puntando a: {relative_staging_art_target}")
                    else:
                        print(f"    [->] Spostamento copertina: \n         DA: {old_art} \n         A : {new_art}")

                    directories_to_check.add(os.path.dirname(old_art))

                    if not dry_run:
                        os.makedirs(new_album_dir, exist_ok=True)
                        if is_art_link:
                            if os.path.exists(new_art) or os.path.islink(new_art):
                                os.unlink(new_art)
                            os.symlink(relative_staging_art_target, new_art)
                            os.unlink(old_art)
                        else:
                            if os.path.exists(new_art):
                                os.remove(new_art)
                            os.rename(old_art, new_art)

                        album.artpath = bytestring_path(new_art)
                        album.store()

    # Fase di rimozione ricorsiva e sicura delle vecchie cartelle rimaste vuote
    print(f"\n[*] Analisi di {len(directories_to_check)} directory originarie per la pulizia delle cartelle vuote...")
    cleaned_directories = 0

    # Ordina i percorsi per lunghezza decrescente per rimuovere prima le sottocartelle annidate
    for dir_path in sorted(list(directories_to_check), key=len, reverse=True):
        if os.path.exists(dir_path) and os.path.isdir(dir_path):
            # Esclude i file nascosti di sistema o di tracciamento per verificare se la cartella è effettivamente vuota
            clutter_files = {".DS_Store", "Thumbs.db"}
            remaining_elements = [f for f in os.listdir(dir_path) if f not in clutter_files]

            if len(remaining_elements) == 0:
                print(f"  [-] Eliminazione directory vuota: {dir_path}")
                cleaned_directories += 1
                if not dry_run:
                    # Rimuove preventivamente gli eventuali file di clutter rimasti
                    for clutter in clutter_files:
                        clutter_file_path = os.path.join(dir_path, clutter)
                        if os.path.exists(clutter_file_path):
                            os.remove(clutter_file_path)
                    os.rmdir(dir_path)
            else:
                print(f"  [+] Directory non vuota (conservata): {dir_path} (contiene {len(remaining_elements)} file)")

    print("\n" + "="*80)
    print("RELAZIONE DI SINTESI DELLA MIGRAZIONE")
    print("="*80)
    print(f"Modalità operativa:     {'DRY-RUN (Simulazione)' if dry_run else 'REAL RUN (Aggiornamento attivo)'}")
    print(f"File/Symlink spostati:  {total_files_moved}")
    print(f"Directory vuote rimosse: {cleaned_directories}")
    print("="*80)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Migrazione sicura dei recital multi-compositore per il file system e per il database Beets.")
    parser.add_argument("--run", action="store_true", help="Disabilita la modalità di simulazione ed effettua le modifiche fisiche sul disco e sul database.")
    parser.add_argument("--db", default=DEFAULT_DB, help="Percorso del database SQLite classical_musiclibrary.db")
    parser.add_argument("--lib", default=DEFAULT_LIB, help="Percorso radice della libreria finale (/Volumes/classical/library)")

    args = parser.parse_args()

    # Se il parametro --run non viene specificato esplicitamente, lo script opera in modalità provvisoria (dry-run)
    is_dry_run = not args.run
    process_recitals(args.db, args.lib, dry_run=is_dry_run)

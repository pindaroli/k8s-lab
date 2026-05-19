#!/usr/bin/env python3
import os
import sys
import re
import shutil
import argparse
import unicodedata
import sqlite3
from beets import library

DB_PATH = "/Users/olindo/prj/k8s-lab/import_music/musiclibrary.db"
lib_dir = "/Volumes/arrdata/media/music_backup"

def get_compare_key(name):
    n = name.lower()
    n = re.sub(r'\b(and|with|feat|featuring|&|,)\b', ' ', n)
    n = re.sub(r'[^a-z0-9\s]', '', n)
    return re.sub(r'\s+', ' ', n).strip()

def sanitize_path_segment(segment):
    if not segment:
        return "Unknown"
    # Sostituisce caratteri vietati nei filesystem comuni
    for c in ['/', '\\', ':', '*', '?', '"', '<', '>', '|']:
        segment = segment.replace(c, '_')
    return ' '.join(segment.split()).strip()

# Carica cache degli artisti esistenti per evitare case clash
existing_artists = {}
if os.path.exists(lib_dir):
    try:
        for d in os.listdir(lib_dir):
            if os.path.isdir(os.path.join(lib_dir, d)) and not d.startswith('.') and not d.startswith('_'):
                d_nfc = unicodedata.normalize('NFC', d)
                key = get_compare_key(d_nfc)
                if key:
                    existing_artists[key] = d_nfc
    except Exception as e:
        print(f"[WARNING] Impossibile leggere la cartella radice {lib_dir}: {e}")

def get_clean_artist(artist_name):
    if not artist_name:
        return "Unknown Artist"
    artist_name = unicodedata.normalize('NFC', artist_name).replace('\u3000', ' ').strip()
    key = get_compare_key(artist_name)
    if key in existing_artists:
        return existing_artists[key]
    return artist_name

def backup_database():
    backup_path = f"{DB_PATH}.bak"
    try:
        shutil.copy2(DB_PATH, backup_path)
        print(f"[INFO] Backup del database effettuato con successo in: {backup_path}")
        return True
    except Exception as e:
        print(f"[ERROR] Impossibile effettuare il backup del database: {e}")
        return False

def main():
    parser = argparse.ArgumentParser(description="Standardizza i percorsi delle cartelle album nel formato [Anno] Titolo Album")
    parser.add_argument("--artist", type=str, help="Filtra e standardizza solo un artista specifico (case-insensitive)")
    parser.add_argument("--limit", type=int, help="Limita il numero di album da elaborare in questa esecuzione")
    parser.add_argument("--run", action="store_true", help="Esegue effettivamente gli spostamenti e aggiorna il database")

    args = parser.parse_args()

    if not os.path.exists(DB_PATH):
        print(f"[ERROR] Database Beets non trovato in: {DB_PATH}")
        sys.exit(1)

    print("=" * 80)
    print("🚀 STRUMENTO DI STANDARDIZZAZIONE PERCORSI ALBUM Beets 🚀")
    print("=" * 80)
    print(f"Database: {DB_PATH}")
    print(f"Library:  {lib_dir}")
    print(f"Modalità: {'REAL RUN (Modifiche attive)' if args.run else 'DRY-RUN (Simulazione)'}")
    if args.artist:
        print(f"Filtro Artista: {args.artist}")
    if args.limit:
        print(f"Limite Album: {args.limit}")
    print("-" * 80)

    # Inizializza libreria Beets
    lib = library.Library(DB_PATH, directory=lib_dir)

    # Raggruppa gli item per album_id
    albums_dict = {}
    for item in lib.items():
        album_id = item.album_id
        if not album_id:
            continue
        if album_id not in albums_dict:
            albums_dict[album_id] = []
        albums_dict[album_id].append(item)

    # Ordina gli album per artista e nome album
    sorted_albums = []
    for album_id, items in albums_dict.items():
        first_item = items[0]
        # Recupera metadati album
        artist = first_item.albumartist or first_item.artist or "Unknown Artist"
        album_name = first_item.album or "Unknown Album"
        sorted_albums.append((artist.lower(), album_name.lower(), album_id, items))
    sorted_albums.sort()

    # Conta modifiche
    albums_processed = 0
    albums_renamed = 0
    tracks_moved = 0
    errors_encountered = 0

    # Se dobbiamo fare la modifica reale, facciamo prima il backup
    if args.run:
        if not backup_database():
            print("[CRITICAL] Interruzione per sicurezza: backup fallito.")
            sys.exit(1)

    for _, _, album_id, items in sorted_albums:
        if args.limit and albums_processed >= args.limit:
            print(f"\n[INFO] Raggiunto il limite configurato di {args.limit} album.")
            break

        first_item = items[0]
        # Artista e album canonici dal DB
        db_artist = first_item.albumartist or first_item.artist or "Unknown Artist"
        db_album = first_item.album or "Unknown Album"

        # Filtro artista
        if args.artist:
            if args.artist.lower() not in db_artist.lower():
                continue

        # Estrai anno massimo dalle tracce
        db_year = 0
        for item in items:
            if item.year:
                db_year = max(db_year, int(item.year))

        # Prova ad analizzare la cartella corrente per trovare l'anno se non è impostato nel DB
        current_dir = os.path.dirname(first_item.path.decode('utf-8', 'replace'))
        current_album_folder = os.path.basename(current_dir)

        if db_year == 0:
            # Cerca pattern tipo (YYYY) o [YYYY]
            match_year = re.search(r'[\(\[](\d{4})[\)\]]$', current_album_folder)
            if match_year:
                db_year = int(match_year.group(1))

        # Normalizza nomi
        artist_clean = get_clean_artist(db_artist)
        album_clean = sanitize_path_segment(db_album)

        # Costruisci nome cartella target
        year_prefix = f"[{db_year:04d}] " if db_year > 0 else "[0000] "
        target_album_folder = f"{year_prefix}{album_clean}"

        # Percorso target della cartella album
        target_dir = os.path.join(lib_dir, artist_clean, target_album_folder)

        # Normalizziamo entrambi i percorsi per il confronto case/NFC-insensitive
        current_dir_norm = os.path.normpath(unicodedata.normalize('NFC', current_dir))
        target_dir_norm = os.path.normpath(unicodedata.normalize('NFC', target_dir))

        # Se la cartella è già in formato corretto, saltiamo
        if current_dir_norm == target_dir_norm:
            albums_processed += 1
            continue

        # Trovato un album da standardizzare!
        print(f"\n📂 Album: {db_artist} - {db_album} (Anno: {db_year})")
        print(f"  Attuale:   {current_dir}")
        print(f"  Target:    {target_dir}")

        albums_renamed += 1
        albums_processed += 1

        # Raccogli le tracce e calcola i nuovi percorsi
        tracks_to_move = []
        for item in items:
            src_track_path = item.path.decode('utf-8', 'replace')
            filename = os.path.basename(src_track_path)

            # Sanitizza il filename (es. track - title.ext)
            track_num = int(item.track) if item.track else 0
            title_clean = sanitize_path_segment(item.title or "Unknown Title")
            _, ext = os.path.splitext(filename)
            if not ext:
                ext = ".mp3"

            track_prefix = f"{track_num:02d} - " if track_num > 0 else "00 - "
            new_filename = f"{track_prefix}{title_clean}{ext}"

            dest_track_path = os.path.join(target_dir, new_filename)
            tracks_to_move.append((item, src_track_path, dest_track_path))

        # Esegui gli spostamenti reali se richiesto
        if args.run:
            try:
                # Crea la directory di destinazione
                os.makedirs(target_dir, exist_ok=True)

                # Sposta ogni traccia
                moved_tracks = []
                for item, src, dest in tracks_to_move:
                    if os.path.exists(src):
                        shutil.move(src, dest)
                        # Aggiorna beets db
                        item.path = dest.encode('utf-8')
                        item.store()
                        moved_tracks.append(src)
                        tracks_moved += 1
                    else:
                        print(f"  [ERROR] File non trovato sul disco: {src}")
                        errors_encountered += 1

                print(f"  [OK] Spostate {len(moved_tracks)} tracce e aggiornato il database Beets!")

                # Prova a rimuovere la vecchia directory se rimasta vuota
                if os.path.exists(current_dir):
                    # Controlla se ci sono altri file spuri (es. .DS_Store, cover.jpg)
                    remaining = os.listdir(current_dir)
                    # Sposta eventuali cover o immagini nella nuova cartella
                    for f in remaining:
                        if f.lower() in ['.ds_store', 'thumbs.db']:
                            try:
                                os.remove(os.path.join(current_dir, f))
                            except Exception:
                                pass
                        else:
                            # Copia cover.jpg o altri file spuri non tracciati da Beets
                            try:
                                shutil.move(os.path.join(current_dir, f), os.path.join(target_dir, f))
                            except Exception as e:
                                print(f"  [WARNING] Impossibile spostare file non tracciato {f}: {e}")

                    # Tenta di cancellare la cartella vecchia
                    try:
                        os.rmdir(current_dir)
                    except Exception:
                        # Se ha ancora file dentro, non forziamo
                        print(f"  [WARNING] Vecchia cartella non rimossa (contiene file residui): {current_dir}")

            except Exception as e:
                print(f"  [CRITICAL ERROR] Errore durante l'elaborazione dell'album: {e}")
                errors_encountered += 1
        else:
            # Dry-run logging
            for _, src, dest in tracks_to_move:
                print(f"  [DRY-RUN] Move file:")
                print(f"    Da: {src}")
                print(f"    A : {dest}")
            tracks_moved += len(tracks_to_move)

    print("\n" + "=" * 80)
    print("📈 STATISTICHE FINALI:")
    print(f"  - Album analizzati: {albums_processed}")
    print(f"  - Album da standardizzare / standardizzati: {albums_renamed}")
    print(f"  - Tracce da spostare / spostate: {tracks_moved}")
    print(f"  - Errori/Eccezioni riscontrati: {errors_encountered}")
    print("=" * 80)

if __name__ == "__main__":
    main()

#!/usr/bin/env python3
import os
import sys
import re
import shutil
import argparse
import unicodedata
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
    backup_path = f"{DB_PATH}.bak.singles"
    try:
        shutil.copy2(DB_PATH, backup_path)
        print(f"[INFO] Backup del database effettuato con successo in: {backup_path}")
        return True
    except Exception as e:
        print(f"[ERROR] Impossibile effettuare il backup del database: {e}")
        return False

def main():
    parser = argparse.ArgumentParser(description="Consolida brani sparsi con anno [0000] o Unknown Album nel formato Non-Album")
    parser.add_argument("--run", action="store_true", help="Esegue effettivamente gli spostamenti e aggiorna il database")
    args = parser.parse_args()

    if not os.path.exists(DB_PATH):
        print(f"[ERROR] Database Beets non trovato in: {DB_PATH}")
        sys.exit(1)

    print("=" * 80)
    print("🚀 CONSOLIDAMENTO BRANI SPARSI (STRATEGIA B) 🚀")
    print("=" * 80)
    print(f"Database: {DB_PATH}")
    print(f"Library:  {lib_dir}")
    print(f"Modalità: {'REAL RUN (Modifiche attive)' if args.run else 'DRY-RUN (Simulazione)'}")
    print("-" * 80)

    lib = library.Library(DB_PATH, directory=lib_dir)

    # Raggruppa gli item per (albumartist, album) per contare quante tracce hanno
    album_groups = {}
    for item in lib.items():
        album_artist = item.albumartist or item.artist or "Unknown Artist"
        album = item.album or ""
        # Riconosciamo come candidato se:
        # 1. album è nullo o vuoto
        # 2. album contiene "Unknown Album" (case-insensitive)
        # 3. year è 0
        is_candidate = (
            not album or
            "unknown album" in album.lower() or
            item.year == 0 or
            item.year is None
        )
        if is_candidate:
            group_key = (album_artist.lower(), album.lower())
            if group_key not in album_groups:
                album_groups[group_key] = []
            album_groups[group_key].append(item)

    # Filtriamo i gruppi candidati a diventare "Singoli/Brani Sparsi" (Non-Album)
    # Criterio: Il gruppo ha meno di 3 tracce (o l'album è vuotato, a indicare brani singoli/sparsi reali)
    singles_to_process = []

    for (artist_key, album_key), items in album_groups.items():
        if len(items) <= 2 or album_key == "":
            singles_to_process.extend(items)

    print(f"Trovate {len(singles_to_process)} tracce candidate al consolidamento in 'Non-Album'.")
    print("-" * 80)

    if not singles_to_process:
        print("[INFO] Nessuna traccia da elaborare.")
        return

    if args.run:
        if not backup_database():
            print("[CRITICAL] Interruzione per sicurezza: backup fallito.")
            sys.exit(1)

    tracks_moved = 0
    errors_encountered = 0
    processed_dirs = set()

    for item in singles_to_process:
        src_path = item.path.decode('utf-8', 'replace')
        filename = os.path.basename(src_path)
        _, ext = os.path.splitext(filename)
        if not ext:
            ext = ".mp3"

        artist_clean = get_clean_artist(item.artist or "Unknown Artist")
        title_clean = sanitize_path_segment(item.title or "Unknown Title")

        # Nuovo percorso target: Non-Album/{Artista}/{Titolo}{ext}
        target_dir = os.path.join(lib_dir, "Non-Album", artist_clean)
        target_path = os.path.join(target_dir, f"{title_clean}{ext}")

        # Normalizziamo entrambi i percorsi per il confronto case/NFC-insensitive
        src_path_norm = os.path.normpath(unicodedata.normalize('NFC', src_path))
        target_path_norm = os.path.normpath(unicodedata.normalize('NFC', target_path))

        # Memorizziamo la cartella sorgente per pulirla successivamente se rimasta vuota
        src_dir = os.path.dirname(src_path)
        processed_dirs.add(src_dir)

        if src_path_norm == target_path_norm:
            # Già al posto giusto
            continue

        print(f"🎵 Traccia: {item.artist} - {item.title}")
        print(f"   Da: {src_path}")
        print(f"   A : {target_path}")

        if args.run:
            try:
                if os.path.exists(src_path):
                    os.makedirs(target_dir, exist_ok=True)
                    shutil.move(src_path, target_path)

                    # Aggiorna il database Beets: rimuove dall'album (diventa singleton)
                    item.album = ""
                    item.albumartist = ""
                    item.album_id = None
                    item.year = 0
                    item.path = target_path.encode('utf-8')
                    item.store()
                    tracks_moved += 1
                else:
                    print(f"   [ERROR] File non trovato sul disco: {src_path}")
                    errors_encountered += 1
            except Exception as e:
                print(f"   [CRITICAL ERROR] Errore durante lo spostamento: {e}")
                errors_encountered += 1
        else:
            tracks_moved += 1

    # Fase di pulizia delle vecchie directory vuote (solo in esecuzione reale)
    if args.run and tracks_moved > 0:
        print("\n🧹 Pulizia delle vecchie directory rimaste vuote...")
        for src_dir in processed_dirs:
            if os.path.exists(src_dir):
                # Rimuove file inutili (es. .DS_Store)
                try:
                    for f in os.listdir(src_dir):
                        if f.lower() in ['.ds_store', 'thumbs.db']:
                            os.remove(os.path.join(src_dir, f))
                except Exception:
                    pass
                # Tenta di cancellare la cartella
                try:
                    os.rmdir(src_dir)
                    print(f"  [OK] Cartella rimossa: {src_dir}")
                except Exception:
                    pass # Se contiene altri file, non la tocca

    print("\n" + "=" * 80)
    print("📈 STATISTICHE FINALI:")
    print(f"  - Tracce elaborate/da elaborare: {len(singles_to_process)}")
    print(f"  - Tracce spostate / da spostare: {tracks_moved}")
    print(f"  - Errori riscontrati: {errors_encountered}")
    print("=" * 80)

if __name__ == "__main__":
    main()

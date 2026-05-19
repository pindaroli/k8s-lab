#!/usr/bin/env python3
import os
import sys
import re
import shutil
import argparse
from beets import library

DB_PATH = "/Users/olindo/prj/k8s-lab/import_music/musiclibrary.db"
lib_dir = "/Volumes/arrdata/media/music_backup"

def is_anonymous(artist, title):
    artist = (artist or "").strip().lower()
    title = (title or "").strip().lower()

    # Heuristic 1: Artista sconosciuto
    is_unknown_artist = (
        not artist or
        "unknown" in artist or
        artist == "artista"
    )

    # Heuristic 2: Titolo sconosciuto o generico (es. Track12, Unknown Title)
    is_unknown_title = (
        not title or
        "unknown" in title or
        re.match(r'^track\s*\d+$', title) or
        title == "titolo"
    )

    return is_unknown_artist and is_unknown_title

def backup_database():
    backup_path = f"{DB_PATH}.bak.purge"
    try:
        shutil.copy2(DB_PATH, backup_path)
        print(f"[INFO] Backup del database effettuato con successo in: {backup_path}")
        return True
    except Exception as e:
        print(f"[ERROR] Impossibile effettuare il backup del database: {e}")
        return False

def main():
    parser = argparse.ArgumentParser(description="Identifica ed elimina brani anonimi (senza artista né titolo validi)")
    parser.add_argument("--run", action="store_true", help="Elimina fisicamente i file e rimuove le tracce dal DB")
    args = parser.parse_args()

    if not os.path.exists(DB_PATH):
        print(f"[ERROR] Database Beets non trovato in: {DB_PATH}")
        sys.exit(1)

    print("=" * 80)
    print("🧹 STRUMENTO DI PURGE BRANI ANONIMI 🧹")
    print("=" * 80)
    print(f"Database: {DB_PATH}")
    print(f"Library:  {lib_dir}")
    print(f"Modalità: {'REAL RUN (Eliminazione attiva)' if args.run else 'DRY-RUN (Simulazione)'}")
    print("-" * 80)

    lib = library.Library(DB_PATH, directory=lib_dir)

    anonymous_items = []
    for item in lib.items():
        if is_anonymous(item.artist, item.title):
            anonymous_items.append(item)

    print(f"Trovate {len(anonymous_items)} tracce completamente anonime.")
    print("-" * 80)

    if not anonymous_items:
        print("[INFO] Nessun brano anonimo da eliminare.")
        return

    for i, item in enumerate(anonymous_items):
        path_str = item.path.decode('utf-8', 'replace')
        print(f"{i+1}. 👤 Artista: {item.artist} | 🎵 Titolo: {item.title}")
        print(f"   📂 Path: {path_str}")
        print("-" * 60)

    if args.run:
        if not backup_database():
            print("[CRITICAL] Interruzione per sicurezza: backup fallito.")
            sys.exit(1)

        print("\n🔥 Avvio eliminazione fisica e logica...")
        deleted_count = 0
        directories_to_clean = set()

        for item in anonymous_items:
            path_str = item.path.decode('utf-8', 'replace')
            directories_to_clean.add(os.path.dirname(path_str))

            # Eliminazione fisica
            if os.path.exists(path_str):
                try:
                    os.remove(path_str)
                    print(f"  [OK] Eliminato file: {path_str}")
                except Exception as e:
                    print(f"  [ERROR] Impossibile eliminare file {path_str}: {e}")
            else:
                print(f"  [WARNING] File non presente sul disco (già rimosso): {path_str}")

            # Rimozione dal database Beets
            try:
                item.remove() # Rimuove l'item dal DB
                deleted_count += 1
            except Exception as e:
                print(f"  [ERROR] Errore durante la rimozione dal database: {e}")

        # Pulizia delle cartelle vuote
        print("\n🧹 Pulizia delle directory vuote...")
        for src_dir in directories_to_clean:
            if os.path.exists(src_dir):
                # Rimuove file spuri tipo .DS_Store
                try:
                    for f in os.listdir(src_dir):
                        if f.lower() in ['.ds_store', 'thumbs.db']:
                            os.remove(os.path.join(src_dir, f))
                except Exception:
                    pass
                # Rimuove la directory se vuota
                try:
                    os.rmdir(src_dir)
                    print(f"  [OK] Cartella vuota rimossa: {src_dir}")
                except Exception:
                    pass

        # Rimuove anche la cartella Non-Album/Unknown Artist se vuota
        parent_unknown = os.path.join(lib_dir, "Non-Album", "Unknown Artist")
        if os.path.exists(parent_unknown):
            try:
                os.rmdir(parent_unknown)
                print(f"  [OK] Cartella madre rimossa: {parent_unknown}")
            except Exception:
                pass

        print("\n" + "=" * 80)
        print("📈 STATISTICHE FINALI:")
        print(f"  - Tracce eliminate con successo: {deleted_count}/{len(anonymous_items)}")
        print("=" * 80)

if __name__ == "__main__":
    main()

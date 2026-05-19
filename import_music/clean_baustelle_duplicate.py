#!/usr/bin/env python3
import os
import sys
import shutil
from beets import library

DB_PATH = "/Users/olindo/prj/k8s-lab/import_music/musiclibrary.db"
DUP_DIR = "/Volumes/arrdata/media/music_backup/Baustelle/[0000] Sussidiario Illustrato della.."

def main():
    if not os.path.exists(DB_PATH):
        print(f"[ERROR] Database Beets non trovato in: {DB_PATH}")
        sys.exit(1)

    print("=" * 80)
    print("🧹 BONIFICA DUPLICATO BAUSTELLE [0000] 🧹")
    print("=" * 80)

    lib = library.Library(DB_PATH)

    # Identifica le tracce duplicate basandosi sull'album_id o sui path specifici
    duplicate_items = []
    for item in lib.items():
        if item.album == "Sussidiario Illustrato della.." and item.year == 0:
            duplicate_items.append(item)

    if not duplicate_items:
        print("[INFO] Nessuna traccia duplicata trovata nel database.")
    else:
        print(f"Trovate {len(duplicate_items)} tracce duplicate nel database:")
        for item in duplicate_items:
            path_str = item.path.decode('utf-8', 'replace')
            print(f"  - ID: {item.id} | {item.artist} - {item.title} ({path_str})")

        # Rimozione dal DB
        print("\n[DB] Rimozione delle tracce duplicate dal database Beets...")
        for item in duplicate_items:
            item.remove()
        print("[DB] Rimozione completata.")

    # Eliminazione della cartella fisica duplicata
    if os.path.exists(DUP_DIR):
        print(f"\n[FS] Eliminazione della cartella fisica duplicata: {DUP_DIR}")
        try:
            shutil.rmtree(DUP_DIR)
            print("[FS] Cartella eliminata con successo.")
        except Exception as e:
            print(f"[FS] [ERROR] Impossibile eliminare la cartella: {e}")
    else:
        print(f"\n[FS] Cartella fisica non trovata (già rimossa): {DUP_DIR}")

    print("=" * 80)

if __name__ == "__main__":
    main()

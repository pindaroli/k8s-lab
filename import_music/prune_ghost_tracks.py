#!/usr/bin/env python3
import os
import sys
import shutil
from beets import library

DB_PATH = "/Users/olindo/prj/k8s-lab/import_music/musiclibrary.db"
lib_dir = "/Volumes/arrdata/media/music_backup"

def backup_database():
    backup_path = f"{DB_PATH}.bak.prune"
    try:
        shutil.copy2(DB_PATH, backup_path)
        print(f"[INFO] Backup pre-pruning creato in: {backup_path}")
        return True
    except Exception as e:
        print(f"[ERROR] Impossibile creare il backup pre-pruning: {e}")
        return False

def main():
    if not os.path.exists(DB_PATH):
        print(f"[ERROR] Database Beets non trovato in: {DB_PATH}")
        sys.exit(1)

    print("=" * 80)
    print("🧹 RIMOZIONE RECORD FANTASMA DAL DATABASE BEETS 🧹")
    print("=" * 80)
    print(f"Database: {DB_PATH}")
    print("-" * 80)

    if not backup_database():
        print("[CRITICAL] Interruzione per sicurezza: backup fallito.")
        sys.exit(1)

    lib = library.Library(DB_PATH, directory=lib_dir)

    ghosts_found = 0

    # Eseguiamo la scansione di tutti gli item
    # Usiamo una lista per evitare problemi di modifica del set durante l'iterazione
    all_items = list(lib.items())

    print(f"[INFO] Analisi di {len(all_items)} tracce in corso...")

    for item in all_items:
        path_str = item.path.decode('utf-8', 'replace')

        # Se il file non esiste fisicamente sul disco
        if not os.path.exists(item.path):
            ghosts_found += 1
            print(f"❌ RIMOZIONE GHOST: ID {item.id} | {item.artist} - {item.album} - {item.title}")
            print(f"   Percorso mancante: {path_str}")

            # Rimuove l'item dal database di Beets in modo definitivo
            item.remove()

    print("-" * 80)
    print("📈 STATISTICHE PULIZIA:")
    print(f"  - Record fantasma rimossi: {ghosts_found}")
    print(f"  - Database Beets allineato al 100%!")
    print("=" * 80)

if __name__ == "__main__":
    main()

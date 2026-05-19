#!/usr/bin/env python3
import os
import sys
import sqlite3
import argparse

DB_PATH = "/Users/olindo/prj/k8s-lab/import_music/musiclibrary.db"
LIB_DIR = "/Volumes/arrdata/media/music_backup"

AUDIO_EXTS = {'.mp3', '.flac', '.m4a', '.ogg', '.wav', '.wma', '.ape'}

def main():
    parser = argparse.ArgumentParser(description="Trova ed elimina in modo sicuro i file audio orfani/duplicati lasciati indietro da precedenti importazioni")
    parser.add_argument("--run", action="store_true", help="Esegue l'eliminazione dei file orfani")
    args = parser.parse_args()

    if not os.path.exists(DB_PATH):
        print(f"[ERROR] Database Beets non trovato: {DB_PATH}")
        sys.exit(1)

    print("=" * 80)
    print("🧹 STRUMENTO DI BONIFICA FILE ORFANI E DUPLICATI DI IMPORTAZIONE 🧹")
    print("=" * 80)
    print(f"Database: {DB_PATH}")
    print(f"Library:  {LIB_DIR}")
    print(f"Modalità: {'REAL RUN (Eliminazione attiva)' if args.run else 'DRY-RUN (Simulazione)'}")
    print("-" * 80)

    # Connessione al DB per ottenere tutti i percorsi tracciati
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT path FROM items")
    db_paths = set(os.path.normpath(row[0].decode('utf-8', 'replace')) for row in cur.fetchall())

    print(f"[INFO] File tracciati nel database Beets: {len(db_paths)}")

    safe_to_delete = []
    total_space_bytes = 0

    # Scansione del filesystem
    for root, dirs, files in os.walk(LIB_DIR):
        # Escludiamo le cartelle di sistema/triage
        if '/_' in root or '/_Triage' in root or '/.AppleDouble' in root:
            continue

        # Troviamo se ci sono file tracciati nel database in questa cartella
        folder_has_tracked_files = False
        for f in files:
            full_path = os.path.join(root, f)
            rel_path = os.path.relpath(full_path, LIB_DIR)
            if os.path.normpath(rel_path) in db_paths:
                folder_has_tracked_files = True
                break

        # Se la cartella contiene almeno un file tracciato, tutti gli altri file audio NON tracciati
        # sono duplicati lasciati indietro da vecchie importazioni o standardizzazioni.
        if folder_has_tracked_files:
            for f in files:
                _, ext = os.path.splitext(f.lower())
                if ext not in AUDIO_EXTS:
                    continue # Saltiamo immagini, log, ecc.

                full_path = os.path.join(root, f)
                rel_path = os.path.relpath(full_path, LIB_DIR)

                # Se il file audio non è tracciato, è un orfano duplicato sicuro
                if os.path.normpath(rel_path) not in db_paths:
                    try:
                        sz = os.path.getsize(full_path)
                        safe_to_delete.append((full_path, sz))
                        total_space_bytes += sz
                    except Exception:
                        pass

    print(f"\n📊 RISULTATI DEL FILE SYSTEM AUDIT:")
    print(f"  - File audio orfani/duplicati individuati: {len(safe_to_delete)}")
    print(f"  - Spazio totale recuperabile: {total_space_bytes / (1024 * 1024 * 1024):.2f} GB")
    print("-" * 80)

    if not safe_to_delete:
        print("[INFO] Nessun file audio orfano rilevato sul filesystem. La cartella è pulita al 100%!")
        return

    # Stampa i primi 20 per verifica
    print("\n🔍 ESEMPI DI FILE ORFANI PRONTI ALL'ELIMINAZIONE:")
    for path, sz in sorted(safe_to_delete)[:20]:
        print(f"  - {path} ({sz / (1024 * 1024):.2f} MB)")
    if len(safe_to_delete) > 20:
        print(f"    ... e altri {len(safe_to_delete) - 20} file.")

    if args.run:
        print("\n🔥 AVVIO ELIMINAZIONE DEI FILE ORFANI...")
        deleted_count = 0
        deleted_space = 0

        for path, sz in safe_to_delete:
            if os.path.exists(path):
                try:
                    os.remove(path)
                    deleted_count += 1
                    deleted_space += sz
                except Exception as e:
                    print(f"  [ERROR] Impossibile eliminare {path}: {e}")

        print("\n" + "=" * 80)
        print("📈 STATISTICHE FINALI:")
        print(f"  - File orfani eliminati: {deleted_count}")
        print(f"  - Spazio disco liberato: {deleted_space / (1024 * 1024 * 1024):.2f} GB")
        print("=" * 80)
    else:
        print("\n[INFO] Modalità DRY-RUN completata. Nessun file è stato rimosso.")

if __name__ == "__main__":
    main()

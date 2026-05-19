#!/usr/bin/env python3
import os
import sys
import shutil
from beets import library

DB_PATH = "/Users/olindo/prj/k8s-lab/import_music/musiclibrary.db"
lib_dir = "/Volumes/arrdata/media/music_backup"

def main():
    if not os.path.exists(DB_PATH):
        print(f"[ERROR] Database Beets non trovato in: {DB_PATH}")
        sys.exit(1)

    print("=" * 80)
    print("🧹 BONIFICA E RIMOZIONE DOPPIONI CARTELLA AKON 🧹")
    print("=" * 80)

    # 1. Backup di sicurezza del database
    backup_path = f"{DB_PATH}.bak.akon"
    try:
        shutil.copy2(DB_PATH, backup_path)
        print(f"[INFO] Backup del DB creato in: {backup_path}")
    except Exception as e:
        print(f"[ERROR] Impossibile creare il backup: {e}")
        sys.exit(1)

    lib = library.Library(DB_PATH, directory=lib_dir)

    # --- PARTE A: RIMOZIONE FILE DUPLICATI FISICI DA KONVICTED E FREEDOM ---
    print("\n--- 1. Pulizia File Orfani (Konvicted & Freedom) ---")
    folders_to_clean = [
        os.path.join(lib_dir, "Akon", "[2006] Konvicted"),
        os.path.join(lib_dir, "Akon", "[2008] Freedom")
    ]

    deleted_physical_count = 0

    for folder in folders_to_clean:
        if not os.path.exists(folder):
            print(f"[WARNING] Cartella non trovata: {folder}")
            continue

        print(f"Scansione cartella: {folder}")
        for file in os.listdir(folder):
            # Cerca i file che iniziano con "Akon - " (es. "Akon - Konvicted - ...")
            if file.startswith("Akon - ") and file.endswith(".flac"):
                file_path = os.path.join(folder, file)
                try:
                    os.remove(file_path)
                    print(f"  🗑️ Rimosso file orfano: {file}")
                    deleted_physical_count += 1
                except Exception as e:
                    print(f"  [ERROR] Impossibile rimuovere {file}: {e}")

    # --- PARTE B: RIMOZIONE RECORD E FILE DUPLICATI DI TROUBLE (2004) ---
    print("\n--- 2. Pulizia Doppioni Album 'Trouble' (2004) ---")

    bad_trouble_ids = [6167, 6168, 6169, 6170, 6171, 6172, 6173, 6174, 6175, 6176, 6177, 6178, 6179]
    trouble_db_removed = 0
    trouble_physical_removed = 0

    # Raccogliamo gli item per non modificare il set durante l'iterazione
    all_items = list(lib.items())

    for item in all_items:
        if item.id in bad_trouble_ids:
            path_str = item.path.decode('utf-8', 'replace')
            print(f"❌ RIMOZIONE TROUBLE DUPLICATO DB: ID {item.id} | {path_str}")

            # 1. Rimuovi dal database Beets
            try:
                item.remove()
                trouble_db_removed += 1
            except Exception as e:
                print(f"  [ERROR] Errore rimozione DB per ID {item.id}: {e}")

            # 2. Rimuovi dal disco fisico
            # Il percorso nel DB potrebbe essere vecchi, lo traduciamo per il volume backup
            relative_part = path_str.replace("/Users/olindo/Music/", "")
            actual_physical_path = os.path.join(lib_dir, relative_part)

            if os.path.exists(actual_physical_path):
                try:
                    os.remove(actual_physical_path)
                    print(f"  🗑️ Rimosso file fisico duplicato: {os.path.basename(actual_physical_path)}")
                    trouble_physical_removed += 1
                except Exception as e:
                    print(f"  [ERROR] Errore rimozione file fisico {actual_physical_path}: {e}")
            else:
                # Controlla se il file esiste con il percorso registrato
                if os.path.exists(item.path):
                    try:
                        os.remove(item.path)
                        print(f"  🗑️ Rimosso file fisico duplicato (path originale): {os.path.basename(item.path)}")
                        trouble_physical_removed += 1
                    except Exception as e:
                        print(f"  [ERROR] Errore rimozione file fisico {item.path}: {e}")

    print("\n" + "=" * 80)
    print("📈 STATISTICHE CONCLUSIVE BONIFICA AKON:")
    print(f"  - File orfani fisici rimossi (Konvicted/Freedom): {deleted_physical_count}")
    print(f"  - Record duplicati rimossi dal DB (Trouble):      {trouble_db_removed}")
    print(f"  - File fisici duplicati rimossi (Trouble):        {trouble_physical_removed}")
    print("=" * 80)

if __name__ == "__main__":
    main()

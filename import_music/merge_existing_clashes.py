#!/usr/bin/env python3
"""
merge_existing_clashes.py — Bonifica e fusione dei duplicati di cartelle
========================================================================
Sposta fisicamente i file dalle cartelle duplicate a quelle canoniche
su /Volumes/arrdata/media/music_backup/ e aggiorna atomicamente
il database SQLite di Beets (musiclibrary.db) per mantenere la coerenza.

Uso:
  python3 merge_existing_clashes.py          # DRY-RUN (Simulazione)
  python3 merge_existing_clashes.py --apply  # ESECUZIONE REALE
"""

import os
import sys
import sqlite3
import shutil
import unicodedata

# Configurazione percorsi
BACKUP_DIR = "/Volumes/arrdata/media/music_backup"
DB_PATH = "/Users/olindo/prj/k8s-lab/import_music/musiclibrary.db"

# Mappa dei gruppi di clash rilevati con le rispettive cartelle canoniche
CLASH_GROUPS = [
    {
        "canonical": "Anne Sofie Von Otter & Brad Mehldau",
        "duplicates": ["Anne Sofie Von Otter, Brad Mehldau"]
    },
    {
        "canonical": "Antony and the Johnsons",
        "duplicates": ["Antony And The Johnsons"]
    },
    {
        "canonical": "Artisti Vari",
        "duplicates": ["Artisti vari"]
    },
    {
        "canonical": "CapaRezza",
        "duplicates": ["Caparezza"]
    },
    {
        "canonical": "Elio e le Storie Tese",
        "duplicates": ["Elio e Le Storie Tese", "Elio E Le Storie Tese"]
    },
    {
        "canonical": "Eric Clapton",
        "duplicates": ["ERIC CLAPTON"]
    },
    {
        "canonical": "Fabrizio De André",  # NFC standard con accento acuto
        "duplicates": [
            "Fabrizio De Andrè",  # NFD standard con accento grave decomposto
            "Fabrizio de André"   # de minuscolo
        ]
    },
    {
        "canonical": "Francesco De Gregori",
        "duplicates": ["Francesco de Gregori"]
    },
    {
        "canonical": "Guns N' Roses",
        "duplicates": ["Guns N’ Roses"]  # apostrofo curvo tipografico
    },
    {
        "canonical": "Leone Di Lernia",
        "duplicates": ["Leone di lernia"]
    },
    {
        "canonical": "People From Venus",
        "duplicates": ["People from Venus"]
    }
]

def get_db_connection(db_path):
    if not os.path.exists(db_path):
        print(f"[ERRORE] Database Beets non trovato in: {db_path}")
        sys.exit(1)
    return sqlite3.connect(db_path)

def merge_clashes(apply_run=False):
    print("=" * 70)
    print(" 🧹 STRUMENTO DI BONIFICA E FUSIONE CLASH ARTISTI (FASE 2)")
    print(f" Percorso Backup : {BACKUP_DIR}")
    print(f" Database Beets  : {DB_PATH}")
    print(f" Modalità        : {'⚠️  APPLICAZIONE REALE ⚠️' if apply_run else '🔍 DRY-RUN (Simulazione)'}")
    print("=" * 70)

    if not os.path.exists(BACKUP_DIR):
        print(f"[ERRORE] Cartella backup {BACKUP_DIR} non montata.")
        sys.exit(1)

    con = get_db_connection(DB_PATH)
    cur = con.cursor()

    total_files_moved = 0
    total_db_updates = 0
    dirs_to_remove = []

    # Risoluzione preventiva Unicode NFD per macOS
    existing_dirs = {unicodedata.normalize('NFC', d): d for d in os.listdir(BACKUP_DIR)}

    for group in CLASH_GROUPS:
        canon_name = group["canonical"]
        canon_nfc = unicodedata.normalize('NFC', canon_name)

        # Determiniamo il nome reale sul disco per la cartella canonica
        canon_real_name = existing_dirs.get(canon_nfc, canon_name)
        canon_path = os.path.join(BACKUP_DIR, canon_real_name)

        print(f"\n📂 Gruppo Canonico: '{canon_real_name}'")

        # Se la cartella canonica non esiste fisicamente, ma esistono duplicati, la creeremo
        canon_exists = os.path.exists(canon_path)
        if not canon_exists:
            # Cerchiamo se almeno un duplicato esiste prima di pianificare la creazione
            any_dup_exists = any(os.path.exists(os.path.join(BACKUP_DIR, dup)) for dup in group["duplicates"])
            if any_dup_exists:
                print(f"  [CREA DIR CANONICA] Verrà creata la cartella: {canon_path}")
                if apply_run:
                    os.makedirs(canon_path, exist_ok=True)
                    canon_exists = True

        for duplicate in group["duplicates"]:
            # Risoluzione esatta del duplicato sul disco (gestione NFD/NFC)
            dup_nfc = unicodedata.normalize('NFC', duplicate)
            dup_real_name = None
            for d in os.listdir(BACKUP_DIR):
                if unicodedata.normalize('NFC', d) == dup_nfc:
                    dup_real_name = d
                    break

            if not dup_real_name:
                # Il duplicato non esiste sul disco, saltiamo
                continue

            dup_path = os.path.join(BACKUP_DIR, dup_real_name)
            print(f"  ⚠️  Rilevato Duplicato: '{dup_real_name}'")

            # Scansione di tutti i file e sottocartelle del duplicato
            for root, dirs, files in os.walk(dup_path):
                for file in files:
                    # Salta TUTTI i file nascosti o speciali di macOS (es. .DS_Store, AppleDouble ._*)
                    # Saranno rimossi in sicurezza durante la cancellazione della cartella vuota
                    if file.startswith('.'):
                        continue

                    src_file_path = os.path.join(root, file)
                    rel_path = os.path.relpath(src_file_path, dup_path)
                    dest_file_path = os.path.join(canon_path, rel_path)

                    print(f"    • Spostamento: {dup_real_name}/{rel_path} ➔ {canon_real_name}/{rel_path}")
                    total_files_moved += 1

                    if apply_run:
                        os.makedirs(os.path.dirname(dest_file_path), exist_ok=True)
                        try:
                            shutil.move(src_file_path, dest_file_path)
                        except FileNotFoundError:
                            # Se il file è stato nel frattempo spostato o rimosso da meccanismi di FS
                            print(f"    [AVVISO] File già spostato o non trovato: {src_file_path}")

            dirs_to_remove.append(dup_path)

            # --- AGGIORNAMENTO DATABASE ---
            old_rel_prefix = dup_real_name + "/"
            new_rel_prefix = canon_real_name + "/"

            old_abs_prefix = os.path.join(BACKUP_DIR, dup_real_name) + "/"
            new_abs_prefix = os.path.join(BACKUP_DIR, canon_real_name) + "/"

            # Eseguiamo gli aggiornamenti sia per i percorsi relativi che assoluti
            for old_prefix, new_prefix in [(old_rel_prefix, new_rel_prefix), (old_abs_prefix, new_abs_prefix)]:
                old_bytes = old_prefix.encode('utf-8')
                new_bytes = new_prefix.encode('utf-8')

                # 1. Aggiornamento Items (tracce)
                cur.execute("SELECT id, path FROM items WHERE path LIKE ?", (old_bytes + b'%',))
                items_to_update = cur.fetchall()
                if items_to_update:
                    print(f"    ➔ DB: Trovate {len(items_to_update)} tracce da aggiornare (prefisso: {old_prefix})")
                    for item_id, path_bytes in items_to_update:
                        new_path_bytes = path_bytes.replace(old_bytes, new_bytes)
                        total_db_updates += 1
                        if apply_run:
                            cur.execute("UPDATE items SET path = ? WHERE id = ?", (new_path_bytes, item_id))

                # 2. Aggiornamento Albums (artpath)
                cur.execute("SELECT id, artpath FROM albums WHERE artpath LIKE ?", (old_bytes + b'%',))
                albums_to_update = cur.fetchall()
                if albums_to_update:
                    print(f"    ➔ DB: Trovati {len(albums_to_update)} album (artpath) da aggiornare (prefisso: {old_prefix})")
                    for album_id, artpath_bytes in albums_to_update:
                        if artpath_bytes:
                            new_artpath_bytes = artpath_bytes.replace(old_bytes, new_bytes)
                            total_db_updates += 1
                            if apply_run:
                                cur.execute("UPDATE albums SET artpath = ? WHERE id = ?", (new_artpath_bytes, album_id))

    if apply_run and dirs_to_remove:
        print("\n🗑️  Pulizia contenitori vuoti in corso...")
        for d in set(dirs_to_remove):
            try:
                if os.path.exists(d):
                    shutil.rmtree(d)
                    print(f"  [ELIMINATA DIR] {d}")
            except Exception as e:
                print(f"  [AVVISO] Impossibile rimuovere {d}: {e}")

    con.commit()
    con.close()

    print("\n" + "=" * 70)
    print(" 📊 RIEPILOGO STATISTICHE")
    print(f" File da spostare fisicamente : {total_files_moved}")
    print(f" Aggiornamenti record nel DB  : {total_db_updates}")
    print("" + "=" * 70)

    if not apply_run:
        print("\n🔍 Simulazione completata senza apportare modifiche reali.")
        print("   Per eseguire la bonifica reale su disco e DB, lancia il comando:")
        print("   python3 merge_existing_clashes.py --apply")
        print("=" * 70)

if __name__ == "__main__":
    apply_run = "--apply" in sys.argv
    merge_clashes(apply_run)

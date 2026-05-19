#!/usr/bin/env python3
"""
merge_album_clashes.py — Bonifica e fusione dei duplicati di cartelle degli album
================================================================================
Rileva automaticamente le cartelle degli album duplicate (es. [2010] Album vs Album (2010)),
sposta fisicamente i file dalle cartelle duplicate a quelle canoniche sotto /Volumes/arrdata/media/music_backup/
e aggiorna atomicamente il database SQLite di Beets (musiclibrary.db) per mantenere la coerenza.

Uso:
  python3 merge_album_clashes.py          # DRY-RUN (Simulazione)
  python3 merge_album_clashes.py --apply  # ESECUZIONE REALE
"""

import os
import sys
import sqlite3
import shutil
import re
import unicodedata

# Configurazione percorsi
BACKUP_DIR = sys.argv[2] if len(sys.argv) > 2 and sys.argv[2] != "--apply" else (sys.argv[1] if len(sys.argv) > 1 and sys.argv[1] != "--apply" else "/Volumes/arrdata/media/music_backup")
DB_PATH = "/Users/olindo/prj/k8s-lab/import_music/musiclibrary.db"

def get_compare_key(name):
    # Rimuove anni tipo [2010] o (2010)
    name_clean = re.sub(r'\[\d{4}\]|\(\d{4}\)', '', name)
    name_clean = unicodedata.normalize('NFC', name_clean).lower()
    name_clean = re.sub(r'[^a-z0-9]', '', name_clean)
    return name_clean.strip()

def extract_year(name):
    m = re.search(r'(\d{4})', name)
    return m.group(1) if m else None

def clean_album_name(name):
    # Rimuove anno tipo [2010], (2010), ecc.
    name = re.sub(r'\[\d{4}\]|\(\d{4}\)', '', name)
    # Pulisce spazi multipli
    return re.sub(r'\s+', ' ', name).strip()

def is_canonical_format(name):
    # Ritorna True se il nome inizia esattamente con [YYYY] seguito da uno spazio
    return bool(re.match(r'^\[\d{4}\]\s+.*', name))

def get_db_connection(db_path):
    if not os.path.exists(db_path):
        print(f"[ERRORE] Database Beets non trovato in: {db_path}")
        sys.exit(1)
    return sqlite3.connect(db_path)

def discover_clash_groups():
    if not os.path.exists(BACKUP_DIR):
        print(f"[ERRORE] Cartella backup {BACKUP_DIR} non montata.")
        sys.exit(1)

    clash_groups = []
    artists = [d for d in os.listdir(BACKUP_DIR) if os.path.isdir(os.path.join(BACKUP_DIR, d))]

    for artist in sorted(artists):
        if artist.startswith('.') or artist.startswith('_'):
            continue

        artist_path = os.path.join(BACKUP_DIR, artist)
        albums = [d for d in os.listdir(artist_path) if os.path.isdir(os.path.join(artist_path, d))]

        album_map = {}
        for album in albums:
            if album.startswith('.') or album.startswith('_') or album == 'Non-Album':
                continue

            comp_key = get_compare_key(album)
            year = extract_year(album)
            key = f"{comp_key}_{year}" if year else f"{comp_key}_noyear"

            if key not in album_map:
                album_map[key] = []
            album_map[key].append(album)

        for key, folders in album_map.items():
            if len(folders) > 1:
                # Abbiamo un clash! Troviamo o stabiliamo il nome canonico
                canonical = None

                # 1. Cerca se una cartella ha già il formato canonico [YYYY] Album
                for folder in folders:
                    if is_canonical_format(folder):
                        canonical = folder
                        break

                # 2. Se nessuna è canonica ma c'è un anno, la costruiamo nel formato [YYYY] Album
                if not canonical:
                    first_folder = folders[0]
                    year = extract_year(first_folder)
                    clean_name = clean_album_name(first_folder)
                    if year and clean_name:
                        canonical = f"[{year}] {clean_name}"
                    else:
                        # Fallback: la prima cartella del gruppo
                        canonical = first_folder

                # Le altre cartelle sono duplicati da fondere
                duplicates = [f for f in folders if f != canonical]

                if duplicates:
                    clash_groups.append({
                        "artist": artist,
                        "canonical": canonical,
                        "duplicates": duplicates
                    })

    return clash_groups

def merge_album_clashes(apply_run=False):
    print("=" * 80)
    print(" 🧹 STRUMENTO DI BONIFICA E FUSIONE CLASH ALBUM (FASE 2)")
    print(f" Percorso Backup : {BACKUP_DIR}")
    print(f" Database Beets  : {DB_PATH}")
    print(f" Modalità        : {'⚠️  APPLICAZIONE REALE ⚠️' if apply_run else '🔍 DRY-RUN (Simulazione)'}")
    print("=" * 80)

    clash_groups = discover_clash_groups()
    if not clash_groups:
        print("✅ Nessun clash di album rilevato nel filesystem. La libreria è a posto!")
        return

    print(f"ℹ️  Trovati {len(clash_groups)} gruppi di album in conflitto da elaborare.\n")

    con = get_db_connection(DB_PATH)
    cur = con.cursor()

    total_files_moved = 0
    total_db_updates = 0
    dirs_to_remove = []

    for group in clash_groups:
        artist = group["artist"]
        canon_name = group["canonical"]
        artist_path = os.path.join(BACKUP_DIR, artist)
        canon_path = os.path.join(artist_path, canon_name)

        print(f"\n📂 Artista: '{artist}'")
        print(f"  ➔ Target Canonico: '{canon_name}'")

        # Se la cartella canonica non esiste fisicamente, la creiamo se siamo in apply_run
        canon_exists = os.path.exists(canon_path)
        if not canon_exists:
            print(f"  [CREA DIR CANONICA] Verrà creata la cartella: {artist}/{canon_name}")
            if apply_run:
                os.makedirs(canon_path, exist_ok=True)
                canon_exists = True

        for duplicate in group["duplicates"]:
            dup_path = os.path.join(artist_path, duplicate)
            print(f"  ⚠️  Sorgente Duplicata: '{duplicate}'")

            # Scansione di tutti i file e sottocartelle del duplicato
            if os.path.exists(dup_path):
                for root, dirs, files in os.walk(dup_path):
                    for file in files:
                        if file.startswith('.'):
                            # Salta i file nascosti di sistema macOS (saranno rimossi cancellando la cartella)
                            continue

                        src_file_path = os.path.join(root, file)
                        rel_path = os.path.relpath(src_file_path, dup_path)
                        dest_file_path = os.path.join(canon_path, rel_path)

                        print(f"    • Spostamento: {artist}/{duplicate}/{rel_path} ➔ {artist}/{canon_name}/{rel_path}")
                        total_files_moved += 1

                        if apply_run:
                            os.makedirs(os.path.dirname(dest_file_path), exist_ok=True)
                            try:
                                shutil.move(src_file_path, dest_file_path)
                            except FileNotFoundError:
                                print(f"    [AVVISO] File già spostato o non trovato: {src_file_path}")

                dirs_to_remove.append(dup_path)

            # --- AGGIORNAMENTO DATABASE ---
            # Costruiamo i percorsi relativi ed assoluti sia per la sorgente che per il target
            old_rel_prefix = f"{artist}/{duplicate}/"
            new_rel_prefix = f"{artist}/{canon_name}/"

            old_abs_prefix = os.path.join(BACKUP_DIR, artist, duplicate) + "/"
            new_abs_prefix = os.path.join(BACKUP_DIR, artist, canon_name) + "/"

            # Aggiorniamo sia i percorsi relativi che assoluti in items.path ed albums.artpath
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

    print("\n" + "=" * 80)
    print(" 📊 RIEPILOGO STATISTICHE")
    print(f" File da spostare fisicamente : {total_files_moved}")
    print(f" Aggiornamenti record nel DB  : {total_db_updates}")
    print("" + "=" * 80)

    if not apply_run:
        print("\n🔍 Simulazione completata senza apportare modifiche reali.")
        print("   Per eseguire la bonifica reale su disco e DB, lancia il comando:")
        print("   python3 merge_album_clashes.py --apply")
        print("=" * 80)

if __name__ == "__main__":
    apply_run = "--apply" in sys.argv
    merge_album_clashes(apply_run)

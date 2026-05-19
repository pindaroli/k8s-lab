#!/usr/bin/env python3
import os
import sys
import shutil
import sqlite3
import argparse
from collections import defaultdict

DB_PATH = "/Users/olindo/prj/k8s-lab/import_music/musiclibrary.db"
LIB_DIR = "/Volumes/arrdata/media/music_backup"

def get_compare_key(name):
    import re
    n = name.lower()
    n = re.sub(r'[^a-z0-9]', '', n)
    return n

def backup_database():
    backup_path = f"{DB_PATH}.bak.all_zeros_purge"
    try:
        shutil.copy2(DB_PATH, backup_path)
        print(f"[INFO] Backup del database effettuato con successo in: {backup_path}")
        return True
    except Exception as e:
        print(f"[ERROR] Impossibile effettuare il backup del database: {e}")
        return False

def main():
    parser = argparse.ArgumentParser(description="Pulisce in modo intelligente i duplicati ad Anno 0 nel DB Beets e nel filesystem")
    parser.add_argument("--run", action="store_true", help="Esegue effettivamente gli spostamenti e aggiorna il database")
    args = parser.parse_args()

    if not os.path.exists(DB_PATH):
        print(f"[ERROR] Database Beets non trovato in: {DB_PATH}")
        sys.exit(1)

    print("=" * 80)
    print("🚀 STRUMENTO DI BONIFICA DUPLICATI ANNO 0 🚀")
    print("=" * 80)
    print(f"Database: {DB_PATH}")
    print(f"Library:  {LIB_DIR}")
    print(f"Modalità: {'REAL RUN (Eliminazione attiva)' if args.run else 'DRY-RUN (Simulazione)'}")
    print("-" * 80)

    from beets import library
    lib = library.Library(DB_PATH, directory=LIB_DIR)

    # Organizza gli items per (artista, normalized_album)
    album_groups = defaultdict(lambda: defaultdict(list))

    for item in lib.items():
        artist = (item.artist or "Unknown Artist").strip()
        album = (item.album or "").strip()
        year = item.year or 0

        album_norm = get_compare_key(album)
        if not album_norm:
            continue

        group_key = (artist.lower(), album_norm)
        album_groups[group_key][year].append(item)

    safe_to_delete = []
    unsafe_groups = []

    for (artist_lower, album_norm), years_dict in album_groups.items():
        if len(years_dict) <= 1:
            continue # Nessuna variazione di anno, quindi non è un duplicato

        if 0 not in years_dict:
            continue # Nessun duplicato ad Anno 0

        # Troviamo gli items ad anno 0 e quelli ad anno > 0
        year_zero_items = years_dict[0]

        # Uniamo tutti gli items con anno > 0
        year_gt_zero_items = []
        for yr, items in years_dict.items():
            if yr > 0:
                year_gt_zero_items.extend(items)

        if not year_gt_zero_items:
            continue

        # Applichiamo il filtro di sicurezza intelligente:
        # La versione con anno > 0 deve contenere almeno tante tracce quante la versione ad anno 0
        # (o comunque essere un album completo con almeno 3 tracce).
        # Questo evita di cancellare l'album principale se la copia con l'anno ha solo 1 traccia (compilation).
        sample_item = year_zero_items[0]
        artist_name = sample_item.artist
        album_name = sample_item.album

        if len(year_gt_zero_items) >= len(year_zero_items) and len(year_gt_zero_items) >= 3:
            safe_to_delete.append({
                'artist': artist_name,
                'album': album_name,
                'zero_items': year_zero_items,
                'clean_items': year_gt_zero_items
            })
        else:
            unsafe_groups.append({
                'artist': artist_name,
                'album': album_name,
                'zero_count': len(year_zero_items),
                'clean_count': len(year_gt_zero_items),
                'zero_items': year_zero_items,
                'clean_items': year_gt_zero_items
            })

    print(f"\n📊 RISULTATI DELL'AUDIT DUPLICATI:")
    print(f"  - Gruppi SICURI da eliminare (duplicati speculari completi): {len(safe_to_delete)}")
    print(f"  - Gruppi SOSPETTI (richiedono review manuale): {len(unsafe_groups)}")
    print("-" * 80)

    if unsafe_groups:
        print("\n⚠️ GRUPPI UN-SAFE CHE NON VERRANNO TOCCATI (Anno 0 ha più tracce o copia pulita parziale):")
        for g in unsafe_groups:
            clean_years = sorted(list(set(item.year for item in g['clean_items'])))
            print(f"  ❌ {g['artist']} - {g['album']}:")
            print(f"     -> Anno 0    : {g['zero_count']} tracce")
            print(f"     -> Anno {clean_years}: {g['clean_count']} tracce")
        print("-" * 80)

    if not safe_to_delete:
        print("[INFO] Nessun duplicato speculare ad Anno 0 sicuro da eliminare.")
        return

    print("\n🟢 GRUPPI SICURI DA ELIMINARE (Anno 0 verrà rimosso):")
    for g in safe_to_delete:
        clean_years = sorted(list(set(item.year for item in g['clean_items'])))
        print(f"  ✅ {g['artist']} - {g['album']}:")
        print(f"     -> Rimuovo {len(g['zero_items'])} tracce (Anno 0)")
        print(f"     -> Mantengo {len(g['clean_items'])} tracce (Anno {clean_years})")

    if args.run:
        if not backup_database():
            print("[CRITICAL] Interruzione per sicurezza: backup fallito.")
            sys.exit(1)

        print("\n🔥 AVVIO ELIMINAZIONE DEI DUPLICATI...")
        deleted_files_count = 0
        deleted_db_count = 0
        directories_to_check = set()

        for g in safe_to_delete:
            print(f"\n👉 Bonifica: {g['artist']} - {g['album']}")

            # Percorsi fisici delle tracce pulite (da non toccare!)
            clean_paths = set(item.path for item in g['clean_items'])

            for item in g['zero_items']:
                path_bytes = item.path
                path_str = path_bytes.decode('utf-8', 'replace')
                directories_to_check.add(os.path.dirname(path_str))

                # Rimuoviamo il file fisico SOLO se il suo percorso NON è lo stesso di una traccia pulita
                # (gestisce i case-clash e file duplicati in cartelle condivise o separate)
                if path_bytes not in clean_paths:
                    if os.path.exists(path_str):
                        try:
                            os.remove(path_str)
                            print(f"  [OK] Eliminato file duplicato: {path_str}")
                            deleted_files_count += 1
                        except Exception as e:
                            print(f"  [ERROR] Errore eliminazione file {path_str}: {e}")
                    else:
                        print(f"  [WARNING] File non trovato sul disco: {path_str}")
                else:
                    print(f"  [SKIP FS] File condiviso per case-clash: {path_str} (non eliminato dal filesystem)")

                # Rimuove il record dal DB Beets
                try:
                    item.remove()
                    deleted_db_count += 1
                except Exception as e:
                    print(f"  [ERROR] Errore DB per ID {item.id}: {e}")

        # Pulizia delle directory vuote residue (es. se la copia ad anno 0 era in una cartella separata)
        print("\n🧹 Pulizia delle directory vuote residue...")
        for src_dir in directories_to_check:
            if os.path.exists(src_dir):
                # Rimuove file spuri tipo .DS_Store o cover.jpg se rimasti orfani
                try:
                    non_trash_files = []
                    for f in os.listdir(src_dir):
                        if f.lower() in ['.ds_store', 'thumbs.db', 'cover.jpg', 'folder.jpg']:
                            os.remove(os.path.join(src_dir, f))
                        else:
                            non_trash_files.append(f)

                    if not non_trash_files:
                        os.rmdir(src_dir)
                        print(f"  [OK] Rimossa cartella orfana rimasta vuota: {src_dir}")
                except Exception as e:
                    pass

        print("\n" + "=" * 80)
        print("📈 STATISTICHE FINALI:")
        print(f"  - Tracce rimosse dal DB: {deleted_db_count}")
        print(f"  - File fisici eliminati: {deleted_files_count}")
        print("=" * 80)
    else:
        print("\n[INFO] Modalità DRY-RUN completata. Nessuna modifica applicata.")

if __name__ == "__main__":
    main()

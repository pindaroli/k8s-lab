#!/usr/bin/env python3
"""
merge_beets_databases.py — Merge external Beets database into local workspace DB
================================================================================
Useful when Beets was run externally using the default global config directory
and we need to import those records into our repository's tracking database.
"""

import sqlite3
import os
import sys

SOURCE_DB = "/Users/olindo/.config/beets/musiclibrary.db"
TARGET_DB = "/Users/olindo/prj/k8s-lab/import_music/musiclibrary.db"

def merge_databases(apply_changes=False):
    print("=" * 70)
    print(" 🛠  UNIFICAZIONE DATABASE BEETS (Home DB -> Workspace DB)")
    print("=" * 70)
    print(f" Sorgente (Home): {SOURCE_DB}")
    print(f" Destinazione (Workspace): {TARGET_DB}")
    print("-" * 70)

    if not os.path.exists(SOURCE_DB):
        print(f"[FATAL] Il database sorgente non esiste a {SOURCE_DB}")
        return False
    if not os.path.exists(TARGET_DB):
        print(f"[FATAL] Il database di destinazione non esiste a {TARGET_DB}")
        return False

    # Apriamo le connessioni
    src_conn = sqlite3.connect(SOURCE_DB)
    src_conn.row_factory = sqlite3.Row
    src_cur = src_conn.cursor()

    tgt_conn = sqlite3.connect(TARGET_DB)
    tgt_conn.row_factory = sqlite3.Row
    tgt_cur = tgt_conn.cursor()

    # 1. Recupero schema delle tabelle principali
    src_cur.execute("PRAGMA table_info(albums)")
    album_cols = [r['name'] for r in src_cur.fetchall()]

    src_cur.execute("PRAGMA table_info(items)")
    item_cols = [r['name'] for r in src_cur.fetchall()]

    src_cur.execute("PRAGMA table_info(album_attributes)")
    album_attr_cols = [r['name'] for r in src_cur.fetchall()]

    src_cur.execute("PRAGMA table_info(item_attributes)")
    item_attr_cols = [r['name'] for r in src_cur.fetchall()]

    print(f"[INFO] Trovate colonne albums: {len(album_cols)}")
    print(f"[INFO] Trovate colonne items: {len(item_cols)}")

    # 2. Caricamento albums sorgente e destinazione per mappatura
    src_cur.execute("SELECT * FROM albums")
    src_albums = {dict(r)['id']: dict(r) for r in src_cur.fetchall()}

    tgt_cur.execute("SELECT * FROM albums")
    tgt_albums = {dict(r)['id']: dict(r) for r in tgt_cur.fetchall()}

    # Creiamo indici di lookup per target per evitare duplicati
    # Mappiamo mb_albumid -> id e (albumartist, album) -> id
    tgt_album_by_mbid = {}
    tgt_album_by_name = {}
    for t_id, t_alb in tgt_albums.items():
        mbid = t_alb.get('mb_albumid')
        if mbid:
            tgt_album_by_mbid[mbid] = t_id

        artist = t_alb.get('albumartist', '')
        title = t_alb.get('album', '')
        if artist and title:
            tgt_album_by_name[(artist.lower(), title.lower())] = t_id

    # Mappa da source_album_id -> target_album_id
    album_id_mapping = {}

    new_albums_to_insert = []

    for s_id, s_alb in src_albums.items():
        # Verifichiamo se l'album esiste già nel target
        matched_tgt_id = None
        mbid = s_alb.get('mb_albumid')
        if mbid and mbid in tgt_album_by_mbid:
            matched_tgt_id = tgt_album_by_mbid[mbid]
        else:
            artist = s_alb.get('albumartist', '')
            title = s_alb.get('album', '')
            key = (artist.lower(), title.lower())
            if key in tgt_album_by_name:
                matched_tgt_id = tgt_album_by_name[key]

        if matched_tgt_id is not None:
            # L'album esiste già, salviamo la mappatura dell'ID
            album_id_mapping[s_id] = matched_tgt_id
        else:
            # L'album è nuovo, lo inseriremo
            new_albums_to_insert.append((s_id, s_alb))

    print(f"[INFO] Album già esistenti: {len(album_id_mapping)}")
    print(f"[INFO] Nuovi album da inserire: {len(new_albums_to_insert)}")

    # 3. Caricamento items sorgente e destinazione
    src_cur.execute("SELECT * FROM items")
    src_items = {dict(r)['id']: dict(r) for r in src_cur.fetchall()}

    tgt_cur.execute("SELECT path FROM items")
    tgt_paths = {r['path'] for r in tgt_cur.fetchall()}

    new_items_to_insert = []
    skipped_items_count = 0

    for s_id, s_itm in src_items.items():
        path = s_itm['path']
        if path in tgt_paths:
            skipped_items_count += 1
        else:
            new_items_to_insert.append((s_id, s_itm))

    print(f"[INFO] Tracce già esistenti (saltate): {skipped_items_count}")
    print(f"[INFO] Nuove tracce da inserire: {len(new_items_to_insert)}")

    if not apply_changes:
        print("\n[DRY RUN] Nessuna modifica applicata. Rilancia con '--apply' per unificare.")
        src_conn.close()
        tgt_conn.close()
        return True

    # ---- APPLICAZIONE MODIFICHE ----
    print("\n🚀 Applicazione delle modifiche al database target...")
    try:
        # Inserimento nuovi albums
        album_insert_cols = [c for c in album_cols if c != 'id']
        album_placeholders = ", ".join(["?"] * len(album_insert_cols))
        album_sql = f"INSERT INTO albums ({', '.join(album_insert_cols)}) VALUES ({album_placeholders})"

        for s_id, s_alb in new_albums_to_insert:
            vals = [s_alb[c] for c in album_insert_cols]
            tgt_cur.execute(album_sql, vals)
            new_id = tgt_cur.lastrowid
            album_id_mapping[s_id] = new_id

            # Copia attributi album
            src_cur.execute("SELECT * FROM album_attributes WHERE entity_id = ?", (s_id,))
            for attr in src_cur.fetchall():
                attr_dict = dict(attr)
                tgt_cur.execute(
                    "INSERT INTO album_attributes (entity_id, key, value) VALUES (?, ?, ?)",
                    (new_id, attr_dict['key'], attr_dict['value'])
                )

        print(f"[SUCCESS] Inseriti {len(new_albums_to_insert)} nuovi record album.")

        # Inserimento nuovi items
        item_insert_cols = [c for c in item_cols if c != 'id']
        item_placeholders = ", ".join(["?"] * len(item_insert_cols))
        item_sql = f"INSERT INTO items ({', '.join(item_insert_cols)}) VALUES ({item_placeholders})"

        for s_id, s_itm in new_items_to_insert:
            # Remappiamo album_id
            s_album_id = s_itm.get('album_id')
            t_album_id = album_id_mapping.get(s_album_id) if s_album_id else None

            # Prepariamo i valori
            vals = []
            for c in item_insert_cols:
                if c == 'album_id':
                    vals.append(t_album_id)
                else:
                    vals.append(s_itm[c])

            tgt_cur.execute(item_sql, vals)
            new_item_id = tgt_cur.lastrowid

            # Copia attributi item
            src_cur.execute("SELECT * FROM item_attributes WHERE entity_id = ?", (s_id,))
            for attr in src_cur.fetchall():
                attr_dict = dict(attr)
                tgt_cur.execute(
                    "INSERT INTO item_attributes (entity_id, key, value) VALUES (?, ?, ?)",
                    (new_item_id, attr_dict['key'], attr_dict['value'])
                )

        print(f"[SUCCESS] Inserite {len(new_items_to_insert)} nuove tracce.")
        tgt_conn.commit()
        print("🎉 Database unificato correttamente con transazione sicura!")

    except Exception as e:
        tgt_conn.rollback()
        print(f"[ERROR] Si è verificato un errore durante l'unificazione. Rollback effettuato: {e}")
        return False
    finally:
        src_conn.close()
        tgt_conn.close()

    return True

if __name__ == "__main__":
    apply = "--apply" in sys.argv
    merge_databases(apply)

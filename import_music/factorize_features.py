#!/usr/bin/env python3
import os
import sys
import re
import argparse
import shutil
from beets import library

DB_PATH = "/Users/olindo/prj/k8s-lab/import_music/musiclibrary.db"
lib_dir = "/Volumes/arrdata/media/music_backup"

# Regex per intercettare i feat nei vari formati (Feat, feat, Feat., feat., Ft, ft, Ft., ft., featuring, Featuring)
FEAT_REGEX = re.compile(r'\s+\b(feat\.?|ft\.?|featuring)\s+(.+)$', re.IGNORECASE)

def backup_database():
    backup_path = f"{DB_PATH}.bak.feat"
    try:
        shutil.copy2(DB_PATH, backup_path)
        print(f"[INFO] Backup pre-fattorizzazione creato in: {backup_path}")
        return True
    except Exception as e:
        print(f"[ERROR] Impossibile creare il backup pre-fattorizzazione: {e}")
        return False

def parse_featuring(artist_name):
    """
    Spezza l'artista in (artista_principale, artista_ospite) se contiene un featuring.
    Esempio: 'Akon Feat. 2Pac' -> ('Akon', '2Pac')
    """
    if not artist_name:
        return None

    match = FEAT_REGEX.search(artist_name)
    if match:
        guest = match.group(2).strip()
        # Rimuove il tag feat dall'artista principale
        main = artist_name[:match.start()].strip()
        return main, guest
    return None

def main():
    parser = argparse.ArgumentParser(description="Generalizza ed estrae i Featuring dai nomi degli artisti spostandoli nei titoli dei brani.")
    parser.add_argument("--run", action="store_true", help="Applica le modifiche reali al database Beets")
    args = parser.parse_args()

    if not os.path.exists(DB_PATH):
        print(f"[ERROR] Database Beets non trovato in: {DB_PATH}")
        sys.exit(1)

    print("=" * 80)
    print("🎸 SCRIPT GENERALIZZATO DI FATTORIZZAZIONE FEATURING 🎸")
    print("=" * 80)
    print(f"Database: {DB_PATH}")
    print(f"Modalità: {'REAL RUN (Modifiche attive)' if args.run else 'DRY-RUN (Simulazione)'}")
    print("-" * 80)

    if args.run:
        if not backup_database():
            sys.exit(1)

    lib = library.Library(DB_PATH, directory=lib_dir)

    modified_tracks_count = 0
    all_items = list(lib.items())

    # Raccogliamo le modifiche per stamparle chiaramente
    changes = []

    for item in all_items:
        artist = item.artist or ""
        albumartist = item.albumartist or ""
        title = item.title or ""

        changed = False
        new_artist = artist
        new_albumartist = albumartist
        new_title = title

        # 1. Controlla e scorpora il feat dall'Artist
        feat_info = parse_featuring(artist)
        if feat_info:
            main_art, guest_art = feat_info
            new_artist = main_art
            changed = True

            # Aggiungi il feat al titolo se non è già presente
            # Controlliamo in modo case-insensitive se 'feat' o il nome dell'ospite è già nel titolo
            if "feat" not in title.lower() and "ft." not in title.lower() and guest_art.lower() not in title.lower():
                new_title = f"{title} (feat. {guest_art})"

        # 2. Controlla e scorpora il feat dall'Album Artist
        album_feat_info = parse_featuring(albumartist)
        if album_feat_info:
            main_album_art, _ = album_feat_info
            new_albumartist = main_album_art
            changed = True

        if changed:
            changes.append({
                'item': item,
                'old_artist': artist,
                'new_artist': new_artist,
                'old_albumartist': albumartist,
                'new_albumartist': new_albumartist,
                'old_title': title,
                'new_title': new_title
            })

    # Stampa i cambiamenti rilevati
    if not changes:
        print("[INFO] Nessun featuring da fattorizzare trovato nel database.")
        return

    print(f"[INFO] Trovati {len(changes)} brani con featuring da elaborare:\n")

    for change in changes:
        item = change['item']
        print(f"🎵 Traccia ID {item.id}: '{change['old_artist']} - {change['old_title']}'")
        if change['old_artist'] != change['new_artist']:
            print(f"   👤 Artista:      '{change['old_artist']}' -> '{change['new_artist']}'")
        if change['old_albumartist'] != change['new_albumartist']:
            print(f"   💿 Album Artist:  '{change['old_albumartist']}' -> '{change['new_albumartist']}'")
        if change['old_title'] != change['new_title']:
            print(f"   📝 Titolo:       '{change['old_title']}' -> '{change['new_title']}'")
        print("-" * 60)

        if args.run:
            item.artist = change['new_artist']
            item.albumartist = change['new_albumartist']
            item.title = change['new_title']
            item.store()
            modified_tracks_count += 1

    print("\n" + "=" * 80)
    print("📈 STATISTICHE FATTORIZZAZIONE:")
    print(f"  - Tracce identificate: {len(changes)}")
    print(f"  - Tracce aggiornate a DB: {modified_tracks_count if args.run else 0}")
    print("=" * 80)
    if not args.run:
        print("[TIP] Per applicare realmente le modifiche, esegui lo script con l'opzione: --run")
        print("      Successivamente, eseguendo lo script di standardizzazione dei percorsi,")
        print("      i file verranno spostati fisicamente nelle nuove cartelle corrette dell'artista principale!")
        print("=" * 80)

if __name__ == "__main__":
    main()

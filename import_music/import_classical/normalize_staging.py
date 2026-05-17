#!/usr/bin/env python3
import os
import sys
import shutil
import re

STAGING_DIR = "/Volumes/classical/staging"

def normalize_layout(apply_run=False):
    print("=" * 60)
    print(" 🎼 NORMALIZZAZIONE LAYOUT CLASSICAL STAGING")
    print(f" Cartella staging: {STAGING_DIR}")
    print(f" Modalità: {'APPLICA MODIFICHE' if apply_run else 'DRY-RUN (Sola simulazione)'}")
    print("=" * 60)

    if not os.path.exists(STAGING_DIR):
        print(f"[ERRORE] La cartella {STAGING_DIR} non esiste o non è montata.")
        sys.exit(1)

    items = os.listdir(STAGING_DIR)
    # Intercetta cartelle di primo livello tipo Disc_1, CD2, CD_3, d4
    disc_pattern = re.compile(r'^(disc|cd|d)[_\s-]*\d+', re.IGNORECASE)

    moves_planned = []
    empty_dirs_to_remove = []

    for item in items:
        item_path = os.path.join(STAGING_DIR, item)
        if not os.path.isdir(item_path):
            continue

        if disc_pattern.match(item):
            subitems = os.listdir(item_path)
            # Esclude file nascosti/sistema (es. .DS_Store)
            subdirs = [s for s in subitems if os.path.isdir(os.path.join(item_path, s)) and not s.startswith('.')]

            if len(subdirs) == 1:
                album_name = subdirs[0]
                disc_name = item # es. "Disc_1"

                src_album_path = os.path.join(item_path, album_name)
                dest_album_path = os.path.join(STAGING_DIR, album_name)
                final_dest_disc_path = os.path.join(dest_album_path, disc_name)

                moves_planned.append({
                    'src': src_album_path,
                    'dest_parent': dest_album_path,
                    'dest_final': final_dest_disc_path,
                    'disc_name': disc_name,
                    'album_name': album_name,
                    'original_top_dir': item_path
                })
            elif len(subdirs) > 1:
                print(f"[AVVISO] La cartella {item} contiene più di una sottocartella, saltata: {subdirs}")
            else:
                print(f"[AVVISO] La cartella {item} non contiene sottocartelle valide.")

    if not moves_planned:
        print("[OK] Nessun layout multi-disco invertito (Disc_X al primo livello) rilevato.")
        return

    print(f"\nRilevate {len(moves_planned)} cartelle di dischi da riorganizzare:")
    for move in moves_planned:
        print(f"  • Rilevato: {move['src']}")
        print(f"    --> Diventerà: {move['dest_final']}")

    if not apply_run:
        print("\n[DRY-RUN] Nessuna modifica eseguita. Per applicare le modifiche, esegui:")
        print("  python3 normalize_staging.py --apply")
        return

    print("\nAvvio riorganizzazione...")
    for move in moves_planned:
        # Crea la cartella dell'album a livello superiore se non esiste
        if not os.path.exists(move['dest_parent']):
            print(f"  [CREA DIR] {move['dest_parent']}")
            os.makedirs(move['dest_parent'], exist_ok=True)

        # Esegue lo spostamento
        print(f"  [SPOSTA] {move['src']} --> {move['dest_final']}")
        shutil.move(move['src'], move['dest_final'])
        empty_dirs_to_remove.append(move['original_top_dir'])

    # Rimuove le vecchie cartelle Disc_X ormai vuote
    print("\nPulizia vecchi contenitori...")
    for d in set(empty_dirs_to_remove):
        try:
            if os.path.exists(d) and not os.listdir(d):
                print(f"  [ELIMINA] {d}")
                os.rmdir(d)
        except Exception as e:
            print(f"  [AVVISO] Impossibile rimuovere {d}: {e}")

    print("\nRiorganizzazione completata!")

if __name__ == "__main__":
    apply_run = "--apply" in sys.argv
    normalize_layout(apply_run)

#!/usr/bin/env python3
import os
import sys
import sqlite3
import re
import argparse
import unicodedata

DB_PATH = "/Users/olindo/prj/k8s-lab/import_music/import_classical/classical_musiclibrary.db"
LIB_DIR = "/Volumes/classical/library"

def sanitize_filename(filename):
    """Rimuove o sostituisce i caratteri non validi per i filesystem standard."""
    for char in ['/', '\\', '?', '*', '<', '>', '|', '\"', ':']:
        filename = filename.replace(char, '_')
    return " ".join(filename.split()).strip()

def main():
    parser = argparse.ArgumentParser(description="Standardizza i nomi dei file delle singole tracce nel DB Beets classica e sul filesystem (symlinks)")
    parser.add_argument("--run", action="store_true", help="Applica fisicamente i rinominamenti")
    args = parser.parse_args()

    if not os.path.exists(DB_PATH):
        print(f"[ERROR] Database Beets classica non trovato: {DB_PATH}")
        sys.exit(1)

    print("=" * 80)
    print("🎼 STRUMENTO DI STANDARDIZZAZIONE TRACCE MUSICA CLASSICA 🎼")
    print("=" * 80)
    print(f"Database: {DB_PATH}")
    print(f"Library:  {LIB_DIR}")
    print(f"Modalità: {'REAL RUN (Rinominamento attivo)' if args.run else 'DRY-RUN (Simulazione)'}")
    print("-" * 80)

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT id, path, disc, disctotal, track, title FROM items")
    rows = cur.fetchall()

    changes = []
    skipped_not_exists = 0

    for rid, path_bytes, disc, disctotal, track, title in rows:
        try:
            current_path = path_bytes.decode('utf-8', 'replace')
        except Exception:
            continue

        # Percorso assoluto completo
        abs_current_path = os.path.join(LIB_DIR, current_path)

        # Saltiamo se il file o il link non esiste
        if not os.path.exists(abs_current_path) and not os.path.islink(abs_current_path):
            skipped_not_exists += 1
            continue

        dir_name = os.path.dirname(current_path)
        base_name = os.path.basename(current_path)
        _, ext = os.path.splitext(base_name)

        # Pulizia del titolo
        clean_title = sanitize_filename(title or "Unknown Movement")

        # Determinazione del prefisso in base alla logica unificata
        disc_num = disc or 1
        disc_total = disctotal or 1
        track_num = track or 1

        is_multi = (disc_num > 1 or disc_total > 1)

        # Se non è multi-disco per tag, controlliamo se il percorso fisico ha indizi di dischi multipli
        if not is_multi:
            try:
                path_str = current_path.lower()
                if re.search(r'\b(cd|disc|disco|vol|volume)[-_\s]*\d+', path_str):
                    is_multi = True
            except Exception:
                pass

        if is_multi:
            prefix = f"{disc_num:02d}-{track_num:02d}"
        else:
            prefix = f"{track_num:02d}"

        # Target Filename Standardizzato
        target_filename = f"{prefix} - {clean_title}{ext}"
        target_path = os.path.join(dir_name, target_filename)

        # Normalizzazione in forma NFD (decomposta - standard per macOS)
        current_normalized = unicodedata.normalize('NFD', current_path)
        target_normalized = unicodedata.normalize('NFD', target_path)

        if os.path.normpath(current_normalized) != os.path.normpath(target_normalized):
            changes.append({
                'id': rid,
                'current_rel': current_path,
                'target_rel': target_path,
                'current_abs': abs_current_path,
                'target_abs': os.path.join(LIB_DIR, target_path),
                'old_name': base_name,
                'new_name': target_filename
            })

    print(f"\n📊 STATISTICHE DEI CAMBIAMENTI:")
    print(f"  - Tracce totali a database       : {len(rows)}")
    print(f"  - Tracce non trovate/saltate     : {skipped_not_exists}")
    print(f"  - Tracce da standardizzare       : {len(changes)}")
    print("-" * 80)

    if not changes:
        print("[INFO] Tutte le tracce classica sono già perfettamente conformi al pattern standard!")
        return

    # Anteprima delle modifiche
    print("\n🔍 ANTEPRIMA DELLE MODIFICHE (Primi 30 esempi):")
    for c in sorted(changes, key=lambda x: x['current_rel'])[:30]:
        print(f"  🎼 Cartella: {os.path.dirname(c['current_rel'])}")
        print(f"     ❌ Vecchio: \"{c['old_name']}\"")
        print(f"     ✅ Nuovo:   \"{c['new_name']}\"")
        print("-" * 40)

    if len(changes) > 30:
        print(f"    ... e altre {len(changes) - 30} tracce.")

    if args.run:
        print("\n🔥 AVVIO RINOMINAMENTO FISICO (SYMLINKS) ED AGGIORNAMENTO DATABASE...")
        success_count = 0

        # Backup preventivo del database SQLite prima dell'esecuzione
        backup_db_path = DB_PATH + ".bak"
        try:
            import shutil
            shutil.copy2(DB_PATH, backup_db_path)
            print(f"[BACKUP] Copia di sicurezza creata con successo in: {backup_db_path}")
        except Exception as e:
            print(f"[FATAL] Impossibile creare il backup del DB: {e}. Esecuzione annullata.")
            sys.exit(1)

        for c in changes:
            try:
                # Normalizziamo esplicitamente a NFD i percorsi prima della creazione fisica su macOS
                target_abs_nfd = unicodedata.normalize('NFD', c['target_abs'])
                target_rel_nfd = unicodedata.normalize('NFD', c['target_rel'])

                # Assicuriamoci che la cartella di destinazione esista
                os.makedirs(os.path.dirname(target_abs_nfd), exist_ok=True)

                # Gestione dei Symlink
                if os.path.islink(c['current_abs']):
                    staging_target = os.readlink(c['current_abs'])
                    # Crea il nuovo symlink e cancella il vecchio
                    if os.path.exists(target_abs_nfd) or os.path.islink(target_abs_nfd):
                        os.unlink(target_abs_nfd)
                    os.symlink(staging_target, target_abs_nfd)
                    os.unlink(c['current_abs'])
                else:
                    # In caso di file regolari
                    if os.path.exists(target_abs_nfd):
                        os.remove(target_abs_nfd)
                    os.rename(c['current_abs'], target_abs_nfd)

                # Aggiornamento database con percorso normalizzato
                cur.execute(
                    "UPDATE items SET path = ? WHERE id = ?",
                    (target_rel_nfd.encode('utf-8'), c['id'])
                )
                success_count += 1
            except Exception as e:
                print(f"  [ERROR] Impossibile rinominare {c['current_abs']} -> {c['target_abs']}: {e}")

        conn.commit()
        print("\n" + "=" * 80)
        print("📈 STATISTICHE FINALI:")
        print(f"  - Tracce standardizzate con successo: {success_count}/{len(changes)}")
        print("=" * 80)
    else:
        print("\n[INFO] Modalità DRY-RUN completata. Nessun file o DB è stato modificato.")

    conn.close()

if __name__ == "__main__":
    main()

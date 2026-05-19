#!/usr/bin/env python3
import os
import sys
import sqlite3
import argparse

DB_PATH = "/Users/olindo/prj/k8s-lab/import_music/musiclibrary.db"
LIB_DIR = "/Volumes/arrdata/media/music_backup"

def sanitize_filename(filename):
    """Rimuove o sostituisce i caratteri non validi per i filesystem standard."""
    # Sostituiamo i separatori di percorso ed i caratteri proibiti
    for char in ['/', '\\', '?', '*', '<', '>', '|', '\"', ':']:
        filename = filename.replace(char, '_')
    # Rimuoviamo spazi multipli e strip
    return " ".join(filename.split()).strip()

def main():
    parser = argparse.ArgumentParser(description="Standardizza i nomi dei file delle singole tracce nel DB Beets e sul filesystem")
    parser.add_argument("--run", action="store_true", help="Applica fisicamente i rinominamenti")
    args = parser.parse_args()

    if not os.path.exists(DB_PATH):
        print(f"[ERROR] Database Beets non trovato: {DB_PATH}")
        sys.exit(1)

    print("=" * 80)
    print("🎵 STRUMENTO DI STANDARDIZZAZIONE NOMI DELLE TRACCE 🎵")
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

    for rid, path_bytes, disc, disctotal, track, title in rows:
        try:
            current_path = path_bytes.decode('utf-8', 'replace')
        except Exception:
            continue

        # Otteniamo il percorso assoluto completo sul filesystem
        abs_current_path = os.path.join(LIB_DIR, current_path)

        # Saltiamo se il file fisico non esiste (es. file mancanti orfani)
        if not os.path.exists(abs_current_path):
            continue

        dir_name = os.path.dirname(current_path)
        base_name = os.path.basename(current_path)
        _, ext = os.path.splitext(base_name)

        # Pulizia del titolo
        clean_title = sanitize_filename(title or "Unknown Title")

        # Determinazione del prefisso in base ai dischi totali o al numero del disco
        disc_num = disc or 1
        disc_total = disctotal or 1
        track_num = track or 1

        if disc_total > 1 or disc_num > 1:
            prefix = f"{disc_num:02}-{track_num:02}"
        else:
            prefix = f"{track_num:02}"

        # Target Filename Standardizzato: [Prefisso] - [Titolo].[estensione]
        target_filename = f"{prefix} - {clean_title}{ext}"
        target_path = os.path.join(dir_name, target_filename)

        # Confrontiamo i percorsi normalizzati per vedere se è necessaria una modifica
        if os.path.normpath(current_path) != os.path.normpath(target_path):
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
    print(f"  - Tracce analizzate sul filesystem: {len(rows)}")
    print(f"  - Tracce da standardizzare: {len(changes)}")
    print("-" * 80)

    if not changes:
        print("[INFO] Tutte le tracce sul filesystem sono già perfettamente conformi al pattern standard!")
        return

    # Stampa i primi 30 esempi per verifica dell'utente
    print("\n🔍 ANTEPRIMA DELLE MODIFICHE (Primi 30 esempi):")
    for c in sorted(changes, key=lambda x: x['current_rel'])[:30]:
        print(f"  💿 Cartella: {os.path.dirname(c['current_rel'])}")
        print(f"     ❌ Vecchio: \"{c['old_name']}\"")
        print(f"     ✅ Nuovo:   \"{c['new_name']}\"")
        print("-" * 40)

    if len(changes) > 30:
        print(f"    ... e altre {len(changes) - 30} tracce.")

    if args.run:
        print("\n🔥 AVVIO RINOMINAMENTO FISICO ED AGGIORNAMENTO DATABASE...")
        success_count = 0

        for c in changes:
            # 1. Rinomina fisica sul filesystem
            if os.path.exists(c['current_abs']):
                try:
                    # Assicuriamoci che la cartella di destinazione esista (dovrebbe già esserci)
                    os.makedirs(os.path.dirname(c['target_abs']), exist_ok=True)
                    os.rename(c['current_abs'], c['target_abs'])

                    # 2. Aggiornamento nel database Beets (come BLOB/bytes)
                    cur.execute(
                        "UPDATE items SET path = ? WHERE id = ?",
                        (c['target_rel'].encode('utf-8'), c['id'])
                    )
                    success_count += 1
                except Exception as e:
                    print(f"  [ERROR] Impossibile rinominare {c['current_abs']} -> {c['target_abs']}: {e}")

        conn.commit()
        print("\n" + "=" * 80)
        print("📈 STATISTICHE FINALI:")
        print(f"  - Tracce rinominate con successo: {success_count}/{len(changes)}")
        print("=" * 80)
    else:
        print("\n[INFO] Modalità DRY-RUN completata. Nessun file è stato modificato sul disco.")

if __name__ == "__main__":
    main()

#!/usr/bin/env python3
import os
import sys
import argparse

LIB_DIR = "/Volumes/arrdata/media/music_backup"
AUDIO_EXTS = {'.mp3', '.flac', '.m4a', '.ogg', '.wav', '.wma', '.ape'}

def has_audio_files_recursive(path):
    """Controlla ricorsivamente se una directory o le sue sottodirectory contengono file audio."""
    for root, dirs, files in os.walk(path):
        for f in files:
            _, ext = os.path.splitext(f.lower())
            if ext in AUDIO_EXTS:
                return True
    return False

def main():
    parser = argparse.ArgumentParser(description="Trova e rimuove ricorsivamente le cartelle vuote o orfane (senza file audio)")
    parser.add_argument("--run", action="store_true", help="Esegue la rimozione fisica delle cartelle vuote")
    args = parser.parse_args()

    print("=" * 80)
    print("🧹 STRUMENTO DI RIMOZIONE CARTELLE VUOTE E ORFANE 🧹")
    print("=" * 80)
    print(f"Target Directory: {LIB_DIR}")
    print(f"Modalità: {'REAL RUN (Eliminazione attiva)' if args.run else 'DRY-RUN (Simulazione)'}")
    print("-" * 80)

    if not os.path.exists(LIB_DIR):
        print(f"[ERROR] Directory non trovata: {LIB_DIR}")
        sys.exit(1)

    deleted_dirs_count = 0
    deleted_junk_files_count = 0

    # Eseguiamo un walk bottom-up (dal basso verso l'alto)
    # Questo ci permette di eliminare prima le sottocartelle vuote (es. album)
    # e poi, se la cartella padre (es. artista) rimane vuota, eliminare anche quella.

    for root, dirs, files in os.walk(LIB_DIR, topdown=False):
        # Escludiamo le cartelle di sistema/triage
        if '/_' in root or root.endswith('/_') or '/_Triage' in root:
            continue

        # Controlliamo se in questa cartella (o sottocartelle) c'è almeno un file audio
        if not has_audio_files_recursive(root):
            # Se NON ci sono file audio, la cartella è considerata orfana/inutile.
            # Raccogliamo tutti i file non-audio presenti (es. cover.jpg, .DS_Store)
            junk_files = []
            for f in os.listdir(root):
                full_path = os.path.join(root, f)
                if os.path.isfile(full_path):
                    junk_files.append(full_path)

            # Se ci sono sottodirectory rimaste che contengono audio, non possiamo eliminarla (non dovrebbe accadere per via del check ricorsivo)
            subdirs = [os.path.join(root, d) for d in os.listdir(root) if os.path.isdir(os.path.join(root, d))]
            if subdirs:
                continue

            print(f"  📂 Cartella da rimuovere: {root}")
            if junk_files:
                print(f"     -> Contiene file junk/metadati: {[os.path.basename(jf) for jf in junk_files]}")

            if args.run:
                # 1. Eliminiamo prima i file di metadati orfani (cover.jpg, .DS_Store, ecc.)
                for jf in junk_files:
                    try:
                        os.remove(jf)
                        deleted_junk_files_count += 1
                    except Exception as e:
                        print(f"     [ERROR] Impossibile rimuovere file {jf}: {e}")

                # 2. Eliminiamo la directory ormai completamente vuota
                try:
                    os.rmdir(root)
                    deleted_dirs_count += 1
                except Exception as e:
                    print(f"     [ERROR] Impossibile rimuovere cartella {root}: {e}")

    print("\n" + "=" * 80)
    print("📈 STATISTICHE FINALI:")
    if args.run:
        print(f"  - Cartelle rimosse fisicamente: {deleted_dirs_count}")
        print(f"  - File junk (cover/log) eliminati: {deleted_junk_files_count}")
    else:
        print("  - Esegui lo script con il flag --run per applicare le modifiche.")
    print("=" * 80)

if __name__ == "__main__":
    main()

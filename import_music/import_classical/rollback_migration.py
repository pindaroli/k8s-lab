#!/usr/bin/env python3
import os
import re
import sys
from pathlib import Path
from collections import defaultdict

# Carichiamo mutagen per ispezionare i tag dei file in collisione
try:
    from mutagen.flac import FLAC
    from mutagen.easyid3 import EasyID3
    from mutagen.mp3 import MP3
    MUTAGEN_AVAILABLE = True
except ImportError:
    MUTAGEN_AVAILABLE = False

MAC_ARRDATA_PREFIX = Path("/Volumes/arrdata")
MAC_CLASSICAL_PREFIX = Path("/Volumes/classical")

NAS_ARRDATA_PREFIX = "/mnt/oliraid/arrdata/"
NAS_CLASSICAL_PREFIX = "/mnt/oliraid/arrdata/classical/"

def map_nas_to_mac(nas_path_str: str) -> Path:
    nas_path_str = nas_path_str.strip('"').rstrip('/')
    if nas_path_str.startswith(NAS_CLASSICAL_PREFIX):
        rel = nas_path_str[len(NAS_CLASSICAL_PREFIX):]
        return MAC_CLASSICAL_PREFIX / rel
    elif nas_path_str.startswith(NAS_ARRDATA_PREFIX):
        rel = nas_path_str[len(NAS_ARRDATA_PREFIX):]
        return MAC_ARRDATA_PREFIX / rel
    elif nas_path_str.startswith("/mnt/oliraid/arrdata/"):
        rel = nas_path_str[len("/mnt/oliraid/arrdata/"):]
        return MAC_ARRDATA_PREFIX / rel
    return Path(nas_path_str)

def map_mac_to_nas(mac_path: Path) -> str:
    mac_str = str(mac_path)
    if mac_str.startswith(str(MAC_CLASSICAL_PREFIX)):
        rel = mac_str[len(str(MAC_CLASSICAL_PREFIX)):]
        return NAS_CLASSICAL_PREFIX + rel.lstrip('/')
    elif mac_str.startswith(str(MAC_ARRDATA_PREFIX)):
        rel = mac_str[len(str(MAC_ARRDATA_PREFIX)):]
        return NAS_ARRDATA_PREFIX + rel.lstrip('/')
    return mac_str

def parse_move_script(script_path: Path):
    rules = []
    rsync_pattern = re.compile(r'rsync -a --remove-source-files "([^"]+)" "([^"]+)"')

    if not script_path.exists():
        print(f"[FATAL] Script move_classical.sh non trovato in {script_path}")
        sys.exit(1)

    with open(script_path, 'r', encoding='utf-8', errors='ignore') as f:
        for idx, line in enumerate(f, 1):
            match = rsync_pattern.search(line)
            if match:
                src_nas = match.group(1)
                dest_nas = match.group(2)
                rules.append({
                    'line_num': idx,
                    'src_nas': src_nas,
                    'dest_nas': dest_nas,
                    'src_mac': map_nas_to_mac(src_nas),
                    'dest_mac': map_nas_to_mac(dest_nas),
                })
    return rules

def get_audio_metadata(file_path: Path):
    """Estrae artist e album da un file audio via mutagen."""
    if not MUTAGEN_AVAILABLE:
        return None, None
    try:
        if file_path.suffix.lower() == '.flac':
            audio = FLAC(file_path)
            artist = audio.get('artist', [''])[0]
            album = audio.get('album', [''])[0]
            return artist, album
        elif file_path.suffix.lower() == '.mp3':
            try:
                audio = EasyID3(file_path)
                artist = audio.get('artist', [''])[0]
                album = audio.get('album', [''])[0]
                return artist, album
            except Exception:
                audio = MP3(file_path)
                # Fallback tag grezzi
                artist = str(audio.get('TPE1', ''))
                album = str(audio.get('TALB', ''))
                return artist, album
    except Exception:
        pass
    return None, None

def clean_name(name: str) -> str:
    """Semplifica una stringa per il confronto morbido."""
    if not name:
        return ""
    return re.sub(r'[^a-zA-Z0-9]', '', name).lower()

def main():
    script_dir = Path(__file__).parent
    script_path = script_dir / "move_classical.sh"
    rules = parse_move_script(script_path)

    # Costruiamo la mappatura inversa dest -> src
    dest_to_rules = defaultdict(list)
    for rule in rules:
        dest_to_rules[rule['dest_mac']].append(rule)

    staging_dir = MAC_CLASSICAL_PREFIX / "staging"
    if not staging_dir.exists():
        print(f"[FATAL] La directory di staging non esiste localmente: {staging_dir}")
        sys.exit(1)

    restore_commands = []
    skipped_files = []

    print("=== COSTRUZIONE PIANO DI RIPRISTINO CHIRURGICO ===")
    print("Scansione dei file in staging in corso...")

    # Otteniamo tutti i file presenti in staging (scansione ricorsiva)
    staging_files = [f for f in staging_dir.glob('**/*') if f.is_file()]
    print(f"Trovati {len(staging_files)} file fisici in staging.\n")

    for f_path in staging_files:
        # Determiniamo a quale directory di staging di primo livello appartiene questo file
        # Es. /Volumes/classical/staging/cd   1/01.flac -> staging/cd   1
        relative_to_staging = f_path.relative_to(staging_dir)
        top_dest_name = relative_to_staging.parts[0]
        top_dest_dir = staging_dir / top_dest_name

        candidates = dest_to_rules.get(top_dest_dir, [])

        if not candidates:
            print(f"[WARNING] File orfano (non presente nello script): {relative_to_staging}")
            skipped_files.append(f_path)
            continue

        if len(candidates) == 1:
            # Caso semplice: nessuna collisione di destinazione
            rule = candidates[0]
            # Ricostruiamo il percorso relativo all'interno di quella destinazione
            rel_file = f_path.relative_to(top_dest_dir)
            target_mac_dir = rule['src_mac']
            target_mac_file = target_mac_dir / rel_file

            restore_commands.append((f_path, target_mac_file))
        else:
            # Caso complesso: COLLISIONE! (es. cd 1, Unknown Album, Don Giovanni)
            # Dobbiamo ispezionare i metadati del file per scegliere il candidato corretto
            artist, album = get_audio_metadata(f_path)
            matched_rule = None

            if artist or album:
                clean_artist = clean_name(artist)
                clean_album = clean_name(album)

                # Cerchiamo tra i candidati quello che contiene l'artista o l'album nel percorso sorgente
                for cand in candidates:
                    src_str_clean = clean_name(str(cand['src_mac']))
                    # Se il percorso sorgente contiene l'artista o l'album dei tag
                    if (clean_artist and clean_artist in src_str_clean) or (clean_album and clean_album in src_str_clean):
                        matched_rule = cand
                        break

            # Se la ricerca con i metadati fallisce, proviamo a vedere se il file originario
            # esiste ancora parzialmente nella sorgente (per capire quale candidato è)
            if not matched_rule:
                for cand in candidates:
                    rel_file = f_path.relative_to(top_dest_dir)
                    potential_src = cand['src_mac'] / rel_file
                    if potential_src.exists():
                        # Se il file esiste ancora all'origine, forse rsync lo ha saltato o interrotto.
                        # Ma se non esiste all'origine e in un'altra si, per esclusione lo abbiniamo
                        pass

            # Se riusciamo ad abbinarlo con certezza
            if matched_rule:
                rel_file = f_path.relative_to(top_dest_dir)
                target_mac_file = matched_rule['src_mac'] / rel_file
                restore_commands.append((f_path, target_mac_file))
            else:
                # Se falliscono tutti i tentativi, abbinamento euristico al primo candidato per non perdere il file
                # ma stampiamo un warning
                matched_rule = candidates[0]
                rel_file = f_path.relative_to(top_dest_dir)
                target_mac_file = matched_rule['src_mac'] / rel_file
                restore_commands.append((f_path, target_mac_file))
                print(f"[COLLISION WARNING] Impossibile associare con precisione: {relative_to_staging}. Abbinato a: {matched_rule['src_mac'].name}")

    # Ora generiamo lo script bash di ripristino per il NAS
    output_sh = script_dir / "restore_dryrun.sh"

    with open(output_sh, 'w', encoding='utf-8') as out_f:
        out_f.write("#!/bin/bash\n")
        out_f.write("# Script di Ripristino Chirurgico Post-Interruzione Rsync\n")
        out_f.write("# Generato in modalità provvisoria (Dry-Run)\n\n")

        # Scriviamo i comandi raggruppati per mkdir e mv
        dirs_to_create = set()
        mv_commands = []

        for src_mac_file, dest_mac_file in restore_commands:
            src_nas = map_mac_to_nas(src_mac_file)
            dest_nas = map_mac_to_nas(dest_mac_file)

            dest_nas_dir = str(Path(dest_nas).parent)
            dirs_to_create.add(dest_nas_dir)

            mv_commands.append(f'mv "{src_nas}" "{dest_nas}"')

        for d in sorted(dirs_to_create):
            out_f.write(f'mkdir -p "{d}"\n')

        out_f.write("\n# Spostamento dei file\n")
        for cmd in mv_commands:
            out_f.write(f"{cmd}\n")

    print(f"\n[SUCCESSO] Analisi completata!")
    print(f"  - File pronti per il ripristino: {len(restore_commands)}")
    print(f"  - File saltati/orfani: {len(skipped_files)}")
    print(f"  - Script di ripristino generato con successo: {output_sh.name}")
    print("\nPuoi ispezionare il file 'restore_dryrun.sh' per validare i comandi prima dell'esecuzione fisica sul NAS.")

if __name__ == '__main__':
    main()

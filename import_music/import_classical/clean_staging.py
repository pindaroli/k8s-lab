#!/usr/bin/env python3
import os
import re
import sys
from pathlib import Path
from collections import defaultdict

# Carichiamo mutagen per i tag
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
                artist = str(audio.get('TPE1', ''))
                album = str(audio.get('TALB', ''))
                return artist, album
    except Exception:
        pass
    return None, None

def clean_name(name: str) -> str:
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
        print(f"[FATAL] La directory di staging non esiste: {staging_dir}")
        sys.exit(1)

    staging_files = [f for f in staging_dir.glob('**/*') if f.is_file()]

    to_delete = []
    to_keep = []

    for f_path in staging_files:
        relative_to_staging = f_path.relative_to(staging_dir)
        top_dest_name = relative_to_staging.parts[0]
        top_dest_dir = staging_dir / top_dest_name

        candidates = dest_to_rules.get(top_dest_dir, [])
        if not candidates:
            continue

        target_mac_file = None
        if len(candidates) == 1:
            target_mac_file = candidates[0]['src_mac'] / f_path.relative_to(top_dest_dir)
        else:
            artist, album = get_audio_metadata(f_path)
            if artist or album:
                clean_artist = clean_name(artist)
                clean_album = clean_name(album)
                for cand in candidates:
                    src_str_clean = clean_name(str(cand['src_mac']))
                    if (clean_artist and clean_artist in src_str_clean) or (clean_album and clean_album in src_str_clean):
                        target_mac_file = cand['src_mac'] / f_path.relative_to(top_dest_dir)
                        break
            if not target_mac_file:
                target_mac_file = candidates[0]['src_mac'] / f_path.relative_to(top_dest_dir)

        if target_mac_file and target_mac_file.exists():
            to_delete.append((f_path, target_mac_file))
        else:
            to_keep.append((f_path, target_mac_file))

    print("=== RISULTATO DETTAGLIATO DRY-RUN DI PULIZIA ===")
    print(f"File totali analizzati in staging: {len(staging_files)}")
    print(f"File sani da mantenere (mancanti all'origine): {len(to_keep)}")
    print(f"File corrotti/duplicati da CANCELLARE dallo staging: {len(to_delete)}")
    print("================================================")

    if to_delete:
        print("\nEsempi di file corrotti/duplicati da CANCELLARE (primi 15):")
        for s, d in to_delete[:15]:
            print(f" - [DRY-RUN CANCELLA] staging/{s.relative_to(staging_dir)} (Origine intatta: {d.name})")
        if len(to_delete) > 15:
            print(f"   ... e altri {len(to_delete) - 15} file.")

    if to_keep:
        print("\nEsempi di file sani da RIPRISTINARE all'origine (primi 15):")
        for s, d in to_keep[:15]:
            print(f" - [DRY-RUN RIPRISTINA] staging/{s.relative_to(staging_dir)} -> {d.parent.name}/{d.name}")
        if len(to_keep) > 15:
            print(f"   ... e altri {len(to_keep) - 15} file.")

if __name__ == '__main__':
    main()

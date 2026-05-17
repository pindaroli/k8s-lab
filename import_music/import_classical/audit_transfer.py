#!/usr/bin/env python3
import os
import re
from pathlib import Path
from collections import defaultdict

MAC_ARRDATA_PREFIX = Path("/Volumes/arrdata")
MAC_CLASSICAL_PREFIX = Path("/Volumes/classical")

NAS_ARRDATA_PREFIX = "/mnt/oliraid/arrdata/"
NAS_CLASSICAL_PREFIX = "/mnt/oliraid/arrdata/classical/"

def map_nas_to_mac(nas_path_str: str) -> Path:
    # Rimuoviamo eventuali slash finali e virgolette
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
    # Cerchiamo rsync -a --remove-source-files "SRC/" "DEST/"
    rsync_pattern = re.compile(r'rsync -a --remove-source-files "([^"]+)" "([^"]+)"')

    if not script_path.exists():
        print(f"[FATAL] Script non trovato: {script_path}")
        return []

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

def main():
    script_path = Path(__file__).parent / "move_classical.sh"
    rules = parse_move_script(script_path)

    print(f"=== AUDIT TRASFERIMENTO CLASSICA ===")
    print(f"Trovate {len(rules)} istruzioni di spostamento nel file move_classical.sh\n")

    # 1. Rileviamo le collisioni teoriche (più sorgenti verso la stessa destinazione)
    dest_to_srcs = defaultdict(list)
    for rule in rules:
        dest_to_srcs[rule['dest_mac']].append(rule)

    collisions = {dest: r_list for dest, r_list in dest_to_srcs.items() if len(r_list) > 1}
    print(f"[INFO] Trovate {len(collisions)} cartelle di destinazione con potenziale collisione di nomi:\n")

    for dest, r_list in sorted(collisions.items(), key=lambda x: len(x[1]), reverse=True):
        print(f"  Destination: {dest.relative_to(MAC_CLASSICAL_PREFIX)}")
        print(f"  Colliding sources ({len(r_list)}):")
        for r in r_list:
            print(f"    - Riga {r['line_num']}: {r['src_mac'].relative_to(MAC_ARRDATA_PREFIX)}")
        print()

    print("=" * 60)
    print("=== STATO EFFETTIVO DEI FILE (CAMPIONE E STATISTICHE) ===")

    total_processed = 0
    total_untouched = 0
    total_partial = 0
    total_completed = 0

    completed_runs = []
    partial_runs = []
    untouched_runs = []

    for rule in rules:
        src = rule['src_mac']
        dest = rule['dest_mac']

        src_exists = src.exists()
        dest_exists = dest.exists()

        src_files = list(src.glob('**/*')) if src_exists else []
        src_file_count = sum(1 for f in src_files if f.is_file())

        dest_files = list(dest.glob('**/*')) if dest_exists else []
        dest_file_count = sum(1 for f in dest_files if f.is_file())

        if src_file_count > 0 and dest_file_count == 0:
            total_untouched += 1
            untouched_runs.append(rule)
        elif src_file_count > 0 and dest_file_count > 0:
            total_partial += 1
            partial_runs.append(rule)
        elif src_file_count == 0 and dest_file_count > 0:
            total_completed += 1
            completed_runs.append(rule)
        else:
            # Entrambe vuote o non esistenti (già ripulite del tutto o mai popolate)
            total_completed += 1
            completed_runs.append(rule)

    print(f"Statistiche di esecuzione:")
    print(f"  - Completati (sorgente vuota, dest popolata): {total_completed}")
    print(f"  - Parziali (file sia in sorgente che in dest) : {total_partial}")
    print(f"  - Intatti (file solo in sorgente)              : {total_untouched}")
    print()

    if partial_runs:
        print("[WARNING] Trovati trasferimenti interrotti a metà (parziali):")
        for r in partial_runs[:5]:
            print(f"  - Riga {r['line_num']}: {r['src_mac'].name}")
        if len(partial_runs) > 5:
            print(f"    ... e altri {len(partial_runs) - 5}...")
        print()

    # Consigliamo un piano di azione
    print("=" * 60)
    print("=== PIANO DI RIPRISTINO E BONIFICA CONSIGLIATO ===")
    print("1. Per le cartelle di collisione (es. cd 1, Unknown Album):")
    print("   - Dobbiamo identificare quali file sono finiti in staging e a quale sorgente appartengono.")
    print("   - Poiché molti album non-classica (falsi positivi) sono in questo set, lo ripristineremo con cura.")
    print("2. Sposteremo indietro i falsi positivi (es. Branduardi, Guccini, Cesaria Evora) ricreando l'esatto percorso originale.")
    print("3. Correggeremo l'euristica per non far collidere mai più i nomi in staging (es. staging/Artist - Album/ invece di staging/Subdir).")

if __name__ == '__main__':
    main()

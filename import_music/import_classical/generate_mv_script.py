#!/usr/bin/env python3
import sys
from pathlib import Path

# Aggiungiamo la dir dello script per importare segregate_classical
sys.path.append(str(Path(__file__).parent))
from segregate_classical import is_classical, extract_paths_from_log

MAC_ARRDATA_PREFIX = "/Volumes/arrdata/"
MAC_CLASSICAL_PREFIX = "/Volumes/classical/"

NAS_ARRDATA_PREFIX = "/mnt/oliraid/arrdata/"
NAS_CLASSICAL_PREFIX = "/mnt/oliraid/arrdata/classical/"

def map_path_to_nas(path_obj: Path) -> str:
    path_str = str(path_obj)
    if path_str.startswith(MAC_ARRDATA_PREFIX):
        return path_str.replace(MAC_ARRDATA_PREFIX, NAS_ARRDATA_PREFIX)
    elif path_str.startswith(MAC_CLASSICAL_PREFIX):
        return path_str.replace(MAC_CLASSICAL_PREFIX, NAS_CLASSICAL_PREFIX)
    # Se per qualche motivo ha già il percorso di TrueNAS
    elif path_str.startswith("/mnt/oliraid/"):
        return path_str
    # Fallback sicuro
    return path_str

def main():
    paths = extract_paths_from_log()
    output_file = Path(__file__).parent / "move_classical.sh"

    print(f"[INFO] Scrittura comandi in {output_file.name}...")

    commands = []
    # Comando iniziale per assicurarsi che la directory di staging esista sul NAS
    commands.append(f'mkdir -p "{NAS_CLASSICAL_PREFIX}staging"')

    classical_count = 0
    for folder in paths:
        if not folder.exists():
            continue

        if is_classical(folder):
            classical_count += 1
            nas_src = map_path_to_nas(folder)
            folder_name = folder.name
            nas_dest = f"{NAS_CLASSICAL_PREFIX}staging/{folder_name}"

            # Genera il comando nativo rsync + rimozione cartella vuota
            commands.append(f'mkdir -p "{nas_dest}" && rsync -a --remove-source-files "{nas_src}/" "{nas_dest}/" && find "{nas_src}" -type d -empty -delete')

    with open(output_file, 'w', encoding='utf-8') as f:
        f.write("#!/bin/bash\n")
        f.write("# Script autogenerato per spostamento rapido sul NAS\n")
        f.write("set -e\n\n")
        f.write("\n".join(commands))
        f.write("\n\necho \"SPOSTAMENTO COMPLETATO CON SUCCESSO!\"\n")

    print(f"[SUCCESS] Generati {classical_count} comandi di spostamento in {output_file}")
    print("Pronto per essere eseguito direttamente sul NAS.")

if __name__ == "__main__":
    main()

#!/usr/bin/env python3
import os
import sys

TARGETS_FILE = "/Users/olindo/prj/k8s-lab/import_music/paths_to_recover.txt"
SANIZED_FILE = "/Users/olindo/prj/k8s-lab/import_music/paths_to_recover_sanitized.txt"

CLASSICAL_KEYWORDS = [
    "mozart", "bach", "beethoven", "vivaldi", "chopin", "tchaikovsky", "debussy",
    "paisiello", "previn", "philharmonic", "symphony", "orchestra", "concerto",
    "sonata", "opera", "schubert", "haydn", "brahms", "wagner", "verdi", "puccini",
    "mahler", "stravinsky", "ravel", "shostakovich", "prokofiev"
]

def sanitize():
    print("=" * 70)
    print(" 🧹 SANIFICAZIONE PERCORSI SOFT RECOVERY")
    print("=" * 70)

    if not os.path.exists(TARGETS_FILE):
        print(f"[ERROR] File dei percorsi non trovato a {TARGETS_FILE}")
        return

    with open(TARGETS_FILE, "r") as f:
        paths = [line.strip() for line in f if line.strip()]

    print(f"[INFO] Percorsi letti da file: {len(paths)}")

    existing_paths = []
    missing_paths = []
    classical_candidates = []

    POP_ROCK_EXCEPTIONS = ["symphonic music of yes", "no smoking orchestra"]

    for path in paths:
        # Verifica se la cartella esiste fisicamente
        if os.path.exists(path):
            # Controlla se è un candidato classico
            path_lower = path.lower()
            is_classical = any(kw in path_lower for kw in CLASSICAL_KEYWORDS)
            is_exception = any(exc in path_lower for exc in POP_ROCK_EXCEPTIONS)

            if is_classical and not is_exception:
                classical_candidates.append(path)
                # Riduciamo il rumore escludendola se è al 100% classica
                existing_paths.append(path)
            else:
                existing_paths.append(path)
        else:
            missing_paths.append(path)

    print(f"[RESULT] Cartelle fisicamente esistenti: {len(existing_paths)}")
    print(f"[RESULT] Cartelle orfane/inesistenti   : {len(missing_paths)}")
    print(f"[RESULT] Candidati musica classica     : {len(classical_candidates)}")
    print("-" * 70)

    if missing_paths:
        print("\n[INFO] Alcune cartelle inesistenti rilevate (Prime 10):")
        for p in missing_paths[:10]:
            print(f"  - {p}")
        if len(missing_paths) > 10:
            print(f"  ... e altre {len(missing_paths) - 10} cartelle.")

    if classical_candidates:
        print("\n[INFO] Candidati musica classica rilevati (Prime 10):")
        for p in classical_candidates[:10]:
            print(f"  - {p}")
        if len(classical_candidates) > 10:
            print(f"  ... e altri {len(classical_candidates) - 10} candidati.")

    # Scrittura del file sanificato
    apply = "--apply" in sys.argv
    if apply:
        # Scriviamo i percorsi filtrati (escludendo le inesistenti)
        # Decidiamo se rimuovere anche le classiche per lasciarle alla pipeline classica
        final_paths = [p for p in existing_paths if p not in classical_candidates]

        with open(TARGETS_FILE, "w") as out:
            for p in sorted(final_paths):
                out.write(f"{p}\n")

        # Salviamo le classiche rilevate per poterle passare alla pipeline classica
        classical_file = "/Users/olindo/prj/k8s-lab/import_music/classical_paths_extracted.txt"
        with open(classical_file, "w") as out:
            for p in sorted(classical_candidates):
                out.write(f"{p}\n")

        print(f"\n[SUCCESS] Aggiornato {TARGETS_FILE} con {len(final_paths)} percorsi validi e non classici.")
        print(f"[SUCCESS] Salvati {len(classical_candidates)} candidati classici in {classical_file}.")
    else:
        print("\n[DRY RUN] Nessuna modifica applicata. Lancia il comando con '--apply' per sanificare il file.")

if __name__ == "__main__":
    sanitize()

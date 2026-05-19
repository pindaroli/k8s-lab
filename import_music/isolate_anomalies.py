import os
import re

ANOMALIES_LOG = "import_anomalies.log"
OUTPUT_FILE = "paths_to_recover.txt"

def main():
    if not os.path.exists(ANOMALIES_LOG):
        print(f"[!] File {ANOMALIES_LOG} non trovato.")
        return

    # Mappa per tracciare l'ultima riga di anomalia per ogni percorso unico
    latest_anomaly = {}

    with open(ANOMALIES_LOG, "r") as f:
        for line in f:
            if line.startswith("[") and "] LOG:" in line:
                parts = line.split("] LOG:")
                path = parts[0][1:]
                content = parts[1].strip()
                latest_anomaly[path] = content

    print(f"[+] Trovati {len(latest_anomaly)} percorsi unici in {ANOMALIES_LOG}")

    # Categorie
    duplicates = []
    technical_errors = []
    weak_matches = []
    missing_tracks = []
    others = []

    tech_keywords = ["429:", "jsondecodeerror", "filenotfounderror", "notfounderror", "file exists", "readonly", "readerror", "crash:", "timed out", "keyerror", "acoustid"]

    for path, content in latest_anomaly.items():
        content_lower = content.lower()

        # Classificazione
        if any(kw in content_lower for kw in tech_keywords):
            technical_errors.append((path, content))
        elif "duplicate" in content_lower:
            duplicates.append((path, content))
        elif "missing tracks" in content_lower:
            missing_tracks.append((path, content))
        elif "skipping" in content_lower or "skip" in content_lower:
            weak_matches.append((path, content))
        else:
            others.append((path, content))

    print("\n=== CLASSIFICAZIONE ANOMALIE ===")
    print(f"  - Errori Tecnici (Rete/Crash) : {len(technical_errors)}")
    print(f"  - Duplicati                    : {len(duplicates)}")
    print(f"  - Tracce Mancanti              : {len(missing_tracks)}")
    print(f"  - Match Deboli (Skipped)       : {len(weak_matches)}")
    print(f"  - Altro                        : {len(others)}")
    print(f"  -------------------------------------------")
    print(f"  - Totale da Recuperare         : {len(latest_anomaly)}")

    # Scrittura dei path da recuperare
    with open(OUTPUT_FILE, "w") as out:
        for path in sorted(latest_anomaly.keys()):
            out.write(f"{path}\n")

    print(f"\n[OK] Scrittura di {len(latest_anomaly)} percorsi in: {OUTPUT_FILE}")

if __name__ == "__main__":
    main()

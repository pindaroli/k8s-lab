#!/usr/bin/env python3
"""
detect_case_clashes.py — Fase 4.2: Artist Case Clash Detection
================================================================
Interroga direttamente il file SQLite del database di Beets per trovare
tutti i casi in cui lo stesso artista esiste con grafie che differiscono
solo per il case (es. "Us3" e "US3", "Abba" e "ABBA").

Non richiede beets installato nell'ambiente Python corrente.
Opera esclusivamente in LETTURA: nessuna modifica al DB o al filesystem.

Output:
  - Tabella a console con i clash trovati
  - artist_clashes.txt   : lista clash (formato: variante1;variante2;...)
  - artist_clashes_mbsync.sh : comandi beet mbsync pronti all'uso

Usage:
  python3 detect_case_clashes.py [path/to/musiclibrary.db]

  Default DB (batch pipeline):
  /Users/olindo/prj/k8s-lab/import_music/musiclibrary.db
"""

import sqlite3
import collections
import sys
import os

# --- Configurazione ---
DEFAULT_DB  = os.path.join(os.path.dirname(__file__), "musiclibrary.db")
OUTPUT_TXT  = os.path.join(os.path.dirname(__file__), "artist_clashes.txt")
OUTPUT_BASH = os.path.join(os.path.dirname(__file__), "artist_clashes_mbsync.sh")


def main():
    db_path = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_DB

    if not os.path.exists(db_path):
        print(f"[ERROR] DB non trovato: {db_path}")
        print(f"  Usa: python3 {os.path.basename(__file__)} /path/to/musiclibrary.db")
        sys.exit(1)

    print(f"[INFO] Apertura DB: {db_path}")

    con = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)  # read-only
    cur = con.cursor()

    # Verifica schema — campo albumartist nella tabella albums
    cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='albums'")
    if not cur.fetchone():
        print("[ERROR] Tabella 'albums' non trovata. Il DB è un database Beets valido?")
        sys.exit(1)

    print("[INFO] Scansione albumartist nel DB...")

    cur.execute("SELECT DISTINCT albumartist FROM albums WHERE albumartist IS NOT NULL AND albumartist != ''")
    rows = cur.fetchall()
    con.close()

    total_artists = len(rows)

    # Raggruppa per nome normalizzato (strip + lowercase)
    artist_map = collections.defaultdict(set)
    for (aa,) in rows:
        aa_clean = aa.strip()
        if aa_clean:
            artist_map[aa_clean.lower()].add(aa_clean)

    # Filtra solo i conflitti reali (>1 variante per lo stesso nome normalizzato)
    clashes = {k: sorted(v) for k, v in artist_map.items() if len(v) > 1}

    print(f"[INFO] Artisti unici (albumartist) nel DB: {total_artists}")
    print(f"[INFO] Nomi unici case-insensitive: {len(artist_map)}")
    print()

    if not clashes:
        print("✅  Nessun clash trovato! La libreria è coerente nel case degli artisti.")
        with open(OUTPUT_TXT, "w") as f:
            f.write("# No case clashes found\n")
        return

    # --- Output console ---
    print(f"⚠️  Trovati {len(clashes)} clash di case:\n")
    col_w = max(len(k) for k in clashes) + 2
    print(f"  {'Nome Normalizzato':<{col_w}} | Varianti nel DB")
    print("  " + "-" * (col_w + 40))
    for lower_name, variants in sorted(clashes.items()):
        print(f"  {lower_name:<{col_w}} | {' | '.join(variants)}")

    # --- Output TXT ---
    with open(OUTPUT_TXT, "w") as f:
        f.write("# Artist case clashes — generato da detect_case_clashes.py\n")
        f.write("# Formato: variante1;variante2;...\n\n")
        for variants in sorted(clashes.values()):
            f.write(f"{';'.join(variants)}\n")
    print(f"\n[OK] Lista clash salvata in: {OUTPUT_TXT}")

    # --- Output BASH con comandi mbsync pronti ---
    with open(OUTPUT_BASH, "w") as f:
        f.write("#!/usr/bin/env bash\n")
        f.write("# Comandi beet mbsync per canonicalizzazione via MusicBrainz\n")
        f.write("# Generato da detect_case_clashes.py — Fase 4.2\n\n")
        f.write("# ATTENZIONE: questi comandi aggiornano il DB di Beets.\n")
        f.write("# Eseguire SOLO dopo aver completato la Fase 4.1 e con il batch fermo.\n\n")
        f.write(f"BEET_CONFIG={os.path.join(os.path.dirname(__file__), 'import_music_batches-config.yaml')}\n\n")
        for lower_name in sorted(clashes.keys()):
            # Protezione per nomi con spazi o caratteri speciali
            safe_name = lower_name.replace('"', '\\"')
            f.write(f'beet --config="$BEET_CONFIG" mbsync albumartist:"{safe_name}"\n')
    os.chmod(OUTPUT_BASH, 0o755)
    print(f"[OK] Comandi mbsync salvati in: {OUTPUT_BASH}")

    # --- Riepilogo decisionale ---
    print()
    print("=" * 65)
    print(f"  CLASH TOTALI     : {len(clashes)}")
    if len(clashes) < 10:
        print("  RACCOMANDAZIONE  : Opzione A — plugin 'rewrite' per i casi noti.")
    else:
        print("  RACCOMANDAZIONE  : Opzione B — lowercase path universale ($lower_artist).")
    print("=" * 65)
    print()
    print(f"  Prossimo passo: esegui  bash {OUTPUT_BASH}")
    print(f"  oppure correggi manualmente le varianti in: {OUTPUT_TXT}")


if __name__ == "__main__":
    main()

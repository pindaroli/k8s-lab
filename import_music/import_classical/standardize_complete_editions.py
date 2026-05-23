#!/usr/bin/env python3
import os
import sys
import argparse
import re

try:
    from beets.library import Library
except ImportError:
    print("[-] Errore: Le librerie di Beets non sono installate nel venv corrente.")
    sys.exit(1)

DEFAULT_DB = "/Users/olindo/prj/k8s-lab/import_music/import_classical/classical_musiclibrary.db"

# Mappa per normalizzare e ordinare le sezioni di Mozart 225
SECTION_MAP = {
    'chamber': ('Chamber', '01 Chamber'),
    'orchestral': ('Orchestral', '02 Orchestral'),
    'keyboard': ('Keyboard', '03 Keyboard'),
    'theatre': ('Theatre', '04 Theatre'),
    'opera': ('Theatre', '04 Theatre'),
    'sacred': ('Sacred', '05 Sacred'),
    'vocal': ('Sacred', '05 Sacred'),
    'supplement': ('Supplement', '06 Supplement'),
    'fragments': ('Fragments', '07 Other'),
    'completions': ('Completions', '07 Other'),
    'arrangements': ('Arrangements', '07 Other'),
    'self': ('Self-Arrangements', '07 Other'),
    'doubtful': ('Doubtful Works', '07 Other')
}

def parse_mozart_album(album_name):
    """
    Riconosce se un album appartiene a Mozart 225 e ne estrae CD, Sezione e Descrizione.
    Esempio: "CD-025-Chamber-a4-String Quartets" -> (025, Chamber, 01 Chamber, a4 - String Quartets)
    """
    m = re.match(r'^CD[-_ ]?(\d{3})[-_ ]+([A-Za-z0-9]+)(?:[-_ ]+(.*))?$', album_name, re.IGNORECASE)
    if m:
        cd_num = m.group(1)
        raw_section = m.group(2).lower()
        raw_desc = m.group(3)

        # Determina sezione e cartella
        section_clean, section_folder = SECTION_MAP.get(raw_section, (raw_section.capitalize(), "07 Other"))

        # Pulisce la descrizione sostituendo i trattini con spazi/trattini spaziati leggibili
        if raw_desc:
            desc_clean = re.sub(r'[-_]+', ' - ', raw_desc)
            desc_clean = re.sub(r'\s+', ' ', desc_clean).strip()
        else:
            desc_clean = ""

        # Rimuove le ridondanze estetiche dovute al parsing dei trattini
        if section_clean == "Self-Arrangements" and desc_clean.lower().startswith("arrangements"):
            desc_clean = re.sub(r'^arrangements\s*[-\s]*', '', desc_clean, flags=re.IGNORECASE).strip()
        elif section_clean == "Doubtful Works" and desc_clean.lower().startswith("works"):
            desc_clean = re.sub(r'^works\s*[-\s]*', '', desc_clean, flags=re.IGNORECASE).strip()

        return cd_num, section_clean, section_folder, desc_clean
    return None

def main():
    parser = argparse.ArgumentParser(description="Standardizzazione edizioni monumentali Mozart 225 a Database Beets.")
    parser.add_argument('--db', default=DEFAULT_DB, help="Percorso al database di Beets")
    parser.add_argument('--dry-run', action='store_true', default=True, help="Simula le modifiche a database senza salvarle")
    parser.add_argument('--run', dest='dry_run', action='store_false', help="Applica realmente le modifiche al database Beets")
    args = parser.parse_args()

    if not os.path.exists(args.db):
        print(f"[-] Database non trovato a: {args.db}")
        sys.exit(1)

    print(f"[*] Inizializzazione della libreria Beets da: {args.db}")
    lib = Library(args.db)

    albums = list(lib.albums())
    matched_albums = []

    print(f"[*] Scansione di {len(albums)} album in corso...")

    for album in albums:
        album_name = album.album
        parsed = parse_mozart_album(album_name)
        if parsed:
            matched_albums.append((album, parsed))

    if not matched_albums:
        print("[-] Nessun album di Mozart 225 identificato con il pattern atteso (es. CD-025-...).")
        return

    print(f"\n[+] Identificati {len(matched_albums)} album appartenenti a Mozart 225.")
    print("="*80)

    for album, (cd_num, sec_clean, sec_folder, desc_clean) in sorted(matched_albums, key=lambda x: x[1][0]):
        old_title = album.album

        # Costruisce il nuovo nome del CD
        if desc_clean:
            new_title = f"Mozart 225 - CD {cd_num}: {sec_clean} - {desc_clean}"
        else:
            new_title = f"Mozart 225 - CD {cd_num}: {sec_clean}"

        new_work = f"Mozart 225 - {sec_folder}"

        print(f"Album ID {album.id}:")
        print(f"  DA: '{old_title}'")
        print(f"  A : '{new_title}'")
        print(f"  Work/Parentwork associato: '{new_work}'")

        if not args.dry_run:
            # Aggiorna l'album
            album.album = new_title
            album.albumartist = "Wolfgang Amadeus Mozart"
            album.year = 2016
            album.original_year = 2016
            album.store()

            # Aggiorna tutte le tracce dell'album
            for item in album.items():
                item.album = new_title
                item.albumartist = "Wolfgang Amadeus Mozart"
                item.composer = "Wolfgang Amadeus Mozart"
                item.work = new_work
                item.parentwork = new_work
                item.year = 2016
                item.original_year = 2016
                item.store()

            print(f"  [x] Aggiornato a database con successo.")

    if args.dry_run:
        print("\n" + "="*80)
        print("[!] ESEGUITO IN MODALITÀ DRY-RUN. Nessuna modifica è stata salvata a database.")
        print("[*] Per applicare realmente le modifiche, rieseguire lo script con l'opzione: --run")
    else:
        print("\n" + "="*80)
        print("[+] MODIFICHE APPLICATE CON SUCCESSO A DATABASE.")
        print("[*] Ora è possibile eseguire 'beet move' per ricollocare fisicamente i file sul disco.")

if __name__ == '__main__':
    main()

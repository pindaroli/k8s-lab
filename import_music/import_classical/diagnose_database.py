#!/usr/bin/env python3
import os
import sys

try:
    from beets.library import Library
except ImportError:
    print("[-] Errore: Le librerie di Beets non sono installate nel venv corrente.")
    sys.exit(1)

db_path = "/Users/olindo/prj/k8s-lab/import_music/import_classical/classical_musiclibrary.db"

if not os.path.exists(db_path):
    print(f"[-] Database non trovato a: {db_path}")
    sys.exit(1)

print(f"[*] Inizializzazione libreria Beets da: {db_path}")
lib = Library(db_path)
albums = list(lib.albums())
tracks = list(lib.items())

def get_track_composers(track):
    """
    Estrae in modo robusto i compositori da una traccia, supportando sia 'composers' (lista o stringa)
    sia 'composer' (singolare) ed eventuali separatori multivalore.
    """
    # 1. Prova con 'composers' (plurale)
    comps = track.get('composers')
    if comps:
        if isinstance(comps, list):
            return [str(c).strip() for c in comps if c]
        elif isinstance(comps, str):
            # Prova a splittare per i tipici delimitatori multivalore
            return [c.strip() for c in comps.replace(';', ',').split(',') if c.strip()]

    # 2. Fallback su 'composer' (singolare)
    comp = track.get('composer')
    if comp:
        if isinstance(comp, list):
            return [str(c).strip() for c in comp if c]
        elif isinstance(comp, str):
            return [c.strip() for c in comp.replace(';', ',').split(',') if c.strip()]

    return []

print("\n" + "="*50)
print("STATISTICHE GENERALI (CON NUOVA LOGICA MULTIVALORE)")
print("="*50)
print(f"Totale Album: {len(albums)}")
print(f"Totale Tracce: {len(tracks)}")

tracks_with_composer = 0
unique_all_composers = set()

for t in tracks:
    comps = get_track_composers(t)
    if comps:
        tracks_with_composer += 1
        for c in comps:
            unique_all_composers.add(c)

print(f"Tracce con compositore individuato: {tracks_with_composer} su {len(tracks)}")
print(f"Compositori unici totali nel DB: {len(unique_all_composers)}")
print("\nPrimi 15 compositori unici rilevati:")
for c in sorted(list(unique_all_composers))[:15]:
    print(f"  - {c}")

# Analizziamo la classificazione Recital con la nuova logica
recital_albums = []
monograph_albums = 0
empty_albums = 0

for album in albums:
    album_tracks = list(album.items())
    album_composers = set()
    for t in album_tracks:
        for c in get_track_composers(t):
            album_composers.add(c.lower().strip())

    if not album_composers:
        empty_albums += 1
    elif len(album_composers) > 1:
        recital_albums.append((album, album_composers))
    else:
        monograph_albums += 1

print("\n" + "="*50)
print("ANALISI RECITAL (Compositori > 1 per Album)")
print("="*50)
print(f"Album Monografici (1 compositore): {monograph_albums}")
print(f"Album senza compositore valorizzato: {empty_albums}")
print(f"Album Recital identificati (multi-compositore): {len(recital_albums)}")

if recital_albums:
    print(f"\nEsempi di Recital individuati (primi 10 di {len(recital_albums)}):")
    for album, comps in recital_albums[:10]:
        print(f"  - ID {album.id}: '{album.album}' di '{album.albumartist}'")
        print(f"    Compositori: {', '.join(sorted(list(comps)))}")

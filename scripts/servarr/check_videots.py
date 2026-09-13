import os
from pathlib import Path

base = Path('/mnt/oliraid/arrdata/media/movies')
folders = [
    "Alexander (2004) {tmdb-1966}",
    "Beetlejuice - Spiritello porcello (1988) {tmdb-4011}",
    "Il dottor Stranamore, ovvero - come ho imparato a non preoccuparmi e ad amare la bomba (1964) {tmdb-935}",
    "La mala educación-(2004)-Pedro Almodóvar",
    "Le crociate - Kingdom of Heaven (2005) {tmdb-1495}",
    "Le streghe di Salem (2013) {tmdb-104755}",
    "Manhattan (1979) {tmdb-696}",
    "Match Point-(2005)-Woody Allen",
    "Red 2 (2013) {tmdb-146216}",
    "Terminator Genisys (2015) {tmdb-87101}",
    "Woody Allen - Sogli e Delitti"
]

print("=== AUDIT PRE-PULIZIA VIDEO_TS ===\n")
total_reclaimable = 0

for f in folders:
    p = base / f
    if not p.exists():
        print(f"[!] Cartella non trovata: {f}")
        continue

    isos = list(p.rglob('*.iso'))
    mkvs = list(p.rglob('*.mkv')) + list(p.rglob('*.mp4')) + list(p.rglob('*.avi'))
    main_vids = [v for v in mkvs if 'VIDEO_TS' not in str(v)]
    videots = [d for d in p.rglob('VIDEO_TS') if d.is_dir()]

    vts_size = 0
    for vd in videots:
        for root, dirs, files in os.walk(vd):
            for file in files:
                try:
                    vts_size += os.path.getsize(os.path.join(root, file))
                except: pass

    iso_size = sum(os.path.getsize(i) for i in isos)

    print(f"[{f}]")
    print(f"  - File ISO: {[i.name for i in isos]} ({iso_size / (1024**3):.2f} GB)")
    print(f"  - File Video alternativi: {[v.name for v in main_vids]}")
    print(f"  - Cartelle VIDEO_TS: {len(videots)} ({vts_size / (1024**3):.2f} GB)")

    if isos or main_vids:
        print("  -> STATO: SICURO DA ELIMINARE (Master ISO/Video presente)")
        total_reclaimable += vts_size
    else:
        print("  -> STATO: ⚠️ PERICOLO! NON ELIMINARE (VIDEO_TS è l'unica copia del film!)")
    print("-" * 50)

print(f"\nTOTALE SPAZIO RECUPERABILE IN SICUREZZA: {total_reclaimable / (1024**3):.2f} GB")

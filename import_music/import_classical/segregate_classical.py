#!/usr/bin/env python3
"""
segregate_classical.py
======================
Fase 1 della Pipeline di Musica Classica.

Legge il file 'import_anomalies.log' della pipeline standard (pop/rock),
identifica euristicamente le cartelle di musica classica tramite:
  1. Keyword matching sul nome della cartella e del compositore (path)
  2. Ispezione dei tag audio (Vorbis Comments FLAC / ID3 MP3) via mutagen

In modalità dry-run (default) stampa i path identificati senza toccare nulla.
Per eseguire la migrazione effettiva: python3 segregate_classical.py run

Struttura paths (dataset ZFS unificato oliraid/arrdata/classical):
  - Anomaly Log sorgente : ../import_anomalies.log
  - Staging destinazione : /Volumes/arrdata/classical/staging/
  - Library finale       : /Volumes/arrdata/classical/library/
  - Script dir           : /Users/olindo/prj/k8s-lab/import_music/import_classical/

Nota: staging e library sono directory dello stesso dataset ZFS—
questo abilita gli hardlink (import.link: yes) preservando il seeding.
"""

import os
import re
import sys
import shutil
from pathlib import Path

# ─── Paths Configuration ─────────────────────────────────────────────────────
# Deriviamo i percorsi relativamente a questa directory per portabilità
SCRIPT_DIR  = Path(__file__).parent
PARENT_DIR  = SCRIPT_DIR.parent

ANOMALY_LOG       = PARENT_DIR / "import_anomalies.log"
CLASSICAL_STAGING = Path("/Volumes/arrdata/classical/staging")
# ─────────────────────────────────────────────────────────────────────────────

# Keyword euristiche per identificazione classica (case-insensitive)
CLASSICAL_KEYWORDS = [
    # Compositori per nome
    'mozart', 'bach', 'beethoven', 'vivaldi', 'chopin', 'tchaikovsky',
    'schubert', 'debussy', 'stravinsky', 'mahler', 'wagner', 'handel',
    'haydn', 'brahms', 'ravel', 'rachmaninoff', 'mendelssohn', 'schumann',
    'grieg', 'sibelius', 'verdi', 'puccini', 'rossini', 'donizetti',
    'bellini', 'dvorak', 'liszt', 'elgar', 'prokofiev', 'shostakovich',
    'monteverdi', 'gesualdo', 'scarlatti', 'corelli', 'telemann',
    'rameau', 'couperin', 'buxtehude', 'tartini', 'albinoni', 'boccherini',
    'hummel', 'paganini', 'berlioz', 'bizet', 'saint-saens', 'gounod',
    'massenet', 'franck', 'bruckner', 'smetana', 'janacek', 'bartok',
    'kodaly', 'sibelius', 'nielsen', 'vaughan williams', 'holst', 'britten',
    'walton', 'tippett', 'messiaen', 'boulez', 'stockhausen', 'xenakis',
    'penderecki', 'gorecki', 'arvo part', 'pärt', 'schnittke', 'gubaidulina',
    # Direttori d'orchestra celebri
    'karajan', 'bernstein', 'abbado', 'furtwangler', 'solti', 'toscanini',
    'klemperer', 'walter', 'szell', 'ormandy', 'marriner', 'gardiner',
    'herreweghe', 'harnoncourt', 'norrington', 'mackerras', 'jansons',
    'gergiev', 'muti', 'chailly', 'rattle', 'thielemann', 'barenboim',
    'mehta', 'ozawa', 'maazel', 'levine', 'masur', 'blomstedt', 'nelsons',
    # Solisti celebri
    'callas', 'pavarotti', 'domingo', 'carreras', 'netrebko', 'villazon',
    'kaufmann', 'gheorghiu', 'hampson', 'bryn terfel', 'mutter', 'perlman',
    'rostropovich', 'yo-yo ma', 'kissin', 'argerich', 'brendel', 'ashkenazy',
    'pollini', 'barenboim', 'perahia', 'schiff', 'radu lupu', 'sokolov',
    # Termini di genere e forma musicale
    'symphony', 'sinfonia', 'concerto', 'orchestra', 'philharmonic',
    'choir', 'coro', 'sonata', 'opera', 'requiem', 'suite', 'rhapsody',
    'overture', 'prelude', 'cantata', 'nocturne', 'baroque', 'klasik',
    'string quartet', 'piano trio', 'chamber music', 'oratorio', 'mass',
    'lieder', 'scena', 'aria', 'adagio', 'allegro', 'andante',
    'philharmoniker', 'gewandhaus', 'staatskapelle', 'chamber orchestra',
]

# ─── Mutagen Optional Import ─────────────────────────────────────────────────
MUTAGEN_AVAILABLE = False
try:
    from mutagen.flac import FLAC
    from mutagen.id3 import ID3
    MUTAGEN_AVAILABLE = True
    print("[INFO] Mutagen library loaded — tag inspection enabled.")
except ImportError:
    print("[WARNING] Mutagen not found. Falling back to path-based heuristics only.")
    print("         Install with: pip install mutagen")


def is_classical(folder_path: Path) -> bool:
    """
    Valuta se una directory è musica classica tramite euristiche multi-livello.
    """
    folder_name = folder_path.name.lower()
    parent_name = folder_path.parent.name.lower() if folder_path.parent != folder_path else ""

    # Livello 1: Keyword nel nome cartella o artista (parent dir)
    if any(kw in folder_name for kw in CLASSICAL_KEYWORDS):
        return True
    if any(kw in parent_name for kw in CLASSICAL_KEYWORDS):
        return True

    if not MUTAGEN_AVAILABLE:
        return False

    # Livello 2: Ispezione binaria dei tag audio
    try:
        for file in os.listdir(folder_path):
            file_path = folder_path / file

            if file.endswith('.flac'):
                try:
                    audio = FLAC(file_path)
                    if 'genre' in audio:
                        for g in audio['genre']:
                            if any(x in g.lower() for x in [
                                'classical', 'classica', 'opera', 'baroque',
                                'symphony', 'sinfonia', 'chamber', 'orchestral'
                            ]):
                                return True
                    if 'composer' in audio and audio.get('composer'):
                        return True
                except Exception:
                    pass

            elif file.endswith('.mp3'):
                try:
                    audio = ID3(file_path)
                    if 'TCON' in audio:
                        if any(x in str(audio['TCON']).lower() for x in [
                            'classical', 'classica', 'opera', 'baroque'
                        ]):
                            return True
                    if 'TCOM' in audio and audio['TCOM']:
                        return True
                except Exception:
                    pass

            # Ottimizzazione: un file rappresentativo per cartella è sufficiente
            if file.endswith(('.flac', '.mp3', '.m4a', '.ogg')):
                break

    except PermissionError:
        pass

    return False


def extract_paths_from_log() -> list:
    """
    Parsa import_anomalies.log ed estrae i path unici delle directory fallite.
    Formato riga: [/path/to/dir] LOG: ...
    """
    if not ANOMALY_LOG.exists():
        print(f"[FATAL] Anomaly log non trovato: {ANOMALY_LOG}")
        sys.exit(1)

    paths = set()
    path_regex = re.compile(r'^\[([^\]]+)\]')

    with open(ANOMALY_LOG, 'r', encoding='utf-8', errors='ignore') as f:
        for line in f:
            match = path_regex.match(line)
            if match:
                paths.add(Path(match.group(1)))

    print(f"[INFO] Trovati {len(paths)} path unici in {ANOMALY_LOG.name}")
    return sorted(paths)


def run(dry_run: bool = True):
    """
    Esegue la segregazione. In dry_run=True stampa senza agire.
    """
    mode_label = "DRY-RUN" if dry_run else "EXECUTE"
    print(f"\n{'='*60}")
    print(f"  CLASSICAL MUSIC SEGREGATION — {mode_label}")
    print(f"{'='*60}")
    print(f"  Sorgente anomalie : {ANOMALY_LOG}")
    print(f"  Staging dest.     : {CLASSICAL_STAGING}")
    print()

    if not dry_run:
        CLASSICAL_STAGING.mkdir(parents=True, exist_ok=True)

    paths = extract_paths_from_log()
    classical_count = 0
    skipped_count   = 0
    missing_count   = 0
    errors          = []

    for folder in paths:
        if not folder.exists():
            missing_count += 1
            continue

        if is_classical(folder):
            classical_count += 1
            dest = CLASSICAL_STAGING / folder.name

            if dry_run:
                print(f"  [✓ CLASSICA] {folder}")
            else:
                try:
                    print(f"  [MOVE] {folder.name}  →  {CLASSICAL_STAGING}/")
                    shutil.move(str(folder), str(dest))
                except Exception as e:
                    errors.append((folder, e))
                    print(f"  [ERROR] {folder.name}: {e}")
        else:
            skipped_count += 1

    print(f"\n{'='*60}")
    print(f"  RIEPILOGO")
    print(f"{'='*60}")
    print(f"  Path totali nel log    : {len(paths)}")
    print(f"  Identificati classica  : {classical_count}")
    print(f"  Saltati (pop/rock/jazz): {skipped_count}")
    print(f"  Non presenti su disco  : {missing_count}")
    if errors:
        print(f"  Errori di spostamento  : {len(errors)}")
    print()

    if dry_run:
        print("  ➡  Dry-run completato. Per eseguire la migrazione reale:")
        print(f"     python3 {Path(__file__).name} run\n")


if __name__ == '__main__':
    dry_run = not (len(sys.argv) > 1 and sys.argv[1].lower() == 'run')
    run(dry_run=dry_run)

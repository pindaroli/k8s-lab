#!/usr/bin/env python3
"""
clean_conversations.py
Motore CLI interattivo per la ricerca, filtro con eccezioni e pulizia
atomica delle conversazioni storiche di Antigravity.
"""

import os
import sys
import sqlite3
import shutil
import re
from datetime import datetime, timezone, timedelta
from pathlib import Path
import argparse

# CWD independence conformemente a go-launcher-script-pattern
SCRIPT_DIR = os.path.dirname(os.path.realpath(__file__))
ROOT_DIR = os.path.abspath(os.path.join(SCRIPT_DIR, "..", ".."))
os.chdir(ROOT_DIR)

ANTIGRAVITY_BASE = Path(os.path.expanduser("~/.gemini/antigravity"))
DB_PATH = ANTIGRAVITY_BASE / "conversation_summaries.db"
CONV_DIR = ANTIGRAVITY_BASE / "conversations"
BRAIN_DIR = ANTIGRAVITY_BASE / "brain"
ANNOT_DIR = ANTIGRAVITY_BASE / "annotations"


def parse_flexible_date(input_str: str, is_end_date: bool = False) -> datetime:
    """Interpreta date esplicite (YYYY-MM-DD) o relative (now, today, 1m, 3m)."""
    s = input_str.strip().lower()
    now_utc = datetime.now(timezone.utc)

    if not s or s in ("now", "today", "oggi"):
        return now_utc
    if s in ("start", "beginning", "inizio", "all"):
        return datetime(1970, 1, 1, tzinfo=timezone.utc)

    # Alias relativi: es. 1m, 30d, 2w
    m = re.match(r"^(\d+)\s*([dwmy])$", s)
    if m:
        qty = int(m.group(1))
        unit = m.group(2)
        if unit == "d":
            return now_utc - timedelta(days=qty)
        elif unit == "w":
            return now_utc - timedelta(weeks=qty)
        elif unit == "m":
            return now_utc - timedelta(days=qty * 30)
        elif unit == "y":
            return now_utc - timedelta(days=qty * 365)

    # Formati standard
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y-%m-%d"):
        try:
            dt = datetime.strptime(s, fmt)
            if is_end_date and fmt == "%Y-%m-%d":
                dt = dt.replace(hour=23, minute=59, second=59)
            return dt.replace(tzinfo=timezone.utc)
        except ValueError:
            continue

    raise ValueError(f"Formato data non riconosciuto: '{input_str}'. Usa YYYY-MM-DD, now, 1m, ecc.")


def parse_index_list(input_str: str, max_index: int) -> set[int]:
    """Interpreta una stringa di indici ed intervalli (es: '1, 3, 5-8')."""
    indices = set()
    parts = [p.strip() for p in input_str.replace(";", ",").split(",") if p.strip()]
    for p in parts:
        if "-" in p:
            range_parts = p.split("-")
            if len(range_parts) == 2 and range_parts[0].strip().isdigit() and range_parts[1].strip().isdigit():
                start = int(range_parts[0].strip())
                end = int(range_parts[1].strip())
                if start > end:
                    start, end = end, start
                for idx in range(start, end + 1):
                    if 1 <= idx <= max_index:
                        indices.add(idx)
        elif p.isdigit():
            idx = int(p)
            if 1 <= idx <= max_index:
                indices.add(idx)
    return indices


def get_available_workspaces(conn: sqlite3.Connection) -> list[str]:
    """Recupera la lista dei workspace distinti dal database."""
    cur = conn.cursor()
    cur.execute("SELECT DISTINCT workspace_uris FROM conversation_summaries WHERE workspace_uris IS NOT NULL")
    workspaces = set()
    for (uris_json,) in cur.fetchall():
        if not uris_json:
            continue
        # Estrai nomi di cartelle/progetti dagli URI
        matches = re.findall(r"file://[^\"']+/([^/\"']+)", uris_json)
        for m in matches:
            workspaces.add(m)
    return sorted(list(workspaces))


def calculate_session_size(cid: str) -> int:
    """Calcola la dimensione fisica occupata da una conversazione su disco."""
    total_bytes = 0
    for ext in (".db", ".pb"):
        f = CONV_DIR / f"{cid}{ext}"
        if f.exists():
            total_bytes += f.stat().st_size

    d = BRAIN_DIR / cid
    if d.exists() and d.is_dir():
        for item in d.rglob("*"):
            if item.is_file():
                total_bytes += item.stat().st_size

    a = ANNOT_DIR / f"{cid}.pbtxt"
    if a.exists():
        total_bytes += a.stat().st_size

    return total_bytes


def main():
    parser = argparse.ArgumentParser(
        description="Pulizia selettiva e compattazione conversazioni storiche Antigravity"
    )
    parser.add_argument("--project", "-p", help="Nome o filtro del progetto/workspace (default: k8s-lab)")
    parser.add_argument("--start-date", "-s", help="Data inizio (più recente)")
    parser.add_argument("--end-date", "-e", help="Data fine (più vecchia)")
    parser.add_argument("--exclude", "-x", help="Indici da escludere (separati da virgola, es: 1,3,5)")
    parser.add_argument("--dry-run", action="store_true", help="Esegui simulazione senza cancellare nulla")
    parser.add_argument("--yes", "-y", action="store_true", help="Conferma automatica non-interattiva")
    args = parser.parse_args()

    if not DB_PATH.exists():
        print(f"❌ Database non trovato nel percorso atteso: {DB_PATH}")
        sys.exit(1)

    conn = sqlite3.connect(DB_PATH)
    available_ws = get_available_workspaces(conn)

    print("=" * 70)
    print("🧹 Antigravity Conversation Cleaner")
    print("=" * 70)

    # 1. Selezione Progetto
    project_filter = args.project
    if not project_filter:
        print("\n📁 Workspace / Progetti rilevati:")
        for i, ws in enumerate(available_ws, 1):
            print(f"  [{i}] {ws}")
        choice = input("\nSeleziona progetto (numero o nome) [default: k8s-lab]: ").strip()
        if not choice:
            project_filter = "k8s-lab"
        elif choice.isdigit() and 1 <= int(choice) <= len(available_ws):
            project_filter = available_ws[int(choice) - 1]
        else:
            project_filter = choice

    print(f"🎯 Progetto selezionato: '{project_filter}'")

    # 2. Selezione Date (Inizio e Fine)
    start_input = args.start_date
    if not start_input:
        start_input = input("\n📅 Data inizio (es: 2026-09-14, 'today', '1m') [default: today]: ").strip()
    dt1 = parse_flexible_date(start_input or "today", is_end_date=True)

    end_input = args.end_date
    if not end_input:
        end_input = input("📅 Data fine limite nel passato (es: 2026-01-01, 'beginning', '6m') [default: beginning]: ").strip()
    dt2 = parse_flexible_date(end_input or "beginning", is_end_date=False)

    # Normalizzazione temporale: fine più vecchia di inizio, oppure intervallo automatico [min, max]
    min_date = min(dt1, dt2)
    max_date = max(dt1, dt2)

    print(f"\n🔍 Intervallo di ricerca normalizzato: dal {min_date.strftime('%Y-%m-%d %H:%M')} al {max_date.strftime('%Y-%m-%d %H:%M')} UTC")

    # 3. Query ed estrazione conversazioni
    cur = conn.cursor()
    cur.execute(
        """
        SELECT conversation_id, title, preview, last_modified_time, last_user_input_time, step_count
        FROM conversation_summaries
        WHERE workspace_uris LIKE ?
        ORDER BY last_modified_time ASC
        """,
        (f"%{project_filter}%",),
    )
    rows = cur.fetchall()

    matching_convs = []
    total_bytes_target = 0

    for r in rows:
        cid, title, preview, mod_time, user_time, step_count = r
        t_str = mod_time or user_time
        if t_str:
            try:
                dt = datetime.fromisoformat(t_str)
            except Exception:
                dt = datetime.strptime(t_str.split(".")[0], "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc)
        else:
            dt = datetime.min.replace(tzinfo=timezone.utc)

        display_title = (title if (title and title.strip()) else preview) or "(Senza titolo)"
        display_title = display_title.replace("\n", " ").strip()

        if min_date <= dt <= max_date:
            sz = calculate_session_size(cid)
            total_bytes_target += sz
            matching_convs.append({
                "id": cid,
                "title": display_title,
                "date": dt.strftime("%Y-%m-%d %H:%M") if dt.year > 1 else "N/A",
                "steps": step_count,
                "size_bytes": sz,
                "size_mb": sz / (1024 * 1024),
            })

    if not matching_convs:
        print("\n✨ Nessuna conversazione trovata nell'intervallo temporale specificato.")
        conn.close()
        sys.exit(0)

    # 4. Presentazione Lista Numerata
    print(f"\n📋 Trovate {len(matching_convs)} conversazioni candidate ({total_bytes_target / (1024 * 1024):.2f} MB):")
    print("-" * 110)
    print(f"{'#':<5} | {'Data/Ora':<16} | {'Titolo / Anteprima':<45} | {'Steps':<6} | {'Dimens.':<9} | {'ID':<10}")
    print("-" * 110)
    for idx, c in enumerate(matching_convs, 1):
        short_title = (c['title'][:42] + "...") if len(c['title']) > 45 else c['title']
        short_id = c['id'][:8] + ".."
        print(f"[{idx:<3}] | {c['date']:<16} | {short_title:<45} | {c['steps']:<6} | {c['size_mb']:>6.2f} MB | {short_id:<10}")
    print("-" * 110)

    # 5. Gestione Eccezioni
    to_delete = list(matching_convs)
    if args.exclude:
        excluded_indices = parse_index_list(args.exclude, len(matching_convs))
        to_delete = [c for i, c in enumerate(matching_convs, 1) if i not in excluded_indices]
    elif not args.yes:
        has_exceptions = input("\n❓ Ci sono eccezioni da NON cancellare? (yes/no) [default: no]: ").strip().lower()
        if has_exceptions in ("yes", "y", "s", "si"):
            ex_input = input("   Inserisci gli indici da ESCLUDERE (es: 1, 3, 5-8): ").strip()
            excluded_indices = parse_index_list(ex_input, len(matching_convs))
            to_delete = [c for i, c in enumerate(matching_convs, 1) if i not in excluded_indices]
            print(f"\n   Esclusi {len(excluded_indices)} elementi. Nuova lista di cancellazione: {len(to_delete)} conversazioni.")

    if not to_delete:
        print("\n⚠️ Tutte le conversazioni sono state escluse. Nessuna operazione eseguita.")
        conn.close()
        sys.exit(0)

    bytes_to_free = sum(c["size_bytes"] for c in to_delete)
    print(f"\n🚨 Stai per cancellare DEFINITIVAMENTE {len(to_delete)} conversazioni (~{bytes_to_free / (1024 * 1024):.2f} MB).")

    # 6. Conferma Definitiva
    if not args.yes and not args.dry_run:
        confirm = input("Procedere con la cancellazione? Digita 'yes' per confermare: ").strip().lower()
        if confirm != "yes":
            print("❌ Operazione annullata dall'utente.")
            conn.close()
            sys.exit(0)

    if args.dry_run:
        print("\n[DRY-RUN] Simulazione completata con successo:")
        print(f"  - Conversazioni che verrebbero eliminate: {len(to_delete)}")
        print(f"  - Spazio recuperabile stimato: {bytes_to_free / (1024 * 1024):.2f} MB ({bytes_to_free / (1024 * 1024 * 1024):.2f} GB)")
        print("  - Nessun file modificato o cancellato.")
        conn.close()
        sys.exit(0)

    # 7. Esecuzione Pulizia
    print("\n📦 1. Creazione backup preventivo del database...")
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_file = Path(f"{DB_PATH}.bak_{ts}")
    shutil.copy2(DB_PATH, backup_file)
    print(f"   Backup salvato in: {backup_file.name}")

    print("🗑️ 2. Eliminazione file e directory su disco...")
    del_conv = 0
    del_brain = 0
    del_annot = 0
    freed_real = 0

    for c in to_delete:
        cid = c["id"]
        for ext in (".db", ".pb"):
            f = CONV_DIR / f"{cid}{ext}"
            if f.exists():
                freed_real += f.stat().st_size
                f.unlink()
                del_conv += 1

        d = BRAIN_DIR / cid
        if d.exists() and d.is_dir():
            for item in d.rglob("*"):
                if item.is_file():
                    freed_real += item.stat().st_size
            shutil.rmtree(d)
            del_brain += 1

        a = ANNOT_DIR / f"{cid}.pbtxt"
        if a.exists():
            freed_real += a.stat().st_size
            a.unlink()
            del_annot += 1

    print(f"   Rimossi: {del_conv} file di sessione, {del_brain} cartelle brain, {del_annot} annotazioni.")

    print("🗄️ 3. Pulizia tabelle database e FTS...")
    target_ids = [c["id"] for c in to_delete]
    batch_size = 100
    for i in range(0, len(target_ids), batch_size):
        batch = target_ids[i:i + batch_size]
        placeholders = ",".join(["?"] * len(batch))
        cur.execute(f"DELETE FROM conversation_summaries WHERE conversation_id IN ({placeholders})", batch)
        cur.execute(f"DELETE FROM conversations_fts WHERE conversation_id IN ({placeholders})", batch)
    conn.commit()

    print("🧹 4. Compattazione database con VACUUM...")
    cur.execute("VACUUM")
    conn.commit()

    cur.execute("PRAGMA integrity_check")
    status = cur.fetchone()[0]
    new_db_size = DB_PATH.stat().st_size

    conn.close()

    # 8. Statistiche Finali
    print("\n" + "=" * 70)
    print("✅ PULIZIA COMPLETATA CON SUCCESSO")
    print("=" * 70)
    print(f"• Conversazioni eliminate:    {len(to_delete)}")
    print(f"• Spazio disco liberato:      {freed_real / (1024 * 1024):.2f} MB ({freed_real / (1024 * 1024 * 1024):.2f} GB)")
    print(f"• Dimensione DB compattato:   {new_db_size / (1024 * 1024):.2f} MB")
    print(f"• Test Integrità SQLite:      {status}")
    print("=" * 70)


if __name__ == "__main__":
    main()

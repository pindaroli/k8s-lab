#!/usr/bin/env python3
# Script di unificazione versioni multiple film per Jellyfin / FileBot (Scenario A)
# Supporta:
# 1. Esclusione strutture disco raw (BDMV, VIDEO_TS) e film multi-parte (CD1/CD2)
# 2. Selezione interattiva dei film da unificare o via CLI (--select, --all)
# 3. Analisi flussi con ffprobe (risoluzione, codec, tracce audio)
# 4. Spostamento, rinomina canonica e pulizia cartelle vuote

import os
import re
import sys
import json
import shutil
import argparse
import unicodedata
import subprocess
from pathlib import Path
from collections import defaultdict

MEDIA_DIR = os.environ.get("MEDIA_DIR", "/mnt/oliraid/arrdata/media/movies")

def get_ffprobe_bin():
    if os.path.exists("/mnt/oliraid/bin/ffprobe"):
        return "/mnt/oliraid/bin/ffprobe"
    return shutil.which("ffprobe")

def is_video_file(filename):
    exts = ['.mkv', '.mp4', '.avi', '.iso', '.m4v', '.ts', '.m2ts']
    return any(filename.lower().endswith(ext) for ext in exts)

def is_multipart_file(filename):
    """Rileva se un file è una parte (CD1, CD2, part1, disc1) di un rilascio diviso."""
    return bool(re.search(r'[-_ .](cd|part|disc|pt)\s*0*([1-9]\d*)', filename, re.IGNORECASE))

def extract_movie_identity(folder_name):
    tmdb_match = re.search(r'(?:tmdbid|tmdb)[-_](\d+)', folder_name, re.IGNORECASE)
    tmdb_id = tmdb_match.group(1) if tmdb_match else None

    year_match = re.search(r'[\(\[\s\.-](19\d{2}|20\d{2})[\)\]\s\.-]?', folder_name)
    year = year_match.group(1) if year_match else None

    clean = re.sub(r'\[.*?\]|\{.*?\}', '', folder_name)
    clean = re.sub(r'(?i)\b(1080p|720p|2160p|4k|bluray|web-dl|webrip|remux|bdrip|hdr|extended|x264|x265|hevc|dvdrip|ac3|dts|ita|eng|french|spanish|multi)\b.*', '', clean)
    if year:
        clean = re.split(rf'[\(\[\s\.-]{year}', clean)[0]

    # Rimuovi accenti (es: Léon -> Leon) per matching
    clean_ascii = unicodedata.normalize('NFKD', clean).encode('ASCII', 'ignore').decode('utf-8')
    clean_ascii = re.sub(r'[\.\-_\(\)]+', ' ', clean_ascii).strip().lower()
    clean_ascii = re.sub(r'^(the|a|an|il|la|lo|i|gli|le|un|uno|una)\s+', '', clean_ascii).strip()

    # Titolo originale per denominazione file (preserva maiuscole/accenti e trattini legittimi)
    display_title = re.sub(r'\[.*?\]|\{.*?\}', '', folder_name)
    if year:
        display_title = re.split(rf'[\(\[\s\.-]{year}', display_title)[0]
    display_title = display_title.strip(' .-_')
    display_title = re.sub(r'\s+', ' ', display_title).strip()

    return tmdb_id, clean_ascii, display_title, year

def analyze_video_info(video_file, folder_name=""):
    if not video_file or not os.path.exists(video_file):
        return {"res": "Sconosciuta", "codec": "N/D", "source": "Rip", "audio_summary": "N/D"}

    file_name = os.path.basename(video_file)
    f_lower = file_name.lower()

    # Rilevamento sorgente da nome file
    source = "Rip"
    if "remux" in f_lower:
        source = "Remux"
    elif "bdrip" in f_lower:
        source = "BDRip"
    elif "bluray" in f_lower or "blu-ray" in f_lower:
        source = "BluRay"
    elif "webdl" in f_lower or "web-dl" in f_lower or "webrip" in f_lower:
        source = "WEBDL"
    elif "dvdrip" in f_lower or f_lower.endswith(('.iso', '.ts')):
        source = "DVD"

    ffprobe = get_ffprobe_bin()
    if not ffprobe:
        return {"res": "N/D", "codec": "N/D", "source": source, "audio_summary": "N/D"}

    cmd = [ffprobe, "-v", "quiet", "-show_format", "-show_streams", "-of", "json", video_file]
    try:
        res = subprocess.run(cmd, stdout=subprocess.PIPE, text=True, timeout=20)
        data = json.loads(res.stdout)

        has_ita = False
        has_eng = False
        video_res = "SD"
        video_codec = "x264"

        for stream in data.get('streams', []):
            ctype = stream.get('codec_type')
            cname = stream.get('codec_name', '')
            tags = stream.get('tags', {})
            lang = tags.get('language', 'und').lower()
            title = tags.get('title', '').lower()

            if ctype == 'video' and video_res == "SD":
                video_codec = cname
                w = stream.get('width', 0)
                h = stream.get('height', 0)
                if w >= 3800 or h >= 2100:
                    video_res = "4K"
                elif w >= 1900 or h >= 1000:
                    video_res = "1080p"
                elif w >= 1200 or h >= 700:
                    video_res = "720p"
                else:
                    video_res = "576p"

            elif ctype == 'audio':
                if 'ita' in lang or 'italian' in title or 'ita' in title:
                    has_ita = True
                elif 'eng' in lang or 'english' in title or 'eng' in title:
                    has_eng = True

        # Fallback euristico se und
        if not has_ita and re.search(r'\b(ita|italian|italiano|iTA-ENG)\b', f"{file_name} {folder_name}", re.IGNORECASE):
            has_ita = True

        audio_parts = []
        if has_ita: audio_parts.append("ITA")
        if has_eng: audio_parts.append("ENG")
        audio_summary = "-".join(audio_parts) if audio_parts else "Original"

        return {
            "res": video_res,
            "codec": video_codec,
            "source": source,
            "audio_summary": audio_summary
        }
    except Exception:
        return {"res": "N/D", "codec": "N/D", "source": source, "audio_summary": "N/D"}

def plan_merges(base_dir):
    folder_entries = []
    parent = {}

    for item in sorted(base_dir.iterdir()):
        if not item.is_dir(): continue
        tmdb_id, clean_ascii, display_title, year = extract_movie_identity(item.name)

        # File video nella cartella, escludendo BDMV, VIDEO_TS, extras
        vids = []
        for root, dirs, files in os.walk(item):
            rparts = [p.upper() for p in Path(root).parts]
            # Escludi cartelle speciali o strutture disco raw
            if any(p in ['EXTRAS', '.TRICKPLAY', '.ACTORS', 'BDMV', 'CERTIFICATE', 'VIDEO_TS', 'AUDIO_TS', 'STREAM', 'CLIPINF', 'PLAYLIST', 'BACKUP'] for p in rparts):
                continue
            for f in files:
                if is_video_file(f) and not f.lower().endswith(('-trailer.mp4', '-trailer.mkv')):
                    vids.append(os.path.join(root, f))

        # Filtro film multi-parte (CD1/CD2/part1/part2):
        # Se tutti i video nella cartella sono segmenti multi-parte dello stesso film,
        # non sono versioni alternative indipendenti e vanno ignorati per il multi-versioning.
        is_multipart_only = False
        if len(vids) > 1:
            all_parts = [is_multipart_file(os.path.basename(v)) for v in vids]
            if all(all_parts):
                is_multipart_only = True

        folder_entries.append({
            "path": item,
            "name": item.name,
            "tmdb_id": tmdb_id,
            "clean_ascii": clean_ascii,
            "display_title": display_title,
            "year": year,
            "video_files": vids,
            "is_multipart_only": is_multipart_only
        })
        parent[item.name] = item.name

    def find(i):
        if parent[i] == i: return i
        parent[i] = find(parent[i])
        return parent[i]

    def union(i, j):
        root_i = find(i)
        root_j = find(j)
        if root_i != root_j:
            parent[root_i] = root_j

    n = len(folder_entries)
    for i in range(n):
        for j in range(i + 1, n):
            e1 = folder_entries[i]
            e2 = folder_entries[j]

            # Non raggruppare se una cartella è vuota di video
            if not e1["video_files"] or not e2["video_files"]:
                continue

            is_match = False
            # Match 1: Stesso TMDb ID
            if e1["tmdb_id"] and e2["tmdb_id"] and e1["tmdb_id"] == e2["tmdb_id"]:
                is_match = True
            # Match 2: Stesso Anno e Titoli Compatibili
            elif e1["clean_ascii"] and e2["clean_ascii"] and e1["year"] and e2["year"] and e1["year"] == e2["year"]:
                t1 = e1["clean_ascii"]
                t2 = e2["clean_ascii"]
                if t1 == t2 and len(t1) >= 3:
                    is_match = True
                else:
                    w1 = t1.split()
                    w2 = t2.split()
                    if w1 and w2 and w1[0] == w2[0] and len(w1[0]) >= 4:
                        if t1.startswith(t2) or t2.startswith(t1):
                            is_match = True
            if is_match:
                union(e1["name"], e2["name"])

    clusters = defaultdict(list)
    for entry in folder_entries:
        clusters[find(entry["name"])].append(entry)

    merge_plans = []

    for root_name, group in clusters.items():
        # Filtra video validi
        all_videos = []
        is_cross_folder = len(group) > 1

        # Se è intra-folder (singola cartella) ed è solo multi-parte (CD1/CD2), salta!
        if not is_cross_folder and group[0]["is_multipart_only"]:
            continue

        for e in group:
            all_videos.extend(e["video_files"])

        # Candidato a merge se ci sono più video indipendenti nel gruppo
        if len(all_videos) > 1:
            # 1. Seleziona la cartella Master canonica
            # Priorità: cartella con [tmdbid-XXX] o {tmdb-XXX}, altrimenti prima cartella
            canonical_folder_entry = group[0]
            for e in group:
                if e["tmdb_id"] and ("tmdbid" in e["name"].lower() or "tmdb" in e["name"].lower()):
                    canonical_folder_entry = e
                    break

            master_dir = canonical_folder_entry["path"]
            master_tmdb = canonical_folder_entry["tmdb_id"]
            master_year = canonical_folder_entry["year"] or group[0]["year"]
            master_title = canonical_folder_entry["display_title"] or group[0]["display_title"]

            # Prefisso comune obbligatorio per Jellyfin multi-versioning:
            # Per la regola ufficiale Jellyfin, il prefisso del file DEVE coincidere carattere per carattere
            # con il nome esatto della cartella padre.
            base_prefix = master_dir.name

            plan_items = []
            used_labels = set()

            for vid in all_videos:
                vid_path = Path(vid)
                info = analyze_video_info(vid, vid_path.parent.name)

                # Etichetta versione: es. [Remux 4K ITA-ENG] o [1080p ITA]
                label_parts = []
                if info["source"] and info["source"] != "Rip":
                    label_parts.append(info["source"])
                if info["res"] and info["res"] != "N/D":
                    label_parts.append(info["res"])
                if info["audio_summary"] and info["audio_summary"] != "N/D":
                    label_parts.append(info["audio_summary"])

                label = " ".join(label_parts) if label_parts else "Default"

                # Gestione duplicati di etichetta
                final_label = label
                counter = 2
                while final_label in used_labels:
                    final_label = f"{label} v{counter}"
                    counter += 1
                used_labels.add(final_label)

                new_filename = f"{base_prefix} - [{final_label}]{vid_path.suffix.lower()}"
                target_path = master_dir / new_filename

                is_same_file = (vid_path == target_path)
                is_same_folder = (vid_path.parent == master_dir)

                action_type = "NOOP"
                if not is_same_file:
                    action_type = "RENAME" if is_same_folder else "MOVE_AND_RENAME"

                plan_items.append({
                    "src_path": str(vid_path),
                    "target_path": str(target_path),
                    "src_folder": str(vid_path.parent),
                    "target_folder": str(master_dir),
                    "action": action_type,
                    "label": final_label,
                    "size_gb": os.path.getsize(vid) / (1024**3)
                })

            # Cartelle secondarie da rimuovere se svuotate
            cleanup_dirs = []
            for e in group:
                if e["path"] != master_dir:
                    cleanup_dirs.append(str(e["path"]))

            merge_plans.append({
                "movie_name": f"{master_title} ({master_year})",
                "master_dir": str(master_dir),
                "is_cross_folder": is_cross_folder,
                "items": plan_items,
                "cleanup_dirs": cleanup_dirs
            })

    return merge_plans

def parse_selection(sel_str, max_val):
    """Interpreta stringhe di selezione come '1, 3-5', 'all', 'q'."""
    s = sel_str.strip().lower()
    if not s or s in ['q', 'quit', 'exit', 'none', 'no']:
        return set()
    if s in ['all', 'tutti', '*']:
        return set(range(1, max_val + 1))

    selected = set()
    parts = re.split(r'[,;\s]+', s)
    for p in parts:
        if not p: continue
        if '-' in p:
            sub = p.split('-')
            if len(sub) == 2 and sub[0].isdigit() and sub[1].isdigit():
                start, end = int(sub[0]), int(sub[1])
                for idx in range(start, end + 1):
                    if 1 <= idx <= max_val: selected.add(idx)
        elif p.isdigit():
            idx = int(p)
            if 1 <= idx <= max_val: selected.add(idx)
    return selected

def main():
    parser = argparse.ArgumentParser(description="Unifica versioni multiple di film per Jellyfin / FileBot")
    parser.add_argument("--select", type=str, default="", help="Numeri dei film da unificare (es. '1,3,5' o 'all')")
    parser.add_argument("--all", action="store_true", help="Seleziona tutti i film candidati trovati")
    parser.add_argument("--apply", action="store_true", help="Applica effettivamente le modifiche (default: dry-run)")
    parser.add_argument("--dry-run", action="store_true", default=False, help="Forza simulazione senza applicare modifiche")
    args = parser.parse_args()

    base_dir = Path(MEDIA_DIR)
    if not base_dir.exists():
        print(f"❌ Errore: {MEDIA_DIR} non esiste.")
        sys.exit(1)

    print("==================================================================")
    print("  🎬 Scansione Versioni Multiple Film per Jellyfin (Scenario A)   ")
    print("==================================================================\n")

    plans = plan_merges(base_dir)

    if not plans:
        print("✅ Nessuna versione multipla da unificare trovata nella libreria.")
        return

    total_candidates = len(plans)
    print(f"🎯 Trovati {total_candidates} film con versioni multiple da unificare:\n")

    for idx, plan in enumerate(plans, start=1):
        type_str = "Accorpamento Cartelle Diverse" if plan["is_cross_folder"] else "Stessa Cartella"
        print(f"[{idx}] 🎬 {plan['movie_name']} ({type_str})")
        print(f"    Cartella Master: {os.path.basename(plan['master_dir'])}")
        for it in plan["items"]:
            print(f"    - Versione: [{it['label']}] ({it['size_gb']:.2f} GB) — {os.path.basename(it['src_path'])}")
        print()

    # Determina la selezione dei film
    selected_indices = set()

    if args.all:
        selected_indices = set(range(1, total_candidates + 1))
    elif args.select:
        selected_indices = parse_selection(args.select, total_candidates)
    else:
        # Modalità Interattiva da Terminale
        if sys.stdin.isatty():
            try:
                print("------------------------------------------------------------------")
                prompt_text = f"👉 Inserisci i numeri dei film da unificare (es. '1, 3-4', 'all', 'q' per uscire): "
                user_input = input(prompt_text)
                selected_indices = parse_selection(user_input, total_candidates)
            except (KeyboardInterrupt, EOFError):
                print("\nOperazione annullata.")
                sys.exit(0)
        else:
            # Stdin non interattivo e nessun argomento di selezione passato: mostra anteprima completa
            print("ℹ️  Esecuzione non interattiva: per selezionare film specifici usa --select 1,2 o --all.")
            selected_indices = set(range(1, total_candidates + 1))

    if not selected_indices:
        print("🛑 Nessun film selezionato. Nessuna modifica eseguita.")
        return

    # Filtra i piani in base alla selezione
    selected_plans = [plans[i - 1] for i in sorted(selected_indices)]
    print("==================================================================")
    print(f"📋 RIEPILOGO AZIONI PER I {len(selected_plans)} FILM SELEZIONATI:")
    print("==================================================================")

    for plan in selected_plans:
        print(f"\n🎬 {plan['movie_name']}:")
        for it in plan["items"]:
            action_tag = "INVARIATO" if it["action"] == "NOOP" else ("SPOSTA E RINOMINA" if it["action"] == "MOVE_AND_RENAME" else "RINOMINA")
            print(f"   🔹 [{it['label']}] ({it['size_gb']:.2f} GB) -> {action_tag}")
            print(f"      Da: {it['src_path']}")
            print(f"      A : {it['target_path']}")
        if plan["cleanup_dirs"]:
            print(f"   🗑️ Cartelle secondarie da eliminare dopo spostamento:")
            for d in plan["cleanup_dirs"]:
                print(f"      - {d}")

    # Determina se applicare o dry-run
    execute_now = False
    if args.apply and not args.dry_run:
        execute_now = True
    elif sys.stdin.isatty() and not args.dry_run:
        try:
            confirm = input(f"\n🚀 Vuoi procedere con l'unificazione reale di questi {len(selected_plans)} film? [s/N]: ")
            if confirm.strip().lower() in ['s', 'si', 'y', 'yes']:
                execute_now = True
        except (KeyboardInterrupt, EOFError):
            execute_now = False

    if not execute_now:
        print("\n==================================================================")
        print("ℹ️  SIMULAZIONE COMPLETATA (DRY-RUN) — Nessun file è stato modificato.")
        print("Per applicare realmente, usa --apply oppure conferma al prompt.")
        print("==================================================================")
        return

    print("\n==================================================================")
    print("🚀 ESECUZIONE ATTIVA: Applicazione modifiche in corso...")
    print("==================================================================")

    for plan in selected_plans:
        print(f"\n▶ Elaborazione: {plan['movie_name']}...")
        for it in plan["items"]:
            if it["action"] in ["RENAME", "MOVE_AND_RENAME"]:
                src = it["src_path"]
                dst = it["target_path"]
                print(f"  [MV] {os.path.basename(src)} -> {os.path.basename(dst)}")
                os.rename(src, dst)

        # Pulizia cartelle secondarie se vuote di altri video
        for d in plan["cleanup_dirs"]:
            remaining_videos = []
            for r, dirs, files in os.walk(d):
                for f in files:
                    if is_video_file(f): remaining_videos.append(f)
            if not remaining_videos:
                print(f"  [RMDIR] Rimozione cartella secondaria vuota: {os.path.basename(d)}")
                shutil.rmtree(d, ignore_errors=True)
            else:
                print(f"  ⚠️ [SKIP] Cartella {os.path.basename(d)} contiene ancora video: {remaining_videos}")

    print("\n==================================================================")
    print("✅ Tutte le operazioni di unificazione selezionate sono completate!")
    print("==================================================================")

if __name__ == "__main__":
    main()

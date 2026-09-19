#!/usr/bin/env python3
# Script di unificazione versioni multiple film per Jellyfin / FileBot (Scenario A)
# Supporta:
# 1. Esclusione strutture disco raw (BDMV, VIDEO_TS) e film multi-parte (CD1/CD2)
# 2. Riconoscimento riedizioni / edizioni anniversario con anni differenti (es. 25th Anniv)
# 3. Analisi flussi con ffprobe (risoluzione, codec, tracce audio) e labeling dettagliato
# 4. Spostamento, rinomina canonica file video e sottotitoli associati (.srt)
# 5. Rilevamento e rimozione automatica artwork corrotti / bassa risoluzione (< 50KB)
# 6. Webhook automatico di refresh libreria Jellyfin via API REST

import os
import re
import sys
import json
import shutil
import argparse
import unicodedata
import subprocess
import urllib.request
import urllib.error
from pathlib import Path
from collections import defaultdict

MEDIA_DIR = os.environ.get("MEDIA_DIR", "/mnt/oliraid/arrdata/media/movies")
JELLYFIN_URL = os.environ.get("JELLYFIN_URL", "http://10.10.10.50:8096")
JELLYFIN_TOKEN = os.environ.get("JELLYFIN_TOKEN", "7c80240c7a9b4326a8690ce140265a14")

EDITION_PATTERNS = [
    (r'\b(\d+)(?:th|°)?\s*anniversary(?:\s*edition)?\b', r'\1th Anniv'),
    (r'\banniversary\s+edition\b', 'Anniv'),
    (r'\banniversary\b', 'Anniv'),
    (r'\bdirector\'?s\s+cut\b', "Director's Cut"),
    (r'\bextended(?:\s*cut|\s*edition)?\b', 'Extended'),
    (r'\btheatrical(?:\s*cut|\s*edition)?\b', 'Theatrical'),
    (r'\bultimate(?:\s*cut|\s*edition)?\b', 'Ultimate'),
    (r'\bcollector\'?s(?:\s*edition)?\b', "Collector's"),
    (r'\bremastered\b', 'Remastered'),
    (r'\brestored\b', 'Restored'),
    (r'\bcriterion\b', 'Criterion'),
    (r'\bimax\b', 'IMAX'),
    (r'\bunrated\b', 'Unrated'),
]

def get_ffprobe_bin():
    if os.path.exists("/mnt/oliraid/bin/ffprobe"):
        return "/mnt/oliraid/bin/ffprobe"
    return shutil.which("ffprobe")

def is_video_file(filename):
    exts = ['.mkv', '.mp4', '.avi', '.iso', '.m4v', '.ts', '.m2ts']
    return any(filename.lower().endswith(ext) for ext in exts)

def is_subtitle_file(filename):
    exts = ['.srt', '.sub', '.idx', '.vtt', '.ass', '.smi']
    return any(filename.lower().endswith(ext) for ext in exts)

def is_multipart_file(filename):
    return bool(re.search(r'[-_ .](cd|part|disc|pt)\s*0*([1-9]\d*)', filename, re.IGNORECASE))

def detect_edition(text):
    for pat, label_template in EDITION_PATTERNS:
        m = re.search(pat, text, re.IGNORECASE)
        if m:
            if r'\1' in label_template:
                return re.sub(pat, label_template, m.group(0), flags=re.IGNORECASE)
            return label_template
    return None

def extract_movie_identity(folder_name):
    tmdb_match = re.search(r'(?:tmdbid|tmdb)[-_](\d+)', folder_name, re.IGNORECASE)
    tmdb_id = tmdb_match.group(1) if tmdb_match else None

    year_match = re.search(r'[\(\[\s\.-](19\d{2}|20\d{2})[\)\]\s\.-]?', folder_name)
    year = year_match.group(1) if year_match else None

    edition = detect_edition(folder_name)

    clean = re.sub(r'\[.*?\]|\{.*?\}', '', folder_name)
    clean = re.sub(r'-\s*\(\d{4}\)\s*-[^-]+$', '', clean)
    clean = re.sub(r'-\s*[A-Z][a-z]+\s+[A-Z][a-z]+$', '', clean)
    clean = re.sub(r'(?i)\b((\d+th|\d+)?\s*(anniversary|edition|remastered|restored|director|criterion|imax|theatrical|extended|cut)|1080p|720p|2160p|4k|bluray|blu-ray|web-dl|webdl|webrip|remux|bdrip|hdr|x264|x265|hevc|dvdrip|ac3|dts|ita|eng|french|spanish|multi)\b.*', '', clean)

    if year:
        clean = re.split(rf'[\(\[\s\.-]{year}', clean)[0]

    clean_ascii = unicodedata.normalize('NFKD', clean).encode('ASCII', 'ignore').decode('utf-8')
    clean_ascii = re.sub(r'[\.\-_\(\)]+', ' ', clean_ascii).strip().lower()
    clean_ascii = re.sub(r'^(the|a|an|il|la|lo|i|gli|le|un|uno|una)\s+', '', clean_ascii).strip()
    clean_ascii = re.sub(r'\s+', ' ', clean_ascii).strip()

    display_title = re.sub(r'\[.*?\]|\{.*?\}', '', folder_name)
    display_title = re.sub(r'-\s*\(\d{4}\)\s*-[^-]+$', '', display_title)
    display_title = re.sub(r'(?i)\b((\d+th|\d+)?\s*(anniversary|edition|remastered|restored)|director)\b.*', '', display_title)
    if year:
        display_title = re.split(rf'[\(\[\s\.-]{year}', display_title)[0]
    display_title = display_title.strip(' .-_')
    display_title = re.sub(r'\s+', ' ', display_title).strip()

    return tmdb_id, clean_ascii, display_title, year, edition

def analyze_video_info(video_file, folder_name=""):
    if not video_file or not os.path.exists(video_file):
        return {"res": "Sconosciuta", "codec": "N/D", "source": "Rip", "audio_summary": "N/D", "edition": None}

    file_name = os.path.basename(video_file)
    f_lower = file_name.lower()

    edition = detect_edition(file_name) or detect_edition(folder_name)

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
        return {"res": "N/D", "codec": "N/D", "source": source, "audio_summary": "N/D", "edition": edition}

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
            "audio_summary": audio_summary,
            "edition": edition
        }
    except Exception:
        return {"res": "N/D", "codec": "N/D", "source": source, "audio_summary": "N/D", "edition": edition}

def find_companion_subtitles(video_path):
    video_p = Path(video_path)
    parent = video_p.parent
    stem = video_p.stem
    subs = []

    if not parent.exists():
        return subs

    for f in parent.iterdir():
        if not f.is_file() or not is_subtitle_file(f.name):
            continue
        if f.name.startswith(stem):
            sub_suffix = f.name[len(stem):]
            subs.append((f, sub_suffix))
    return subs

def find_corrupted_artwork(folder_path, threshold_kb=50):
    corrupted = []
    p = Path(folder_path)
    if not p.exists():
        return corrupted

    image_exts = ['.jpg', '.jpeg', '.png', '.webp']
    for f in p.iterdir():
        if f.is_file() and any(f.name.lower().endswith(ext) for ext in image_exts):
            size_kb = f.stat().st_size / 1024
            if size_kb < threshold_kb:
                corrupted.append({
                    "path": str(f),
                    "filename": f.name,
                    "size_kb": size_kb
                })
    return corrupted

def plan_merges(base_dir):
    folder_entries = []
    parent = {}

    for item in sorted(base_dir.iterdir()):
        if not item.is_dir(): continue
        tmdb_id, clean_ascii, display_title, year, edition = extract_movie_identity(item.name)

        vids = []
        for root, dirs, files in os.walk(item):
            rparts = [p.upper() for p in Path(root).parts]
            if any(p in ['EXTRAS', '.TRICKPLAY', '.ACTORS', 'BDMV', 'CERTIFICATE', 'VIDEO_TS', 'AUDIO_TS', 'STREAM', 'CLIPINF', 'PLAYLIST', 'BACKUP'] for p in rparts):
                continue
            for f in files:
                if is_video_file(f) and not f.lower().endswith(('-trailer.mp4', '-trailer.mkv')):
                    vids.append(os.path.join(root, f))

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
            "edition": edition,
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

            if not e1["video_files"] or not e2["video_files"]:
                continue

            is_match = False
            if e1["tmdb_id"] and e2["tmdb_id"] and e1["tmdb_id"] == e2["tmdb_id"]:
                is_match = True
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
            elif e1["clean_ascii"] and e2["clean_ascii"] and (e1["clean_ascii"] == e2["clean_ascii"]):
                if e1["edition"] or e2["edition"]:
                    is_match = True

            if is_match:
                union(e1["name"], e2["name"])

    clusters = defaultdict(list)
    for entry in folder_entries:
        clusters[find(entry["name"])].append(entry)

    merge_plans = []

    for root_name, group in clusters.items():
        all_videos = []
        is_cross_folder = len(group) > 1

        if not is_cross_folder and group[0]["is_multipart_only"]:
            continue

        for e in group:
            all_videos.extend(e["video_files"])

        if len(all_videos) > 1:
            def sort_key(e):
                has_tmdb = 0 if e["tmdb_id"] else 1
                yr = int(e["year"]) if (e["year"] and e["year"].isdigit()) else 9999
                has_edition = 1 if e["edition"] else 0
                return (has_tmdb, has_edition, yr)

            sorted_group = sorted(group, key=sort_key)
            canonical_folder_entry = sorted_group[0]

            master_dir = canonical_folder_entry["path"]
            master_tmdb = canonical_folder_entry["tmdb_id"]
            master_year = canonical_folder_entry["year"] or group[0]["year"]
            master_title = canonical_folder_entry["display_title"] or group[0]["display_title"]

            base_prefix = master_dir.name

            plan_items = []
            used_labels = set()

            for vid in all_videos:
                vid_path = Path(vid)
                info = analyze_video_info(vid, vid_path.parent.name)

                label_parts = []
                if info["edition"]:
                    label_parts.append(info["edition"])
                if info["source"] and info["source"] != "Rip":
                    label_parts.append(info["source"])
                if info["res"] and info["res"] != "N/D":
                    label_parts.append(info["res"])
                if info["audio_summary"] and info["audio_summary"] != "N/D":
                    label_parts.append(info["audio_summary"])

                label = " ".join(label_parts) if label_parts else "Default"

                final_label = label
                counter = 2
                while final_label in used_labels:
                    final_label = f"{label} v{counter}"
                    counter += 1
                used_labels.add(final_label)

                target_stem = f"{base_prefix} - [{final_label}]"
                new_filename = f"{target_stem}{vid_path.suffix.lower()}"
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
                    "is_subtitle": False,
                    "size_gb": os.path.getsize(vid) / (1024**3)
                })

                companion_subs = find_companion_subtitles(vid)
                for sub_file, sub_suffix in companion_subs:
                    target_sub = master_dir / f"{target_stem}{sub_suffix}"
                    sub_action = "NOOP"
                    if sub_file != target_sub:
                        sub_action = "RENAME" if sub_file.parent == master_dir else "MOVE_AND_RENAME"
                    plan_items.append({
                        "src_path": str(sub_file),
                        "target_path": str(target_sub),
                        "src_folder": str(sub_file.parent),
                        "target_folder": str(master_dir),
                        "action": sub_action,
                        "label": f"Sub {sub_suffix}",
                        "is_subtitle": True,
                        "size_gb": sub_file.stat().st_size / (1024**3)
                    })

            artwork_purges = []
            for e in group:
                corrupted = find_corrupted_artwork(e["path"], threshold_kb=50)
                for c in corrupted:
                    artwork_purges.append({
                        "src_path": c["path"],
                        "filename": c["filename"],
                        "size_kb": c["size_kb"],
                        "folder": e["name"]
                    })

            cleanup_dirs = []
            for e in group:
                if e["path"] != master_dir:
                    cleanup_dirs.append(str(e["path"]))

            merge_plans.append({
                "movie_name": f"{master_title} ({master_year})",
                "master_dir": str(master_dir),
                "is_cross_folder": is_cross_folder,
                "items": plan_items,
                "cleanup_dirs": cleanup_dirs,
                "artwork_purges": artwork_purges
            })

    return merge_plans

def trigger_jellyfin_refresh(base_url, token):
    refresh_url = f"{base_url.rstrip('/')}/Library/Refresh"
    print(f"\n📡 Invio notifica di refresh libreria a Jellyfin ({refresh_url})...")
    req = urllib.request.Request(
        refresh_url,
        data=b"",
        headers={
            "Authorization": f'MediaBrowser Token="{token}"',
            "Content-Length": "0"
        },
        method="POST"
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            if resp.status in [200, 204]:
                print("   ✅ Refresh Jellyfin avviato con successo!")
                return True
            else:
                print(f"   ⚠️ Risposta Jellyfin: HTTP {resp.status}")
                return False
    except urllib.error.URLError as e:
        print(f"   ❌ Errore di connessione a Jellyfin: {e}")
        return False

def parse_selection(sel_str, max_val):
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
    parser.add_argument("--no-refresh", action="store_true", help="Disabilita il refresh automatico di Jellyfin")
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
            if not it["is_subtitle"]:
                print(f"    - Versione: [{it['label']}] ({it['size_gb']:.2f} GB) — {os.path.basename(it['src_path'])}")
            else:
                print(f"      ↳ Sub: {os.path.basename(it['src_path'])}")
        if plan["artwork_purges"]:
            for art in plan["artwork_purges"]:
                print(f"    - ⚠️ Artwork microscopico: {art['filename']} ({art['size_kb']:.1f} KB < 50 KB)")
        print()

    selected_indices = set()
    if args.all:
        selected_indices = set(range(1, total_candidates + 1))
    elif args.select:
        selected_indices = parse_selection(args.select, total_candidates)
    else:
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
            print("ℹ️  Esecuzione non interattiva: per selezionare film specifici usa --select 1,2 o --all.")
            selected_indices = set(range(1, total_candidates + 1))

    if not selected_indices:
        print("🛑 Nessun film selezionato. Nessuna modifica eseguita.")
        return

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
        if plan["artwork_purges"]:
            print(f"   🗑️ Bonifica artwork corrotti / microscopici (< 50KB):")
            for art in plan["artwork_purges"]:
                print(f"      - RIMOZIONE: {art['filename']} ({art['size_kb']:.1f} KB) in {art['folder']}")
        if plan["cleanup_dirs"]:
            print(f"   🗑️ Cartelle secondarie da eliminare dopo spostamento:")
            for d in plan["cleanup_dirs"]:
                print(f"      - {d}")

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

        for art in plan["artwork_purges"]:
            art_p = art["src_path"]
            if os.path.exists(art_p):
                print(f"  [RM_ART] Rimozione artwork corrotto: {art['filename']} ({art['size_kb']:.1f} KB)")
                os.remove(art_p)

        for d in plan["cleanup_dirs"]:
            remaining_videos = []
            for r, dirs, files in os.walk(d):
                for f in files:
                    if is_video_file(f): remaining_videos.append(f)
            if not remaining_videos:
                print(f"  [RMDIR] Rimozione cartella secondaria svuotata: {os.path.basename(d)}")
                shutil.rmtree(d, ignore_errors=True)
            else:
                print(f"  ⚠️ [SKIP] Cartella {os.path.basename(d)} contiene ancora video: {remaining_videos}")

    print("\n==================================================================")
    print("✅ Tutte le operazioni di unificazione selezionate sono completate!")
    print("==================================================================")

    if not args.no_refresh and JELLYFIN_URL and JELLYFIN_TOKEN:
        trigger_jellyfin_refresh(JELLYFIN_URL, JELLYFIN_TOKEN)

if __name__ == "__main__":
    main()

#!/usr/bin/env python3
# Script di audit libreria film su TrueNAS (ricerca anomalie, duplicati e multi-parte)

import os
import re
import json
import shutil
import unicodedata
import subprocess
from pathlib import Path
from collections import defaultdict, Counter

MEDIA_DIR = os.environ.get("MEDIA_DIR", "/mnt/oliraid/arrdata/media/movies")

def get_ffprobe_bin():
    if os.path.exists("/mnt/oliraid/bin/ffprobe"):
        return "/mnt/oliraid/bin/ffprobe"
    return shutil.which("ffprobe")

def is_video_file(filename):
    exts = ['.mkv', '.mp4', '.avi', '.iso', '.m4v', '.ts', '.m2ts']
    return any(filename.lower().endswith(ext) for ext in exts)

def extract_movie_identity(folder_name):
    # 1. TMDb ID
    tmdb_match = re.search(r'(?:tmdbid|tmdb)[-_](\d+)', folder_name, re.IGNORECASE)
    tmdb_id = tmdb_match.group(1) if tmdb_match else None

    # 2. Anno
    year_match = re.search(r'[\(\[\s\.-](19\d{2}|20\d{2})[\)\]\s\.-]?', folder_name)
    year = year_match.group(1) if year_match else None

    # 3. Titolo normalizzato
    clean = re.sub(r'\[.*?\]|\{.*?\}', '', folder_name)
    clean = re.sub(r'(?i)\b(1080p|720p|2160p|4k|bluray|web-dl|webrip|remux|bdrip|hdr|extended|x264|x265|hevc|dvdrip|ac3|dts|ita|eng|french|spanish|multi)\b.*', '', clean)
    if year:
        clean = re.split(rf'[\(\[\s\.-]{year}', clean)[0]
    # Rimuovi accenti (es: Léon -> Leon)
    clean = unicodedata.normalize('NFKD', clean).encode('ASCII', 'ignore').decode('utf-8')
    clean = re.sub(r'[\.\-_\(\)]+', ' ', clean).strip().lower()
    clean = re.sub(r'^(the|a|an|il|la|lo|i|gli|le|un|uno|una)\s+', '', clean).strip()

    return tmdb_id, clean, year

def analyze_media_tracks(video_file, folder_name=""):
    if not video_file or not os.path.exists(video_file):
        return {
            "error": "File non trovato",
            "has_italian": False,
            "italian_detail": "File non presente",
            "resolution": "N/D",
            "codec": "N/D",
            "audio_str": "N/D",
            "sub_str": "N/D"
        }

    file_name = os.path.basename(video_file)
    file_size_gb = os.path.getsize(video_file) / (1024 ** 3)

    ffprobe = get_ffprobe_bin()
    if not ffprobe:
        # Fallback euristico se ffprobe manca
        has_ita = bool(re.search(r'\b(ita|italian|italiano)\b', f"{file_name} {folder_name}", re.IGNORECASE))
        return {
            "file_name": file_name,
            "file_size_gb": file_size_gb,
            "has_italian": has_ita,
            "italian_detail": "Rilevato dal nome file (ffprobe assente)" if has_ita else "Non rilevato nel nome file",
            "resolution": "N/D",
            "codec": "N/D",
            "audio_str": "ffprobe assente",
            "sub_str": "N/D"
        }

    cmd = [ffprobe, "-v", "quiet", "-show_format", "-show_streams", "-of", "json", video_file]
    try:
        result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=20)
        data = json.loads(result.stdout)

        duration_str = "N/D"
        try:
            dur = float(data.get('format', {}).get('duration', 0))
            if dur > 0:
                hours = int(dur // 3600)
                mins = int((dur % 3600) // 60)
                duration_str = f"{hours}h {mins}m" if hours > 0 else f"{mins}m"
        except:
            pass

        audio_langs = []
        sub_langs = []
        has_italian = False
        italian_details = []
        video_res = "Sconosciuta"
        video_codec = "Sconosciuto"

        for stream in data.get('streams', []):
            codec_type = stream.get('codec_type')
            codec_name = stream.get('codec_name', '')
            tags = stream.get('tags', {})
            lang = tags.get('language', 'und').lower()
            title = tags.get('title', '').lower()

            if codec_type == 'video' and video_res == "Sconosciuta":
                video_codec = codec_name
                width = stream.get('width', 0)
                height = stream.get('height', 0)
                if width >= 3800 or height >= 2100:
                    video_res = "2160p (4K UHD)"
                elif width >= 1900 or height >= 1000:
                    video_res = "1080p (Full HD)"
                elif width >= 1200 or height >= 700:
                    video_res = "720p (HD)"
                elif height >= 500 or width >= 700:
                    video_res = "576p/480p (SD/DVD)"
                else:
                    video_res = f"{width}x{height}" if width else "N/D"

            elif codec_type == 'audio':
                channels = stream.get('channel_layout', '')
                audio_tag = f"{codec_name} {channels}".strip()
                label = f"{lang} ({audio_tag})" if audio_tag else lang

                if 'ita' in lang or 'italian' in title or 'ita' in title:
                    has_italian = True
                    detail = f"{codec_name} {channels} [{title or lang}]".strip()
                    italian_details.append(detail)
                    label = f"🇮🇹 {label}"

                audio_langs.append(label)

            elif codec_type == 'subtitle':
                sub_langs.append(lang)
                if 'ita' in lang:
                    has_italian_sub = True

        # Fallback euristico su nome file/cartella per ISO DVD o rip privi di tag lingua interno
        if not has_italian:
            if re.search(r'\b(ita|italian|italiano|iTA-ENG)\b', f"{file_name} {folder_name}", re.IGNORECASE):
                has_italian = True
                italian_details.append("Rilevato dal titolo della release/file (tag und in traccia)")

        return {
            "file_name": file_name,
            "file_size_gb": file_size_gb,
            "duration": duration_str,
            "has_italian": has_italian,
            "italian_detail": ", ".join(italian_details) if italian_details else "Nessuna traccia italiana trovata",
            "resolution": video_res,
            "codec": video_codec,
            "audio_str": ", ".join(audio_langs) if audio_langs else "Nessuna",
            "sub_str": ", ".join(sub_langs) if sub_langs else "Nessuno"
        }
    except Exception as e:
        return {
            "error": str(e),
            "file_name": file_name,
            "file_size_gb": file_size_gb,
            "has_italian": False,
            "italian_detail": "Errore lettura ffprobe",
            "resolution": "N/D",
            "codec": "N/D",
            "audio_str": "Errore",
            "sub_str": "Errore"
        }

def get_main_video(folder_path):
    video_exts = ['.mkv', '.mp4', '.avi', '.iso', '.m4v', '.ts', '.m2ts']
    largest_file = None
    max_size = 0
    for root, dirs, files in os.walk(folder_path):
        for f in files:
            if any(f.lower().endswith(ext) for ext in video_exts):
                full_path = os.path.join(root, f)
                try:
                    size = os.path.getsize(full_path)
                    if size > max_size:
                        max_size = size
                        largest_file = full_path
                except: pass
    return largest_file

def main():
    base_dir = Path(MEDIA_DIR)
    if not base_dir.exists():
        print(f"Errore: {MEDIA_DIR} non esiste.")
        return

    cat_nfo = defaultdict(list)
    cat_videots = defaultdict(list)
    cat_multipart = {}

    movie_identities = defaultdict(list)

    for item in sorted(base_dir.iterdir()):
        if not item.is_dir(): continue

        folder_name = item.name
        folder_path = item

        has_iso = False
        has_video_ts = False
        video_files = []
        nfo_files = []
        cd_files = []

        for root, dirs, files in os.walk(folder_path):
            root_path_obj = Path(root)
            if root_path_obj.name.lower() in ['extras', 'featurettes', 'behind the scenes', 'deleted scenes', 'interviews', 'scenes', 'shorts', 'trailers', 'other']:
                continue

            for d in dirs:
                if d.upper() == 'VIDEO_TS':
                    has_video_ts = True

            for f in files:
                f_lower = f.lower()
                if f_lower.endswith('.iso'):
                    has_iso = True
                    video_files.append(os.path.join(root, f))
                elif is_video_file(f):
                    if not f_lower.endswith('-trailer.mp4') and not f_lower.endswith('-trailer.mkv'):
                        video_files.append(os.path.join(root, f))
                        if re.search(r'(cd[1-9]|pt[1-9]|part[1-9]|atto[1-9])', f_lower):
                            cd_files.append(os.path.join(root, f))
                elif f_lower.endswith('.nfo'):
                    nfo_files.append(os.path.join(root, f))

        # 1. Cartelle con problemi di .nfo
        if len(nfo_files) > 1:
            cat_nfo[folder_name].append(f"Trovati {len(nfo_files)} file .nfo")

        # 3. Cartelle con VIDEO_TS o .iso sdoppiati
        if has_video_ts:
            if has_iso:
                cat_videots[folder_name].append("Cartella VIDEO_TS annidata insieme a un file .iso")
            else:
                cat_videots[folder_name].append("Cartella VIDEO_TS non compressa")

        # 4. Cartelle Multi-parte (CD1/CD2 o Atti sparsi) o File Video Multipli
        candidate_files = []
        is_cd_naming = False
        if cd_files:
            candidate_files = cd_files
            is_cd_naming = True
        elif len(video_files) > 1 and not has_video_ts:
            candidate_files = video_files
            is_cd_naming = False

        if candidate_files:
            cd_info = []
            sizes = []
            for f in sorted(candidate_files):
                sz = 0
                try:
                    sz = os.path.getsize(f)
                except:
                    pass
                sizes.append(sz)
                a = analyze_media_tracks(f, folder_name)
                cd_info.append({
                    "path": f,
                    "size_bytes": sz,
                    "analysis": a
                })

            # Controllo Cloni Identici al byte (Caso 2)
            is_clone = False
            wasted_bytes = 0
            size_counts = Counter(sizes)
            for sz, cnt in size_counts.items():
                if cnt > 1 and sz > 100 * 1024 * 1024:
                    is_clone = True
                    wasted_bytes += sz * (cnt - 1)

            cat_multipart[folder_name] = {
                "folder": folder_name,
                "is_clone": is_clone,
                "is_cd_naming": is_cd_naming,
                "wasted_gb": wasted_bytes / (1024**3),
                "files": cd_info
            }

    # =========================================================
    # RAGGRUPPAMENTO DUPLICATI CON UNION-FIND (TMDb ID o Titolo+Anno)
    # =========================================================
    folder_entries = []
    parent = {}

    for item in sorted(base_dir.iterdir()):
        if not item.is_dir(): continue
        tmdb_id, clean_title, year = extract_movie_identity(item.name)
        folder_entries.append({
            "path": item,
            "name": item.name,
            "tmdb_id": tmdb_id,
            "clean_title": clean_title,
            "year": year
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

            is_match = False
            # Match 1: Stesso TMDb ID
            if e1["tmdb_id"] and e2["tmdb_id"] and e1["tmdb_id"] == e2["tmdb_id"]:
                is_match = True
            # Match 2: Titoli compatibili e stesso Anno
            elif e1["clean_title"] and e2["clean_title"] and e1["year"] and e2["year"] and e1["year"] == e2["year"]:
                t1 = e1["clean_title"]
                t2 = e2["clean_title"]
                if t1 == t2 and len(t1) >= 3:
                    is_match = True
                else:
                    # Match per prefisso o alias (es. "leon the professional" vs "leon", "volver tornare" vs "volver")
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

    cat_duplicati = []
    for root_name, group in clusters.items():
        if len(group) > 1:
            group_info = []
            for entry in group:
                main_vid = get_main_video(entry["path"])
                analysis = analyze_media_tracks(main_vid, entry["name"])
                group_info.append({
                    "folder": entry["name"],
                    "path": str(entry["path"]),
                    "analysis": analysis
                })
            cat_duplicati.append(group_info)

    # =========================================================
    # STAMPA REPORT CON I 4 PARAGRAFI
    # =========================================================

    print("=========================================================")
    print("CARTELLE PROBLEMI DI .NFO")
    print("=========================================================\n")
    if not cat_nfo:
        print("Nessuna anomalia.\n")
    else:
        for k, v in sorted(cat_nfo.items()):
            print(f"[{k}]")
            for msg in v: print(f"  - {msg}")
            print()

    print("=========================================================")
    print("CARTELLE DIVERSE CHE CONTENGONO LO STESSO FILM (Duplicati)")
    print("=========================================================\n")
    if not cat_duplicati:
        print("Nessun film duplicato trovato in cartelle diverse.\n")
    else:
        for idx, group in enumerate(cat_duplicati, start=1):
            print(f"--- GRUPPO DUPLICATO #{idx} ---")
            for item in group:
                a = item["analysis"]
                print(f"📁 Cartella: [{item['folder']}]")
                if "error" in a:
                    print(f"   ❌ File: {a.get('error')}")
                else:
                    ita_status = "SÌ ✅" if a["has_italian"] else "NO ❌"
                    print(f"   🎬 File Video   : {a['file_name']} ({a['file_size_gb']:.2f} GB)")
                    print(f"   📺 Formato      : {a['resolution']} [{a['codec']}]")
                    print(f"   🇮🇹 AUDIO ITALIA : {ita_status} ({a['italian_detail']})")
                    print(f"   🔊 Tutte Tracce : {a['audio_str']}")
                    print(f"   💬 Sottotitoli  : {a['sub_str']}")
                print()
            print("-" * 50 + "\n")

    print("=========================================================")
    print("CARTELLE CON VIDEO_TS O .ISO SDOPPIATI")
    print("=========================================================\n")
    if not cat_videots:
        print("Nessuna anomalia.\n")
    else:
        for k, v in sorted(cat_videots.items()):
            print(f"[{k}]")
            for msg in v: print(f"  - {msg}")
            print()

    print("=========================================================")
    print("CARTELLE MULTI-PARTE (CD1/CD2 O ATTI SPARSI) & CASO 2 (CLONI)")
    print("=========================================================\n")
    if not cat_multipart:
        print("Nessuna anomalia.\n")
    else:
        total_clone_wasted_gb = 0.0
        # Ordiniamo prima i cloni (Caso 2) e poi i multi-parte reali (Caso 1)
        sorted_multipart = sorted(cat_multipart.items(), key=lambda x: (not x[1]["is_clone"], x[0]))
        for folder_name, data in sorted_multipart:
            is_clone = data["is_clone"]
            is_cd_naming = data["is_cd_naming"]
            wasted_gb = data["wasted_gb"]
            files = data["files"]

            print(f"📁 Cartella: [{folder_name}]")
            if is_clone:
                total_clone_wasted_gb += wasted_gb
                print(f"   🚨 CASO 2 - CLONI IDENTICI DELLO STESSO FILM (Falsi Multi-parte!)")
                print(f"   💾 Dimensione IDENTICA al byte! Spazio sprecato da recuperare: {wasted_gb:.2f} GB")
                print(f"   💡 Azione consigliata: Eliminare i file cloni superflui (es. CD2) e rinominare il file principale.")
            elif is_cd_naming and len(files) == 1:
                print(f"   🏷️  FILE SINGOLO CON SUFFISSO CD1 ERRATO (Film completo già unico)")
                print(f"   💡 Azione consigliata: Rinominare il file rimuovendo '- CD1'.")
            elif is_cd_naming:
                print(f"   ℹ️  CASO 1 - SPLIT MULTI-PARTE REALE (File con dimensioni diverse)")
                print(f"   💡 Azione consigliata: Unire i file in un unico MKV (mkvmerge) o preservare lo split.")
            else:
                print(f"   ⚠️  VERSIONI/FILE MULTIPLI NELLA STESSA CARTELLA (Dimensioni diverse, senza dicitura CD)")
                print(f"   💡 Azione consigliata: Verificare se una delle versioni è obsoleta.")

            for item in files:
                a = item["analysis"]
                if "error" in a:
                    print(f"      ❌ File: {a['file_name']} - {a.get('error')}")
                else:
                    ita_status = "SÌ ✅" if a["has_italian"] else "NO ❌"
                    dur = f" | Durata: {a.get('duration', 'N/D')}" if a.get('duration') else ""
                    print(f"      🎬 File: {a['file_name']} ({a['file_size_gb']:.2f} GB{dur})")
                    print(f"         📺 Formato      : {a['resolution']} [{a['codec']}]")
                    print(f"         🇮🇹 AUDIO ITALIA : {ita_status} ({a['italian_detail']})")
                    print(f"         🔊 Tutte Tracce : {a['audio_str']}")
                    print(f"         💬 Sottotitoli  : {a['sub_str']}")
            print()

        if total_clone_wasted_gb > 0:
            print(f"🔥 TOTALE SPAZIO RECUPERABILE DA CLONI CASO 2: {total_clone_wasted_gb:.2f} GB\n")

if __name__ == "__main__":
    main()

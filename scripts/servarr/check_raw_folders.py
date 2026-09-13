import os
import re
import json
import subprocess
from pathlib import Path

MEDIA_DIR = "/media/movies"

raw_folders = [
    "Arbitrage 2012 BDRiP Eng Aac Sub Ita x265",
    "Crimson Peak.2015.BDRip.1080p Ita Eng x265-NAHOM",
    "Empire.of.Light.2022.HDR.2160p.WEB.H265-NAISU[TGx]",
    "Eternal.Sunshine.of.the.Spotless.Mind.2004.4K.HDR.DV.2160p BDRemux Ita Eng x265-NAHOM",
    "Fargo.1996.4K.HDR.DV.2160p.BDRip Ita Eng x265-NAHOM",
    "Kill.Bill.Vol.2.2004.4K.HDR.DV.2160p.BDRemux Ita Eng x265-NAHOM",
    "Killers.of.the.Flower.Moon.2023.4K.HDR.DV.2160p.WEBDL Ita Eng x265-NAHOM",
    "La Dolce Vita 1960 Remastered BDRip 1080p HEVC ITA RUS AC3-NAHOM",
    "Leon.The.Professional.1994.EXTENDED.4K.HDR.2160p.BDRip Ita Eng Fre x265-NAHOM",
    "Memento.2000.2160p.HDR.AI.Enhance.ENG.RUS.GER.ITA.LATINO.Multi.Sub.DTS-HD.Master.DDP5.1.x265.MKV-BEN.THE.MEN",
    "Paris,.Texas.1984.4K.HDR.DV.2160p.BDRemux Ita Eng Fre x265-NAHOM",
    "Pinocchio.2019.WebDL.1080p.AC3.ITA.SUB.LFi[EtHD]",
    "Point Break.1991.4K.HDR.DV.2160p BDRip Ita Eng x265-NAHOM",
    "Scarface.1983.4K.HDR.2160p.BDRemux Ita Eng x265-NAHOM",
    "Smile.2022.4K.HDR.DV.2160p.BDRemux Ita Eng x265-NAHOM",
    "The Paperboy 2012 HDRip 720p Eng AC3 Sub Ita x264",
    "The.Elephant.Man.1980.4K.HDR.DV.2160p BDRemux Ita Eng x265-NAHOM",
    "The.Fifth.Element.1997.REPACK.4K.HDR.DV.2160p.BDRemux Ita Eng x265-NAHOM",
    "The.VVitch.2015.4K.HDR.DV.2160p.BDRemux Ita Eng x265-NAHOM",
    "Una.Pura.Formalita.1994 BDRip 720p Ita Ger x265-NAHOM",
    "[ Torrent911.lol ] The.Master.and.Margarita.2024.MULTi.1080p.WEB-DL.H264-Slay3R"
]

def get_main_video(folder_path):
    video_exts = ['.mkv', '.mp4', '.avi']
    largest_file = None
    max_size = 0
    for root, dirs, files in os.walk(folder_path):
        for f in files:
            if any(f.lower().endswith(ext) for ext in video_exts):
                full_path = os.path.join(root, f)
                size = os.path.getsize(full_path)
                if size > max_size:
                    max_size = size
                    largest_file = full_path
    return largest_file

def check_italian_audio(video_file):
    if not video_file:
        return "No video file found"

    cmd = ["ffprobe", "-v", "quiet", "-show_streams", "-select_streams", "a", "-of", "json", video_file]
    try:
        result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        data = json.loads(result.stdout)

        has_audio = False
        ita_found = False

        for stream in data.get('streams', []):
            has_audio = True
            tags = stream.get('tags', {})
            lang = tags.get('language', '').lower()
            title = tags.get('title', '').lower()
            if lang in ['ita', 'it'] or 'ita' in title:
                ita_found = True
                break

        if ita_found:
            return "SI (Traccia audio ITA confermata)"
        elif not has_audio:
            return "Nessuna traccia audio trovata"
        else:
            return "NO (Nessuna traccia ITA esplicita)"
    except Exception as e:
        return f"Errore ffprobe: {e}"

def clean_title(raw_name):
    clean = re.sub(r'\[.*?\]', '', raw_name)
    clean = clean.replace('.', ' ').strip()
    match = re.search(r'^(.*?)\s+(?:19|20)\d{2}', clean)
    if match:
        title = match.group(1).strip()
    else:
        title = clean.split()[0]
    return title.lower()

all_folders = [f.name for f in Path(MEDIA_DIR).iterdir() if f.is_dir()]

print("Analisi delle 21 cartelle RAW...\n")

for raw in raw_folders:
    print(f"RAW FOLDER: {raw}")

    year_match = re.search(r'(19\d{2}|20\d{2})', raw)
    year = year_match.group(1) if year_match else None

    title_words = clean_title(raw).split()
    first_word = title_words[0] if title_words else ""

    possible_duplicates = []
    for f in all_folders:
        if f == raw:
            continue
        if year and year in f and first_word and first_word.lower() in f.lower():
            possible_duplicates.append(f)

    if not possible_duplicates:
        print("  -> NESSUN DUPLICATO TROVATO (Il film esiste solo in questa cartella raw)")
        raw_vid = get_main_video(os.path.join(MEDIA_DIR, raw))
        print(f"  -> Audio ITA in RAW: {check_italian_audio(raw_vid)}")
    else:
        print(f"  -> DUPLICATI TROVATI: {', '.join(possible_duplicates)}")
        raw_vid = get_main_video(os.path.join(MEDIA_DIR, raw))
        print(f"  -> Audio ITA in RAW: {check_italian_audio(raw_vid)}")
        for dup in possible_duplicates:
            dup_vid = get_main_video(os.path.join(MEDIA_DIR, dup))
            print(f"  -> Audio ITA in '{dup}': {check_italian_audio(dup_vid)}")
    print("-" * 50)

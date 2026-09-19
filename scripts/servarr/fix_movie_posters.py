#!/usr/bin/env python3
# Script di Bonifica Intelligente Artwork e Ripristino Locandine per Jellyfin
# Implementa la "Regola Intelligente" per risolvere il conflitto delle immagini orizzontali <nome-video>.jpg:
# 1. Riconosce aspect ratio (larghezza / altezza):
#    - ratio >= 1.2 -> Orizzontale (Fanart / Fotogramma 16:9 o 4:3)
#    - ratio <= 0.85 -> Verticale (Vera Locandina 2:3)
# 2. Se Orizzontale:
#    - Se nella cartella MANCA backdrop.jpg / fanart.jpg -> RINOMINA in backdrop.jpg (salva lo sfondo!)
#    - Se nella cartella ESISTE GIÀ backdrop.jpg -> ELIMINA il duplicato superfluo che scavalca folder.jpg
# 3. Se Verticale:
#    - Se MANCA folder.jpg -> RINOMINA in folder.jpg
#    - Se ESISTE GIÀ folder.jpg -> MANTIENI INTATTO (protetto)
# 4. Rileva e rimuove folder.jpg / poster.jpg microscopici (< 50KB) per sbloccare lo scraper TMDb.
# 5. Invia notifica di refresh libreria a Jellyfin al termine dell'applicazione reale.

import os
import sys
import json
import struct
import argparse
import urllib.request
import urllib.error
from pathlib import Path

MEDIA_DIR = os.environ.get("MEDIA_DIR", "/mnt/oliraid/arrdata/media/movies")
JELLYFIN_URL = os.environ.get("JELLYFIN_URL", "http://10.10.10.50:8096")
JELLYFIN_TOKEN = os.environ.get("JELLYFIN_TOKEN", "7c80240c7a9b4326a8690ce140265a14")

VIDEO_EXTS = {".mkv", ".mp4", ".avi", ".ts", ".m4v", ".m2ts"}
IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".webp"}

def get_image_size(file_path):
    """Estrae larghezza e altezza leggendo gli header binari (senza dipendenze esterne)."""
    try:
        with open(file_path, "rb") as f:
            data = f.read(65536)
            # JPEG
            if data.startswith(b"\xff\xd8"):
                i = 0
                while i < len(data) - 1:
                    if data[i] == 0xFF and data[i+1] in [0xC0, 0xC1, 0xC2]:
                        h, w = struct.unpack(">HH", data[i+5:i+9])
                        return w, h
                    i += 1
            # PNG
            elif data.startswith(b"\x89PNG\r\n\x1a\n"):
                w, h = struct.unpack(">II", data[16:24])
                return w, h
            # WebP
            elif data.startswith(b"RIFF") and data[8:12] == b"WEBP":
                if data[12:16] == b"VP8 ":
                    w, h = struct.unpack("<HH", data[26:30])
                    return w & 0x3fff, h & 0x3fff
                elif data[12:16] == b"VP8L":
                    b0, b1, b2, b3 = data[21:25]
                    w = 1 + (((b1 & 0x3F) << 8) | b0)
                    h = 1 + (((b3 & 0xF) << 10) | (b2 << 2) | ((b1 & 0xC0) >> 6))
                    return w, h
    except Exception:
        pass
    return 0, 0

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

def scan_and_plan(base_dir, filter_text=""):
    plans = []

    for movie_dir in sorted(base_dir.iterdir()):
        if not movie_dir.is_dir():
            continue

        if filter_text and filter_text.lower() not in movie_dir.name.lower():
            continue

        dir_files = list(movie_dir.iterdir())
        video_stems = set()
        for f in dir_files:
            if f.is_file() and f.suffix.lower() in VIDEO_EXTS:
                video_stems.add(f.stem)

        if not video_stems:
            continue

        has_backdrop = (movie_dir / "backdrop.jpg").exists() or (movie_dir / "fanart.jpg").exists()
        has_folder = (movie_dir / "folder.jpg").exists() or (movie_dir / "poster.jpg").exists()

        folder_jpg = movie_dir / "folder.jpg"
        poster_jpg = movie_dir / "poster.jpg"

        actions = []

        # 1. Analisi file <nome-video>.ext
        for f in dir_files:
            if not f.is_file() or f.suffix.lower() not in IMAGE_EXTS:
                continue

            # Corrisponde esattamente allo stem di uno dei video
            if f.stem in video_stems:
                w, h = get_image_size(f)
                if w == 0 or h == 0:
                    continue

                ratio = w / h
                size_kb = f.stat().st_size / 1024

                # Orizzontale (16:9 / 4:3)
                if ratio >= 1.2:
                    if not has_backdrop:
                        target = movie_dir / "backdrop.jpg"
                        actions.append({
                            "type": "RENAME_TO_BACKDROP",
                            "src": f,
                            "target": target,
                            "res": f"{w}x{h}",
                            "size_kb": size_kb,
                            "desc": f"Salva sfondo mancante (rinomina in backdrop.jpg)"
                        })
                        has_backdrop = True
                    else:
                        actions.append({
                            "type": "DELETE_SUPERFLUOUS_IMAGE",
                            "src": f,
                            "target": None,
                            "res": f"{w}x{h}",
                            "size_kb": size_kb,
                            "desc": f"Rimuove immagine orizzontale duplicata (backdrop già presente)"
                        })

                # Verticale (2:3)
                elif ratio <= 0.85:
                    if not has_folder:
                        target = movie_dir / "folder.jpg"
                        actions.append({
                            "type": "RENAME_TO_FOLDER",
                            "src": f,
                            "target": target,
                            "res": f"{w}x{h}",
                            "size_kb": size_kb,
                            "desc": f"Promuove a locandina ufficiale folder.jpg"
                        })
                        has_folder = True
                    else:
                        # Locandina verticale aggiuntiva: mantieni o rimuovi se identica
                        actions.append({
                            "type": "KEEP_VERTICAL",
                            "src": f,
                            "target": None,
                            "res": f"{w}x{h}",
                            "size_kb": size_kb,
                            "desc": f"Locandina verticale valida (mantenuta)"
                        })

        # 2. Controllo locandina principale corrotta (< 50KB)
        for cand in [folder_jpg, poster_jpg]:
            if cand.exists():
                sz_kb = cand.stat().st_size / 1024
                if sz_kb < 50:
                    actions.append({
                        "type": "PURGE_CORRUPTED_POSTER",
                        "src": cand,
                        "target": None,
                        "res": "Miniatura < 50KB",
                        "size_kb": sz_kb,
                        "desc": f"Rimuove miniatura corrotta per consentire download HD da TMDb"
                    })

        if actions:
            plans.append({
                "movie_dir": movie_dir,
                "movie_name": movie_dir.name,
                "actions": actions
            })

    return plans

def main():
    parser = argparse.ArgumentParser(description="Bonifica intelligente artwork e ripristino locandine per Jellyfin")
    parser.add_argument("--dry-run", action="store_true", default=False, help="Forza la modalità simulazione (default se non --apply)")
    parser.add_argument("--apply", action="store_true", help="Applica le modifiche reali sul filesystem")
    parser.add_argument("--filter", type=str, default="", help="Filtra per nome cartella film (es. 'Wasabi')")
    parser.add_argument("--no-refresh", action="store_true", help="Disabilita il webhook di refresh a Jellyfin")
    args = parser.parse_args()

    execute_mode = args.apply and not args.dry_run

    base_dir = Path(MEDIA_DIR)
    if not base_dir.exists():
        print(f"❌ Errore: la directory {MEDIA_DIR} non esiste.")
        sys.exit(1)

    print("==================================================================")
    print("  🖼️  Bonifica Intelligente Artwork e Ripristino Locandine Jellyfin ")
    print("==================================================================\n")

    plans = scan_and_plan(base_dir, filter_text=args.filter)

    if not plans:
        print("✅ Nessuna anomalia o conflitto di artwork rilevato nella libreria.")
        return

    # Statistiche di riepilogo
    tot_rename_backdrop = 0
    tot_del_horizontal = 0
    tot_rename_folder = 0
    tot_keep_vertical = 0
    tot_purge_corrupted = 0

    for p in plans:
        for a in p["actions"]:
            t = a["type"]
            if t == "RENAME_TO_BACKDROP": tot_rename_backdrop += 1
            elif t == "DELETE_SUPERFLUOUS_IMAGE": tot_del_horizontal += 1
            elif t == "RENAME_TO_FOLDER": tot_rename_folder += 1
            elif t == "KEEP_VERTICAL": tot_keep_vertical += 1
            elif t == "PURGE_CORRUPTED_POSTER": tot_purge_corrupted += 1

    print(f"🎯 Risultati Scansione ({len(plans)} film con azioni identificate):")
    print(f"   🔄 Sfondi mancanti salvati (rinomina in backdrop.jpg): {tot_rename_backdrop}")
    print(f"   🗑️  Immagini orizzontali duplicate rimosse:              {tot_del_horizontal}")
    print(f"   🖼️  Locandine promosse a folder.jpg:                    {tot_rename_folder}")
    print(f"   🛡️  Locandine verticali valide protette:                {tot_keep_vertical}")
    print(f"   ⚠️  Miniature corrotte da rimuovere (< 50KB):           {tot_purge_corrupted}\n")

    print("==================================================================")
    print("📋 DETTAGLIO AZIONI PER FILM:")
    print("==================================================================")

    for p in plans:
        # Non stampare film che hanno solo KEEP_VERTICAL
        active_actions = [a for a in p["actions"] if a["type"] != "KEEP_VERTICAL"]
        if not active_actions:
            continue

        print(f"\n🎬 {p['movie_name']}:")
        for a in p["actions"]:
            icon = "🗑️" if "DELETE" in a["type"] or "PURGE" in a["type"] else ("🔄" if "RENAME" in a["type"] else "🛡️")
            target_str = f" ➔ {a['target'].name}" if a["target"] else ""
            print(f"   {icon} [{a['type']}] {a['src'].name} ({a['res']}, {a['size_kb']:.1f} KB){target_str}")
            print(f"      Motivazione: {a['desc']}")

    if not execute_mode:
        print("\n==================================================================")
        print("ℹ️  SIMULAZIONE COMPLETATA (DRY-RUN) — Nessun file è stato toccato.")
        print("Per applicare realmente queste modifiche, lancia con il flag --apply")
        print("==================================================================")
        return

    print("\n==================================================================")
    print("🚀 ESECUZIONE ATTIVA: Applicazione modifiche in corso...")
    print("==================================================================")

    for p in plans:
        for a in p["actions"]:
            src = a["src"]
            atype = a["type"]

            if atype in ["RENAME_TO_BACKDROP", "RENAME_TO_FOLDER"]:
                target = a["target"]
                print(f"  [RENAME] {p['movie_name']} / {src.name} ➔ {target.name}")
                os.rename(src, target)

            elif atype in ["DELETE_SUPERFLUOUS_IMAGE", "PURGE_CORRUPTED_POSTER"]:
                print(f"  [DELETE] {p['movie_name']} / {src.name} ({a['size_kb']:.1f} KB)")
                if src.exists():
                    os.remove(src)

    print("\n==================================================================")
    print("✅ Tutte le operazioni di bonifica artwork sono completate!")
    print("==================================================================")

    if not args.no_refresh and JELLYFIN_URL and JELLYFIN_TOKEN:
        trigger_jellyfin_refresh(JELLYFIN_URL, JELLYFIN_TOKEN)

if __name__ == "__main__":
    main()

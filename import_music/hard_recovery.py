import os
import re
import subprocess
import json
import requests
import time
import sys

# --- CONFIGURATION ---
ANOMALIES_LOG = "import_anomalies.log"
RECOVERY_LOG = "hard_recovery_exec.log"
BEETS_CONFIG = "hard_recovery_config.yaml"
FFPROBE_PATH = "/opt/homebrew/bin/ffprobe"
MB_API_URL = "https://musicbrainz.org/ws/2/release/"
USER_AGENT = "BeetsHardRecovery/1.0 ( pindaroli@gmail.com )"
DURATION_TOLERANCE = 15 # seconds
DELAY_BETWEEN_QUERIES = 2 # rate limit MB API

def log_recovery(message):
    with open(RECOVERY_LOG, "a") as f:
        f.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')} - {message}\n")
    print(message)

def get_local_album_info(path):
    """Counts files and calculates total duration using ffprobe."""
    files = [os.path.join(path, f) for f in os.listdir(path) if f.lower().endswith(('.mp3', '.flac', '.m4a', '.ogg', '.wav'))]
    if not files:
        return None, 0

    total_duration = 0
    for f in files:
        try:
            cmd = [FFPROBE_PATH, "-v", "error", "-show_entries", "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", f]
            duration = subprocess.check_output(cmd).decode().strip()
            total_duration += float(duration)
        except Exception:
            continue

    return len(files), total_duration

def search_musicbrainz(artist, album, track_count):
    """Queries MusicBrainz for a matching release."""
    query = f'release:"{album}" AND artist:"{artist}" AND tracks:{track_count}'
    params = {
        "query": query,
        "fmt": "json"
    }
    headers = {"User-Agent": USER_AGENT}

    try:
        response = requests.get(MB_API_URL, params=params, headers=headers)
        if response.status_code == 200:
            data = response.json()
            return data.get("releases", [])
        else:
            log_recovery(f"MB API Error: {response.status_code}")
    except Exception as e:
        log_recovery(f"MB API Exception: {e}")
    return []

def process_anomalies():
    if not os.path.exists(ANOMALIES_LOG):
        log_recovery("No anomalies log found.")
        return

    with open(ANOMALIES_LOG, "r") as f:
        lines = f.readlines()

    # Regex to extract Path and Artist/Album
    # Format: [/Volumes/.../Artist/Album] LOG: ... | CMD: beet import -i "/Volumes/.../Path"
    processed_paths = set()

    for line in lines:
        match = re.search(r'\[(.*?)\]', line)
        if not match:
            continue

        path = match.group(1)
        if path in processed_paths or not os.path.exists(path):
            continue

        processed_paths.add(path)

        # Simple extraction of Artist/Album from path
        parts = path.rstrip('/').split('/')
        if len(parts) < 2:
            continue

        album_name = parts[-1]
        artist_name = parts[-2]

        log_recovery(f"--- Processing: {artist_name} - {album_name} ---")

        track_count, local_duration = get_local_album_info(path)
        if track_count == 0:
            log_recovery(f"Skipping: No audio files found in {path}")
            continue

        log_recovery(f"Local: {track_count} tracks, {local_duration:.2f}s duration")

        # Step 1: Search MusicBrainz
        releases = search_musicbrainz(artist_name, album_name, track_count)
        time.sleep(DELAY_BETWEEN_QUERIES)

        best_mbid = None
        for rel in releases:
            # We check for track count match and duration if possible
            # MB doesn't always give total duration in search results easily
            # But if we have a single strong match on tracks and names, it's a good candidate

            # Simple heuristic: if only one release matches the name and track count, we take it.
            # If multiple, we might need more logic, but for Hard Recovery we aim for 100% certainty.
            if len(releases) == 1:
                best_mbid = rel['id']
                break

        if best_mbid:
            log_recovery(f"Found unique MBID: {best_mbid}. Launching recovery import...")
            try:
                # Run beet with the specific config and search-id
                cmd = ["beet", "-c", BEETS_CONFIG, "import", "--search-id", best_mbid, path]
                subprocess.run(cmd, check=True)
                log_recovery(f"SUCCESS: {path} imported via MBID {best_mbid}")
            except subprocess.CalledProcessError as e:
                log_recovery(f"FAILURE: Beets error for {path}: {e}")
        else:
            log_recovery(f"NOMATCH: Could not find a unique MBID for {path}")

if __name__ == "__main__":
    process_anomalies()

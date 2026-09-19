#!/usr/bin/env python3
import http.server
import socketserver
import urllib.parse
import urllib.request
import urllib.error
import subprocess
import threading
import sys
import os

def trigger_jellyfin_refresh(folder_id="f137a2dd21bbc1b99aa5c0f6bf02a805"):
    """Innesca lo scan della libreria su Jellyfin (mirato a Movies o generale)."""
    jellyfin_url = os.environ.get("JELLYFIN_URL", "http://jellyfin:8096").rstrip('/')
    token = os.environ.get("JELLYFIN_TOKEN", "7c80240c7a9b4326a8690ce140265a14")
    headers = {
        "Authorization": f'MediaBrowser Client="FileBot", Device="Server", DeviceId="filebot-normalizer", Version="1.0.0", Token="{token}"',
        "Content-Length": "0"
    }

    url = f"{jellyfin_url}/Items/{folder_id}/Refresh" if folder_id else f"{jellyfin_url}/Library/Refresh"
    print(f"📡 Innesco scan libreria su Jellyfin ({url})...")
    req = urllib.request.Request(url, data=b"", headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            if resp.status in [200, 204]:
                print("✅ Scan libreria Jellyfin avviato con successo!")
                return True
            else:
                print(f"⚠️ Risposta Jellyfin: HTTP {resp.status}")
    except Exception as e:
        print(f"⚠️ Refresh mirato fallito ({e}), fallback a refresh generale libreria...")
        try:
            fallback_req = urllib.request.Request(f"{jellyfin_url}/Library/Refresh", data=b"", headers=headers, method="POST")
            with urllib.request.urlopen(fallback_req, timeout=10) as resp:
                if resp.status in [200, 204]:
                    print("✅ Scan generale libreria Jellyfin avviato con successo!")
                    return True
        except Exception as e2:
            print(f"❌ Errore innesco scan Jellyfin: {e2}")
    return False

class WebhookHandler(http.server.BaseHTTPRequestHandler):
    def do_POST(self):
        if self.path == '/hooks/normalize':
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length).decode('utf-8')
            params = urllib.parse.parse_qs(post_data)

            path = params.get('path', [''])[0]
            category = params.get('category', [''])[0]
            target_output = params.get('target', [''])[0]

            if not path or not category:
                self.send_response(400)
                self.end_headers()
                self.wfile.write(b"Missing path or category")
                return

            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"Processing started in background")

            # Start in background
            def run_script():
                script = "/app/normalize.sh"
                nonlocal target_output
                if category == "video-filebot":
                    script = "/app/normalize-video.sh"
                    if not target_output:
                        target_output = "/media/movies"
                elif "classical" in category:
                    if not target_output:
                        target_output = "/media/music/Classical"
                elif not target_output:
                    target_output = "/media/music"

                email_recipient = os.environ.get("EMAIL_RECIPIENT", "")

                cmd = [script, path, target_output, "/media", email_recipient]
                print(f"Running: {' '.join(cmd)}")
                try:
                    subprocess.run(cmd, check=True)
                    # Scatena automaticamente lo scan della libreria Movies su Jellyfin
                    if category == "video-filebot":
                        trigger_jellyfin_refresh("f137a2dd21bbc1b99aa5c0f6bf02a805")
                except Exception as e:
                    print(f"Error: {e}")

            threading.Thread(target=run_script).start()
        else:
            self.send_response(404)
            self.end_headers()

if __name__ == "__main__":
    PORT = 9000
    with socketserver.TCPServer(("", PORT), WebhookHandler) as httpd:
        print(f"Serving at port {PORT}")
        httpd.serve_forever()

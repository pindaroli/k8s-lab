#!/usr/bin/env python3
import http.server
import socketserver
import urllib.parse
import subprocess
import threading
import sys
import os

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
                except Exception as e:
                    print(f"Error: {e}")

            threading.Thread(target=run_script).start()
        else:
            self.send_response(404)
            self.end_headers()

PORT = 9000
with socketserver.TCPServer(("", PORT), WebhookHandler) as httpd:
    print(f"Serving at port {PORT}")
    httpd.serve_forever()

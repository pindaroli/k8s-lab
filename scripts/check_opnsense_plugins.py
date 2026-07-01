import json
import ssl
import urllib.request
import base64
import sys
import os

# Load credentials from the standard location
script_dir = os.path.dirname(os.path.abspath(__file__))
root_dir = os.path.abspath(os.path.join(script_dir, '..'))
apikey_file = os.path.join(root_dir, 'ansible/OPNsense.internal_root_apikey.txt')

if not os.path.exists(apikey_file):
    print(f"Error: API key file not found at {apikey_file}")
    sys.exit(1)

# Read credentials
api_key = None
api_secret = None
with open(apikey_file, 'r') as f:
    for line in f:
        if line.startswith('key='):
            api_key = line.split('=', 1)[1].strip()
        elif line.startswith('secret='):
            api_secret = line.split('=', 1)[1].strip()

if not api_key or not api_secret:
    print("Error: Could not parse key or secret from apikey file.")
    sys.exit(1)

# Load URL from rete.json dynamically
rete_path = os.path.join(root_dir, 'rete.json')
try:
    with open(rete_path, 'r') as f:
        rete = json.load(f)
    opnsense = next(n for n in rete['nodi'] if n['id'] == 'opnsense')
    URL = f"https://{opnsense['management_ip']}"
except Exception as e:
    print(f"Warning: Could not read management IP from rete.json ({e}). Using default IP.")
    URL = "https://192.168.100.1"

# Try both the dynamic URL and the alternate transit IP
IPS = [URL, "https://192.168.2.254"]

def call_api(base_url, endpoint):
    full_url = f"{base_url.rstrip('/')}{endpoint}"
    credentials = f"{api_key}:{api_secret}"
    auth_header = "Basic " + base64.b64encode(credentials.encode()).decode()

    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE

    req = urllib.request.Request(full_url, headers={
        'User-Agent': 'curl/8.7.1',
        'Authorization': auth_header
    })

    try:
        with urllib.request.urlopen(req, context=ctx, timeout=90) as response:
            return json.loads(response.read().decode('utf-8'))
    except Exception as e:
        print(f"Error querying {full_url}: {e}")
        return None

# Find which URL works
working_url = None
for base_url in IPS:
    print(f"Testing connectivity to {base_url}...")
    res = call_api(base_url, "/api/core/firmware/status")
    if res is not None:
        working_url = base_url
        print(f"Success connecting to {base_url}")
        break

if not working_url:
    print("Could not connect to any OPNsense IP.")
    sys.exit(1)

print("\nFetching firmware info/plugins...")
info = call_api(working_url, "/api/core/firmware/info")
if not info:
    print("Failed to fetch firmware info.")
    sys.exit(1)

# Process plugins list (handles both dict and list response structures)
plugins_raw = info.get("plugin", [])
if isinstance(plugins_raw, dict):
    plugins_list = list(plugins_raw.values())
elif isinstance(plugins_raw, list):
    plugins_list = plugins_raw
else:
    plugins_list = []

# Print all installed plugins
print("\n--- INSTALLED PLUGINS ---")
installed_plugins = []
for pkg in plugins_list:
    if pkg.get("installed") == "1" or pkg.get("installed") == 1:
        installed_plugins.append(pkg)
        print(f"- {pkg.get('name')} ({pkg.get('version')}): {pkg.get('comment')}")

print("\n--- SEARCHING FOR SCHEDULER/CRON/ACTION PLUGINS ---")
found = False
for pkg in plugins_list:
    comment = pkg.get("comment", "").lower()
    pkg_name = pkg.get("name", "").lower()
    if "cron" in comment or "schedul" in comment or "action" in comment or "cron" in pkg_name or "schedul" in pkg_name or "action" in pkg_name:
        status = "Installed" if pkg.get("installed") == "1" or pkg.get("installed") == 1 else "Available but not installed"
        print(f"- {pkg.get('name')} ({pkg.get('version')}): {pkg.get('comment')} [{status}]")
        found = True

if not found:
    print("No scheduling/cron plugins found in the repository list.")

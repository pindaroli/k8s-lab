import json
import ssl
import urllib.request
import base64
import sys

# Credentials
API_KEY = "rvg43fWFkyFvpgzcRsv7q6rQ04fEXPiA0jWpwLFIgQMRtiUTc9VSdNZ8lFdd7thidksp0oiuPeLcq9nT"
API_SECRET = "eYjZ2MiqLNagun+Wf4C35gCzxiB3mEMvEUhVjYiPhM0yrpV0F4U5WkhtQRAO4RRnp4hETbZFgIgzEoFq"
URL = "https://10.10.20.254" # Using IP from rete.json

def call_api(endpoint, method='GET', data=None):
    full_url = f"{URL}{endpoint}"
    credentials = f"{API_KEY}:{API_SECRET}"
    auth_header = "Basic " + base64.b64encode(credentials.encode()).decode()

    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE

    payload = json.dumps(data).encode() if data else b'{}'

    req = urllib.request.Request(full_url, method=method, data=payload, headers={
        'Content-Type': 'application/json',
        'Authorization': auth_header
    })

    try:
        with urllib.request.urlopen(req, context=ctx) as response:
            return json.loads(response.read().decode())
    except Exception as e:
        print(f"Error hitting {endpoint}: {e}")
        return None

# Try several possible endpoints
endpoints = [
    "/api/firewall/nat/portforward/searchItem",
    "/api/firewall/nat/port_forward/searchItem",
    "/api/firewall/filter/searchRule"
]

for ep in endpoints:
    print(f"Checking {ep}...")
    res = call_api(ep, method='POST', data={})
    if res:
        print(f"SUCCESS: {ep}")
        print(json.dumps(res, indent=2)[:500])
        break
    else:
        print(f"FAILED: {ep}")

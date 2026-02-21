import urllib.request
import ssl
import json
import base64
import sys
import xml.etree.ElementTree as ET

URL = "https://192.168.2.254"
API_KEY = "x2JVfDZgKrtF2TZTNTMg+5hjJFAHEAaGntzDT/qqchHiu2N4f1gaYIZNCn0RjC86mPztyCQuElsg3mJp"
API_SECRET = "F/rPySIuiZ8C3KmXUqPz42nXkkzUEMGqtZ21xVOPSQLFCwHRuar58FGR4P9fOP+cXTwW45CvcmWogJOT"

credentials = f"{API_KEY}:{API_SECRET}"
auth_header = "Basic " + base64.b64encode(credentials.encode()).decode()

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

def do_request(endpoint):
    req = urllib.request.Request(f"{URL}{endpoint}", headers={
        'Authorization': auth_header
    })
    try:
        with urllib.request.urlopen(req, context=ctx) as response:
            return response.read()
    except Exception as e:
        print(f"Error for {endpoint}: {e}")
        return None

print("Downloading OPNsense configuration...")
config_data = do_request("/api/core/backup/download/this")

if config_data:
    try:
        root = ET.fromstring(config_data)
        dhcpd = root.find('dhcpd')
        if dhcpd is not None:
            for interface in dhcpd:
                print(f"--- DHCP Settings for interface: {interface.tag} ---")
                gateway = interface.find('gateway')
                if gateway is not None and gateway.text:
                    print(f"Custom Gateway Configured: {gateway.text}")
                else:
                    print("No Custom Gateway configured (Uses OPNsense Interface IP).")
        else:
            print("No DHCP configuration found in config.")
    except Exception as e:
        print("Failed to parse config XML:", e)
else:
    print("Failed to download config.")

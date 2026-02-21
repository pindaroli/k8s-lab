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

print("Downloading OPNsense configuration...")
req = urllib.request.Request(f"{URL}/api/core/backup/download/this", headers={
    'Authorization': auth_header
})
try:
    with urllib.request.urlopen(req, context=ctx) as response:
        config_data = response.read()
        root = ET.fromstring(config_data)
        dhcpd = root.find('dhcpd')
        if dhcpd is not None:
             for interface in dhcpd:
                  print(f"--- Interface: {interface.tag} ---")
                  for staticmap in interface.findall('staticmap'):
                       mac = staticmap.find('mac').text if staticmap.find('mac') is not None else 'None'
                       ipaddr = staticmap.find('ipaddr').text if staticmap.find('ipaddr') is not None else 'None'
                       hostname = staticmap.find('hostname').text if staticmap.find('hostname') is not None else 'None'
                       print(f"  {hostname}: IP={ipaddr}, MAC={mac}")
except Exception as e:
    print(f"Error: {e}")

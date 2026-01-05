#!/usr/bin/env python3
import json
import subprocess
import sys
import re
import os

STORAGE_JSON_PATH = "../storage.json"
TRUENAS_IP = "10.10.10.50"
TRUENAS_USER = "olindo"
TRUENAS_PASS = "Compli61!"  # Prone to change, ideally env var

def fetch_exports():
    """Fetches /etc/exports from TrueNAS using the helper script."""
    script_path = os.path.join(os.path.dirname(__file__), "fetch_exports.sh")
    
    # Ensure script is executable
    subprocess.run(["chmod", "+x", script_path], check=True)
    
    result = subprocess.run(
        [script_path, TRUENAS_IP, TRUENAS_USER, TRUENAS_PASS],
        capture_output=True,
        text=True
    )
    
    if result.returncode != 0:
        print(f"Error fetching exports: {result.stderr}")
        sys.exit(1)
        
    return result.stdout

def parse_exports(raw_exports):
    """
    Parses raw /etc/exports content into a simplified dictionary.
    Format example:
    "/mnt/stripe/k8s-arr" 10.10.10.0/24(sec=sys,rw,no_subtree_check)
    """
    exports = {}
    
    # Regex to handle quoted paths and multiline entries
    # This is a basic parser; TrueNAS exports format is slightly specific.
    # We assume one path per export block.
    
    # Split by lines, but merge backslash-continued lines
    lines = raw_exports.replace('\\\n', '').splitlines()
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
            
        # Match path at the beginning (quoted or not)
        match = re.match(r'^"?(/mnt/[^"\s]+)"?\s+(.*)', line)
        if match:
            path = match.group(1)
            acl_str = match.group(2)
            
            # Extract IPs/Networks from ACL string
            # Example: 10.10.10.0/24(opts) 10.10.20.141(opts)
            networks = []
            acl_parts = re.findall(r'([0-9\./]+)\(', acl_str)
            networks.extend(acl_parts)
            
            exports[path] = networks
            
    return exports

def sync_storage_json(parsed_exports):
    """Updates storage.json based on parsed exports."""
    try:
        with open(STORAGE_JSON_PATH, 'r') as f:
            data = json.load(f)
    except FileNotFoundError:
        print("storage.json not found, creating new structure.")
        data = {"nas": {"hostname": "truenas", "ips": {}, "exports": {}}}

    current_exports = data.get("nas", {}).get("exports", {})
    
    # 1. Update existing and add new
    for path, networks in parsed_exports.items():
        found = False
        for key, info in current_exports.items():
            if info.get("path") == path:
                print(f"Updating ACLs for {key} ({path})")
                info["networks"] = networks
                found = True
                break
        
        if not found:
            # Create a slug from the path
            slug = path.split('/')[-1].replace('-', '_').replace('.', '_')
            print(f"Adding new export: {slug} ({path})")
            current_exports[slug] = {
                "path": path,
                "description": "Imported from TrueNAS",
                "protocol": "nfs",
                "mount_options": ["nfsvers=4.1", "soft", "timeo=50", "retrans=3", "noatime"],
                "networks": networks
            }

    # 2. Check for removed exports (optional, maybe just warn?)
    for key, info in list(current_exports.items()):
        if info.get("path") not in parsed_exports:
            print(f"WARNING: Share {key} ({info.get('path')}) is in storage.json but NOT in TrueNAS exports.")

    data["nas"]["exports"] = current_exports
    
    with open(STORAGE_JSON_PATH, 'w') as f:
        json.dump(data, f, indent=2)
    
    print("storage.json updated successfully.")

if __name__ == "__main__":
    print("Fetching exports from TrueNAS...")
    raw = fetch_exports()
    # print("DEBUG RAW:\n", raw)
    
    parsed = parse_exports(raw)
    print(f"Found {len(parsed)} exports.")
    
    sync_storage_json(parsed)

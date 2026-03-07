#!/usr/bin/env python3
"""
Sincronizza e monta gli share NFS da TrueNAS via script.
"""
import json
import sys
import re
import os

# Aggiungi scripts/ al path per poter importare utils.common
_base = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
sys.path.insert(0, os.path.join(_base, "scripts"))
from utils.common import PROJECT_ROOT, run_cmd

STORAGE_JSON_PATH = os.path.join(PROJECT_ROOT, "storage.json")

TRUENAS_IP = "10.10.10.50"
TRUENAS_USER = "olindo"
TRUENAS_PASS = "Compli61!"  # Prone to change, ideally env var

def fetch_exports():
    """Fetches /etc/exports from TrueNAS using the helper script."""
    script_path = os.path.join(PROJECT_ROOT, "scripts", "utils", "fetch_exports.sh")
    
    # Ensure script is executable
    if os.path.exists(script_path):
        os.chmod(script_path, 0o755)
    
    stdout = run_cmd([script_path, TRUENAS_IP, TRUENAS_USER, TRUENAS_PASS])
    if stdout is None:
        print(f"Error fetching exports from TrueNAS ({TRUENAS_IP})")
        sys.exit(1)
        
    return stdout

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
        print(f"{STORAGE_JSON_PATH} not found, creating new structure.")
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
    
    print(f"storage.json ({STORAGE_JSON_PATH}) updated successfully.")

def main():
    # Salva il CWD originale
    original_cwd = os.getcwd()
    try:
        # Spostati nella root del progetto
        os.chdir(PROJECT_ROOT)
        print("Fetching exports from TrueNAS...")
        raw = fetch_exports()
        
        parsed = parse_exports(raw)
        print(f"Found {len(parsed)} exports.")
        
        sync_storage_json(parsed)
    finally:
        # Ripristina CWD
        os.chdir(original_cwd)

if __name__ == "__main__":
    main()

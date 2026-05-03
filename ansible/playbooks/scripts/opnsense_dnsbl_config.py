import requests
import sys
import json
import argparse
import urllib3
import time

# Disable warnings for self-signed certs
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--api-key", required=True)
    parser.add_argument("--api-secret", required=True)
    parser.add_argument("--url", required=True)
    parser.add_argument("--file", required=True, help="Path to rete.json")
    args = parser.parse_args()

    auth = (args.api_key, args.api_secret)
    
    try:
        # 0. Load tracking wildcards from rete.json
        with open(args.file, 'r') as f:
            rete_data = json.load(f)
        
        tracking_wildcards = rete_data.get("opnsense", {}).get("outbound", {}).get("blocked-domain", [])
        if not tracking_wildcards:
            print("[WARNING] No blocked domains found in rete.json under opnsense.outbound.blocked-domain")

        # 1. Update Config (Wildcards)
        r = requests.get(f"{args.url}/api/unbound/settings/get", auth=auth, verify=False)
        r.raise_for_status()
        full_config = r.json()
        
        dnsbl_section = full_config.get("unbound", {}).get("dnsbl", {}).get("blocklist", {})
        uuid = list(dnsbl_section.keys())[0]
        
        current_wildcards = dnsbl_section[uuid].get("wildcards", {})
        if not isinstance(current_wildcards, dict):
            current_wildcards = {}

        for domain in tracking_wildcards:
            current_wildcards[domain] = {"value": domain, "selected": 1}
        
        payload = {
            "unbound": {
                "dnsbl": {
                    "blocklist": {
                        uuid: {
                            "enabled": "1",
                            "wildcards": current_wildcards
                        }
                    }
                }
            }
        }
        
        print("[*] Updating Wildcard configuration...")
        update_r = requests.post(f"{args.url}/api/unbound/settings/set", auth=auth, verify=False, json=payload)
        update_r.raise_for_status()
        
        # 2. Trigger Download & Update (The "Missing Link")
        # In OPNsense, this is usually core/configd/run/unbound/dnsbl or download_dnsbl
        print("[*] Triggering DNSBL Download & Update (this may take a few seconds)...")
        # Proviamo l'azione dnsbl che di solito fa tutto (download + reload)
        action_r = requests.post(f"{args.url}/api/core/configd/run/unbound/dnsbl", auth=auth, verify=False)
        
        if action_r.status_code != 200:
            # Fallback if the action is named differently
            print("[*] Trying alternative update action...")
            action_r = requests.post(f"{args.url}/api/core/configd/run/unbound/download_dnsbl", auth=auth, verify=False)
        
        # 3. Final Reconfigure to be sure
        print("[*] Final Unbound reconfigure...")
        requests.post(f"{args.url}/api/unbound/service/reconfigure", auth=auth, verify=False)
        
        print("[SUCCESS] All automated steps completed.")

    except Exception as e:
        print(f"[ERROR] {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()

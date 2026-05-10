import json
import ssl
import urllib.request
import urllib.error
import argparse
import sys
import os
# Import sourcing logic from validate_rete_dns
import validate_rete_dns

def get_opnsense_overrides(url, api_key, api_secret):
    """Fetch existing Host Overrides from OPNsense"""
    # Sanitize inputs (remove quotes potentially captured from shell extraction)
    api_key = api_key.strip().strip("'").strip('"')
    api_secret = api_secret.strip().strip("'").strip('"')

    endpoint = f"{url}/api/unbound/settings/searchHostOverride"
    print(f"DEBUG: Connecting to {endpoint}")
    print(f"DEBUG: API Key length: {len(api_key) if api_key else 0}")
    print(f"DEBUG: API Secret length: {len(api_secret) if api_secret else 0}")

    # Force Basic Auth Header
    import base64
    credentials = f"{api_key}:{api_secret}"
    auth_header = "Basic " + base64.b64encode(credentials.encode()).decode()

    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE

    try:
        req = urllib.request.Request(endpoint, method='POST', data=b'{}', headers={
            'Content-Type': 'application/json',
            'Authorization': auth_header
        })
        with urllib.request.urlopen(req, context=ctx) as response:
            raw_data = response.read().decode('utf-8')
            try:
                data = json.loads(raw_data)
                # OPNsense usually returns { 'rows': [...] } for grids
                return data.get('rows', [])
            except json.JSONDecodeError as e:
                print(f"DEBUG: Failed to decode JSON from OPNsense.")
                print(f"DEBUG: Response Status: {response.status}")
                print(f"DEBUG: Raw Response Content:\n{raw_data}")
                raise e
    except urllib.error.HTTPError as e:
        print(f"Error fetching overrides: {e.code} {e.reason}")
        try:
            print(e.read().decode())
        except:
            pass
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

def delete_override(uuid, url, api_key, api_secret):
    """Delete a specific override by UUID"""
    # Sanitize inputs
    api_key = api_key.strip().strip("'").strip('"')
    api_secret = api_secret.strip().strip("'").strip('"')

    endpoint = f"{url}/api/unbound/settings/delHostOverride/{uuid}"

    # Force Basic Auth Header
    import base64
    credentials = f"{api_key}:{api_secret}"
    auth_header = "Basic " + base64.b64encode(credentials.encode()).decode()

    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE

    try:
        req = urllib.request.Request(endpoint, method='POST', data=b'{}', headers={
            'Content-Type': 'application/json',
            'Authorization': auth_header
        })
        with urllib.request.urlopen(req, context=ctx) as response:
            result = json.loads(response.read().decode('utf-8'))
            if result.get('result') != 'saved':
                print(f"Warning deleting {uuid}: {result}")
            else:
                print(f"✅ Deleted UUID {uuid}")
    except Exception as e:
        print(f"Error deleting {uuid}: {e}")

def main():
    import os
    script_dir = os.path.dirname(os.path.abspath(__file__))
    # Go up 3 levels: scripts -> playbooks -> ansible -> repo root
    project_root = os.path.abspath(os.path.join(script_dir, '../../../'))
    default_rete = os.path.join(project_root, 'rete.json')

    parser = argparse.ArgumentParser()
    parser.add_argument('--api-key', required=True, help="OPNsense API Key")
    parser.add_argument('--api-secret', required=True, help="OPNsense API Secret")
    parser.add_argument('--url', default="https://192.168.2.254", help="OPNsense URL")
    parser.add_argument('--file', default=default_rete, help='Path to rete.json')
    parser.add_argument('--dry-run', action='store_true', help="Do not actually delete")
    args = parser.parse_args()

    # 1. Get Desired State
    print("\n--- 1. Loading Desired State from rete.json ---")
    desired_records = validate_rete_dns.check_duplicates(args.file, mode='return')
    print(f"Found {len(desired_records)} canonical records.")

    # 2. Get Current State
    print("\n--- 2. Fetching Current State from OPNsense ---")
    current_overrides = get_opnsense_overrides(args.url, args.api_key, args.api_secret)
    print(f"Found {len(current_overrides)} existing overrides.")

    # 3. Compare & Prune
    print("\n--- 3. Analyzing Conflicts (Pruning Mode) ---")

    # We want to find overrides in OPNsense that:
    # A) Have a hostname/domain that matches a desired record but a DIFFERENT IP.
    # B) (Optional) Are completely unknown (orphans).
    #    For safety, let's stick to (A) - fixing conflicts for known hosts first.

    desired_map = {} # (hostname, domain) -> ip
    for r in desired_records:
        key = (r['hostname'], 'pindaroli.org')
        desired_map[key] = r['ip']

    orphans = []
    conflicts = []
    exact_duplicates = []
    seen_in_opnsense = set()

    for row in current_overrides:
        hostname = row.get('hostname')
        domain = row.get('domain')
        ip = row.get('server')
        uuid = row.get('uuid')

        key = (hostname, domain)

        if key in desired_map:
            # It's a known host.
            if key in seen_in_opnsense:
                print(f"♻️  DUPLICATE: {hostname}.{domain} -> {ip} (Already exists, extra entry found)")
                exact_duplicates.append(row)
                continue

            seen_in_opnsense.add(key)

            # Check IP.
            expected_ip = desired_map[key]
            if ip != expected_ip:
                print(f"❌ CONFLICT: {hostname}.{domain}")
                print(f"   Current (OPNsense): {ip}")
                print(f"   Desired (rete.json): {expected_ip}")
                conflicts.append(row)
            else:
                # Matches perfectly.
                pass
        else:
            # Unknown host.
            print(f"⚠️  ORPHAN: {hostname}.{domain} -> {ip} (Not in rete.json)")
            orphans.append(row)

    # 4. Execute Pruning
    if not conflicts and not orphans and not exact_duplicates:
        print("\n✅ System matches Desired State. No pruning needed.")
        return

    to_delete = conflicts + exact_duplicates

    if os.environ.get('PRUNE_ORPHANS') == 'true':
         to_delete += orphans

    print(f"\n--- 4. Execution (Pruning {len(to_delete)} records) ---")
    if args.dry_run:
        print("DRY RUN: No changes made.")
        for item in to_delete:
            print(f"[DRY-RUN] Would delete {item['hostname']} ({item['server']}) - UUID: {item['uuid']}")
    else:
        for item in to_delete:
            print(f"Deleting {item['hostname']} ({item['server']})...")
            delete_override(item['uuid'], args.url, args.api_key, args.api_secret)

        # Apply changes (Reconfigure Unbound)
        print("Applying configuration...")
        ep = f"{args.url}/api/unbound/service/reconfigure"

        # Force Basic Auth Header
        import base64
        # Sanitize inputs
        key = args.api_key.strip().strip("'").strip('"')
        secret = args.api_secret.strip().strip("'").strip('"')

        credentials = f"{key}:{secret}"
        auth_header = "Basic " + base64.b64encode(credentials.encode()).decode()

        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE

        req = urllib.request.Request(ep, method='POST', data=b'{}', headers={
            'Content-Type': 'application/json',
            'Authorization': auth_header
        })
        try:
             urllib.request.urlopen(req, context=ctx)
             print("✅ Configuration Applied.")
        except Exception as e:
             print(f"Error applying config: {e}")

if __name__ == "__main__":
    main()

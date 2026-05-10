import json
import ssl
import urllib.request
import urllib.error
import sys
import argparse
import base64

def get_kea_subnets(url, auth_header, ctx):
    endpoint = f"{url}/api/kea/dhcpv4/searchSubnet"
    try:
        req = urllib.request.Request(endpoint, headers={'Authorization': auth_header})
        with urllib.request.urlopen(req, context=ctx) as response:
            data = json.loads(response.read().decode('utf-8'))
            return data.get('rows', [])
    except Exception as e:
        print(f"Error fetching Kea subnets: {e}")
        return []

def push_kea_dhcp_reservations(url, api_key, api_secret, reservations):
    api_key = api_key.strip().strip("'").strip('"')
    api_secret = api_secret.strip().strip("'").strip('"')

    credentials = f"{api_key}:{api_secret}"
    auth_header = "Basic " + base64.b64encode(credentials.encode()).decode()

    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE

    print("Fetching active Kea Subnets to map reservations...")
    subnets = get_kea_subnets(url, auth_header, ctx)
    if not subnets:
        print("No Kea subnets found or API error. Cannot map reservations without a Subnet UUID.")
        sys.exit(1)

    print(f"Applying {len(reservations)} DHCP Reservations via Kea API...")

    for item in reservations:
        # Kea DHCPv4 needs the subnet uuid. We map it by checking if the IP fits in the subnet
        # For our simple homelab, we just fetch the subnet by interface or rough match
        # The user has subnet "10.10.20.0/24" for opt2. We'll string match the first 3 octets
        ip_prefix = ".".join(item['ip'].split('.')[:3])
        target_subnet_uuid = None

        for sub in subnets:
            if sub['subnet'].startswith(ip_prefix):
                 target_subnet_uuid = sub['uuid']
                 break

        if not target_subnet_uuid:
             print(f"  -> ERROR: Could not find a Kea Subnet UUID matching IP {item['ip']} for hostname {item['hostname']}")
             continue

        endpoint = f"{url}/api/kea/dhcpv4/addReservation"
        print(f"Applying: {item['hostname']} ({item['ip']} / {item['mac']}) -> Subnet UUID: {target_subnet_uuid}")

        payload = {
            "reservation": {
                "hw_address": item['mac'],
                "ip_address": item['ip'],
                "hostname": item['hostname'],
                "description": item['descr'],
                "subnet": target_subnet_uuid
            }
        }

        try:
            req = urllib.request.Request(endpoint, method='POST', data=json.dumps(payload).encode('utf-8'), headers={
                'Content-Type': 'application/json',
                'Authorization': auth_header
            })
            with urllib.request.urlopen(req, context=ctx) as response:
                result = json.loads(response.read().decode('utf-8'))
                if result.get('result') != 'saved':
                    print(f"  -> WARNING/INFO: {result}")
                else:
                    print(f"  -> ✅ SUCCESS")
        except urllib.error.HTTPError as e:
            print(f"  -> Error applying {item['hostname']}: {e.code} - {e.reason}")
            try:
                print(e.read().decode())
            except:
                pass
        except Exception as e:
            print(f"  -> Error applying {item['hostname']}: {e}")

    # Reconfigure KEA
    print("\nApplying Kea Configuration...")
    try:
        req = urllib.request.Request(f"{url}/api/kea/service/reconfigure", method='POST', data=b'{}', headers={
            'Content-Type': 'application/json',
            'Authorization': auth_header
        })
        with urllib.request.urlopen(req, context=ctx) as response:
            result = json.loads(response.read().decode('utf-8'))
            print("✅ Kea DHCP Reconfigured.")
    except Exception as e:
         print(f"Error reconfiguring Kea: {e}")

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--api-key', required=True)
    parser.add_argument('--api-secret', required=True)
    parser.add_argument('--url', default="https://192.168.2.254")
    parser.add_argument('--file', help='JSON file containing reservations', default='-')

    args = parser.parse_args()

    if args.file == '-':
        data = sys.stdin.read()
    else:
        with open(args.file, 'r') as f:
            data = f.read()

    try:
        reservations = json.loads(data)
    except Exception as e:
        print(f"Error parsing JSON reservations: {e}")
        sys.exit(1)

    push_kea_dhcp_reservations(args.url, args.api_key, args.api_secret, reservations)

if __name__ == "__main__":
    main()

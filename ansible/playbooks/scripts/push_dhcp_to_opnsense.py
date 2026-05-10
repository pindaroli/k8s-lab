import json
import ssl
import urllib.request
import urllib.error
import argparse
import sys
import base64

def push_dhcp_reservations(url, api_key, api_secret, reservations):
    # Sanitize inputs
    api_key = api_key.strip().strip("'").strip('"')
    api_secret = api_secret.strip().strip("'").strip('"')

    credentials = f"{api_key}:{api_secret}"
    auth_header = "Basic " + base64.b64encode(credentials.encode()).decode()

    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE

    for item in reservations:
        print(f"Applying DHCP Reservation: {item['hostname']} ({item['ip']} / {item['mac']}) to {item['interface']}...")

        # We need to hit the OPNsense API to add a static DHCP map
        # Endpoint: /api/dhcpv4/settings/addStaticMap/<interface>
        endpoint = f"{url}/api/dhcpv4/settings/addStaticMap/{item['interface']}"

        payload = {
            "staticmap": {
                "mac": item['mac'],
                "ipaddr": item['ip'],
                "hostname": item['hostname'],
                "descr": item['descr']
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
                    # Sometimes it complains it already exists or returns validation errors
                    print(f"  -> WARNING/INFO: {result}")
                else:
                    print(f"  -> ✅ SUCCESS")
        except Exception as e:
            print(f"  -> Error applying {item['hostname']}: {e}")

    # Reconfigure DHCP Server to apply changes
    print("\nApplying DHCP Configuration...")
    try:
        req = urllib.request.Request(f"{url}/api/dhcpv4/service/reconfigure", method='POST', data=b'{}', headers={
            'Content-Type': 'application/json',
            'Authorization': auth_header
        })
        with urllib.request.urlopen(req, context=ctx) as response:
            result = json.loads(response.read().decode('utf-8'))
            print("✅ DHCP Reconfigured.")
    except Exception as e:
        print(f"Error reconfiguring DHCP: {e}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--api-key', required=True)
    parser.add_argument('--api-secret', required=True)
    parser.add_argument('--url', default="https://192.168.2.254")
    parser.add_argument('--file', help='JSON file containing reservations (output of extract_dhcp)', default='-')

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

    push_dhcp_reservations(args.url, args.api_key, args.api_secret, reservations)

if __name__ == "__main__":
    main()

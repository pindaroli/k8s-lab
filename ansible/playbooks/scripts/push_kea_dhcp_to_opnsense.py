import json
import ssl
import urllib.request
import urllib.error
import sys
import argparse
import base64
import ipaddress

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_ctx():
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    return ctx

def _auth_header(api_key, api_secret):
    credentials = f"{api_key.strip()}:{api_secret.strip()}"
    return "Basic " + base64.b64encode(credentials.encode()).decode()

def _post(url, payload, auth_header, ctx):
    req = urllib.request.Request(
        url, method='POST',
        data=json.dumps(payload).encode('utf-8'),
        headers={'Content-Type': 'application/json', 'Authorization': auth_header},
    )
    with urllib.request.urlopen(req, context=ctx) as resp:
        return json.loads(resp.read().decode('utf-8'))

def _get(url, auth_header, ctx):
    req = urllib.request.Request(url, headers={'Authorization': auth_header})
    with urllib.request.urlopen(req, context=ctx) as resp:
        return json.loads(resp.read().decode('utf-8'))

# ---------------------------------------------------------------------------
# Kea Subnets (discovery)
# ---------------------------------------------------------------------------

def get_kea_subnets(base_url, auth_header, ctx):
    try:
        data = _get(f"{base_url}/api/kea/dhcpv4/searchSubnet", auth_header, ctx)
        return data.get('rows', [])
    except Exception as e:
        print(f"[ERROR] Fetching Kea subnets: {e}")
        return []

def _find_subnet_uuid(subnets, ip_str):
    """Trova l'UUID della subnet Kea che contiene l'IP specificato."""
    try:
        ip = ipaddress.ip_address(ip_str.split('/')[0])
    except ValueError:
        return None
    for sub in subnets:
        try:
            network = ipaddress.ip_network(sub['subnet'], strict=False)
            if ip in network:
                return sub['uuid']
        except Exception:
            continue
    return None

# ---------------------------------------------------------------------------
# Phase A: Sync Subnet Global Options
# ---------------------------------------------------------------------------

def sync_subnet_options(base_url, auth_header, ctx, subnet_options, subnets):
    """
    Per ogni subnet in subnet_options (letta da rete.json → sezione VLAN),
    trova il UUID corrispondente su OPNsense e aggiorna le opzioni globali
    (gateway, dns, domain) tramite setSubnet.
    Idempotente: l'API setSubnet sovrascrive sempre il valore corrente.
    """
    print("\n=== Phase A: Sync Subnet Global Options ===")
    if not subnet_options:
        print("  Nessuna subnet_option trovata — step saltato.")
        return

    for cidr, opts in subnet_options.items():
        # Trova UUID matching
        uuid = None
        for sub in subnets:
            if sub.get('subnet') == cidr:
                uuid = sub['uuid']
                break

        if not uuid:
            print(f"  [SKIP] Subnet {cidr} non trovata su OPNsense Kea.")
            continue

        gateway = opts.get('gateway', '')
        dns     = opts.get('dns', '').split(',')[0].strip()  # primo DNS
        domain  = opts.get('domain', '')

        # Il formato corretto per setSubnet usa valori stringa semplici in option_data
        payload = {
            'subnet4': {
                'option_data': {
                    'routers':             gateway,
                    'domain_name_servers': dns,
                    'domain_name':         domain,
                }
            }
        }

        print(f"  Aggiorno subnet {cidr} (UUID: {uuid}) → routers={gateway}, domain_name_servers={dns}, domain={domain}")
        try:
            result = _post(f"{base_url}/api/kea/dhcpv4/setSubnet/{uuid}", payload, auth_header, ctx)
            if result.get('result') == 'saved':
                print(f"  ✅ UPDATED")
            else:
                print(f"  ⚠️  WARNING: {result}")
        except Exception as e:
            print(f"  [ERROR] setSubnet {cidr}: {e}")

# ---------------------------------------------------------------------------
# Phase B: Sync Reservations (check-before-write)
# ---------------------------------------------------------------------------

def _search_reservation_by_mac(base_url, auth_header, ctx, mac):
    """Cerca una reservation esistente per MAC address. Restituisce (uuid, data) o (None, None)."""
    try:
        data = _get(
            f"{base_url}/api/kea/dhcpv4/searchReservation?searchPhrase={mac}",
            auth_header, ctx,
        )
        rows = data.get('rows', [])
        for row in rows:
            if row.get('hw_address', '').lower() == mac.lower():
                return row.get('uuid'), row
    except Exception as e:
        print(f"    [WARN] searchReservation per {mac}: {e}")
    return None, None

def sync_reservations(base_url, auth_header, ctx, reservations, subnets):
    """
    Sincronizza le reservation per-host. Per ogni entry:
      1. Cerca la reservation per MAC su OPNsense.
      2. Se NON esiste → addReservation.
      3. Se esiste e i dati sono diversi → setReservation/<uuid> (update).
      4. Se esiste e i dati sono identici → SKIP (già aggiornato).
    Idempotente per tutti e tre i casi.
    """
    print("\n=== Phase B: Sync Reservations (check-before-write) ===")
    print(f"  Elaboro {len(reservations)} reservation da rete.json...")

    for item in reservations:
        hostname = item['hostname']
        ip       = item['ip'].split('/')[0]  # rimuove eventuale CIDR suffix
        mac      = item['mac']
        descr    = item.get('descr', '')

        subnet_uuid = _find_subnet_uuid(subnets, ip)
        if not subnet_uuid:
            print(f"  [SKIP] {hostname} ({ip}): nessuna subnet Kea trovata.")
            continue

        payload = {
            "reservation": {
                "hw_address":  mac,
                "ip_address":  ip,
                "hostname":    hostname,
                "description": descr,
                "subnet":      subnet_uuid,
            }
        }

        # Check-before-write
        existing_uuid, existing = _search_reservation_by_mac(base_url, auth_header, ctx, mac)

        if existing_uuid is None:
            # Caso 1: Non esiste → ADD
            print(f"  [ADD] {hostname} ({ip} / {mac})")
            try:
                result = _post(f"{base_url}/api/kea/dhcpv4/addReservation", payload, auth_header, ctx)
                if result.get('result') == 'saved':
                    print(f"    ✅ ADDED")
                else:
                    print(f"    ⚠️  {result}")
            except urllib.error.HTTPError as e:
                body = e.read().decode() if hasattr(e, 'read') else ''
                print(f"    [ERROR] {e.code} {e.reason}: {body}")
            except Exception as e:
                print(f"    [ERROR] {e}")
        else:
            # Casi 2/3: Esiste → verifica se aggiornamento necessario
            needs_update = (
                existing.get('ip_address') != ip
                or existing.get('hostname') != hostname
                or existing.get('description') != descr
            )
            if not needs_update:
                print(f"  [SKIP] {hostname} ({ip} / {mac}) — già aggiornato")
                continue

            # Caso 2: Esiste ma diverso → UPDATE
            print(f"  [UPDATE] {hostname} ({ip} / {mac}) — UUID: {existing_uuid}")
            try:
                result = _post(f"{base_url}/api/kea/dhcpv4/setReservation/{existing_uuid}", payload, auth_header, ctx)
                if result.get('result') == 'saved':
                    print(f"    ✅ UPDATED")
                else:
                    print(f"    ⚠️  {result}")
            except Exception as e:
                print(f"    [ERROR] setReservation: {e}")

# ---------------------------------------------------------------------------
# Reconfigure Kea
# ---------------------------------------------------------------------------

def reconfigure_kea(base_url, auth_header, ctx):
    print("\n=== Reconfigure Kea ===")
    try:
        result = _post(f"{base_url}/api/kea/service/reconfigure", {}, auth_header, ctx)
        print("✅ Kea DHCP Reconfigured.")
    except Exception as e:
        print(f"[ERROR] Reconfigure Kea: {e}")

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Sincronizza Kea DHCP su OPNsense: subnet globali + reservation per-host da rete.json."
    )
    parser.add_argument('--api-key',    required=True)
    parser.add_argument('--api-secret', required=True)
    parser.add_argument('--url',        default="https://192.168.2.254")
    parser.add_argument('--file',       help='JSON prodotto da extract_dhcp_from_rete_json.py', default='-')

    args = parser.parse_args()

    if args.file == '-':
        raw = sys.stdin.read()
    else:
        with open(args.file, 'r') as f:
            raw = f.read()

    try:
        data = json.loads(raw)
    except Exception as e:
        print(f"[ERROR] Parsing JSON input: {e}")
        sys.exit(1)

    subnet_options = data.get('subnet_options', {})
    reservations   = data.get('reservations', [])

    api_key    = args.api_key.strip().strip("'\"")
    api_secret = args.api_secret.strip().strip("'\"")
    auth       = _auth_header(api_key, api_secret)
    ctx        = _make_ctx()
    base_url   = args.url.rstrip('/')

    print(f"Connessione a OPNsense: {base_url}")
    subnets = get_kea_subnets(base_url, auth, ctx)
    if not subnets:
        print("[ERROR] Nessuna subnet Kea trovata — impossibile procedere.")
        sys.exit(1)
    print(f"  Trovate {len(subnets)} subnet Kea: {[s['subnet'] for s in subnets]}")

    # Fase A: opzioni globali subnet
    sync_subnet_options(base_url, auth, ctx, subnet_options, subnets)

    # Fase B: reservation per-host
    sync_reservations(base_url, auth, ctx, reservations, subnets)

    # Applica configurazione
    reconfigure_kea(base_url, auth, ctx)

if __name__ == "__main__":
    main()

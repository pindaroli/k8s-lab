import json
import argparse

def get_opnsense_interface(ip):
    if not ip:
        return None
    if ip.startswith('10.10.10.'): return 'opt1' # VLAN 10 Server
    if ip.startswith('10.10.20.'): return 'opt2' # VLAN 20 Client
    if ip.startswith('10.10.30.'): return 'opt3' # VLAN 30 IoT
    if ip.startswith('192.168.2.'): return 'opt4' # Transit
    if ip.startswith('192.168.100.'): return 'lan' # Admin LAN
    return None

def extract_subnet_options(data):
    """
    Legge la sezione VLAN di rete.json e restituisce le opzioni DHCP globali
    per subnet (gateway, dns, domain). Solo le VLAN con blocco 'dhcp' sono incluse.
    Chiave = subnet CIDR, valore = dict con gateway/dns/domain.
    """
    options = {}
    for vlan in data.get('VLAN', []):
        subnet = vlan.get('subnet')
        dhcp = vlan.get('dhcp')
        if subnet and dhcp:
            options[subnet] = {
                'mode':        dhcp.get('mode', 'relay'),
                'opnsense_ip': dhcp.get('opnsense_ip'),
                'pool_start':  dhcp.get('pool_start'),
                'pool_end':    dhcp.get('pool_end'),
                'gateway':     dhcp.get('gateway'),
                'dns':         dhcp.get('dns'),
                'domain':      dhcp.get('domain', ''),
            }
    return options

def extract_reservations(data):
    """
    Percorre la sezione 'nodi' di rete.json ed estrae tutte le reservation DHCP
    per-host (MAC → IP). Non include gateway/dns per-host: i client ereditano
    le opzioni dalla subnet globale configurata da extract_subnet_options().
    """
    reservations = []

    for node in data.get('nodi', []):
        if str(node.get('status', '')).lower() == 'removed':
            continue

        node_id    = node.get('id', 'unknown')
        node_label = node.get('label', node_id)

        # MAC a livello root del nodo
        if 'mac' in node:
            ip = (node.get('ip') or node.get('management_ip')
                  or node.get('client_ip_vlan20') or node.get('management_ip_vlan10'))
            if ip:
                reservations.append({
                    'hostname':  node_id,
                    'ip':        ip,
                    'mac':       node['mac'],
                    'interface': get_opnsense_interface(ip),
                    'descr':     node.get('description') or node.get('notes') or node_label,
                })

        # MAC sulle interfacce
        for iface in node.get('interfaces', []):
            if 'mac' in iface:
                ip = iface.get('ip')
                if ip:
                    descr    = (iface.get('description') or iface.get('notes')
                                or f"{node_label} - {iface.get('interface', '')}")
                    hostname = node_id.replace(' ', '-')
                    reservations.append({
                        'hostname':  hostname,
                        'ip':        ip,
                        'mac':       iface['mac'],
                        'interface': get_opnsense_interface(ip),
                        'descr':     descr,
                    })

        # MAC sulle porte fisiche (e relative logical_interfaces)
        for port in node.get('ports', []):
            if 'mac' in port:
                ip = port.get('ip')
                if ip:
                    reservations.append({
                        'hostname':  f"{node_id}-port{port.get('id', '')}",
                        'ip':        ip,
                        'mac':       port['mac'],
                        'interface': get_opnsense_interface(ip),
                        'descr':     port.get('description') or port.get('role') or node_label,
                    })
            for log_if in port.get('logical_interfaces', []):
                if 'mac' in log_if:
                    subnet = log_if.get('subnet', '')
                    ip     = subnet.split('/')[0] if '/' in subnet else subnet
                    if ip:
                        reservations.append({
                            'hostname':  f"{node_id}-{log_if.get('name', 'intf')}",
                            'ip':        ip,
                            'mac':       log_if['mac'],
                            'interface': get_opnsense_interface(ip),
                            'descr':     log_if.get('description') or log_if.get('name') or node_label,
                        })

    # Scarta entry senza un'interfaccia OPNsense mappata
    return [r for r in reservations if r['interface'] is not None]

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Estrae da rete.json le opzioni DHCP globali (per subnet) e le reservation per-host."
    )
    parser.add_argument('--file', required=True, help='Path to rete.json')
    args = parser.parse_args()

    with open(args.file, 'r') as f:
        data = json.load(f)

    output = {
        'subnet_options': extract_subnet_options(data),
        'reservations':   extract_reservations(data),
    }
    print(json.dumps(output, indent=2))

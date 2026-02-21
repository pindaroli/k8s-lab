import json
import argparse
import sys

def get_opnsense_interface(ip):
    if not ip:
        return None
    if ip.startswith('10.10.10.'): return 'opt1' # VLAN 10 Server
    if ip.startswith('10.10.20.'): return 'opt2' # VLAN 20 Client
    if ip.startswith('10.10.30.'): return 'opt3' # VLAN 30 IoT
    if ip.startswith('192.168.2.'): return 'opt4' # Transit
    if ip.startswith('192.168.100.'): return 'lan' # Admin LAN
    return None

def extract_dhcp(file_path):
    with open(file_path, 'r') as f:
        data = json.load(f)
        
    reservations = []
    
    for node in data.get('nodi', []):
        if str(node.get('status', '')).lower() == 'removed':
            continue

        node_id = node.get('id', 'unknown')
        node_label = node.get('label', node_id)
        
        # Check root level MAC
        if 'mac' in node:
            ip = node.get('ip') or node.get('management_ip') or node.get('client_ip_vlan20') or node.get('management_ip_vlan10')
            if ip:
                reservations.append({
                    'hostname': node_id,
                    'ip': ip,
                    'mac': node['mac'],
                    'interface': get_opnsense_interface(ip),
                    'descr': node.get('description') or node.get('notes') or node_label
                })
                
        # Check interfaces list
        for iface in node.get('interfaces', []):
            if 'mac' in iface:
                ip = iface.get('ip')
                if ip:
                    descr = iface.get('description') or iface.get('notes') or f"{node_label} - {iface.get('interface', '')}"
                    hostname = node_id
                    # clean up spaces in hostname for DHCP
                    hostname = hostname.replace(' ', '-')
                    
                    reservations.append({
                        'hostname': hostname,
                        'ip': ip,
                        'mac': iface['mac'],
                        'interface': get_opnsense_interface(ip),
                        'descr': descr
                    })
                    
        # Check ports -> logical_interfaces
        for port in node.get('ports', []):
            if 'mac' in port:
                ip = port.get('ip') # Sometimes MAC is on the port itself with an IP
                if ip:
                    reservations.append({
                        'hostname': f"{node_id}-port{port.get('id', '')}",
                        'ip': ip,
                        'mac': port['mac'],
                        'interface': get_opnsense_interface(ip),
                        'descr': port.get('description') or port.get('role') or node_label
                    })
            for log_if in port.get('logical_interfaces', []):
                if 'mac' in log_if:
                    subnet = log_if.get('subnet', '')
                    ip = subnet.split('/')[0] if '/' in subnet else subnet
                    if ip:
                        reservations.append({
                            'hostname': f"{node_id}-{log_if.get('name', 'intf')}",
                            'ip': ip,
                            'mac': log_if['mac'],
                            'interface': get_opnsense_interface(ip),
                            'descr': log_if.get('description') or log_if.get('name') or node_label
                        })

    # Filter out anything without a valid interface mapped
    filtered_reservations = [r for r in reservations if r['interface'] is not None]
    return filtered_reservations

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--file', required=True, help='Path to rete.json')
    args = parser.parse_args()
    
    results = extract_dhcp(args.file)
    print(json.dumps(results, indent=2))

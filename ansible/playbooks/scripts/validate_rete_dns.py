import json
import re

def get_ip(node):
    # Replicating Ansible IP precedence logic
    if 'ip' in node: return node['ip']
    if 'management IP' in node: return node['management IP']
    if 'management_ip' in node: return node['management_ip']
    if 'management_ip_vlan10' in node: return node['management_ip_vlan10']
    
    if 'interfaces' in node:
        for iface in node['interfaces']:
            if 'ip' in iface: return iface['ip']
            
    if 'ports' in node:
        for port in node['ports']:
            if 'logical_interfaces' in port:
                for log_if in port['logical_interfaces']:
                    if 'subnet' in log_if:
                         return log_if['subnet'].split('/')[0]
    return None

def check_duplicates(file_path, mode='validate'):
    with open(file_path, 'r') as f:
        data = json.load(f)
        
    records = []
    
    # 1. Parse all nodes
    for node in data.get('nodi', []):
        ip = get_ip(node)
        if not ip:
            continue
            
        # Primary ID
        records.append({
            'hostname': node.get('id'),
            'ip': ip,
            'source': f"Node ID: {node.get('id')}"
        })
        
        # Aliases
        for alias in node.get('aliases', []):
            records.append({
                'hostname': alias,
                'ip': ip,
                'source': f"Alias of {node.get('id')}"
            })
            
            # Traefik Internal Aliases Logic
            if node.get('id') == 'traefik-lb' and not alias.endswith('-internal'):
                records.append({
                    'hostname': f"{alias}-internal",
                    'ip': ip,
                    'source': f"Auto-Internal Alias of {alias}"
                })

    # 2. Analyze or Output
    if mode == 'json':
        # Transform for Output
        output_list = []
        for r in records:
            output_list.append({
                'hostname': r['hostname'],
                'domain': 'pindaroli.org', # Hardcoded or pass as arg? Keeping simple for now as per rete.json context
                'ip': r['ip'],
                'desc': r['source']
            })
        print(json.dumps(output_list, indent=2))
        return

    # Debug / Validation Mode
    seen_exact = {} # (host, ip) -> count
    seen_host = {}  # host -> {ip1, ip2}
    
    issues_found = False
    
    print(f"--- Scanning {len(records)} generated DNS records from rete.json ---\n")

    for r in records:
        pair = (r['hostname'], r['ip'])
        host = r['hostname']
        
        # Check Exact Duplicates
        if pair in seen_exact:
            print(f"[DUPLICATE] {host} -> {r['ip']}")
            print(f"  - Source 1: {seen_exact[pair]['source']}")
            print(f"  - Source 2: {r['source']}")
            issues_found = True
        else:
            seen_exact[pair] = r
            
        # Check Conflicts (Split-Brain)
        if host in seen_host:
            if r['ip'] not in seen_host[host]:
                print(f"[CONFLICT] {host} resolves to multiple IPs:")
                print(f"  - {seen_host[host]}")
                print(f"  - {r['ip']} (Source: {r['source']})")
                issues_found = True
                seen_host[host].add(r['ip'])
        else:
            seen_host[host] = {r['ip']}

    if not issues_found:
        print("✅ No duplicates or conflicts found in rete.json.")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--file', default='../../rete.json', help='Path to rete.json')
    parser.add_argument('--json', action='store_true', help='Output results as JSON for Ansible')
    args = parser.parse_args()
    
    check_duplicates(args.file, mode='json' if args.json else 'validate')

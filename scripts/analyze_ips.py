import json
import os

def analyze_rete(file_path):
    if not os.path.exists(file_path):
        print(f"Error: {file_path} not found.")
        return

    with open(file_path, 'r') as f:
        data = json.load(f)

    ip_map = {}

    def add_ip(ip, aliases):
        if not ip:
            return
        # Clean IP if it has subnet mask
        ip = ip.split('/')[0].strip()
        if ip.endswith('.0'):
            return
        # Clean aliases
        clean_aliases = []
        for a in aliases:
            if a:
                # Basic DNS sanitization: spaces and colons to hyphens, all lowercase, remove parentheses
                safe_a = str(a).strip().lower().replace(' ', '-').replace(':', '-').replace('(', '').replace(')', '')
                # Ensure no trailing hyphens
                safe_a = safe_a.strip('-')
                if safe_a:
                    clean_aliases.append(safe_a)
        
        if ip not in ip_map:
            ip_map[ip] = set()
        ip_map[ip].update(clean_aliases)

    for node in data.get('nodi', []):
        node_id = node.get('id')
        hostname = node.get('hostname')
        node_aliases = node.get('aliases', [])
        
        # Base aliases for this node
        base_aliases = [node_id, hostname] + node_aliases
        base_aliases = [a for a in base_aliases if a]

        # Check various IP fields
        add_ip(node.get('management_ip'), base_aliases)
        add_ip(node.get('ip'), base_aliases)
        
        # VIPs defined inside a host node are shared cluster IPs, not the host itself.
        # We don't attach the host's base_aliases (like 'k1') to the shared VIP.
        if node.get('vip'):
            add_ip(node.get('vip'), [f"{node_id}-shared-vip"])
        
        # Check interfaces list
        for iface in node.get('interfaces', []):
            # We explicitly ignore the 'network' (description) field now.
            # We ignore the 'interface' string (en0, eth0) as a DNS name, but we can assign an explicit alias if needed.
            # Usually, interface IPs without explicit names just resolve back to the main node_id.
            add_ip(iface.get('ip'), [node_id])

        # Check logical_interfaces (in ports)
        for port in node.get('ports', []):
            for log_iface in port.get('logical_interfaces', []):
                # DNS Policy: Only use the explicit functional 'name' (e.g., gw-vlan20), ignore 'interface' (opt2)
                log_name = log_iface.get('name', '')
                log_aliases = [f"{node_id}-{log_name}"] if log_name else [node_id]
                
                # Use only explicitly defined IP, avoid subnet strings.
                if 'ip' in log_iface:
                    add_ip(log_iface['ip'], log_aliases)

    # Sort IPs for better readability
    sorted_ips = sorted(ip_map.keys(), key=lambda x: [int(part) if part.isdigit() else 0 for part in x.split('.')])

    print("| IP Address | Aliases |")
    print("| :--- | :--- |")
    for ip in sorted_ips:
        aliases = sorted(list(ip_map[ip]))
        print(f"| {ip} | {', '.join(aliases)} |")

    # Reverse mapping to check for duplicated names
    print("\n\n### Duplicate Name Analysis")
    alias_map = {}
    for ip, aliases in ip_map.items():
        for a in aliases:
            if a not in alias_map:
                alias_map[a] = []
            alias_map[a].append(ip)
    
    found_duplicates = False
    for a, ips in alias_map.items():
        if len(ips) > 1:
            print(f"- **WARNING**: The name `{a}` points to multiple IPs: {', '.join(ips)}")
            found_duplicates = True
            
    if not found_duplicates:
        print("- **OK**: No duplicated names found across different IPs.")

if __name__ == "__main__":
    analyze_rete('/Users/olindo/prj/k8s-lab/rete.json')

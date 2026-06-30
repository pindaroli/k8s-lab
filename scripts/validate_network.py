#!/usr/bin/env python3
import json
import sys
import re
import ipaddress

def load_network_data(filepath):
    try:
        with open(filepath, 'r') as f:
            return json.load(f)
    except Exception as e:
        print(f"❌ Errore nel caricamento del file JSON {filepath}: {e}")
        sys.exit(1)

def validate_ip(ip_str):
    if not ip_str or ip_str.lower() in ['none', 'tbd', 'none (split-routing)']:
        return None
    # Rimuove subnet mask se presente (es. /24)
    ip_clean = ip_str.split('/')[0].strip()
    try:
        return ipaddress.ip_address(ip_clean)
    except ValueError:
        return None

def validate_mac(mac_str):
    if not mac_str or mac_str.lower() in ['none', 'tbd']:
        return None
    mac_clean = mac_str.strip().lower()
    # Verifica il formato standard del MAC address (xx:xx:xx:xx:xx:xx)
    if re.match(r'^([0-9a-f]{2}[:-]){5}([0-9a-f]{2})$', mac_clean):
        return mac_clean
    return None

def check_congruence(data):
    errors = []
    ips = {}      # IP -> list of host_ids
    macs = {}     # MAC -> list of host_ids

    nodi = data.get("nodi", [])

    for nodo in nodi:
        nodo_id = nodo.get("id", "sconosciuto")

        # 1. Controlla IP a livello di nodo principale
        m_ip = nodo.get("management_ip")
        if m_ip:
            ip_obj = validate_ip(m_ip)
            if ip_obj:
                ip_str = str(ip_obj)
                ips.setdefault(ip_str, []).append(f"{nodo_id} (management_ip)")

        n_ip = nodo.get("ip")
        if n_ip:
            ip_obj = validate_ip(n_ip)
            if ip_obj:
                ip_str = str(ip_obj)
                # I Virtual IP (VIP) sono condivisi per design, quindi saltiamo il check di duplicazione per loro
                is_vip = "vip" in nodo or nodo.get("role") == "Virtual IP"
                if not is_vip:
                    ips.setdefault(ip_str, []).append(f"{nodo_id} (ip)")

        # 2. Controlla MAC a livello di nodo principale
        n_mac = nodo.get("mac")
        if n_mac:
            mac_obj = validate_mac(n_mac)
            if mac_obj:
                macs.setdefault(mac_obj, []).append(f"{nodo_id} (mac)")

        # 3. Controlla porte del nodo
        ports = nodo.get("ports", [])
        for port in ports:
            port_id = port.get("id", "port")
            p_ip = port.get("ip")
            if p_ip:
                ip_obj = validate_ip(p_ip)
                if ip_obj:
                    ip_str = str(ip_obj)
                    ips.setdefault(ip_str, []).append(f"{nodo_id} (port {port_id} ip)")
            p_mac = port.get("mac")
            if p_mac:
                mac_obj = validate_mac(p_mac)
                if mac_obj:
                    macs.setdefault(mac_obj, []).append(f"{nodo_id} (port {port_id} mac)")

        # 4. Controlla interfacce del nodo
        interfaces = nodo.get("interfaces", [])
        for iface in interfaces:
            iface_name = iface.get("interface", "interface")
            i_ip = iface.get("ip")
            if i_ip:
                ip_obj = validate_ip(i_ip)
                if ip_obj:
                    ip_str = str(ip_obj)
                    ips.setdefault(ip_str, []).append(f"{nodo_id} (interface {iface_name} ip)")
            i_mac = iface.get("mac")
            if i_mac:
                mac_obj = validate_mac(i_mac)
                if mac_obj:
                    # Alcune interfacce virtuali (es. vlan su Mac Studio) condividono lo stesso MAC fisico,
                    # consentiamo la duplicazione solo se appartengono allo stesso nodo
                    macs.setdefault(mac_obj, []).append(f"{nodo_id} (interface {iface_name} mac)")

        # 5. Verifica coerenza delle Subnet (VLAN matching semplice)
        # Es. Se l'IP inizia con 10.10.20., deve appartenere alla VLAN 20
        all_node_ips = []
        for val in [m_ip, n_ip]:
            if val:
                ip_obj = validate_ip(val)
                if ip_obj:
                    all_node_ips.append((str(ip_obj), "nodo"))
        for port in ports:
            p_ip = port.get("ip")
            if p_ip:
                ip_obj = validate_ip(p_ip)
                if ip_obj:
                    all_node_ips.append((str(ip_obj), f"port {port.get('id')}"))
        for iface in interfaces:
            i_ip = iface.get("ip")
            if i_ip:
                ip_obj = validate_ip(i_ip)
                if ip_obj:
                    all_node_ips.append((str(ip_obj), f"interface {iface.get('interface')}"))

        network_context = nodo.get("network", "")
        for ip, source in all_node_ips:
            if ip.startswith("10.10.10.") and "VLAN 20" in network_context:
                errors.append(f"⚠️ Incoerenza subnet per {nodo_id} ({source}): IP {ip} associato a contesto {network_context}")
            elif ip.startswith("10.10.20.") and "VLAN 10" in network_context:
                errors.append(f"⚠️ Incoerenza subnet per {nodo_id} ({source}): IP {ip} associato a contesto {network_context}")

    # Analisi dei duplicati IP
    for ip, owners in ips.items():
        if len(owners) > 1:
            # Raggruppa per verificare se sono nodi distinti
            distinct_nodes = set([o.split()[0] for o in owners])
            if len(distinct_nodes) > 1:
                errors.append(f"❌ IP DUPLICATO: {ip} è usato da nodi differenti: {', '.join(owners)}")

    # Analisi dei duplicati MAC
    for mac, owners in macs.items():
        if len(owners) > 1:
            distinct_nodes = set([o.split()[0] for o in owners])
            if len(distinct_nodes) > 1:
                errors.append(f"❌ MAC DUPLICATO: {mac} è usato da nodi differenti: {', '.join(owners)}")

    return errors

def main():
    filepath = "rete.json"
    print(f"🔍 Avvio validazione di congruenza di {filepath}...")
    data = load_network_data(filepath)
    errors = check_congruence(data)

    if errors:
        print(f"❌ Trovate {len(errors)} incongruenze di configurazione:")
        for err in errors:
            print(f"  {err}")
        sys.exit(1)
    else:
        print("✅ Configurazione di rete congruente al 100%! Nessun IP o MAC duplicato rilevato.")
        sys.exit(0)

if __name__ == "__main__":
    main()

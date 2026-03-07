#!/usr/bin/env python3
"""
Homelab Diagnostics Script
Controlla lo stato di Proxmox, TrueNAS, Talos e della Rete via SSH e API pvesh.
Dipendenze richieste: Python 3 standard. L'utente deve avere l'accesso SSH 'root' configurato ai nodi Proxmox.
"""

import subprocess
import json
import sys
import time

class Colors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'

SSH_USER = "root"

# Configurazione Asset
PVE_NODES = {"pve1/pve": "10.10.10.11", "pve2": "10.10.10.21", "pve3": "10.10.10.31"}
TALOS_IPS = {"CP 01": "10.10.20.141", "CP 02": "10.10.20.142", "CP 03": "10.10.20.143"}
GATEWAYS = {
    "OPNsense VLAN 10 (Server)": "10.10.10.254", 
    "OPNsense VLAN 20 (Client)": "10.10.20.254",
    "Switch Transit (192.168.2.1)": "192.168.2.1",
    "MetalLB Traefik VIP": "10.10.20.56",
    "MetalLB Postgres VIP": "10.10.20.57"
}

warnings_count = 0
errors_count = 0

def log_ok(msg):
    print(f"[ {Colors.OKGREEN}OK{Colors.ENDC} ] 🟢 {msg}")

def log_warn(msg):
    global warnings_count
    warnings_count += 1
    print(f"[{Colors.WARNING}WARN{Colors.ENDC}] 🟡 {msg}")

def log_err(msg):
    global errors_count
    errors_count += 1
    print(f"[{Colors.FAIL}FAIL{Colors.ENDC}] 🔴 {msg}")

def log_info(msg):
    print(f"       {Colors.OKCYAN}├─{Colors.ENDC} {msg}")

def log_info_end(msg):
    print(f"       {Colors.OKCYAN}└─{Colors.ENDC} {msg}")

def print_section(title):
    print(f"\n{Colors.BOLD}{title}{Colors.ENDC}")
    print("-" * 65)

def run_ssh_json(host, cmd):
    # Esegue un comando ssh e ritorna un dizionario JSON (timeout breve per non bloccarsi)
    full_cmd = ["ssh", "-o", "StrictHostKeyChecking=no", "-o", "ConnectTimeout=3", "-o", "BatchMode=yes", f"{SSH_USER}@{host}", cmd]
    try:
        res = subprocess.run(full_cmd, capture_output=True, text=True, check=True)
        return json.loads(res.stdout)
    except Exception as e:
        return None

def check_ping(host):
    # Esegue un ping OS-agnostico (Windows non supportato per default)
    ping_cmd = ["ping", "-c", "1", "-W", "1000", host] if sys.platform == "darwin" else ["ping", "-c", "1", "-W", "1", host]
    try:
        res = subprocess.run(ping_cmd, capture_output=True, text=True)
        return res.returncode == 0
    except:
        return False

def format_bytes(b):
    gb = b / (1024**3)
    return f"{gb:.1f} GB"

def main():
    print(f"{Colors.HEADER}======================================================================{Colors.ENDC}")
    print(f"{Colors.HEADER}{Colors.BOLD}                 HOMELAB DIAGNOSTICS - DATA CENTER                    {Colors.ENDC}")
    print(f"{Colors.HEADER}======================================================================{Colors.ENDC}")
    
    start_time = time.time()

    # 1. Trova un nodo Proxmox vivo per interrogare le API
    api_node = None
    for name, ip in PVE_NODES.items():
        if check_ping(ip):
            api_node = ip
            break
            
    if not api_node:
        log_err("NESSUN NODO PROXMOX RAGGIUNGIBILE VIA PING. Cluster irraggiungibile.")
        sys.exit(1)

    # 2. Check Quorum e Status Nodi PVE
    print_section("CLUSTER PROXMOX & NODI PVE")
    cluster_status = run_ssh_json(api_node, "pvesh get /cluster/status --output-format json")
    resources = run_ssh_json(api_node, "pvesh get /cluster/resources --output-format json")
    
    if not cluster_status:
        log_err("Impossibile contattare le API del cluster Proxmox.")
    else:
        nodes = sorted([item for item in cluster_status if item.get('type') == 'node'], key=lambda x: x.get('name', ''))
        cluster = next((item for item in cluster_status if item.get('type') == 'cluster'), None)
        
        # Check Quorum
        if cluster and cluster.get('quorate') == 1:
            log_ok("Cluster Quorum: FORMATO (OK)")
        else:
            log_err("Cluster Quorum: PERSO / BROKEN")
        
        # Check Nodes resources
        for i, node in enumerate(nodes):
            name = node.get('name')
            # Look up the IP from PVE_NODES mapping (ignoring the "pve1/pve" key quirk if possible, or using node matching)
            ip = node.get('ip')
            if not ip:
                ip = next((v for k, v in PVE_NODES.items() if name in k), 'N/A')
            
            ping_ok = check_ping(ip)
            api_online = node.get('online') == 1

            if ping_ok and api_online:
                log_ok(f"Nodo '{name}' ({ip}): ONLINE (Ping & API)")
                if resources:
                    n_res = next((r for r in resources if r.get('type') == 'node' and r.get('node') == name), None)
                    if n_res:
                        cpu = n_res.get('cpu', 0.0) * 100
                        mem_used = n_res.get('mem', 0)
                        mem_tot = n_res.get('maxmem', 1)
                        if mem_tot > 0:
                            mem_pct = (mem_used / mem_tot) * 100
                            log_info_end(f"CPU: {cpu:>4.1f}% | RAM: {mem_pct:>4.1f}% ({format_bytes(mem_used)} / {format_bytes(mem_tot)})")
            elif ping_ok and not api_online:
                log_err(f"Nodo '{name}' ({ip}): DEGRADED (Ping OK, ma servizio Cluster/API OFFLINE)")
            else:
                log_err(f"Nodo '{name}' ({ip}): OFFLINE (Irreaggiungibile via Rete)")

    # 3. Check Core Storage & VMs
    print_section("CORE STORAGE & SERVICES")
    if resources:
        truenas = next((r for r in resources if r.get('vmid') == 1100), None)
        pbs = next((r for r in resources if r.get('vmid') == 1400), None)
        
        if truenas and truenas.get('status') == 'running':
            if check_ping("10.10.10.50"):
                log_ok("TrueNAS (VM 1100)  : RUNNING e ONLINE (Ping OK a 10.10.10.50)")
            else:
                log_warn("TrueNAS (VM 1100)  : RUNNING ma NON RISPONDE AL PING (Possibile Booting)")
        else:
            log_err("TrueNAS (VM 1100)  : OFFLINE. Lo Storage condiviso NON E' DISPONIBILE.")

        if pbs and pbs.get('status') == 'running':
            log_ok("Proxmox Backup     : RUNNING (LXC 1400)")
        else:
            log_warn("Proxmox Backup     : OFFLINE (LXC 1400)")
    else:
        log_warn("Impossibile recuperare lo stato delle VM da Proxmox.")

    # 4. Check Nodi Talos (Control Planes)
    print_section("TALOS KUBERNETES CONTROL PLANES")
    for cp_name, cp_ip in TALOS_IPS.items():
        if check_ping(cp_ip):
            log_ok(f"Talos {cp_name} ({cp_ip}): ONLINE")
        else:
            log_err(f"Talos {cp_name} ({cp_ip}): UNREACHABLE / OFFLINE")

    # 5. Check Connettività di Rete
    print_section("NETWORK GATEWAYS & VIPs")
    for gw_name, gw_ip in GATEWAYS.items():
        if check_ping(gw_ip):
            log_ok(f"{gw_name:<28} ({gw_ip:<14}): REACHABLE")
        else:
            log_warn(f"{gw_name:<28} ({gw_ip:<14}): UNREACHABLE")

    # Footer
    elapsed = round(time.time() - start_time, 2)
    print(f"\n{Colors.HEADER}======================================================================{Colors.ENDC}")
    status_str = f"{Colors.OKGREEN}TUTTO REGOLARE{Colors.ENDC}"
    if errors_count > 0:
        status_str = f"{Colors.FAIL}Rilevati {errors_count} ERRORI (Critici){Colors.ENDC}"
    elif warnings_count > 0:
        status_str = f"{Colors.WARNING}Rilevati {warnings_count} AVVISI (Da investigare){Colors.ENDC}"
        
    print(f" Diagnostica completata in {elapsed}s | Stato Globale: {status_str}")
    print(f"{Colors.HEADER}======================================================================{Colors.ENDC}\n")

if __name__ == "__main__":
    main()

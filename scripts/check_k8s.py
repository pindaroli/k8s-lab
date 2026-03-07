#!/usr/bin/env python3
"""
Kubernetes & Talos Comprehensive Diagnostics
Un'analisi dettagliata dello stato del cluster K8s, dei nodi Talos e dei carichi di lavoro.
"""

import subprocess
import json
import os
import sys
import time
from datetime import datetime

# Aggiungi scripts/ al path per poter importare utils.common
_base = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
sys.path.insert(0, os.path.join(_base, "scripts"))
import utils.common as common
from utils.common import (
    Colors, PROJECT_ROOT, log_ok, log_warn, log_err, 
    log_info, log_info_end, print_section, run_cmd, run_cmd_json, check_ping
)

KUBECONFIG = os.path.join(PROJECT_ROOT, "talos-config/kubeconfig")
TALOSCONFIG = os.path.join(PROJECT_ROOT, "talos-config/talosconfig")

# Verifica esistenza file config
def verify_configs():
    for name, path in [("KUBECONFIG", KUBECONFIG), ("TALOSCONFIG", TALOSCONFIG)]:
        if not os.path.exists(path):
            log_err(f"File di configurazione non trovato: {path}")
            return False
    return True

# Imposta anche le variabili d'ambiente per sicurezza
os.environ["KUBECONFIG"] = KUBECONFIG
os.environ["TALOSCONFIG"] = TALOSCONFIG

CRITICAL_NAMESPACES = ["kube-system", "arr", "traefik", "metallb-system", "cert-manager", "cnpg-system"]

def run_cmd_clean(cmd):
    # Ritorna l'output pulito (senza warning Talos)
    stdout = run_cmd(cmd)
    if not stdout:
        return ""
    lines = [l for l in stdout.splitlines() if not l.strip().startswith('WARNING:')]
    return "\n".join(lines).strip()

def get_top_stats():
    # Ritorna un dizionario {node_name: {cpu: val, mem: val, cpu_pct: val, mem_pct: val}}
    stdout = run_cmd_clean(["kubectl", "--kubeconfig", KUBECONFIG, "top", "nodes", "--no-headers"])
    stats = {}
    if stdout:
        for line in stdout.splitlines():
            parts = line.split()
            if len(parts) >= 5:
                stats[parts[0]] = {
                    'cpu': parts[1],
                    'cpu_pct': parts[2],
                    'mem': parts[3],
                    'mem_pct': parts[4]
                }
    return stats

def get_node_disks(node_ip):
    # Ritorna una stringa con il sommario dei dischi per un nodo
    cmd = ["talosctl", "--talosconfig", TALOSCONFIG, "--context", "talos-k8s-lab", "-n", node_ip, "get", "disks", "-o", "json"]
    disks = run_cmd_json(cmd)
    if not disks:
        return "N/D"
    
    items = disks if isinstance(disks, list) else [disks]
    phy_disks = []
    for d in items:
        spec = d.get('spec', {})
        if spec.get('cdrom') or spec.get('size', 0) < 1024*1024*1024:
            continue
        dev = spec.get('dev_path', '').split('/')[-1]
        size = spec.get('pretty_size', 'N/D')
        phy_disks.append(f"{dev}:{size}")
    
    return ", ".join(phy_disks) if phy_disks else "No physical disks"

def check_talos():
    print_section("TALOS CLUSTER MEMBERSHIP")
    
    # Check connettività base prima di talosctl
    target_ip = "10.10.20.142"
    if not check_ping(target_ip):
        log_warn(f"Endpoint {target_ip} non risponde al ping. Provo backup...")
        target_ip = "10.10.20.141"
        if not check_ping(target_ip):
             log_err("Nessun endpoint Talos raggiungibile via rete (Ping fallito).")
             return

    # Usiamo talos-cp-02 come endpoint affidabile (quello nel config)
    # Specifichiamo esplicitamente il context per evitare confusioni da Home
    context = "talos-k8s-lab"
    cmd_base = ["talosctl", "--talosconfig", TALOSCONFIG, "--context", context, "-n", target_ip, "get", "members", "-o", "json"]
    members = run_cmd_json(cmd_base)
    
    if not members:
        # Tenta altro endpoint (cambia l'indice dell'IP, non del context!)
        cmd_base[6] = "10.10.20.141"
        members = run_cmd_json(cmd_base)
    
    if not members:
        log_err("Impossibile contattare il Control Plane Talos.")
        return

    # Se members è un singolo oggetto (dict), lo mettiamo in lista
    items = members if isinstance(members, list) else [members]

    for item in items:
        metadata = item.get('metadata', {})
        spec = item.get('spec', {})
        node_id = metadata.get('id', 'unknown')
        hostname = spec.get('hostname', node_id)
        # Talos member addresses typical order: VIP, NodeIP
        addresses = spec.get('addresses', [])
        node_ip = addresses[-1] if addresses else "unknown"
        phase = metadata.get('phase', 'running')
        
        # Disk stats from Talos
        disk_sum = get_node_disks(node_ip)
        
        if phase == "running":
            log_ok(f"Talos Node: {hostname:<25} | Phase: {phase:<10} | {', '.join(addresses)}")
            log_info_end(f"Physical Disks: {disk_sum}")
        else:
            log_warn(f"Talos Node: {hostname:<25} | Phase: {phase:<10} | {', '.join(addresses)}")

def check_nodes():
    print_section("KUBERNETES NODES STATUS & RESOURCES")
    # Aggiungi --kubeconfig ovunque per sicurezza
    nodes = run_cmd_json(["kubectl", "--kubeconfig", KUBECONFIG, "get", "nodes", "-o", "json"])
    top_stats = get_top_stats()
    
    if not nodes or not isinstance(nodes, dict):
        log_err("Impossibile recuperare i nodi Kubernetes.")
        return

    for node in nodes.get('items', []):
        name = node['metadata']['name']
        status = "Unknown"
        for cond in node['status']['conditions']:
            if cond['type'] == 'Ready':
                status = "Ready" if cond['status'] == 'True' else f"NotReady ({cond['reason']})"
                break
        
        version = node['status']['nodeInfo']['kubeletVersion']
        labels = node['metadata'].get('labels', {})
        roles = [k.split('/')[-1] for k in labels if k.startswith('node-role.kubernetes.io/')]
        role_str = ", ".join(roles) if roles else "worker"
        
        # Resource capacity
        mem_total_str = node['status']['capacity'].get('memory', 'N/D')
        
        # Resource used
        stats = top_stats.get(name, {})
        cpu_usage = stats.get('cpu_pct', 'N/D')
        mem_usage = stats.get('mem', 'N/D')
        mem_pct = stats.get('mem_pct', 'N/D')

        if status == "Ready":
            log_ok(f"Node: {name:<12} | Status: {status:<10} | Role: {role_str:<12}")
            log_info_end(f"CPU: {cpu_usage:>4} | RAM: {mem_pct:>4} ({mem_usage} / {mem_total_str})")
        else:
            log_err(f"Node: {name:<12} | Status: {status:<10} | Role: {role_str:<12}")

def check_pods():
    print_section("CRITICAL WORKLOADS (PODS)")
    pods = run_cmd_json(["kubectl", "--kubeconfig", KUBECONFIG, "get", "pods", "-A", "-o", "json"])
    if not pods or not isinstance(pods, dict):
        log_err("Impossibile recuperare i Pod.")
        return

    bad_pods = []
    namespace_stats = {}

    for pod in pods.get('items', []):
        ns = pod['metadata']['namespace']
        name = pod['metadata']['name']
        status_info = pod['status']
        phase = status_info.get('phase')
        
        if ns not in namespace_stats:
            namespace_stats[ns] = {'total': 0, 'ready': 0}
        
        namespace_stats[ns]['total'] += 1
        
        # Check if all containers are ready
        container_statuses = status_info.get('containerStatuses', [])
        is_ready = False
        if container_statuses:
            is_ready = all(cs.get('ready', False) for cs in container_statuses)
            if is_ready:
                namespace_stats[ns]['ready'] += 1
        elif phase == "Succeeded": # Job pods
            namespace_stats[ns]['ready'] += 1
            is_ready = True

        if phase not in ["Running", "Succeeded"] or (phase == "Running" and not is_ready):
            reason = status_info.get('reason', phase)
            if container_statuses:
                for cs in container_statuses:
                    state = cs.get('state', {})
                    if 'waiting' in state:
                        w_reason = state['waiting'].get('reason', 'Wait')
                        w_msg = state['waiting'].get('message', '')[:40]
                        reason = f"{w_reason}: {w_msg}"
                        break
                    elif 'terminated' in state and state['terminated'].get('exitCode') != 0:
                        reason = f"Terminated (Exit {state['terminated'].get('exitCode')})"
            
            bad_pods.append(f"[{ns}] {name} -> {reason}")

    # Report by critical namespaces
    for ns in CRITICAL_NAMESPACES:
        stats = namespace_stats.get(ns)
        if stats:
            msg = f"Namespace {ns:<15}: {stats['ready']}/{stats['total']} pods ready"
            if stats['ready'] == stats['total']:
                log_ok(msg)
            else:
                log_warn(msg)
        else:
            log_warn(f"Namespace {ns:<15}: NON TROVATO o vuoto")

    if bad_pods:
        print(f"\n{Colors.WARNING}POD PROBLEMATICI RILEVATI:{Colors.ENDC}")
        for p in bad_pods[:15]: # Limit output
            print(f"  - {p}")
        if len(bad_pods) > 15:
            print(f"  ... ed altri {len(bad_pods)-15} pod.")

def check_storage():
    print_section("STORAGE & PERSISTENT VOLUMES")
    pvcs = run_cmd_json(["kubectl", "--kubeconfig", KUBECONFIG, "get", "pvc", "-A", "-o", "json"])
    if not pvcs:
        log_ok("Nessun PVC trovato o errore nel comando.")
        return

    pending_pvcs = [p for p in pvcs.get('items', []) if p['status']['phase'] != 'Bound']
    if not pending_pvcs:
        log_ok("Tutti i Persistent Volume Claims sono 'Bound' (OK).")
    else:
        log_err(f"Rilevati {len(pending_pvcs)} PVC non collegati (Pending/Lost).")
        for pvc in pending_pvcs:
            ns = pvc['metadata']['namespace']
            name = pvc['metadata']['name']
            log_info(f"[{ns}] {name} -> {pvc['status']['phase']}")

def check_events():
    print_section("RECENT WARNING EVENTS (Last 15m)")
    # Correzione sintassi sort-by
    events = run_cmd_json(["kubectl", "--kubeconfig", KUBECONFIG, "get", "events", "-A", "--sort-by=.metadata.creationTimestamp", "-o", "json"])
    if not events:
        return

    # kubectl events output structure
    items = events.get('items', [])
    
    warnings = []
    for event in items:
        if event.get('type') == 'Warning':
            msg = f"[{event['metadata']['namespace']}] {event['involvedObject']['kind']}/{event['involvedObject']['name']}: {event['message']}"
            warnings.append(msg)
            
    if warnings:
        for w in warnings[-5:]: # Ultime 5 segnalazioni
            log_warn(w)
    else:
        log_ok("Nessun warning recente rilevato negli eventi del cluster.")

def main():
    # Salva il CWD originale
    original_cwd = os.getcwd()
    
    # Cambia CWD nella root del progetto per coerenza (i file config sono lì)
    os.chdir(PROJECT_ROOT)
    
    print(f"{Colors.HEADER}======================================================================{Colors.ENDC}")
    print(f"{Colors.HEADER}{Colors.BOLD}                 KUBERNETES COMPREHENSIVE DIAGNOSTICS                 {Colors.ENDC}")
    print(f"{Colors.HEADER}======================================================================{Colors.ENDC}")
    
    if not verify_configs():
        sys.exit(1)

    start_time = time.time()

    try:
        # Esegui i controlli
        check_talos()
        check_nodes()
        check_pods()
        check_storage()
        check_events()
    finally:
        # Torna al CWD originale prima di uscire
        os.chdir(original_cwd)

    # Footer
    elapsed = round(time.time() - start_time, 2)
    print(f"\n{Colors.HEADER}======================================================================{Colors.ENDC}")
    status_str = f"{Colors.OKGREEN}K8S HEALTHY{Colors.ENDC}"
    if common.errors_count > 0:
        status_str = f"{Colors.FAIL}STATO CRITICO ({common.errors_count} errori){Colors.ENDC}"
    elif common.warnings_count > 0:
        status_str = f"{Colors.WARNING}STATO DEGRADATO ({common.warnings_count} avvisi){Colors.ENDC}"
        
    print(f" Diagnostica completata in {elapsed}s | Stato Globale: {status_str}")
    print(f"{Colors.HEADER}======================================================================{Colors.ENDC}\n")

if __name__ == "__main__":
    main()

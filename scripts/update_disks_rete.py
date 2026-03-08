#!/usr/bin/env python3
import json
import os
import sys
import subprocess
from utils.common import log_ok, log_warn, log_err, log_info, print_section, PROJECT_ROOT, run_cmd

RETE_PATH = os.path.join(PROJECT_ROOT, "rete.json")

def get_remote_disks(host):
    """Esegue lsblk via SSH sul nodo e restituisce i dati JSON."""
    cmd = ["ssh", f"root@{host}", "lsblk -J -o NAME,SIZE,TYPE,MODEL,SERIAL,FSTYPE,MOUNTPOINT"]
    output = run_cmd(cmd)
    if not output:
        return []
    try:
        data = json.loads(output)
        return data.get("blockdevices", [])
    except Exception as e:
        log_err(f"Errore nel parsing JSON da {host}: {e}")
        return []

def get_pve_hostpci(host, vmid):
    """Controlla se ci sono dispositivi PCI passati in una VM (es. TrueNAS)."""
    cmd = ["ssh", f"root@{host}", f"qm config {vmid} | grep 'hostpci'"]
    output = run_cmd(cmd)
    if not output:
        return []
    
    devices = []
    for line in output.splitlines():
        if "hostpci" in line and ":" in line:
            # line is 'hostpci0: 0000:05:00.0,pcie=1'
            try:
                # Get everything after the first colon, then split by comma to remove options
                val = line.split(":", 1)[1].strip().split(",")[0]
                devices.append(val)
            except:
                continue
    return devices

def update_disks():
    print_section("Aggiornamento Dischi in rete.json")
    
    if not os.path.exists(RETE_PATH):
        log_err(f"File non trovato: {RETE_PATH}")
        return

    with open(RETE_PATH, 'r') as f:
        rete = json.load(f)

    updated = False
    for nodo in rete.get("nodi", []):
        nodetype = nodo.get("type", "")
        mg_ip = nodo.get("management_ip", nodo.get("ip", ""))
        
        if nodetype == "Hypervisor" and mg_ip:
            log_ok(f"Analisi nodo: {nodo['id']} ({mg_ip})")
            
            disks_info = []
            block_devices = get_remote_disks(mg_ip)
            
            for dev in block_devices:
                # Escludiamo i volumi ZFS (zd) per pulizia
                if dev['name'].startswith("zd"):
                    continue
                
                disk_data = {
                    "name": dev["name"],
                    "size": dev["size"],
                    "model": dev.get("model", "Unknown").strip() if dev.get("model") else "Unknown",
                    "serial": dev.get("serial", "Unknown").strip() if dev.get("serial") else "Unknown",
                    "type": dev.get("type", "disk")
                }
                disks_info.append(disk_data)
                log_info(f"Trovato: {disk_data['name']} ({disk_data['size']}) - {disk_data['model']}")

            # Caso speciale PVE1: TrueNAS Passthrough
            if nodo['id'] == "pve":
                pci_devs = get_pve_hostpci(mg_ip, 1100)
                if pci_devs:
                    for pci in pci_devs:
                        note = "Passthrough to VM 1100 (TrueNAS)"
                        if "05:00.0" in pci:
                            note += " - Likely 2x 4TB HDDs"
                        disks_info.append({
                            "pci_id": pci,
                            "note": note,
                            "type": "pci_passthrough"
                        })
                        log_info(f"Passthrough: {pci} ({note})")

            nodo["disks"] = disks_info
            updated = True

    if updated:
        with open(RETE_PATH, 'w') as f:
            json.dump(rete, f, indent=4)
        log_ok("rete.json aggiornato correttamente.")
    else:
        log_warn("Nessun nodo Hypervisor trovato o nessun aggiornamento necessario.")

if __name__ == "__main__":
    update_disks()

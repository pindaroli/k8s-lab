#!/usr/bin/env python3
"""
scripts/network/wake_node.py
Utilità autonoma per l'invio di Magic Packet Wake-on-LAN (WoL) ai nodi fisici dell'homelab:
- pve1, pve2, pve3 (Cluster Proxmox VE)
- truenas (TrueNAS SCALE Bare Metal)

Zero dipendenze esterne (solo Python standard library socket/argparse).
Supporta broadcast su VLAN 99 OOB (192.168.100.255), VLAN 20 Client (10.10.20.255) o broadcast globale.
"""

import sys
import socket
import argparse
import json
from pathlib import Path

# Registro canonico dei target fisici WoL (allineato a rete.json e wiki/plans/wake-on-lan-homelab-automation.md)
NODES_WOL_REGISTRY = {
    "pve1": {
        "label": "Proxmox Node 1 (Minisforum BD790i)",
        "primary_interface": "nic0",
        "mac": "58:47:ca:7b:d9:3d",  # 2.5G Realtek OOB
        "broadcast": "192.168.100.255",
        "vlan": "99 (OOB)",
        "ip_ref": "192.168.100.11",
        "mac_10g_p1": "3c:fd:fe:05:5e:a0",  # Intel X710 10G Port 1 (VLAN 10)
        "mac_10g_p2": "3c:fd:fe:05:5e:a2",  # Intel X710 10G Port 2 (VLAN 20)
        "alt_macs": ["3c:fd:fe:05:5e:a0", "3c:fd:fe:05:5e:a2"],
    },
    "pve2": {
        "label": "Proxmox Node 2 (Minisforum BD790i)",
        "primary_interface": "nic0",
        "mac": "58:47:ca:7c:55:32",
        "broadcast": "192.168.100.255",
        "vlan": "99 (OOB)",
        "ip_ref": "192.168.100.21",
    },
    "pve3": {
        "label": "Proxmox Node 3 (GMKtec NucBox EVO-X1)",
        "primary_interface": "nic0",
        "mac": "c8:ff:bf:05:50:24",
        "broadcast": "192.168.100.255",
        "vlan": "99 (OOB)",
        "ip_ref": "192.168.100.31",
        "notes": "Richiede cavo RJ45 2.5G collegato allo switch-25g-server porta 3. WoL NON supportato sulla scheda 10G OCuLink.",
    },
    "truenas": {
        "label": "TrueNAS SCALE (ASUS TUF GAMING)",
        "primary_interface": "enp8s0",
        "mac": "3c:7c:3f:d9:fd:73",  # Realtek RTL8125 2.5G OOB
        "broadcast": "192.168.100.255",
        "vlan": "99 (OOB)",
        "ip_ref": "192.168.100.50",
        "alt_mac": "8c:fd:18:f7:f5:92",  # Intel X710 10G (VLAN 20 Client, LACP bond0 master)
        "alt_broadcast": "10.10.20.255",
    },
}

def clean_mac(mac_str: str) -> bytes:
    """Normalizza e converte una stringa MAC (con : o -) in 6 byte raw."""
    cleaned = mac_str.replace(":", "").replace("-", "").strip()
    if len(cleaned) != 12:
        raise ValueError(f"Indirizzo MAC non valido (lunghezza errata): {mac_str}")
    return bytes.fromhex(cleaned)

def create_magic_packet(mac_bytes: bytes) -> bytes:
    """Costruisce il payload standard Magic Packet: 6x 0xFF seguito da 16 ripetizioni del MAC."""
    return b"\xff" * 6 + (mac_bytes * 16)

def send_wol(mac_str: str, broadcast_ip: str, port: int = 9, dry_run: bool = False) -> bool:
    """Invia un pacchetto Magic Packet UDP broadcast all'indirizzo specificato."""
    mac_bytes = clean_mac(mac_str)
    packet = create_magic_packet(mac_bytes)

    if dry_run:
        print(f"  [DRY-RUN] Invierei Magic Packet ({len(packet)} bytes) per MAC {mac_str} a {broadcast_ip}:{port}")
        return True

    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            sock.sendto(packet, (broadcast_ip, port))
        print(f"  [OK] Magic Packet inviato a {broadcast_ip}:{port} per MAC {mac_str}")
        return True
    except Exception as e:
        print(f"  [ERRORE] Invio fallito verso {broadcast_ip}:{port} per MAC {mac_str}: {e}", file=sys.stderr)
        return False

def list_nodes():
    """Elenca tutti i nodi e relative interfacce WoL censite."""
    print("\n📋 REGISTRO TARGET WAKE-ON-LAN HOMELAB:")
    print("-" * 80)
    for name, info in NODES_WOL_REGISTRY.items():
        print(f"🔹 {name.upper()}: {info['label']}")
        print(f"   - Interfaccia Principale: {info['primary_interface']} ({info['vlan']})")
        print(f"   - MAC Principale:         {info['mac']}")
        print(f"   - Broadcast Consigliato:  {info['broadcast']}")
        if "alt_mac" in info:
            print(f"   - MAC Alternativo:        {info['alt_mac']}")
        if "notes" in info:
            print(f"   - Nota Tecnica:           {info['notes']}")
        print("-" * 80)

def main():
    parser = argparse.ArgumentParser(
        description="Invio Magic Packet Wake-on-LAN per nodi fisici Homelab (pve1, pve2, pve3, truenas)"
    )
    parser.add_argument(
        "node",
        nargs="?",
        choices=list(NODES_WOL_REGISTRY.keys()) + ["all"],
        help="Nome del nodo da svegliare (pve1, pve2, pve3, truenas, oppure 'all')",
    )
    parser.add_argument(
        "--mac",
        help="Invia a un MAC address custom arbitrario invece che a un nodo predefinito",
    )
    parser.add_argument(
        "--broadcast",
        "-b",
        help="Indirizzo IP broadcast di destinazione (es. 192.168.100.255, 10.10.20.255, 255.255.255.255)",
    )
    parser.add_argument(
        "--port",
        "-p",
        type=int,
        default=9,
        help="Porta UDP di destinazione (default: 9; alternativa comune: 7)",
    )
    parser.add_argument(
        "--use-alt-mac",
        action="store_true",
        help="Usa il MAC secondario/alternativo se configurato per il nodo",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Simula l'invio senza trasmettere pacchetti sulla rete",
    )
    parser.add_argument(
        "--list",
        "-l",
        action="store_true",
        help="Elenca la configurazione WoL dei nodi disponibili",
    )

    args = parser.parse_args()

    if args.list or not (args.node or args.mac):
        list_nodes()
        if not (args.node or args.mac):
            sys.exit(0)

    # Invio su MAC arbitrario
    if args.mac:
        broadcast = args.broadcast or "255.255.255.255"
        print(f"\n⚡ Risveglio MAC custom: {args.mac}")
        success = send_wol(args.mac, broadcast, args.port, args.dry_run)
        sys.exit(0 if success else 1)

    target_nodes = list(NODES_WOL_REGISTRY.keys()) if args.node == "all" else [args.node]

    print(f"\n⚡ INVIO WAKE-ON-LAN ({'SIMULAZIONE' if args.dry_run else 'INVIO REALE'})...")
    all_ok = True

    for node_name in target_nodes:
        info = NODES_WOL_REGISTRY[node_name]
        macs_to_send = (
            info.get("alt_macs", [info.get("alt_mac")])
            if args.use_alt_mac
            else [info["mac"]] + info.get("alt_macs", ([info["alt_mac"]] if "alt_mac" in info else []))
        )
        # Rimuovi None e duplicati preservando l'ordine
        macs_to_send = list(dict.fromkeys([m for m in macs_to_send if m]))

        print(f"\n➡️  Target: {node_name.upper()} ({info['label']})")
        # Se non è specificato un broadcast custom, invia su broadcast primario, broadcast alternativo (se presente), globale e unicast diretto
        dest_ips = [args.broadcast] if args.broadcast else list(dict.fromkeys([
            info["broadcast"],
            info.get("alt_broadcast", "10.10.20.255"),
            "10.10.10.255",
            "255.255.255.255",
            info.get("ip_ref")
        ]))
        dest_ips = [ip for ip in dest_ips if ip]

        for target_mac in macs_to_send:
            for ip in dest_ips:
                ok = send_wol(target_mac, ip, args.port, args.dry_run)
                if not args.dry_run:
                    send_wol(target_mac, ip, 7, args.dry_run)
                if not ok:
                    all_ok = False

    print("\n🏁 Operazione conclusa.")
    sys.exit(0 if all_ok else 1)

if __name__ == "__main__":
    main()

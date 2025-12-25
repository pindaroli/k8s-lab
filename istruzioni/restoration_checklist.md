# OPNsense Manual Restoration Checklist

This checklist extracts the configuration steps from `l3_config_guide.md` to help you restore your OPNsense setup manually.

## 1. VM Hardware Setup (Proxmox)
- [ ] **Run Configuration Script**:
  Run this on **pve2** (or the node hosting OPNsense) to ensure 5 network interfaces are attached:
  ```bash
  /root/configure_opnsense.sh
  ```
  *(If the script is not there, I can help you recreate it)*

## 2. Interface Assignment (OPNsense Console)
Access the OPNsense VM Console. If interfaces are mismatched:
- [ ] **Assign Interfaces**:
  - WAN -> `vtnet0` (vmbr999)
  - LAN -> `vtnet1` (vmbr0 - Management)
  - OPT1 -> `vtnet2` (vmbr10 - Server)
  - OPT2 -> `vtnet3` (vmbr20 - Client)
  - OPT3 -> `vtnet4` (vmbr30 - IoT)
- [ ] **Set LAN IP**:
  - Interface: LAN
  - IP: `192.168.2.254` / `24`
  - Gateway: None (or upstream if different)

## 3. General Configuration (Web GUI)
Access GUI at `https://192.168.2.254` (from a PC with static IP `192.168.2.99`).

### Gateways & Routing
- [ ] **System -> Gateways -> Configuration**:
  - Add Gateway: `SWITCH_L3`
  - IP: `192.168.2.1` (Your Switch IP)
  - Interface: LAN
- [ ] **System -> Routes -> Configuration**:
  - Add Route: `10.10.10.0/24` -> `SWITCH_L3` (Server)
  - Add Route: `10.10.20.0/24` -> `SWITCH_L3` (Client)

### Virtual IPs (Legacy Support)
- [ ] **Interfaces -> Virtual IPs**:
  - Create IP Alias: `192.168.1.1/24` on **LAN** Interface.
  - *Restores 1.1 gateway for devices not yet migrated.*

### DHCP Servers
- [ ] **Services -> DHCPv4 -> [OPT3/IoT]**:
  - Enable: Yes
  - Range: `10.10.30.50` - `10.10.30.100`
  - Gateway: `10.10.30.1` (Wait, Check Guide: IoT L2 or L3? Guide says IoT is L2 passed through to OPNsense, so OPNsense IS the gateway `10.10.30.1` usually, but guide says "Switch Managed... NON CREARLA". So OPNsense is the gateway for IoT)

## 4. Firewall Rules
- [ ] **Firewall -> Rules -> LAN / OPT1 / OPT2**:
  - Allow access as needed (Start with "Allow All" on trusted LANs if testing).
- [ ] **Firewall -> Rules -> IoT (OPT3)**:
  - Block Destination `RFC1918` (Private Networks).
  - Allow Destination `Any` (Internet).

## 5. Verification
- [ ] Ping `192.168.2.1` (Switch) from OPNsense.
- [ ] Check Internet access from a Client in VLAN 20.

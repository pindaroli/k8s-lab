---
title: "DHCP Relay Outage in Symmetric Routing"
type: incident
status: archived
certified_for_ai: false
date: 2026-06-20
severity: P2
resolved: true
resolved_at: 2026-06-20T23:59:59Z
tags:
  - "#incident"
  - "#network"
  - "#network"
  - "#storage"
  - "#talos"
  - "#opnsense"
---

# Incident: DHCP Relay Outage in Symmetric Routing
**Date**: 2026-06-20
**Status**: RESOLVED (DHCP transitioned to direct mode on OPNsense, Relay disabled on L3 Switch)
**Severity**: High (Clients on VLAN 20 were unable to acquire IP addresses dynamically)

## 🔍 Diagnosis
During the transition of the homelab network to a **Symmetric Routing** architecture, DHCP propagation on VLAN 20 failed. Initially, the L3 Switch SVI for VLAN 20 was configured to relay DHCP requests to the OPNsense Transit IP (`192.168.2.254`).

However, several issues blocked this setup:
1. **ONTi Firmware Limitations**: Attempting to delete or modify the incorrect helper address (`10.10.20.254`) on the active port via CLI resulted in errors: `failed to delete helper address on active port 67`. The switch firmware does not allow proper control over global DHCP Relay status via command line.
2. **Kea DHCP Interface Bindings**: OPNsense Kea DHCP was globally configured to listen *only* on the `TRANSIT` interface (`opt4`), completely ignoring any incoming DHCP requests on the `LAN_CLIENT` (`opt2` / VLAN 20) interface.

## 🛠️ Actions Taken & Resolution

### 1. Shift to Direct DHCP on VLAN 20
To bypass the buggy DHCP Relay firmware behavior of the ONTi switch, we transitioned the network design to **Direct DHCP** for VLAN 20:
* **OPNsense IP SVI**: Configured the log interface `gw-vlan20` (`opt2`) with static IP **`10.10.20.254/24`** on OPNsense.
* **Firewall Rules**: Confirmed that the "Block private networks" option was disabled on `opt2` and added a `Pass Any` rule from the `10.10.20.0/24` subnet.

### 2. Switch Clean Up (WebGUI)
* **DHCP Relay Disabled**: Accessed the WebGUI of the ONTi Switch (`http://192.168.2.1`) and toggled **`DHCP Relay Forwarding`** to **`Off`**. This stopped the switch from intercepting port 67 packets, allowing DHCP broadcast traffic to travel natively at Layer 2 to OPNsense.

### 3. Kea DHCP Subnet & Listen Interfaces Configuration
* **Gateway Hijack (Symmetric Routing)**: Created a Kea subnet for `10.10.20.0/24` on OPNsense. Critically, we set the **`Router (option 3)`** parameter to **`10.10.20.1`** (the L3 Switch SVI) rather than OPNsense's interface IP. This preserves symmetric routing since client exit traffic is still sent to the L3 Switch.
* **DNS Settings**: Injected `192.168.2.254` as the primary DNS server.
* **Listen Interfaces**: Enabled Kea DHCP to listen on both **`LAN_CLIENT`** and **`TRANSIT`** interfaces, resolving the binding issue.

### 4. Code & Configuration Synchronization
* **`rete.json`**: Updated the VLAN 20 definition to map `mode: "direct"`, the correct DHCP IP pool (`10.10.20.201-253`), and OPNsense logical interface IP `10.10.20.254`.
* **Automation Scripts**: Patched `extract_dhcp_from_rete_json.py` and `push_kea_dhcp_to_opnsense.py` to extract and sync the `pools` field directly to OPNsense via API.
* **Unit Tests**: Updated `test_network_configs.py` to assert the presence of OPNsense SVI IP and correct DHCP configurations, confirming that the new schema passes all CI validation rules.

## 🧪 Verification Results
* **DHCP Lease**: The Mac Studio immediately renewed its IP and received exactly **`10.10.20.100`** via Kea static mapping.
* **Gateway & DNS Options**: Verified that the default gateway is indeed **`10.10.20.1`** (L3 Switch) and DNS is **`192.168.2.254`** (OPNsense).
* **Routing Path**: A traceroute to `8.8.8.8` confirmed the correct routing hops:
  1. `* * *` (L3 Switch SVI - ICMP TTL Exceeded disabled by policy)
  2. `192.168.2.254` (OPNsense Transit interface)
  3. ISP Public Gateway
* **Internet**: Ping to `8.8.8.8` and name resolution for external/internal hosts function perfectly with 0% packet loss.

## 🔗 References
* [[OPNsense]]
* [[Talos_Cluster]]
* [rete.json](file:///Users/olindo/prj/k8s-lab/rete.json)
* [[Network_Registry]]

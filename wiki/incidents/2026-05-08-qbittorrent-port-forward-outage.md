# Incident: qBittorrent P2P Port Forwarding Outage
**Date**: 2026-05-08
**Status**: IN PROGRESS (Pending Manual Action)
**Severity**: Medium (Service Functional but degraded/firewalled)

## 🔍 Diagnosis
qBittorrent was reporting a "firewalled" status (yellow icon) and zero upload/download speed despite the container being healthy and the WebUI accessible.
The P2P port `30661` was found to be unreachable from the public IP.

### Root Cause
Missing **Destination NAT (Port Forwarding)** rule on OPNsense to route external traffic on port `30661/TCP+UDP` to the VIP `10.10.20.60` inside the cluster.

## 🛠️ Planned Resolution (Manual)
As the OPNsense API (version 26.1.6) does not reliably expose the NAT Port Forwarding table for automation via Ansible/Python, a manual rule must be created.

### OPNsense Configuration Steps:
1. Navigate to **Firewall > NAT > Destination NAT**.
2. Create a new rule:
   - **Interface**: `WAN`
   - **Protocol**: `TCP/UDP`
   - **Destination Port**: `30661`
   - **Redirect Target IP**: `10.10.20.60`
   - **Redirect Target Port**: `30661`
   - **Filter rule association**: `Add associated filter rule`
3. Save and **Apply Changes**.

## 🛡️ Future Prevention
- Implement an **Alias-based** NAT strategy. 
- Create a static NAT rule in OPNsense once, pointing to an Alias `AL_QBITTORRENT_IP`.
- Automate the update of this Alias via Ansible when the service moves or VIP changes.

## 🔗 References
- [[OPNsense]]
- [[Servarr]]
- [rete.json](file:///Users/olindo/prj/k8s-lab/rete.json)

# Phase 2b: Network Stabilization (DHCP Reservations)

**Goal**: Ensure all 3 Talos Control Plane nodes always receive the same IP address from OPNsense.
**Strategy**: Use DHCP Reservations (Static Mappings) on OPNsense.

## 1. Prerequisites (Gather MAC Addresses)

You need the MAC address of the network interface for each Talos VM.

| Node | Proxmox Node | VM ID | Target IP | MAC Address | Status |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **talos-cp-01** | pve | 1300 | `10.10.20.141` | `bc:24:11:81:6a:19` | ✅ Configured |
| **talos-cp-02** | pve2 | *Check GUI* | `10.10.20.142` | `bc:24:11:77:40:fc` | ✅ Configured |
| **talos-cp-03** | pve3 | *Check GUI* | `10.10.20.143` | `bc:24:11:0b:e0:61` | ✅ Configured |

**How to find MACs:**
1.  Log into Proxmox GUI.
2.  Select the VM (e.g., `200` or `300`).
3.  Go to **Hardware** > **Network Device (net0)**.
4.  Copy the MAC address (e.g., `BC:24:11:XX:XX:XX`).

## 2. Configuration on OPNsense

**Method A: Manual GUI (Recommended for speed)**
1.  Go to **Services** > **DHCPv4** > **[LAN_CLIENT / VLAN 20]**.
2.  Scroll to bottom > click **+** (Add Static Mapping).
3.  **Entry 2 (Node 2):**
    *   MAC: `[Insert MAC Node 2]`
    *   IP: `10.10.20.143`
    *   Hostname: `talos-cp-02`
4.  **Entry 3 (Node 3):**
    *   MAC: `[Insert MAC Node 3]`
    *   IP: `10.10.20.144`
    *   Hostname: `talos-cp-03`
5.  Click **Save** and **Apply Changes**.

**Method B: Ansible (Automated)**
1.  Edit `ansible/playbooks/dhcp_reservations.yml`.
2.  Replace the placeholder MACs (`00:00...`) with real values.
3.  Run: `ansible-playbook -i ansible/inventory.ini ansible/playbooks/dhcp_reservations.yml`

## 3. Apply & Verify

For each node (starting with Node 2 and 3):
1.  **Reboot the VM** from Proxmox.
2.  Wait for it to come online.
3.  Verify IP: `talosctl -n 10.10.20.14X version` (should respond).

## 4. Updates for Talos Client
Once IPs are stable, update your local config to allow managing any node:
```bash
talosctl config node 10.10.20.142,10.10.20.143,10.10.20.144
talosctl config endpoint 10.10.20.142,10.10.20.143,10.10.20.144
```

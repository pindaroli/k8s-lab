# Switch Configuration Guide (Offline Mode)

This guide is designed for configuring your 3 switches offline, one by one.
**Priority**: Use `rete.json` for Ports/VLANs and `l3_config_guide.md` for L3 logic (IPs, Routing).

---

## 🟥 Switch 1: switch10g (The Core)
**Role**: L3 Core Router + Aggregation
**Model**: ONTi ONT-S508cl-8S / XikeStor SKS8300-8X

### 0. Factory Reset & Restore
**Option A: Factory Reset** (If you want to start fresh)
1.  **Power On** the switch.
2.  **Locate the Reset Hole**: Small pinhole on front panel.
3.  **Action**: Use a paperclip, hold for **10 seconds** until lights flash.
4.  **Default IP**: `192.168.2.1` (or `192.168.10.12`).
5.  **Credentials**: `admin` / `admin`.
6.  **Important**: When changing password, set "User Level" / "Priority" to **15** (Admin).
    -   *If you see "admin does not have sufficient permissions", you set it too low.* -> **Reset again**.
> [!WARNING]
> **DO NOT** check any "Encrypted" or "Ciphertext" box next to the password field!
> This tells the switch you are pasting a *hashed* code (like `7$28d...`). If you check it and type `pippo`, the switch saves `pippo` as the hash. When you try to login, you will be locked out. **Leave it unchecked (Plaintext).**

**Option B: Restore Backup** (If you have a `.cfg` or `.bin` file)
1.  Connect your PC physically to the switch (e.g. Port 3).
2.  Set your PC IP to `192.168.2.99`.
3.  Login to Web GUI (`http://192.168.2.1`).
4.  **Find the Menu**: Go to **Management Config -> HTTP** (Expand the menu if needed).
5.  **Select Action**: Look for "Import" or "Restore" options.
6.  **Upload** your backup file.
6.  The switch will reboot with the old configuration.

### 1. VLAN Settings (Layer 2)
Create these VLANs in the **802.1Q VLAN** menu:
- **VLAN 1**: Management (Default)
- **VLAN 10**: Server
- **VLAN 20**: Client
- **VLAN 30**: IoT

### 2. Port Configuration
| Port | Mode | PVID | Tagged VLANs | Untagged VLANs | Notes |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **1** | Trunk | 1 | `10, 20, 30` | `1` | Uplink to **Switch Server** |
| **8** | Trunk | 1 | `10, 20, 30` | `1` | Uplink to **Switch Letto** |
| **3** | Access | 10 | - | `10` | Connects to **PVE Node 1** (Port 1) |
| **4** | Access | 1 | - | `1` | **Reserved / Free** (Use for Emergency Mgmt) |
| **5** | Access | 20 | - | `20` | Connects to **PVE Node 1** (Port 2) |
| *Others* | Access | 1 | - | `1` | Unused |

> [!TIP]
> **Ingress Check**: If you see an option called "Ingress Filtering" or "Ingress Check":
> *   **Enable it** (Best Practice): This improves security by dropping packets tagged with VLANs that are not allowed on that port.
> *   Only disable if debugging weird connectivity issues.

### 3. Layer 3 Configuration (Routing)
*Enable "L3 Features" or "IPv4 Routing" in Global Settings.*

1.  **VLAN Interfaces**:
    -   **Menu**: Go to **System Config -> IP Config** (or sometimes *VLAN Config -> VLAN Interface*).
    -   **Add**: Create an interface for each VLAN ID and assign the IP.
    -   **VLAN 1**: `192.168.2.1` / `255.255.255.0`
    -   **VLAN 10**: `10.10.10.1` / `255.255.255.0`
    -   **VLAN 20**: `10.10.20.1` / `255.255.255.0`
    -   **VLAN 30**: **DO NOT CONFIGURE IP** (Layer 2 Only - Traffic goes to OPNsense).

2.  **Static Route (Default Gateway)**:
    -   **Destination**: `0.0.0.0` Mask `0.0.0.0`
    -   **Next Hop**: `192.168.2.254` (OPNsense LAN IP)

3.  **DHCP Relay**:
    -   **Menu**: Go to **DHCP Config -> DHCP Relay Config**.
    -   **Global**: Switch **DHCP Relay Forwarding** to **ON**.
    -   **Server**: Look for **Helper-server Address** (or "DHCP Server Group"). Set IP to `192.168.2.254`.
    -   **Interfaces**: If asked, enable Relay on **VLAN 10** and **VLAN 20**.

---

## 🟦 Switch 2: switch25gMLetto (Bedroom)
**Role**: Layer 2 Access
**Management IP**: `192.168.2.2` / `255.255.255.0`
**Gateway**: `192.168.2.1`

### 1. VLAN Settings
Create VLANs: `1`, `10`, `20`, `30`.

### 2. Port Configuration
| Port | Mode | PVID | Tagged VLANs | Untagged VLANs | Notes |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **2** | Access | 10 | - | `10` | Devices (Server VLAN) |
| **3** | Access | 1 | - | `1` | Management / Free |
| **4** | Access | 20 | - | `20` | Client Devices |
| **5** | Trunk | 1 | `10, 20, 30` | `1` | Uplink to **switch10g** (Port 8) |
| **6** | Trunk | 20 | `30` | `20` | Uplink to **AP1100** (Native 20, Tagged 30) |

---

## 🟩 Switch 3: switch25gMServer (Server Room)
**Role**: Layer 2 Access + Aggregation for OPNsense
**Management IP**: `192.168.2.3` / `255.255.255.0`
**Gateway**: `192.168.2.1`

### 1. VLAN Settings
Create VLANs: `1`, `10`, `20`, `30`.

### 2. Port Configuration
| Port | Mode | PVID | Tagged VLANs | Untagged VLANs | Notes |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **1** | Access | 10 | - | `10` | **PVE2** Port 1 (Server) |
| **2** | Access | 20 | - | `20` | **PVE2** Port 2 (Client VM) |
| **3** | Access | 10 | - | `10` | **PVE3** Port 1 (Server) |
| **4** | Access | 20 | - | `20` | **PVE3** Port 2 (Client VM) |
| **5** | Trunk | 1 | `10, 20, 30` | `1` | Uplink to **OPNsense** (Port 2) |
| **6** | Trunk | 1 | `10, 20, 30` | `1` | Uplink to **switch10g** (Port 1) |

> [!IMPORTANT]
> **OPNsense Connection** (Port 5):
> Updated to carry **VLAN 10, 20, 30** so OPNsense can serve as Gateway for all of them.

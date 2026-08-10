# Switch Configuration Guide (Offline Mode)

This guide is designed for configuring your 3 switches offline, one by one.
**Priority**: Use `rete.json` for Ports/VLANs and `l3_config_guide.md` for L3 logic (IPs, Routing).

---

### 🟥 Switch 1: extreme (The Core)
**Role**: L3 Core Router + Aggregation
**Model**: Extreme Networks X620-X10 (ExtremeXOS)
**Management IP**: `192.168.2.1` (Transit) / `192.168.100.100` (OOB Mgmt)

### 1. VLAN & Port Configuration (Layer 2)
| Port | Mode | PVID | Tagged VLANs | Untagged VLANs | Notes |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **1** | Trunk | 1 | `10, 20, 30, 99` | `1` | Uplink to **Switch Server** (Horaco Port 6) |
| **2** | Access | 10 | - | `10` | LAN Server (VLAN 10) - PVE DAC uplink |
| **3** | Access | 10 | - | `10` | Connects to **PVE Node 1** (Port 1 `enp1s0f0`) |
| **4** | Access | 10 | - | `10` | LAN Server (VLAN 10) - PVE DAC uplink |
| **5** | Access | 20 | - | `20` | Connects to **PVE Node 1** (Port 2 `enp1s0f1np1`) |
| **6** | Access | 20 | - | `20` | LAN Client (VLAN 20) - PVE DAC uplink |
| **7** | Access | 10 | - | `10` | LAN Server (VLAN 10) - PVE DAC uplink |
| **8** | Access | 20 | - | `20` | LAN Client (VLAN 20) - PVE DAC uplink |
| **9-10**| Access| 1  | - | `1`  | Free / Spares 10G SFP+ |

### 2. ExtremeXOS CLI Configuration Script
```exos
# VLAN Creation
create vlan "server" tag 10
create vlan "client" tag 20
create vlan "IOT" tag 30
create vlan "OOB" tag 99

# Port Assignments
configure vlan Default add ports 1,9-10 untagged
configure vlan server add ports 1 tagged
configure vlan server add ports 2-4,7 untagged
configure vlan client add ports 1 tagged
configure vlan client add ports 5-6,8 untagged
configure vlan IOT add ports 1 tagged
configure vlan OOB add ports 1 tagged

# Layer 3 SVIs & IP Forwarding
configure vlan Default ipaddress 192.168.2.1 255.255.255.0
enable ipforwarding vlan Default
configure vlan server ipaddress 10.10.10.1 255.255.255.0
enable ipforwarding vlan server
configure vlan client ipaddress 10.10.20.1 255.255.255.0
enable ipforwarding vlan client
enable ipforwarding

# Static Default Route
configure iproute add default 192.168.2.254

# DNS Client & Bootprelay
configure dns-client add name-server 192.168.2.254 vr VR-Default
configure bootprelay add 192.168.2.254 vr VR-Default
enable bootprelay ipv4 vlan client
enable bootprelay ipv4 vlan server

# Save Config
save config
```

------

## 🟦 Switch 2: switch25gMLetto (Bedroom)
**Role**: Layer 2 Access
**Management IP**: `192.168.2.2` / `255.255.255.0`
**Gateway**: `192.168.2.1`

### 1. VLAN Settings
Create VLANs: `1`, `10`, `20`, `30`.

### 2. Port Configuration
| Port | Mode | PVID | Tagged VLANs | Untagged VLANs | Notes |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **1** | Access | 1 | - | `1` | Free / Unused |
| **2** | Access | 10 | - | `10` | Devices (Server VLAN) |
| **3** | Access | 1 | - | `1` | Free / Unused |
| **4** | Trunk | 20 | `30` | `20` | Uplink to **AP11000** (Native 20, Tagged 30) |
| **5** | Trunk | 1 | `10, 20, 30` | `1` | Uplink to **switch10g** (Port 8) |
| **6** | Access | 20 | - | `20` | Mac Studio M2 Ultra Client (en0) |

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

---

## 🟧 Switch 4: switch25gStudio (Studio)
**Role**: Layer 2 Access + Aggregation for OPNsense (Active)
**Model**: Horaco HC-SWTGW218ASHC
**Management IP**: `192.168.2.3` / `255.255.255.0`
**Gateway**: `192.168.2.1`

### 1. VLAN Settings
Create VLANs: `1`, `10`, `20`, `30`, `99`.

### 2. Port Configuration
| Port | Mode | PVID | Tagged VLANs | Untagged VLANs | Notes |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **1** | Access | 99 | - | `99` | **PVE2** OOB Service Port |
| **2** | Access | 99 | - | `99` | **PVE1** OOB Service Port |
| **3** | Access | 99 | - | `99` | **PVE3** OOB Service Port |
| **4** | Access | 99 | - | `99` | **OPNsense** igc3 OOB |
| **5** | Access | 99 | - | `99` | **Free OOB Port** (e.g. KVM Extender) |
| **6** | Trunk | 1 | `10, 20, 30, 99` | `1` | Uplink to **OPNsense** igc1 (LAN Trunk) |
| **7** | Access | 1 | - | `1` | Free / Unused |
| **8** | Access | 1 | - | `1` | Free / Unused |
| **9** | Trunk | 1 | `1, 10, 20, 30, 99` | `1` | Downlink to **switch10g** Port 1 |

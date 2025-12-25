# OPNsense Migration Report: Cron & UPnP

This report details the settings extracted from your old `config.xml` (192.168.1.1) and provides instructions to apply them to your new topology.

> [!IMPORTANT]
> **New Topology Mapping**:
> - **LAN (Old)**: `192.168.1.1` -> **Client VLAN 20** (`10.10.20.1`)
> - **Interfaces**: Old `lan` maps to new `opt2` (Client) and `opt3` (IoT).

## 1. Cron Jobs (Scheduled Tasks)
**Source**: `<cron>...</cron>` section.

| Description | Command | Schedule | Action |
| :--- | :--- | :--- | :--- |
| **Riavvio se non risponde Google** | `syncping syncping` | `* * * * *` (Every Minute) | **Recreate**. Useful for WAN monitoring. |
| **IDS Rule Updates** | `ids update` | `0 0 * * *` (Daily) | **Skip** (Disabled in old config). |

### How to Apply
> [!TIP]
> **Improved Logic**: OPNsense doesn't have a native "Auto-Renew on Ping Loss" checkbox, but we can improve your script. Instead of rebooting the whole firewall (`/sbin/reboot`), we can just reload the WAN interface (`configctl interface reconfigure wan`). This is much faster/safer.

1. **Restore Custom Action (Improved)**:
   - **Create File**: `/usr/local/opnsense/service/conf/actions.d/actions_syncping.conf`
   - **Content**:
     ```ini
     [syncping]
     command: /sbin/ping -q -c 10 -W 2 8.8.8.8 >/dev/null || /usr/local/sbin/configctl interface reconfigure wan
     description: syncping - test connettivity and reload WAN
     parameters:
     type:script
     message:syncping failed --- reloading WAN
     ```
   - **Apply**: Run `service configd restart` via SSH.

2. **Restore Cron Job**:
   - Go to **System -> Settings -> Cron**.
   - **Command**: Select `syncping - test connettivity and reload WAN`.
   - **Schedule**: `* * * * *` (Every minute).

> [!NOTE]
> This new command only restarts the internet connection, not the whole server.


## 2. Universal Plug and Play (UPnP)
**Source**: `<miniupnpd>` section.

### UPnP Global Settings
- **Enable**: Yes
- **Enable NAT-PMP**: Yes
- **Ext Interface**: WAN
- **Interfaces (Listening)**:
  - **OLD**: `lan`
  - **NEW (Recommended)**: `opt2` (Client VLAN 20) and `opt3` (IoT) if you have consoles there.
- **User Permissions (ACL)**:
  - `allow 1024-65535 192.168.1.249 1024-65535`
  - `allow 1024-65535 192.168.1.11 1024-65535`
  - `allow 1024-65535 192.168.64.6 1024-65535`

### How to Apply
1. **Install Plugin**: Ensure `os-upnp` is installed (**System -> Firmware -> Plugins**).
2. Go to **Services -> Universal Plug and Play -> Settings**.
3. **Enable**: Checked.
4. **Interfaces**: Select **CLIENT** (VLAN 20) and **IOT** (VLAN 30).
5. **User Permissions**:
   - The old IPs (`192.168.1.xxx`) are invalid in the new network.
   - **Recommended Policy**: Use a generic allow for the Client subnet or specific reservations if you assign static IPs in the new range.
   - Example Entry: `allow 1024-65535 10.10.20.0/24 1024-65535` (Allows entire Client VLAN).

## 3. Firewall Rules (UPnP Related)
Your old config had specific Allow rules for UPnP traffic. This is good practice if "Default Deny" is on, but UPnP plugin usually handles generic auto-rules.

**Extracted Rules**:
1. **SSDP (Discovery)**: Allow UDP from `151.59.34.116` (?) to `239.255.255.250:1900`.
   - *Note: `151.59.xxx` looks like a public IP. Allowing UPnP discovery from WAN is DANGEROUS. Verify if this source IP is trusted or a mistake.*
2. **NAT-PMP**: Allow UDP from `192.168.1.249` to Port `5351`.
3. **UPnP TCP**: Allow TCP from `192.168.1.249` to Port `2189`.

### How to Apply (New Topology)
Create these rules on the **CLIENT** (VLAN 20) interface:
1. **Pass / UDP**: Source `Client Net`. Dest `239.255.255.250`, Port `1900`.
2. **Pass / UDP**: Source `Client Net`. Dest `This Firewall`, Port `5351`.
3. **Pass / TCP**: Source `Client Net`. Dest `This Firewall`, Port `2189`.

## 4. Other Important Settings
### Dynamic DNS (Cloudflare)
**Source**: `<DynDNS>` dictionary.
- **Enabled**: Yes
- **Service**: Cloudflare
- **Hostname**: `pindaroli.org`
- **Username**: (Empty/Token based)
- **Password**: `bUIQ3VrLSFMTMgGpITh11j555osNBSgKq_J3uoy9` (API Token)
- **Interface**: WAN

**How to Apply**:
1. Install `os-ddclient` plugin.
2. Go to **Services -> Dynamic DNS**.
3. Add new account with above details.
4. *Verify if you need `os-ddclient` or legacy DynDNS plugin (check plugins list).*

### System Tunables (Sysctl)
**Source**: `<sysctl>` section.
- `hw.ibrs_disable`: (Empty value - Likely set to default or disabled)
- `vm.pmap.pti`: (Empty value)
*These seem to be CPU mitigation toggles (Spectre/Meltdown). Apply only if you know why they were added (performance vs security).*

### Unused/Disabled Services (Found but Disabled)
- **WireGuard**: Configured but Enabled=0.
- **Monit**: Configured but Enabled=0.
- **HAProxy**: Configured but Enabled=0.

## 5. Static Mappings (Bonus)
I found these devices in your old DHCP. You should assign them new IPs in the `10.10.20.x` range via **Services -> DHCPv4 -> [Client]**.

| Hostname | MAC Address | Old IP | Proposed New IP |
| :--- | :--- | :--- | :--- |
| **Google-Nest-Mini** | `d4:f5:47:24:40:bf` | `192.168.1.102` | `10.10.20.102` |
| **Tab-S9** | `7a:5d:a2:f4:c5:dd` | `192.168.1.108` | `10.10.20.108` |
| **Google-Home-Mini** | `00:f6:20:9b:28:bf` | `192.168.1.140` | `10.10.20.140` |
| **AP11000** | `80:af:ca:c0:2e:5a` | `192.168.1.147` | `10.10.20.147` |
| **SteamDeck** | `0c:79:55:d5:ef:a6` | `192.168.1.151` | `10.10.20.151` |


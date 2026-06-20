# Incident: DHCP Relay Outage in Symmetric Routing
**Date**: 2026-06-20
**Status**: UNRESOLVED (DHCP propagation fails, client falls back to APIPA)
**Severity**: High (Clients on VLAN 20 cannot acquire IP addresses dynamically)

## 🔍 Diagnosis
During the alignment of the network to a **Symmetric Routing** architecture, OPNsense interface IPs on VLAN 10 and VLAN 20 were set to `None`. IP routing and DHCP requests on VLAN 20 are intended to be managed via L3 Switch Relay to the OPNsense Transit IP (`192.168.2.254`).

However, clients on VLAN 20 (such as the Mac Studio M2 Ultra on `en0`) fail to acquire an IP address and fall back to self-assigned IP addresses (`169.254.x.x`).

### Findings
1. **Relay simulation test**: Running a manual python script mimicking the relay packet (`giaddr = 10.10.20.1`, `chaddr = Mac MAC`) directly to `192.168.2.254:67` works successfully. OPNsense Kea DHCP receives it, allocates `10.10.20.100` and responds.
2. **Switch CLI configuration**:
   * Inspecting `show running-config` via Telnet (Port 23) revealed that the switch was originally configured with `ip helper-address 10.10.20.254` (the old OPNsense IP on VLAN 20).
   * The L3 Switch configuration was manually corrected via Telnet CLI to:
     ```text
     interface Vlan20
      ip helper-address 192.168.2.254
     ```
3. **Current issue**: Despite the helper IP correction on the switch SVI `Vlan20`, native DHCP broadcast requests from clients on VLAN 20 are still not reaching OPNsense or the offers are not successfully propagated back to the clients.

## 🛠️ Actions Taken
* Verified switch port configuration and VLAN tagging between `switch-25g-letto` and `switch10g` (Core).
* Discovered and documented that the switch Telnet port (23) is open.
* Updated `rete.json` to document Telnet port 23 availability on the core switch.
* Switched the `ip helper-address` on `Vlan20` from `10.10.20.254` to `192.168.2.254` via switch CLI.

## 🛡️ Next Steps / Recommendations for Next Session
* Run packet captures on the switch interfaces to see if the client's DHCP Discover broadcast is intercepted by the L3 SVI.
* Inspect if Option 82 inserts or DHCP Snooping configurations on the Layer 2 switch (`switch-25g-letto`) are dropping DHCP packets.
* Verify if firewall rules on OPNsense Transit interface (`opt4`) are blocking the UDP 67/68 relay traffic from the switch IP `192.168.2.1`.

## 🔗 References
* [[OPNsense]]
* [[Talos_Cluster]]
* [rete.json](file:///Users/olindo/prj/k8s-lab/rete.json)
* [[Network_Registry]]

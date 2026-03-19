# DNS Naming Policy based on `rete.json`

This policy defines the strict criteria used to translate the `rete.json` inventory into valid, resolvable DNS records (e.g., for Unbound).

## Guiding Principles
- **Validity:** All generated hostnames must comply with RFC 1123 (`A-Z`, `a-z`, `0-9`, `-`). Colons, spaces, and parentheses are strictly sanitized or dropped.
- **Functionality:** Only actionable identifiers and service endpoints are translated into DNS names. 
- **Exclusion:** Internal OS strings, hardware descriptions, and human-readable context fields are explicitly ignored.

## ✅ Criteria: Valid DNS Naming Sources
These fields in `rete.json` **MUST** generate a DNS record pointing to their respective IP:

1. **`id`**: The primary device identifier (e.g., `truenas`, `pve`, `opnsense`). This record maps to the device's main `management_ip`.
2. **`hostname`**: The internal FQDN string, if explicitly defined on the node.
3. **`aliases`**: The array of manually defined, explicit service names (e.g., `s3`, `auth`, `radarr`, `jellyfin`).
4. **Logical Interface `name`**: Functional endpoints (e.g., `gw-vlan20`). To prevent namespace collisions across devices, these are prefixed with the node's `id` (e.g., `opnsense-gw-vlan20`).
5. **VIPs (`vip`, VIP Nodes)**: Aliases linked to Virtual IPs. Note that if a physical node has a `vip` field, its base aliases (like `k1`) do *not* map to the VIP. The VIP is for the clustered service, isolated from the hardware identity.

## ❌ Criteria: Fields Ignored for DNS
These fields provide context but **MUST NOT** be used to generate DNS records:

1. **`network` / `description` / `notes`**: Human-readable context fields (e.g., "Client (VLAN 20)").
2. **`interface` / `os_name`**: Internal OS identifiers reflecting physical or virtual hardware assignments (e.g., `opt2`, `en0`, `enp1s0f0`, `nic0`).
3. **Hardware Metadata**: Fields such as `role`, `type`, `model`, `vendor`, and `brand`.

---
title: "Incidente: DNS Split-Horizon Resolution Failure"
date: "2026-05-03"
status: "RESOLVED"
severity: "High"
tags:
  - "#incident"
  - "#networking"
entities:
  - "[[OPNsense]]"
  - "[[Talos_Cluster]]"
---

# Incident Report: DNS Split-Horizon Resolution Failure

## 1. Symptoms
- Internal services using the `-internal.pindaroli.org` suffix were intermittently unreachable or resolved to `0.0.0.0`.
- Kubernetes Pods (Homepage, Tdarr) reported connection errors when attempting to resolve internal domain names.
- Browsers (Chrome) showed "Refused to connect" errors even when the network appeared stable.

## 2. Root Cause Analysis
The issue was caused by a "Perfect Storm" of three misconfigurations:

1. **OPNsense DNS Access List (ACL)**: Unbound DNS was configured to only answer queries from local physical VLANs. The Kubernetes Pod overlay subnet (`10.244.0.0/16`) was not in the "Allow" list, causing OPNsense to reject DNS queries from the cluster pods.
2. **Talos Configuration Error**: The Talos nodes were hardcoded to use `10.10.20.1` (the L3 Switch) as their primary nameserver. Since the switch does not run a DNS server, queries timed out or were refused, forcing a fallback to public DNS (`1.1.1.1`).
3. **Public DNS "Black Hole" Records**: Cloudflare (Public DNS) contained A records for `*-internal.pindaroli.org` pointing to `0.0.0.0`. This was a legacy security measure to prevent external resolution. However, when the internal DNS failed (due to causes 1 and 2), clients received the `0.0.0.0` response and cached it aggressively (exacerbated by Chrome's DNS-over-HTTPS).

## 3. Resolution Steps
1. **Firewall Access**: Added `10.244.0.0/16` to OPNsense Unbound Access Lists with `Allow` action.
2. **Talos Alignment**: Corrected `talos-config/controlplane.yaml` to point to the real OPNsense DNS IP: `10.10.20.254`.
3. **Cleanup**: Removed the `0.0.0.0` blackhole records from the Cloudflare Dashboard.
4. **Automation Update**: Removed the Ansible task in `cloudflare_sync.yml` that was responsible for creating the blackhole records to prevent re-occurrence.
5. **OPNsense Optimization**: Set Unbound to `transparent` mode and verified DHCP Option 15 (Domain Name) as `pindaroli.org`.

## 4. Lessons Learned
- **Avoid 0.0.0.0 for Internal Shadows**: Using `0.0.0.0` on public DNS is dangerous because it is a "valid" IP that browsers cache. It is better to have no record (NXDOMAIN) so that the client is forced to try the local resolver.
- **Nameserver Source of Truth**: Always ensure that infrastructure-level DNS settings (Talos, DHCP) point to the authoritative internal resolver (OPNsense) and not the gateway/switch unless explicitly intended.
- **ACL Visibility**: When adding new virtual subnets (like K8s CNI), the firewall ACLs must be updated immediately.

## 5. Verification
- `nslookup tdarr-internal.pindaroli.org` from inside a Pod: **SUCCESS** (Returns 10.10.20.56)
- `curl -I https://home-internal.pindaroli.org` from Mac Studio: **SUCCESS** (200 OK)
- Ansible `cloudflare_sync.yml` run: **SUCCESS** (No blackhole records created)

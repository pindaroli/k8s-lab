# Incident Report: Servarr VPN Routing Loop & OOM Crashes

**Date:** 2026-01-08
**Status:** 🟢 RESOLVED
**Impact:** `qbittorrent` and `prowlarr` pods unstable (CrashLoopBackOff), causing downtime for media ingestion.
**Components:** Kubernetes, Servarr Helm Chart, Tun2Socks, Xray Core.

## 1. Executive Summary
The Servarr stack experienced severe instability manifested as `OOMKilled` crashes in the `tun2socks-gateway` variable `xray-core` sidecars. The root cause was identified as a network routing loop where outbound proxy traffic was re-routed back into the tunnel interface, causing infinite recursion and instant memory saturation. A secondary issue caused `prowlarr` readiness probes to fail due to incorrect routing of Kubelet traffic.

Both issues have been resolved by implementing **Policy Based Routing (PBR)**, granting necessary container privileges (`NET_ADMIN`, `Privileged`), and implementing specific routing bypass rules for private subnets.

## 2. Technical Details

### 2.1 The Crash (Routing Loop)
*   **Symptoms**: `tun2socks` and `xray-core` containers crashing with `Exit Code 137 (OOMKilled)` seconds after startup, despite memory limits of 1Gi.
*   **Mechanism**:
    1.  `tun2socks` created a default route (`0.0.0.0/0`) via `tun0`.
    2.  `xray-core` attempted to connect to the external proxy server (e.g., `188.114.x.x`).
    3.  Because the default route was `tun0`, this connection was sent to `tun2socks`.
    4.  `tun2socks` encapsulated the packet and sent it back to `xray-core` (SOCKS5).
    5.  `xray-core` tried to send it out again -> **LOOP**.
    6.  The loop generated packets faster than the kernel could process, consuming all available RAM.

### 2.2 The Probe Failure (Prowlarr)
*   **Symptoms**: `prowlarr` pod Stuck in `2/3 Running` state. `tun2socks` logs showed no activity blocking it, but Kubelet reported `Readiness probe failed: context deadline exceeded`.
*   **Mechanism**:
    *   Kubelet (IPs `10.10.x.x`) polls `prowlarr` on port `9696`.
    *   `prowlarr` receives the request.
    *   The reply packet uses the default route (`tun0`).
    *   The packet is tunneled out to the VPN endpoint instead of being returned to the Kubelet on the local network.

### 2.3 Regression: Memory Pressure (qBittorrent)
*   **Symptoms**: After solving the loop, `qBittorrent`'s `tun2socks` container continued to crash with OOMKilled, while `prowlarr` remained stable.
*   **Analysis**: qBittorrent handles significantly higher traffic (UDP DHT, many TCP connections) than Prowlarr. The initial debug limit of 128Mi was insufficient for the increased state table size of `tun2socks` under load.
*   **Fix**: Increased `tun2socks` memory limit to **512Mi** for qBittorrent.

## 3. Resolution

### 3.1 Policy Based Routing (PBR)
To break the loop, we moved away from replacing the global default gateway.
*   **Xray Config**: Added `sockopt: { mark: 255 }` to outbound connections to tag them.
*   **Routing Rules**:
    1.  Created a separate routing table (`100`) for tunneled traffic.
    2.  Added `ip rule add fwmark 255 lookup main` -> Traffic from Xray bypasses the tunnel.
    3.  Added `ip rule add lookup 100` -> Everything else goes to the tunnel.

### 3.2 Privilege Escalation
The `fwmark` solution initially failed because Xray lacked permissions to set packet marks.
*   **Fix**: Updated Helm values to grant `privileged: true`, `runAsUser: 0`, and `capabilities: [NET_ADMIN]` to Xray containers.

### 3.3 Probe & Internal Routing Fix
To solve the Probe failure, we explicitly bypassed local and cluster networks.
*   **Fix**: Added `ip rule add to 10.0.0.0/8 lookup main`.
*   This covers:
    *   **Nodes**: `10.10.0.0/24`
    *   **Pods**: `10.244.0.0/16`
    *   **Services**: `10.96.0.0/12`

### 3.4 Script Hardening
*   **Fix**: Appended `|| true` to all `ip route` and `ip rule` commands in the `tun2socks` startup script. This ensures the pod can restart cleanly even if the network namespace retains previous rules (idempotency).

## 4. Current Configuration
**File**: `servarr/arr-values.yaml`
```yaml
# Xray Sidecar
- name: xray-core
  securityContext: { privileged: true, runAsUser: 0, capabilities: { add: ["NET_ADMIN"] } }
  # ...

# Tun2Socks Sidecar
- name: tun2socks-gateway
  args:
    - |
      # ...
      ip rule add to 10.0.0.0/8 lookup main priority 450 || true
      ip rule add fwmark 255 lookup main priority 600 || true
      ip rule add lookup 100 priority 800 || true
```

## 5. Verification
*   **qBittorrent**: Running 3/3. Public IP verified as VPN Exit Node.
*   **Prowlarr**: Running 3/3. Readiness probes passing. Indexers functional.

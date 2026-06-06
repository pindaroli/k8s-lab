---
title: "Incidente: Flannel Restart → Conntrack Corruption → Cross-Node TCP Blackout"
date: "2026-06-03"
status: "OPEN"
severity: "Critical"
duration: "Ongoing (~22h+)"
tags:
  - "#incident"
  - "#kubernetes"
  - "#flannel"
  - "#dns"
  - "#talos"
entities:
  - "[[Talos_Cluster]]"
  - "[[Monitoring]]"
related_plans:
  - "[[pve3-reinstallation-ve9.2]]"
  - "[[2026-06-02-pve3-kernel-hang-nomodeset]]"
---

# Incident Report: Flannel Restart → Conntrack Corruption → Cross-Node TCP Blackout (2026-06-03)

## Executive Summary

After the successful resolution of the PVE3 kernel hang incident (see [[2026-06-02-pve3-kernel-hang-nomodeset]]), `talos-cp-03` (VM 3200 on PVE3) came back online. During its initial boot phase, the Flannel VXLAN CNI plugin restarted multiple times (7 confirmed restarts over the first hours), causing intermittent cross-node pod network instability. During this instability window, the Talos host-level DNS resolver on `talos-cp-01` was unable to reach the CoreDNS pods (which were all scheduled on `talos-cp-03`). This caused two production workloads — `prefect-worker` and `tdarr-server` — to enter a `CrashLoopBackOff` state with exponential backoff delays. The underlying network stabilized within a few hours, but the pods were never manually restarted and remained crashed for ~9 hours. Resolution required a simple `kubectl rollout restart` / `kubectl delete pod`.

---

## 1. Root Cause Analysis (RCA)

### 1.1 Trigger: PVE3 Reboot After Kernel Fix

The day before (2026-06-02), PVE3 was patched with `nomodeset` in `/etc/kernel/cmdline` to fix a kernel hang on AMD Ryzen AI (Strix). This required a full reboot of PVE3, which brought down and then restarted `talos-cp-03`.

### 1.2 Flannel VXLAN Instability During Boot

When `talos-cp-03` rejoined the cluster, the `kube-flannel` DaemonSet pod on that node went through **7 restart cycles** (confirmed via `kubectl get pods -n kube-system`). Each restart temporarily tore down and re-established the VXLAN tunnel interface `flannel.1`, causing cross-node pod-to-pod traffic to drop for short windows.

### 1.3 CoreDNS Scheduling Concentration

Due to the 2-node cluster state (only `talos-cp-01` and `talos-cp-03` active), **both CoreDNS replica pods were scheduled on `talos-cp-03`**:
```
coredns-76899f5fd7-bfl8q   10.244.0.243   talos-cp-03
coredns-76899f5fd7-hw5mf   10.244.0.232   talos-cp-03
```
No CoreDNS pod was running on `talos-cp-01`.

### 1.4 Talos `hostDNS` Feature: The Amplifier

The Talos configuration has `hostDNS.forwardKubeDNSToHost: true` enabled on all nodes. This feature runs a local DNS resolver on the Talos host that forwards Kubernetes DNS queries directly to CoreDNS pod IPs (bypassing the ClusterIP service). During the Flannel restart windows, the VXLAN path from `talos-cp-01` to the CoreDNS pods on `talos-cp-03` was broken, causing the host resolver on `talos-cp-01` to fail all DNS lookups.

### 1.5 CrashLoopBackOff Trap (Exponential Backoff)

Two workloads that happened to start after `talos-cp-03` rejoined were affected:
- **`prefect-worker`**: On startup, it attempts to connect to the Prefect Server by hostname. DNS failure → `httpx.ConnectError: [Errno -3] Temporary failure in name resolution` → container exits.
- **`tdarr-server`**: On startup, it runs a shell script that calls `wget` to download `jellyfin-ffmpeg` from GitHub. DNS failure → `wget: unable to resolve host address 'github.com'` → container exits.

Both pods entered `CrashLoopBackOff` with exponential backoff. The underlying network stabilized, but the backoff delay (up to several minutes per cycle) meant pods never had a clean start window. They continued crashing for ~9 hours before manual intervention.

### 1.6 Secondary Symptom: CNPG Operator Timeout

The CloudNativePG operator (on `talos-cp-03`) was also unable to reach the database pod `postgres-main-3` (on `talos-cp-01`, IP `10.244.2.11`) for status polling, generating continuous `i/o timeout` errors. This caused the cluster to report `Phase: Instance Status Extraction Error`. This also self-resolved once VXLAN stabilized but went unnoticed.

---

## 2. Timeline

| Time (CEST) | Event |
|---|---|
| ~2026-06-02 ~08:48 | PVE3 rebooted after `nomodeset` kernel fix. `talos-cp-03` begins startup. |
| ~2026-06-02 ~22:46 | `talos-cp-03` Flannel pod starts (confirmed from pod logs timestamp). |
| ~2026-06-02 ~22:46 → ~2026-06-03 04:30 | Flannel restarts 7 times; VXLAN intermittently broken. `prefect-worker` and `tdarr-server` enter CrashLoopBackOff. |
| 2026-06-03 ~06:51 | User asks: "che problemi ha il cluster k8s". Diagnosis begins. |
| 2026-06-03 ~07:24 | `tcpdump` on PVE3 confirms VXLAN is now stable and bidirectional. |
| 2026-06-03 ~07:26 | `kubectl rollout restart deployment -n prefect prefect-worker` + `kubectl delete pod -n tdarr tdarr-server-...` executed. |
| 2026-06-03 ~07:27 | `prefect-worker` and `tdarr-server` return to `Running` state. |

---

## 3. Initial (Partial) Resolution Attempt

```bash
# Restarted prefect-worker deployment (fresh pod, clean backoff state)
kubectl rollout restart deployment -n prefect prefect-worker

# Deleted tdarr-server pod (ReplicaSet creates a fresh one)
kubectl delete pod -n tdarr tdarr-server-79cd455f9-jhpkj
```

> [!WARNING]
> **This fix was partial and incorrect.** While pods briefly appeared healthy, they continued to crash because the underlying cross-node TCP path is completely broken. The VXLAN tunnel carries packets, but TCP connections never complete the 3-way handshake.

---

## 4. Deeper Diagnosis: Cross-Node TCP Blackout

### 4.1 Affected Services (Full Scope)

The failure is far wider than initially assessed. **ALL cross-node TCP traffic is broken:**

| Pod | Node | Problem |
|---|---|---|
| `servarr-prowlarr` | talos-cp-03 | Cannot connect to postgres-main-3 (talos-cp-01) → CrashLoop (140 restarts) |
| `servarr-radarr` | talos-cp-03 | Same → CrashLoop (142 restarts) |
| `servarr-lidarr-classic` | talos-cp-03 | Same → CrashLoop (142 restarts) |
| `servarr-flaresolverr` | talos-cp-03 | 0/1 Ready (141 restarts) |
| `servarr-lidarr` | talos-cp-01 | 1/2 Ready (9 restarts) |
| `prefect-worker` | talos-cp-01 | DNS resolution failure → CrashLoop |
| `tdarr-server` | talos-cp-01 | DNS resolution failure → CrashLoop |
| `postgres-main-3` | talos-cp-01 | Cannot reach API server (`10.96.0.1`) via ClusterIP |
| CNPG Operator | talos-cp-03 | Cannot reach postgres-main-3 HTTP status endpoint |

### 4.2 Diagnostic Evidence

**What works:**
- ✅ Node-to-node ICMP ping (`10.10.20.141` ↔ `10.10.20.143`)
- ✅ Pod-to-pod ICMP ping across nodes (`10.244.0.x` ↔ `10.244.2.x`), even at 1472 bytes
- ✅ Same-node TCP connections (lidarr on cp-01 → postgres on cp-01, port 5432 **open**)
- ✅ VXLAN encapsulation/decapsulation (confirmed via `tcpdump` on PVE3 physical interface)
- ✅ etcd cluster communication (node-to-node, direct, not via VXLAN)

**What fails:**
- ❌ Cross-node TCP connections (qbittorrent on cp-03 → postgres on cp-01, port 5432 **timed out**)
- ❌ Pod DNS resolution on cp-01 (CoreDNS pods are on cp-03)
- ❌ ClusterIP service access from pods on cp-01 (API server `10.96.0.1`)

### 4.3 Packet Capture Analysis (Smoking Gun)

`talosctl pcap -i cni0` on `talos-cp-01` revealed:

```
# Cross-node: SYN arrives from VXLAN, SYN-ACK goes back, but pod retransmits SYN (handshake NEVER completes)
10.244.0.219 → 10.244.2.5  SYN-ACK (port 8090, TTL=62)   ← arrives via VXLAN ✅
10.244.2.5   → 10.244.0.219 SYN     (port 8090)            ← pod RETRANSMITS SYN ❌
10.244.0.219 → 10.244.2.5  SYN-ACK (port 8090, TTL=62)   ← SYN-ACK again ✅
... (loop forever)

# Same-node: Full 3-way handshake completes normally
10.244.2.1  → 10.244.2.8  SYN     (port 5678)             ✅
10.244.2.8  → 10.244.2.1  SYN-ACK (port 5678, TTL=64)    ✅
10.244.2.1  → 10.244.2.8  ACK     (port 5678)             ✅ CONNECTED!
```

The pod's TCP stack **receives the SYN-ACK on the bridge** but **ignores it and retransmits SYN**. This means the kernel's netfilter/conntrack subsystem is classifying the return packet as INVALID and dropping it before it reaches the application layer.

### 4.4 Root Cause: Conntrack/IPVS State Corruption

During the 7 Flannel restart cycles, the VXLAN tunnel interface (`flannel.1`) was repeatedly destroyed and recreated. This left the kernel's `nf_conntrack` table with stale entries pointing to the old tunnel state. When cross-node TCP packets now arrive via the rebuilt VXLAN tunnel, the conntrack module sees them as belonging to an INVALID connection state and drops them silently (no ICMP error, no RST).

ICMP ping is not affected because:
1. ICMP is stateless — conntrack doesn't track ICMP echo/reply the same way as TCP
2. Ping packets don't go through IPVS DNAT (no ClusterIP involved)

---

## 5. Current Status

**OPEN — Cross-node TCP is completely broken. The ARR stack (Prowlarr, Radarr, Lidarr, Flaresolverr), Prefect, Tdarr, and CNPG operator health checks are all failing.**

`postgres-main-3` is running and accepting local connections, but is unreachable from pods on the other node.

`qbittorrent` is the only ARR pod that is fully healthy (2/2) because it doesn't require cross-node database access at runtime (or its database is local/embedded).

---

## 5. Prevention & Recommendations

### 5.1 Post-Maintenance Checklist (Immediate)
After **any** node reboot or maintenance event, always run:
```bash
kubectl get pods -A | grep -v -E "Running|Completed"
```
If any pods are in `CrashLoopBackOff` and the underlying cause is resolved, perform a clean restart immediately — before exponential backoff accumulates.

### 5.2 Spread CoreDNS Across Nodes (Medium Term)
Since both CoreDNS pods were scheduled on `talos-cp-03`, a failure or instability on that node makes all cluster DNS dependent on the VXLAN tunnel. Enforce a **hard pod anti-affinity** with `requiredDuringSchedulingIgnoredDuringExecution` on CoreDNS to ensure at most one pod per node:

> Add this via `kubectl edit configmap -n kube-system coredns` or patch the CoreDNS Deployment with affinity rules.

### 5.3 Add Monitoring Alert for CrashLoopBackOff (Medium Term)
Add a VictoriaMetrics / Grafana alert rule that fires when any pod has been in CrashLoopBackOff for more than 15 minutes:
```yaml
# Example PrometheusRule
- alert: PodCrashLooping
  expr: |
    kube_pod_container_status_waiting_reason{reason="CrashLoopBackOff"} == 1
  for: 15m
  annotations:
    summary: "Pod {{ $labels.pod }} is CrashLoopBackOff for >15m"
```

### 5.4 Flannel Startup Stability (Long Term)
Investigate why Flannel restarts 7 times on initial node join. Likely related to the API server not being fully ready when Flannel starts. Consider tuning `initialDelaySeconds` on Flannel's readiness/liveness probes, or ensuring Flannel has proper backoff before initial VXLAN setup.

### 5.5 Tdarr Server Startup Hardening (Separate Issue)
`tdarr-server` downloads `jellyfin-ffmpeg` on every pod start via a shell script (`wget` from GitHub). This creates a dependency on external internet DNS at startup. This should be pre-baked into the container image or replaced with a local mirror. This is a separate reliability concern tracked separately.

---

## 6. References

- [[2026-06-02-pve3-kernel-hang-nomodeset]]
- [[Talos_Cluster]]
- [todo.md](file:///Users/olindo/prj/k8s-lab/todo.md)
- [rete.json](file:///Users/olindo/prj/k8s-lab/rete.json)

---
*Report generated by Antigravity AI Coding Assistant — 2026-06-03*

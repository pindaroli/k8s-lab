# Incident Report: Homepage Dashboard API Error

**Date:** 2026-01-10
**Status:** 🟢 RESOLVED
**Impact:** "API Error" banner on Homepage Dashboard. `kubernetes` widget failed to display Cluster/Node CPU and Memory stats.
**Components:** Homepage, Metrics Server, Talos Linux.

## 1. Executive Summary
The Homepage dashboard displayed a persistent "API Error" banner. Investigation revealed the `kubernetes` widget was failing to query cluster metrics because the `metrics-server` component was missing from the cluster. The issue was resolved by installing `metrics-server` with configuration appropriate for the Talos environment.

## 2. Technical Details

### 2.1 The Issue
*   **Symptoms**: 
    *   Red "API Error" banner at the top of the dashboard.
    *   Empty CPU/Memory graphs for the Cluster and Nodes.
    *   Homepage Pod logs contained repeated errors: `Error getting metrics, ensure you have metrics-server installed`.
*   **Root Cause**: 
    *   The `metrics-server` is not included by default in the Talos Linux cluster bootstrap.
    *   The Homepage application's `kubernetes` widget depends on the Metrics API (`/apis/metrics.k8s.io/`) to fetch real-time usage data.

### 2.2 Constraints
*   **TLS Trust**: In a standard Talos/Homelab setup, Kubelet certificates are often self-signed or not signed by a CA that the standard `metrics-server` image trusts by default. This typically results in `x509: certificate signed by unknown authority` errors if standard settings are used.

## 3. Resolution

### 3.1 Installation
We installed the standard Kubernetes `metrics-server` via Helm but added a critical argument to bypass the strict TLS verification for Kubelets.

**Helm Command**:
```bash
helm install metrics-server metrics-server/metrics-server -n kube-system -f metrics-server-values.yaml
```

**Configuration (`metrics-server-values.yaml`)**:
```yaml
args:
  # Required for Talos/Homelab if kubelet certs are not signed by a CA trusted by metrics-server
  - --kubelet-insecure-tls
```

### 3.2 Homepage Recovery
After installing the metrics server, we deleted the Homepage pod to force a restart. This cleared any back-off timers or cached connection states for the widget.

## 4. Verification
*   **CLI**: `kubectl top nodes` now correctly returns CPU and Memory usage for all three control plane nodes (`talos-cp-01`, `02`, `03`).
*   **UI**: The "API Error" banner is gone. cpu/memory bars are populating correctly.
*   **Logs**: Homepage logs no longer show the "Error getting metrics" exception.

## 5. Remaining Low-Severity Items
*   **GitHub API**: Logs still show `SSL routines:ssl3_read_bytes:ssl/tls alert handshake failure` when checking for Homepage updates (`api.github.com`). This is likely an upstream/MTU network issue irrelevant to the dashboard's internal functionality.

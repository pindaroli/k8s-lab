# Incident Report: 2026-05-03 - CNPG Database Logical Deadlock & Recovery

**Status**: ✅ RESOLVED
**Severity**: CRITICAL (Full Database Outage)
**Date**: 2026-05-03
**Services Impacted**: PostgreSQL (postgres-main), n8n, and all dependent workloads.

## 🔴 Executive Summary
Following a physical maintenance and reinstallation of Talos OS on `talos-cp-01` and `talos-cp-03`, the CloudNativePG (CNPG) operator entered a logical deadlock. Despite PersistentVolumes being physically intact, the operator failed to spawn any database pods, marking the primary volume as "Dangling".

## 🔍 Root Cause Analysis (RCA)
1.  **Node Identity Loss**: The Talos reinstall assigned random hostnames, breaking the `nodeAffinity` of Local-Path PersistentVolumes.
2.  **Stale Lock Files**: The abrupt shutdown/reinstall left `postmaster.pid` files on the data volumes.
3.  **Operator Deadlock**: The CNPG operator detected the stale lock files and the missing instance #1 (index gap), categorizing existing volumes as "Dangling" and refusing to initiate reconciliation to prevent potential data corruption.

## 🛠️ Resolution Steps
The recovery required a multi-layer intervention:

1.  **Identity Restoration**: Applied Talos patches to restore `talos-cp-01` and `talos-cp-03` hostnames, satisfying K8s volume affinity.
2.  **Lock File Removal**:
    - Created a `rescue-pod` to mount the `postgres-main-3` PVC.
    - Manually deleted `/data/pgdata/postmaster.pid`.
3.  **Orphan Re-adoption (The Pivot)**:
    - Deleted the `Cluster` object using `--cascade=orphan` to preserve data volumes.
    - Re-applied a cleaned `Cluster` manifest to force the operator to re-scan and adopt existing PVCs.
4.  **Strategic Fencing**:
    - Fenced `postgres-main-2` (which resides on the still-offline PVE2 node) to force the operator to promote and start `postgres-main-3`.
5.  **Zombie Pod Cleanup**: Force-deleted a 15-day-old `Pending` pod that was confusing the new operator.

## 💡 Lessons Learned & Prevention
- **Declarative Hostnames**: Hostnames MUST be set in the base Talos machine config, not just applied via patch later, to avoid identity mismatch on reinstall.
- **Dangling PVC Awareness**: CNPG operators can be extremely conservative; manual status patching or object recreation is sometimes the only way to break a logical loop.
- **Rescue Pods**: Always keep a generic rescue-pod template ready for disk inspection on local-path storage.

## 📈 Status Check
```bash
# Verify the primary pod is running
kubectl get pods -n cnpg-system -l postgresql.cnpg.io/cluster=postgres-main
```
**Current Primary**: `postgres-main-3` on `talos-cp-01`.

# Technical Incident: 2026-05-03-DB-STALL-IDENTITY-LOSS

**Status**: RESOLVED
**Incident Date**: 2026-05-03
**Resolution Date**: 2026-05-03
**Component**: CloudNativePG (PostgreSQL) / Talos OS

## 1. Incident Description
Following a maintenance window involving the reinstallation of Talos OS on control-plane nodes, the `postgres-main` cluster failed to recover. All database pods remained in a pending state or were not created at all, despite the underlying persistent storage (Local-Path) being physically intact.

## 2. Technical Findings
1.  **Hostname Mismatch**: Talos reinstallation resulted in random hostnames (e.g., `talos-default-xxx`). Kubernetes PersistentVolumes (PV) with `nodeAffinity` for the original hostnames (`talos-cp-01`) became unmountable.
2.  **Stale Lock Files**: The abrupt node shutdown left `/data/pgdata/postmaster.pid` files on the disks, which caused the PG engine to refuse startup during recovery attempts.
3.  **Operator Logic Stall**: The CNPG operator categorized the existing volumes as "Dangling" and entered a reconciliation loop where it refused to spawn pods to avoid potential data corruption.
4.  **IP Change**: The deletion/recreation of the cluster changed the Service ClusterIPs, breaking connectivity for applications (e.g., Lidarr) that used hardcoded IPs in their environment variables.

## 3. Corrective Actions Taken
- **Node Patching**: Manually restored node hostnames via Talos machine configuration patches.
- **Forensic Cleanup**: Deployed a rescue pod to mount the PVCs and manually delete the `postmaster.pid` files.
- **Orphan Re-adoption**: Deleted the `Cluster` CRD using `--cascade=orphan` and recreated it to force the operator to re-adopt the existing volumes.
- **Fencing/Scaling**: Fenced the offline node (PVE2) and scaled the cluster to 2 instances to match the available hardware.
- **App Fixes**: Updated Lidarr deployment to use the DNS service name `postgres-main-rw.cnpg-system.svc.cluster.local`.

## 4. Hardening & Prevention
- **Node-Specific Configs**: Created `controlplane-cp-01.yaml`, etc., with hardcoded hostnames and IPs.
- **Maintenance Workflow**: Documented a new procedure for "Safe Node Maintenance" in the project wiki.
- **IaC Stabilization**: Moved the verified cluster manifest to `postgres/cluster.yaml`.

---
*Reported by Antigravity AI Engineering*

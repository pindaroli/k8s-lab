# Backup Scheduling & Retention

This document serves as the source of truth for the automated backup strategies implemented in the `pindaroli-lab`.

---

## 1. Virtual Machine Backups (Proxmox)
**Engine**: `vzdump` (Proxmox Native)
**Target**: Proxmox Backup Server (PBS) via NFS Share `backup-proxmox`.

**Schedule:**
*   **Frequency**: Daily
*   **Time**: `02:00 AM`
*   **Compression**: `zstd` (Fast & Efficient)

**Retention Policy:**
*   **Keep Daily**: `7` (Last 7 days)
*   **Keep Weekly**: `4` (Last 4 weeks)

**Scope:**
Backs up **ALL** Virtual Machines and LXC Containers managed by the cluster, including:
*   Talos Control Plane Nodes
*   TrueNAS Core (Config/OS)
*   Utility Containers (Jellyfin, PBS itself)

---

## 2. Kubernetes Cluster Backups (Velero)
**Engine**: `velero` (Cloud-Native)
**Target**: MinIO Object Storage (S3-compatible).

**Schedule:**
*   **Frequency**: Daily
*   **Time**: `03:00 AM` (1 hour after VM backup)
*   **Name**: `velero-daily-backup`

**Retention Policy (TTL):**
*   **TTL**: `720h` (30 Days)

**Scope:**
Backs up all Kubernetes resources and Persistent Volumes (PVs) via Restic/Kopia integration (if enabled), including:
*   Cluster Configurations (Deployments, Secrets, ConfigMaps)
*   Namespace state (`arr`, `default`, `monitoring`)

---

## 3. PostgreSQL Database Backups (CloudNativePG)
**Engine**: `Barman` (Streaming WAL Archiving)
**Target**: MinIO S3 Bucket `s3://postgres-wal/` (`10.10.10.50:9000`).

**Strategy: Continuous Protection (PITR)**
Instead of just "daily snapshots", the database streams every transaction (WAL) to MinIO in real-time.
*   **RPO (Data Loss)**: Near Zero (< 5 minutes).
*   **Retention**: `30 Days`.
*   **Status**: **Active** (`ContinuousArchiving: True`).

**Scope:**
Protects all databases hosted in the `postgres-main` cluster:
*   `radarr-main`
*   `lidarr-main`
*   `prowlarr-main`
*   `jellyfin`

---

## 4. Recovery Procedures

### Restoring a VM (Proxmox)
1.  Go to **Proxmox GUI** -> **Storage** -> `pbs`.
2.  Select the **Backup** tab.
3.  Right-click the VM backup -> **Restore**.

### Restoring Kubernetes (Velero)
```bash
# List available backups
velero backup get

# Restore from latest daily backup
velero restore create --from-backup velero-daily-backup-<TIMESTAMP>
```

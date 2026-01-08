# Prowlarr Migration Guide (SQLite to PostgreSQL)

> [!IMPORTANT]
> This guide documents the successful "Schema-First" strategy used to migrate Prowlarr to CloudNativePG.
> It addresses specific issues with the **LSIO image** (configuration changes ignored) and **DNS/VPN leaks** (sidecar routing issues).

## 1. Prerequisites

### Image Selection (Critical)
The standard `linuxserver/prowlarr` image **does not** reliably support PostgreSQL configuration via environment variables.
*   **Recommendation**: Use `ghcr.io/hotio/prowlarr:release` (Stable).
*   **Configuration**: Hotio uses `.NET` style double-underscore variables (e.g., `PROWLARR__POSTGRES__HOST`).

### Network Stability (Critical)
If Prowlarr runs with a simplified `tun2socks` sidecar, local DNS resolution might leak through the VPN or fail.
*   **Workaround**: Hardcode the **ClusterIP** or **Pod IP** of the PostgreSQL Primary/RW service in `PROWLARR__POSTGRES__HOST`.
*   **Why**: This bypasses Kubernetes Service discovery (CoreDNS) which might be intercepted by the VPN rules.

---

## 2. Migration Procedure

### Step 1: Configure & Start (Schema Init)
Unlike generic migrations, we let Prowlarr create its own schema first on a clean database.

1.  **Stop Prowlarr**: `kubectl scale deployment -n arr servarr-prowlarr --replicas=0`
2.  **Reset Database**: Ensure the target DB is empty.
    ```bash
    # Run a temporary pod to drop/create schema public
    kubectl run db-reset -n arr --rm -i --image=postgres:alpine -- env PGPASSWORD=prowlarr psql -h <PG_IP> -U prowlarr -d prowlarr -c "DROP SCHEMA public CASCADE; CREATE SCHEMA public;"
    ```
3.  **Update Config (`arr-values.yaml`)**:
    ```yaml
    image:
      repository: ghcr.io/hotio/prowlarr
      tag: "release"
    env:
      # Use proper prefix for Hotio/NET
      PROWLARR__POSTGRES__HOST: "10.108.78.94" # Use generic Service IP if DNS works, or static Pod IP if unstable
      PROWLARR__POSTGRES__PORT: "5432"
      PROWLARR__POSTGRES__MAINDB: prowlarr
      PROWLARR__POSTGRES__USER: prowlarr
      PROWLARR__POSTGRES__PASSWORD: prowlarr
    ```
4.  **Start Prowlarr**: `kubectl scale deployment -n arr servarr-prowlarr --replicas=1`
5.  **Wait**: Monitor logs until you see `MigrationController: ... Migrating Database`. Wait for initialization to finish. Even if it crashes with `UpdateHistory` error (non-fatal bug in some versions), the tables should be created.

### Step 2: Migrate Data (PgLoader)
Use `pgloader` to copy data from the existing SQLite file to the new Postgres schema.

**Manifest (`postgres/migrate-prowlarr.yaml`)**:
```yaml
apiVersion: batch/v1
kind: Job
metadata:
  name: migrate-prowlarr
  namespace: arr
spec:
  template:
    spec:
      restartPolicy: Never
      containers:
        - name: pgloader
          image: ghcr.io/dimitri/pgloader:latest
          securityContext:
            runAsUser: 1000 # MATCH Prowlarr UID to avoid NFS ReadOnly errors
            runAsGroup: 1000
          command:
            - pgloader
            - --with
            - "data only"
            - --with
            - "truncate"
            - --with
            - "quote identifiers"
            - /mnt/data/prowlarr.db
            - postgresql://prowlarr:prowlarr@10.244.0.114:5432/prowlarr
          volumeMounts:
            - name: data
              mountPath: /mnt/data
      volumes:
        - name: data
          persistentVolumeClaim:
            claimName: servarr-prowlarr-config
```

1.  **Stop Prowlarr**: `kubectl scale deployment -n arr servarr-prowlarr --replicas=0`
2.  **Run Job**: `kubectl apply -f postgres/migrate-prowlarr.yaml`
3.  **Verify**: Check logs `kubectl logs -n arr job/migrate-prowlarr`. Expect warnings about type casting, but ensure "rows" are copied > 0.

### Step 3: Finalize
1.  **Restart Prowlarr**: `kubectl scale deployment -n arr servarr-prowlarr --replicas=1`
2.  **Verify UI**: Check if Indexers and History are preserved.

---

## 3. Common Errors & Fixes
| Error | Cause | Fix |
|---|---|---|
| `Code READONLY` | `pgloader` running as root (0) on NFS share owned by 1000. | Set `runAsUser: 1000` in Job. |
| `Socket error ETIMEDOUT` | VPN/Sidecar intercepting internal DNS/Service IPs. | Hardcode Postgres Pod IP in Connection String & values.yaml. |
| `UpdateHistory relation does not exist` | Hotio `latest` tag unstable or database partial init. | Use `tag: release` and fully reset schema before first boot. |
| `Schema public not found` | Prowlarr didn't run before migration. | Run "Step 1" restart sequence to let Prowlarr create tables first. |

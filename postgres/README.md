# PostgreSQL Storage Setup (Proxmox Zvol + Talos)

To ensure high performance for our Postgres cluster, we use dedicated **ZFS Volumes (Zvols)** on Proxmox, passed through to the Talos VMs.

## 1. Why Zvol?
We cannot pass a "Dataset" (directory) directly to a VM efficiently for database use.
Instead, we create a block device (**Zvol**) on ZFS. To the VM, this looks like a raw physical disk (e.g., `/dev/vdb`).

## 2. Proxmox Instructions (For each Node)
Repeat this for `pve` (CP1), `pve2` (CP2), and `pve3` (CP3).

1.  **Login to Proxmox Shell** (SSH).
2.  **Create Zvol**: Allocates 100GB on the `rpool` (or your NVMe pool).
    ```bash
    # Replace 'rpool' with your actual ZFS pool name (e.g., 'local-zfs' or 'nvme')
    zfs create -V 100G rpool/data/vm-10X-postgres-disk
    ```
    *Note: Adjust `vm-10X` to match the VM ID (e.g., `vm-101`, `vm-102`).*

3.  **Attach to VM**:
    ```bash
    # Example for VM 101 on 'local-zfs' storage
    qm set 101 --scsi1 local-zfs:vm-101-postgres-disk
    ```
    *Or via GUI*: VM -> Hardware -> Add -> Hard Disk -> Storage: (Your ZFS) -> Disk Image: (The Zvol you created).

4.  **Verification**:
    The disk should appear as `/dev/sdb` (or `/dev/vdb`) inside Talos.

## 3. Talos Configuration
Once attached, we need to tell Talos to use this disk for our `nvme-hot` storage class (Local Path Provisioner).
We likely already configured this in Phase 4, but verify that `/var/mnt/hot` is mounted to this new disk.

## 4. Accessing the Database (PSQL Console)

To verify the cluster or manage users manually, you can access the `psql` shell on the primary instance.

**Find the Primary Pod:**
```bash
kubectl get cluster -n cnpg-system
# Check the "PRIMARY" column
```

**Connect to Console (Example for `postgres-main-1`):**
```bash
kubectl exec -ti -n cnpg-system postgres-main-1 -- psql -U app app
```
*Password is usually not required for local socket connection, or check the secret `postgres-main-app`.*

**Basic Commands:**
```sql
\l        -- List databases
\dt       -- List tables
\du       -- List users
\conninfo -- Connection info
```

## 5. Migration Guides
- [Prowlarr (SQLite -> Postgres)](MIGRATION_GUIDE_PROWLARR.md)

## 6. External Access (DBeaver / LAN)
The database is exposed to the LAN via MetalLB on a dedicated IP.

**Connection Details:**
*   **Host/IP**: `10.10.20.57`
*   **Port**: `5432`
*   **Service Name**: `postgres-main-external` (Namespace: `cnpg-system`)

**DBeaver Setup:**
1.  **Database**: `radarr` (or `lidarr`, `postgres`)
2.  **Username**: `radarr`
3.  **Password**: `radarr`
4.  **SSL**: `Factory` or `Disable` (if connection fails)

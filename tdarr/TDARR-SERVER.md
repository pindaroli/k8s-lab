# Tdarr Architecture & Storage Strategy

## Overview
This setup uses a **Mixed Architecture** to combine the centralized management of Kubernetes with the high-performance hardware encoding of a dedicated Mac Studio.

- **Tdarr Server**: Running in Kubernetes (`tdarr` namespace). Handles the UI, database, and job coordination.
- **Tdarr Node**: Running natively on macOS (Mac Studio). Handles the heavy lifting (transcoding) using M2/M3 hardware encoders.

## Storage Configuration

### 1. Media Library (Source/Output)
- **TrueNAS Location**: `/mnt/oliraid/arrdata/media` (Mechanical RAID)
- **Server Path**: `/media` (Mounted via NFS)
- **Node Path**: `/Volumes/arrdata/media` (Mounted via SMB/NFS)
- **Rationale**: Mechanical HDDs are sufficient for sequential read/write of media files.

### 2. Transcode Cache (High-Performance IO)
- **Location**: Mac Studio Internal SSD (NVMe)
- **Server Path**: `/temp` (Ephemeral `emptyDir` on K8s for validation)
- **Node Path**: `/Users/olindo/Library/Caches/Tdarr`
- **Rationale**: Transcoding creates massive temporary IO. Using the internal NVMe SSD of the Mac Studio avoids network bottlenecks and maximizes performance.

## Path Translation Strategy
To ensure the Server and Node can talk to each other, the following translations are configured on the Mac Studio Node:

| Server Path | Node Path |
|-------------|-----------|
| `/media`    | `/Volumes/arrdata/media` |
| `/temp`     | `/Users/olindo/Library/Caches/Tdarr` |

## Maintenance
- **Cache Cleaning**: The cache folder on the Mac Studio should be monitored. It is located in the standard macOS Cache directory.
- **Node parità**: Ensure both Server and Node use version `2.70.01` to maintain compatibility.

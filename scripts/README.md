# Utility Scripts

This directory contains Python and Shell scripts for complex validation and integration tasks that are better suited for code than declarative YAML.

## Core Scripts (Keep)

| Script | Type | Description |
|---|---|---|
| **`ansible/playbooks/scripts/validate_rete_dns.py`** | Python | **Core Logic**. Parses `rete.json` to generate the authoritative list of DNS records for Ansible. Also performs validation (duplicate checks). |
| **`sync_storage.py`** | Python | **Integration**. Connects to TrueNAS via SSH, fetches `/etc/exports`, and syncs them to `storage.json` to keep the cluster storage config up to date. |
| **`fetch_exports.sh`** | Bash | **Helper**. Expect wrapper used by `sync_storage.py` to handle SSH password input (legacy) for fetching exports. |

## Archived
One-off fix scripts are moved to `_OLD_ARCHIVE/`.

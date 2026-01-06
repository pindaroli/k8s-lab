# Ansible Playbooks

This directory contains automation playbooks for managing DNS and other infrastructure components.

## Prerequisites

### Secrets & Vault
The sensitive variables (API keys, etc.) are stored in `../vars/secrets.yml` which is encrypted with Ansible Vault.

**The Vault Password File is located at:**
`/Users/olindo/.vault_pass.txt`

## Playbooks

### 1. OPNsense DNS Sync
Syncs DNS records from `rete.json` to the OPNsense Unbound DNS (Host Overrides).

**Usage:**
```bash
ansible-playbook opnsense_sync_dns.yml --vault-password-file /Users/olindo/.vault_pass.txt
```

### 2. Cloudflare DNS Sync
Syncs "External" aliases (e.g. `*.pindaroli.org`) to Cloudflare DNS.
*Requires `cloudflare_api_token` in secrets.yml.*

**Usage:**
```bash
ansible-playbook cloudflare_sync.yml --vault-password-file /Users/olindo/.vault_pass.txt
```

### 3. DHCP Reservations
Syncs static IP mappings to OPNsense DHCP.

**Usage:**
```bash
ansible-playbook dhcp_reservations.yml --vault-password-file /Users/olindo/.vault_pass.txt
```

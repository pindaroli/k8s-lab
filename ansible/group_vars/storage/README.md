# TrueNAS API Vault Setup

## Encrypting the Vault File

The `vault.yml` file contains sensitive TrueNAS API credentials and should be encrypted:

```bash
cd /Users/olindo/prj/k8s-lab/ansible
ansible-vault encrypt group_vars/storage/vault.yml
```

You'll be prompted to create a vault password. Remember this password!

## Using the Encrypted Vault

### Running Playbooks with Vault

When running playbooks that use the TrueNAS API, you need to provide the vault password:

```bash
# Restart NFS service on TrueNAS
ansible-playbook playbooks/restart-nfs-truenas-api.yml --ask-vault-pass
```

### Editing the Vault

To edit the encrypted vault file:

```bash
ansible-vault edit group_vars/storage/vault.yml
```

### Viewing the Vault

To view the decrypted contents without editing:

```bash
ansible-vault view group_vars/storage/vault.yml
```

### Decrypting the Vault

To decrypt the file permanently (not recommended):

```bash
ansible-vault decrypt group_vars/storage/vault.yml
```

## Vault Password File (Optional)

For automation, you can store the vault password in a file:

```bash
echo 'your-vault-password' > ~/.ansible_vault_pass
chmod 600 ~/.ansible_vault_pass
```

Then use it in playbooks:

```bash
ansible-playbook playbooks/restart-nfs-truenas-api.yml --vault-password-file ~/.ansible_vault_pass
```

## Current Vault Variables

- `vault_truenas_api_key`: TrueNAS SCALE REST API authentication key

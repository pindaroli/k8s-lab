# Managing Ansible Secrets and Sandbox Constraints

This document outlines the architectural approach for running Ansible within a restricted **macOS / AI Agent Sandbox** environment. It details why we use a localized `.ansible/` directory and how to securely manage secrets without triggering `[Errno 1] Operation not permitted` (EPERM).

## 1. The Core Problem: Sandbox Capability Denial
When an AI agent (like Antigravity) executes shell commands on macOS, it is confined by a **Seatbelt Sandbox** profile.
- **The Restriction**: Subprocesses are generally forbidden from performing `stat64` (metadata checks) or `read` operations on files outside the explicitly permitted project workspace (e.g., `~/.vault_pass.txt`).
- **The Result**: Even with correct POSIX permissions (`chmod 600`), Ansible fails with `EPERM` because the kernel intercepts the system call before it can verify the file exists.

---

## 2. Methodology: In-Boundary Provisioning
To resolve this, we implement a **"Safe Zone"** strategy where all operational dependencies are localized within the project root.

### A. The `.ansible/` Directory
We have established a project-specific `.ansible/` folder:
- **Location**: `PROJECT_ROOT/.ansible/`
- **Purpose**: A local repository for vault passwords, temporary execution streams, and Ansible-specific ephemeral data.
- **Why it works**: The sandbox profile typically grants the agent **full read/write and metadata capabilities** for files *inside* the project folder. Moving credentials here satisfies the kernel's proximity check.

### B. Localizing the Vault Password
Instead of referencing `~/.vault_pass.txt`, we copy it to the local workspace:
```bash
# User action to initialize the safe zone
mkdir -p .ansible && cp ~/.vault_pass.txt .ansible/vault_pass.txt && chmod 600 .ansible/vault_pass.txt
```
The AI agent then executes commands using:
`--vault-password-file .ansible/vault_pass.txt`

---

## 3. Security and Git Integrity
Because the `.ansible/` folder now contains sensitive credentials, it **MUST** be aggressively ignored by version control.

### `.gitignore` configuration
We have ensured the following is present in the project's `.gitignore`:
```markdown
# Ansible Security & Sandbox Workarounds
.ansible/
.ansible-local-tmp/
ansible.cfg
```
> [!IMPORTANT]
> **NEVER commit the `.ansible/` folder.** It is intended solely for local automation and sandbox-bypassing within this specific machine's environment.

---

## 4. Redirecting Temporary Files
Ansible natively tries to use `~/.ansible/tmp`. This is a guaranteed `EPERM` trigger in many sandboxed environments.

### The `ansible.cfg` Override
We have created an **`ansible.cfg`** in the project root to permanently redirect these operations to our writable safe zone:
```ini
[defaults]
local_tmp = ./.ansible/tmp
```

### The `ANSIBLE_LOCAL_TEMP` Backup
For one-off runs where the `.cfg` might be ignored by the loader, we use the environment variable override:
```bash
ANSIBLE_LOCAL_TEMP=/tmp/ansible ansible-playbook ...
```

---

## 5. Summary Flow for New Sessions
If you reset your environment or clear your project, follow this 3-step sequence to restore automation capability:
1.  **Ensure `.ansible/` exists** in the root.
2.  **Copy your vault pass** into `.ansible/vault_pass.txt`.
3.  **Run the master sync script**:
    ```bash
    ansible-playbook ansible/playbooks/opnsense_sync_dns.yml --vault-password-file .ansible/vault_pass.txt
    ```

This approach maintains the maximum security boundary provided by the macOS sandbox while granting the necessary friction-free access for infrastructure automation.

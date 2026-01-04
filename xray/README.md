# Xray Proxy Configuration

## Architecture
This directory contains the configuration and secrets for the Xray Proxy service, used for OCI (Oracle Cloud Infrastructure) tunneling/proxying.

## Directory Structure
- **`xray_secrets.yml`**: **[GITIGNORED]** Contains the sensitive credentials (UUID, Keys, ShortIds).
  - *Source of Truth*: This file is the local backup of credentials.
  - *Format*: YAML (Ansible-vault ready).

## Kubernetes Secret
The sensitive data is deployed to the cluster as a Kubernetes Secret named `xray-secrets` in the `xray` namespace.

**Manual creation command (reference):**
```bash
kubectl create secret generic xray-secrets -n xray \
  --from-literal=uuid="<value>" \
  --from-literal=private-key="<value>" \
  --from-literal=public-key="<value>" \
  --from-literal=short-id="<value>"
```

## Workload Deployment
*To be implemented.*
Currently, this directory manages the **Secrets Phase**. The actual `Deployment` and `Service` manifests for Xray will be added in subsequent phases.

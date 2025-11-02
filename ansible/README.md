# Ansible Configuration for k8s-lab Infrastructure

This directory contains Ansible configurations for managing the entire k8s-lab infrastructure, including Kubernetes cluster nodes, Proxmox hypervisor, TrueNAS storage, and OPNsense firewall.

## Directory Structure

```
ansible/
├── ansible.cfg              # Ansible configuration file
├── inventory.yml            # Inventory file with all hosts
├── group_vars/             # Group-specific variables
│   ├── all.yml             # Variables for all hosts
│   ├── kubernetes.yml      # Kubernetes-specific variables
│   └── infrastructure.yml  # Infrastructure hosts variables
├── host_vars/              # Host-specific variables (empty initially)
├── playbooks/              # Ansible playbooks
│   ├── ping-all.yml        # Test connectivity to all hosts
│   ├── cluster-info.yml    # Gather cluster information
│   ├── cluster-startup.yml # Start the Kubernetes cluster (auto-resumes descheduler)
│   ├── cluster-shutdown.yml # Shutdown the Kubernetes cluster (auto-suspends descheduler)
│   ├── install-descheduler.yml # Install Kubernetes descheduler for pod rebalancing
│   ├── deploy-n8n.yml      # Deploy n8n workflow automation
│   ├── update-n8n.yml      # Update n8n configuration
│   └── update-system.yml   # Update all systems
└── roles/                  # Custom Ansible roles (empty initially)
```

## Inventory Overview

The inventory is organized into logical groups:

### Kubernetes Cluster
- **k8s_control**: k8s-control (192.168.1.11) - Control plane node
- **k8s_workers**: k8s-runner-1 - Worker node

### Infrastructure
- **proxmox**: 192.168.1.10 - Proxmox VE hypervisor
- **truenas**: 192.168.1.250 - TrueNAS storage server
- **opnsense**: 192.168.1.1 - OPNsense firewall/router

## Quick Start

### 1. Test Connectivity

```bash
cd /Users/olindo/prj/k8s-lab/ansible
ansible-playbook playbooks/ping-all.yml
```

### 2. Gather Cluster Information

```bash
ansible-playbook playbooks/cluster-info.yml
```

### 3. Start the Cluster

```bash
ansible-playbook playbooks/cluster-startup.yml
```

### 4. Shutdown the Cluster

```bash
ansible-playbook playbooks/cluster-shutdown.yml
```

### 5. Install Descheduler for Automatic Pod Rebalancing

```bash
ansible-playbook playbooks/install-descheduler.yml
```

This playbook will:
- Install the Kubernetes Descheduler via Helm
- Apply Pod Disruption Budgets to protect critical services
- Configure automatic pod rebalancing based on memory usage (65%/80% thresholds)
- Verify installation and display monitoring commands
- Integrate with cluster-startup.yml and cluster-shutdown.yml for automatic suspend/resume

**What is Descheduler?**
The descheduler automatically moves pods between nodes to maintain balanced resource usage. Unlike the scheduler (which only runs when pods are created), the descheduler runs every 15 minutes and evicts poorly-placed pods so they can be rescheduled on better nodes.

**Why it's needed:**
Kubernetes scheduler only acts during pod creation. If a node becomes overloaded later, pods stay there forever. The descheduler fixes this by continuously rebalancing the cluster.

### 6. Update All Systems

```bash
ansible-playbook playbooks/update-system.yml
```

### 7. Deploy n8n Workflow Automation

```bash
ansible-playbook playbooks/deploy-n8n.yml
```

This playbook will:
- Add the 8gears Helm repository
- Create the PersistentVolumeClaim with csi-nfs-stripe-arr-conf storage class
- Install/upgrade n8n using Helm with custom values
- Apply the Traefik IngressRoute with OAuth2 authentication
- Verify deployment status
- Access at: https://n8n.pindaroli.org

### 8. Update n8n Configuration

```bash
ansible-playbook playbooks/update-n8n.yml
```

This playbook will:
- Copy updated configuration files from n8n/ directory
- Apply updated PersistentVolumeClaim
- Upgrade n8n Helm release with new values
- Apply updated IngressRoute
- Wait for pod to be ready and verify status
- Use this when you modify n8n-values.yaml, n8n-pvc.yaml, or n8n-ingress-route.yaml

## Common Ad-hoc Commands

### Check all hosts are reachable
```bash
ansible all -m ping
```

### Run a command on all Kubernetes nodes
```bash
ansible kubernetes -a "microk8s status"
```

### Check Proxmox VM status
```bash
ansible proxmox -a "qm list"
```

### Get disk usage on all hosts
```bash
ansible all -m shell -a "df -h"
```

### Check system uptime
```bash
ansible all -a "uptime"
```

## Inventory Groups

You can target specific groups with playbooks:

- `all` - All hosts in the inventory
- `kubernetes` - All Kubernetes nodes
- `k8s_control` - Only the control plane node
- `k8s_workers` - Only worker nodes
- `infrastructure` - All infrastructure hosts (Proxmox, TrueNAS, OPNsense)
- `hypervisors` - Proxmox only
- `storage` - TrueNAS only
- `network` - OPNsense only

## Variables

### Global Variables (group_vars/all.yml)
- Network configuration (gateway, subnet, DNS)
- Admin user information
- Common packages
- Timezone and NTP servers

### Kubernetes Variables (group_vars/kubernetes.yml)
- MicroK8s configuration
- MetalLB IP pool
- Storage (NFS CSI)
- Ingress controller (Traefik)
- Certificate manager
- OAuth2 Proxy
- Application namespaces

### Infrastructure Variables (group_vars/infrastructure.yml)
- Proxmox VM definitions
- TrueNAS NFS exports
- OPNsense service configuration
- Backup settings

## SSH Configuration

The ansible.cfg is configured to:
- Disable host key checking (lab environment)
- Use SSH pipelining for better performance
- Enable persistent SSH connections
- Log all operations to ansible.log

## Requirements

- Ansible 2.19.3 or later
- SSH access to all hosts (root user)
- Python 3 installed on all target hosts

## Security Notes

⚠️ **Important**: This configuration is designed for a lab environment and includes:
- Disabled host key checking
- Root SSH access
- No password prompts for privilege escalation

For production use, consider:
- Enabling host key verification
- Using non-root users with sudo
- Implementing Ansible Vault for secrets
- Restricting SSH access with key-based authentication only

## Network Information

- **Network**: 192.168.1.0/24
- **Gateway**: 192.168.1.1 (OPNsense)
- **DNS**: 192.168.1.1
- **MetalLB Pool**: 192.168.1.3-192.168.1.13
- **Local Domain**: .local
- **External Domain**: pindaroli.org

## Next Steps

1. Test connectivity with `ansible-playbook playbooks/ping-all.yml`
2. Review and customize variables in `group_vars/` as needed
3. **Install descheduler** with `ansible-playbook playbooks/install-descheduler.yml` for automatic pod rebalancing
4. Create custom playbooks in `playbooks/` directory
5. Develop custom roles in `roles/` directory for complex configurations

## Cluster Lifecycle Management

The cluster startup and shutdown playbooks now integrate with the descheduler:

**Startup sequence:**
1. Start VMs (k8s-control → k8s-runner-1)
2. Wait for nodes to be ready
3. Uncordon worker nodes
4. **Automatically resume descheduler** if it was suspended
5. Display pod distribution

**Shutdown sequence:**
1. **Automatically suspend descheduler** to prevent interference
2. Drain worker nodes
3. Shutdown VMs (k8s-runner-1 → k8s-control)

This ensures the descheduler doesn't interfere with controlled pod migrations during shutdown.

## Useful Resources

- [Ansible Documentation](https://docs.ansible.com/)
- [MicroK8s Documentation](https://microk8s.io/docs)
- [Proxmox API](https://pve.proxmox.com/wiki/Proxmox_VE_API)

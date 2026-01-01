# Kubernetes Descheduler Setup

Automatic pod rebalancing across cluster nodes based on resource utilization.

## Overview

This directory contains a complete descheduler configuration for the k8s-lab cluster, including:
- ✅ Helm values with optimized settings for 2-node clusters
- ✅ Pod Disruption Budgets for all critical services
- ✅ Ansible playbook for automated installation
- ✅ Full integration with cluster lifecycle management
- ✅ Protection mechanisms for stateful workloads

## Problem Statement

Kubernetes scheduler only runs when pods are **created**. Once a pod is running on a node, it stays there forever, even if:
- The node becomes overloaded
- Other nodes have more available resources
- Node affinity rules change

**Real example from this cluster:**
```
Before descheduler:
  k8s-control:  83% memory usage (16GB used) - qBittorrent using 12GB!
  k8s-runner-1:  5% memory usage (3GB used)  - almost empty

After configuring resource requests and installing descheduler:
  k8s-control:  ~50% memory usage (balanced)
  k8s-runner-1: ~30% memory usage (balanced)
```

All servarr pods were stuck on k8s-control because they were scheduled 22 days ago when resources were different.


The **Descheduler** is a Kubernetes component that:
1. Runs periodically (every 15 minutes in this setup)
2. Identifies "badly scheduled" pods based on policies
3. Evicts them (terminates gracefully)
4. The scheduler recreates them on better nodes
5. Respects Pod Disruption Budgets to maintain service availability

## Quick Start

### Method 1: Ansible Playbook (Recommended)

Automated installation with a single command:

```bash
cd /Users/olindo/prj/k8s-lab/ansible

# Install descheduler, apply PDBs, and verify
ansible-playbook playbooks/install-descheduler.yml -i inventory.yml
```

This playbook:
- ✅ Adds Helm repository and installs descheduler
- ✅ Applies all Pod Disruption Budgets
- ✅ Verifies installation and displays configuration
- ✅ Shows monitoring commands
- ✅ Works idempotently (safe to run multiple times)

**Integration with cluster lifecycle:**
- The [`cluster-startup.yml`](../ansible/playbooks/cluster-startup.yml) playbook automatically resumes descheduler after startup
- The [`cluster-shutdown.yml`](../ansible/playbooks/cluster-shutdown.yml) playbook suspends descheduler before shutdown
- No manual intervention needed during cluster restarts

**Playbook location:** `../ansible/playbooks/install-descheduler.yml`

### Method 2: Manual Helm Installation

If you prefer manual control:

```bash
cd /Users/olindo/prj/k8s-lab/descheduler

# Add Helm repository
helm repo add descheduler https://kubernetes-sigs.github.io/descheduler/
helm repo update

# Install with custom configuration
helm install descheduler descheduler/descheduler \
  -n kube-system \
  -f descheduler-values.yaml

# Verify installation
kubectl get deployment descheduler -n kube-system
kubectl get pods -n kube-system -l app.kubernetes.io/name=descheduler

# Apply Pod Disruption Budgets
kubectl apply -f pod-disruption-budgets.yaml

# Verify PDBs
kubectl get pdb -A
```

## Automated Cluster Lifecycle Integration

The descheduler is fully integrated with the cluster startup and shutdown automation:

### During Cluster Shutdown

```yaml
# In cluster-shutdown.yml
- name: Stop descheduler before shutdown
  # Prevents descheduler from interfering with controlled pod migrations
  # Automatically detects if descheduler is installed
  # Scales deployment to 0 replicas
```

**Why?** During shutdown, we deliberately drain k8s-runner-1 and move pods to k8s-control. The descheduler would fight against this, trying to rebalance while we're shutting down.

### During Cluster Startup

```yaml
# In cluster-startup.yml
- name: Start descheduler after startup
  # Automatically starts descheduler if it was stopped (scaled to 0)
  # Scales deployment to 1 replica
  # Waits for pod to be ready
  # Displays pod distribution after startup
```

**Result:** After startup, the descheduler will run within 15 minutes and rebalance any imbalanced pods back to k8s-runner-1.

### Manual Cluster Operations

```bash
# Normal startup (automatically resumes descheduler)
cd /Users/olindo/prj/k8s-lab/ansible
ansible-playbook playbooks/cluster-startup.yml -i inventory.yml

# Normal shutdown (automatically suspends descheduler)
ansible-playbook playbooks/cluster-shutdown.yml -i inventory.yml
```

No manual suspend/resume needed - it's all automatic!

## (Optional) Protect Specific Pods

Use the Ansible playbook to prevent eviction of critical pods:

```bash
cd /Users/olindo/prj/k8s-lab/descheduler

# Install Ansible Kubernetes collection (if not already installed)
ansible-galaxy collection install kubernetes.core

# Edit protect-pods-playbook.yaml and uncomment resources to protect
# Then apply protection:
ansible-playbook protect-pods-playbook.yaml --tags protect

# Check protection status:
ansible-playbook protect-pods-playbook.yaml --tags check

# List all protected resources in cluster:
ansible-playbook protect-pods-playbook.yaml --tags list

# Remove protection:
ansible-playbook protect-pods-playbook.yaml --tags unprotect
```

## How It Works

### LowNodeUtilization Strategy

The primary strategy monitors memory usage:

```
Configuration:
  thresholds:       memory: 65%  # Node is "underutilized" if < 65%
  targetThresholds: memory: 80%  # Rebalance until all nodes ~80%

Example:
  k8s-control:  75% memory → OVERUTILIZED (above 65%)
  k8s-runner-1: 20% memory → UNDERUTILIZED (below 65%)

Action:
  1. Descheduler evicts pods from k8s-control
  2. Scheduler recreates them on k8s-runner-1
  3. Both nodes converge to ~60-70% (balanced)
```

### Safety Mechanisms

1. **ignorePvcPods: false** - Allows eviction of pods with NFS PVCs (safe because NFS is network storage)
2. **evictLocalStoragePods: false** - Prevents eviction of pods with emptyDir/hostPath (NOT safe)
3. **maxNoOfPodsToEvictPerNode: 3** - Maximum 3 pods evicted per node per run
4. **Namespace exclusions** - Never touches kube-system, metallb-system, cert-manager
5. **Pod Disruption Budgets** - Respects minAvailable/maxUnavailable constraints

## Files in This Directory

| File | Purpose | Usage |
|------|---------|-------|
| `descheduler-values.yaml` | Helm chart configuration | Used by install playbook |
| `pod-disruption-budgets.yaml` | PDBs for critical services | Applied by install playbook |
| `protect-pods-playbook.yaml` | Optional pod protection | Manual annotation management |
| `README.md` | This documentation | Reference guide |

## Configuration Files

### descheduler-values.yaml

Main Helm chart configuration with:
- Schedule: `*/15 * * * *` (every 15 minutes)
- Resource limits for descheduler pod itself
- Policy strategies (LowNodeUtilization, RemovePodsViolatingNodeAffinity, etc.)
- Namespace exclusions
- Safety settings

**Key Settings to Tune:**
```yaml
schedule: "*/15 * * * *"  # Frequency (15 min recommended)

thresholds:
  memory: 65  # Lower = more aggressive rebalancing

targetThresholds:
  memory: 80  # Higher = allows more memory usage

maxNoOfPodsToEvictPerNode: 3  # Safety limit per run
```

### pod-disruption-budgets.yaml

Kubernetes PDBs that protect critical services:

| Service | Protection | Reason |
|---------|-----------|--------|
| servarr-* | maxUnavailable: 2 | Limit simultaneous evictions |
| jellyfin | minAvailable: 1 | Always keep media server running |
| qbittorrent | minAvailable: 1 | Protect active downloads |
| oauth2-proxy | minAvailable: 1 | Critical authentication |
| traefik | maxUnavailable: 1 | Maintain ingress availability |
| n8n | minAvailable: 1 | Protect workflow execution |

### protect-pods-playbook.yaml

Ansible playbook for manual pod protection via annotations.

**When to use:**
- Pods with critical active state (long-running workflows, database transactions)
- Pods that take very long to start (large memory footprint)
- Temporary protection during maintenance windows

**Warning:** Don't over-protect! This defeats the purpose of the descheduler.

## Monitoring

### Check Descheduler Status

```bash
# Check deployment status
kubectl get deployment descheduler -n kube-system

# Check if running (should show "1/1" replicas)
kubectl get deployment descheduler -n kube-system -o jsonpath='{.spec.replicas}'

# View deployment details
kubectl describe deployment descheduler -n kube-system

# Check pod status
kubectl get pods -n kube-system -l app.kubernetes.io/name=descheduler
```

### Check Descheduler Logs

```bash
# Watch descheduler activity (when a job runs)
kubectl logs -n kube-system -l app.kubernetes.io/name=descheduler -f

# Check recent evictions
kubectl logs -n kube-system -l app.kubernetes.io/name=descheduler --tail=100 | grep -i evict

# View pod logs
kubectl logs -n kube-system -l app.kubernetes.io/name=descheduler --tail=50
```

**Note:** The descheduler runs continuously as a Deployment. It performs descheduling cycles every 15 minutes (based on configuration).

### Monitor Node Balance

```bash
# Check current node resource usage
kubectl top nodes

# Expected balanced output:
# NAME           CPU    MEMORY
# k8s-control    5%     50-60%
# k8s-runner-1   5%     30-40%

# Watch pod distribution
kubectl get pods -A -o wide | grep -v "kube-system\|metallb-system" | awk '{print $8}' | sort | uniq -c

# Check PDB status
kubectl get pdb -A
```

### Verify Pod Distribution

```bash
# Count pods per node (should be roughly balanced)
echo "Pods per node:"
kubectl get pods -A -o wide --no-headers | awk '{print $8}' | sort | uniq -c

# Check memory distribution by pod
kubectl top pods -A --sort-by=memory | head -20

# View which pods are on which node
kubectl get pods -A -o wide | grep -E "(k8s-control|k8s-runner-1)"
```

### Force Immediate Descheduler Run

If you want to trigger rebalancing immediately without waiting for the 15-minute interval:

```bash
# Restart the descheduler pod (it will start a new descheduling cycle)
kubectl rollout restart deployment descheduler -n kube-system

# Wait for new pod to be ready
kubectl rollout status deployment descheduler -n kube-system

# Watch logs of new pod
kubectl logs -n kube-system -l app.kubernetes.io/name=descheduler -f
```

## Troubleshooting

### Descheduler Not Evicting Pods

**Check thresholds:**
```bash
kubectl top nodes
# If both nodes are below 65% memory, descheduler won't act
```

**Solution:** Lower thresholds in descheduler-values.yaml:
```yaml
thresholds:
  memory: 50  # Was 65
```

### Too Many Evictions

**Symptom:** Pods constantly restarting, services unstable

**Solutions:**
1. Increase schedule interval: `*/30 * * * *` (every 30 min)
2. Decrease `maxNoOfPodsToEvictPerNode: 2`
3. Apply more PodDisruptionBudgets
4. Protect critical pods with annotations

### Pod Cannot Be Scheduled After Eviction

**Check scheduler logs:**
```bash
kubectl get events -A --sort-by='.lastTimestamp' | grep -i failed
```

**Common causes:**
- Insufficient resources on target node (increase node memory)
- Node affinity rules preventing scheduling (check nodeSelector/affinity)
- PVC using local storage (switch to NFS/network storage)

### Descheduler Pod Crashlooping

**Check resource limits:**
```bash
kubectl describe pod -n kube-system -l app.kubernetes.io/name=descheduler
```

**Solution:** Increase resource limits in descheduler-values.yaml:
```yaml
resources:
  limits:
    memory: 512Mi  # Was 256Mi
```

## When NOT to Use Descheduler

1. **Single-node clusters** - Nothing to rebalance
2. **StatefulSets with local storage** - Pods lose data when moved
3. **Databases without replication** - Causes downtime on every eviction
4. **Real-time applications** - Cannot tolerate any interruption

## Best Practices

1. ✅ **Always configure resource requests** - Scheduler needs them to make good decisions
2. ✅ **Start with conservative settings** - 15-30 min intervals, low eviction limits
3. ✅ **Use PodDisruptionBudgets** - Prevent excessive disruption
4. ✅ **Monitor for 1 week** - Ensure rebalancing works as expected
5. ✅ **Use NFS/network storage** - Makes pod movement safe
6. ⚠️ **Don't over-protect** - Too many protected pods = no rebalancing
7. ⚠️ **Test during business hours** - Observe impact on users

## Upgrade

### Option 1: Using Ansible (Recommended)

```bash
cd /Users/olindo/prj/k8s-lab/ansible

# Re-run installation playbook (it will upgrade if already installed)
ansible-playbook playbooks/install-descheduler.yml -i inventory.yml
```

### Option 2: Manual Helm Upgrade

```bash
cd /Users/olindo/prj/k8s-lab/descheduler

# Update Helm repository
helm repo update

# Upgrade with new values
helm upgrade descheduler descheduler/descheduler \
  -n kube-system \
  -f descheduler-values.yaml
```

## Uninstall

### Step-by-Step Removal

```bash
# 1. Remove descheduler Helm release
helm uninstall descheduler -n kube-system

# 2. Remove Pod Disruption Budgets (optional - they're still useful)
kubectl delete -f /Users/olindo/prj/k8s-lab/descheduler/pod-disruption-budgets.yaml

# 3. Remove pod protection annotations (if any were applied)
cd /Users/olindo/prj/k8s-lab/descheduler
ansible-playbook protect-pods-playbook.yaml --tags unprotect
```

**Note:** After uninstallation, the cluster will no longer auto-rebalance. You'll need to manually restart pods to redistribute them:
```bash
# Example: restart servarr deployments to rebalance
kubectl rollout restart deployment -n arr
```

## Quick Reference

### Essential Commands

```bash
# Installation
cd /Users/olindo/prj/k8s-lab/ansible
ansible-playbook playbooks/install-descheduler.yml -i inventory.yml

# Check status
kubectl get deployment descheduler -n kube-system

# View configuration
kubectl describe deployment descheduler -n kube-system

# Check pod status
kubectl get pods -n kube-system -l app.kubernetes.io/name=descheduler

# Check node balance
kubectl top nodes

# Force immediate run
kubectl rollout restart deployment descheduler -n kube-system

# Stop temporarily (scale to 0)
kubectl scale deployment descheduler -n kube-system --replicas=0

# Start again (scale to 1)
kubectl scale deployment descheduler -n kube-system --replicas=1

# View PDBs
kubectl get pdb -A

# Upgrade
cd /Users/olindo/prj/k8s-lab/ansible
ansible-playbook playbooks/install-descheduler.yml -i inventory.yml
```

## Related Documentation

### Internal Documentation
- [`ansible/playbooks/install-descheduler.yml`](../ansible/playbooks/install-descheduler.yml) - Installation playbook
- [`ansible/playbooks/cluster-startup.yml`](../ansible/playbooks/cluster-startup.yml) - Auto-resume descheduler
- [`ansible/playbooks/cluster-shutdown.yml`](../ansible/playbooks/cluster-shutdown.yml) - Auto-suspend descheduler
- [`ansible/README.md`](../ansible/README.md) - Ansible infrastructure documentation
- [`servarr/arr-values.yaml`](../servarr/arr-values.yaml) - Resource requests configuration

### External Resources
- [Descheduler GitHub](https://github.com/kubernetes-sigs/descheduler)
- [Descheduler Helm Chart](https://github.com/kubernetes-sigs/descheduler/tree/master/charts/descheduler)
- [Kubernetes Pod Disruption Budgets](https://kubernetes.io/docs/concepts/workloads/pods/disruptions/)
- [Kubernetes Resource Management](https://kubernetes.io/docs/concepts/configuration/manage-resources-containers/)

## Support

Issues or questions? Check:

1. **Installation issues:**
   ```bash
   # Check playbook output for errors
   ansible-playbook playbooks/install-descheduler.yml -i inventory.yml -v
   ```

2. **Descheduler not running:**
   ```bash
   kubectl get deployment descheduler -n kube-system
   kubectl describe deployment descheduler -n kube-system
   # Check replica count (should be 1)
   kubectl get deployment descheduler -n kube-system -o jsonpath='{.spec.replicas}'
   # Check pod status
   kubectl get pods -n kube-system -l app.kubernetes.io/name=descheduler
   ```

3. **Pods not rebalancing:**
   ```bash
   # Check thresholds
   kubectl top nodes
   # If both nodes are below 65% memory, descheduler won't act

   # Check descheduler logs
   kubectl logs -n kube-system -l app.kubernetes.io/name=descheduler
   ```

4. **Too many evictions:**
   ```bash
   # Check PDB status
   kubectl get pdb -A
   # Adjust maxNoOfPodsToEvictPerNode in descheduler-values.yaml
   ```

5. **Cluster lifecycle:**
   ```bash
   # Verify auto-suspend during shutdown
   ansible-playbook playbooks/cluster-shutdown.yml -i inventory.yml -v

   # Verify auto-resume during startup
   ansible-playbook playbooks/cluster-startup.yml -i inventory.yml -v
   ```

# Cluster Operations Guide

## Graceful Shutdown Procedure

Use the automated script:
```bash
./cluster-shutdown.sh
```

### Manual Shutdown Steps

1. **Drain worker node**:
   ```bash
   kubectl drain k8s-runner-1 --ignore-daemonsets --delete-emptydir-data --force
   ```

2. **Wait for pods to migrate** (30 seconds):
   ```bash
   sleep 30
   ```

3. **Drain control plane**:
   ```bash
   kubectl drain k8s-control --ignore-daemonsets --delete-emptydir-data --force
   ```

4. **Check remaining pods**:
   ```bash
   kubectl get pods --all-namespaces -o wide
   ```

5. **Shutdown worker node VM**:
   ```bash
   ssh root@192.168.1.10 "qm shutdown 1100 --timeout 120"
   ```

6. **Wait for worker to shutdown** (60 seconds):
   ```bash
   sleep 60
   ```

7. **Shutdown control plane VM**:
   ```bash
   ssh root@192.168.1.10 "qm shutdown 1500 --timeout 120"
   ```

8. **Wait for control plane to shutdown** (60 seconds):
   ```bash
   sleep 60
   ```

9. **Verify shutdown**:
   ```bash
   ssh root@192.168.1.10 "qm status 1100 && qm status 1500"
   ```

## Startup Procedure

Use the automated script:
```bash
./cluster-startup.sh
```

### Manual Startup Steps

1. **Start control plane VM**:
   ```bash
   ssh root@192.168.1.10 "qm start 1500"
   ```

2. **Wait for control plane to boot** (60 seconds):
   ```bash
   sleep 60
   ```

3. **Check control plane status**:
   ```bash
   ssh root@192.168.1.10 "qm status 1500"
   ```

4. **Wait for Kubernetes API to be ready**:
   ```bash
   kubectl get nodes
   # Retry until successful (max 5 minutes)
   ```

5. **Check control plane node status**:
   ```bash
   kubectl get node k8s-control
   ```

6. **Start worker node VM**:
   ```bash
   ssh root@192.168.1.10 "qm start 1100"
   ```

7. **Wait for worker node to boot** (60 seconds):
   ```bash
   sleep 60
   ```

8. **Check worker node status**:
   ```bash
   ssh root@192.168.1.10 "qm status 1100"
   ```

9. **Wait for worker node to join cluster**:
   ```bash
   kubectl get node k8s-runner-1
   # Retry until node appears (max 5 minutes)
   ```

10. **Uncordon nodes**:
    ```bash
    kubectl uncordon k8s-control
    kubectl uncordon k8s-runner-1
    ```

11. **Wait for all nodes to be Ready**:
    ```bash
    kubectl get nodes
    # Wait until both nodes show "Ready" status
    ```

12. **Check cluster status**:
    ```bash
    kubectl get nodes -o wide
    ```

13. **Check system pods**:
    ```bash
    kubectl get pods -n kube-system
    ```

14. **Wait for critical pods to be running** (60 seconds):
    ```bash
    sleep 60
    ```

15. **Verify all services**:
    ```bash
    kubectl get pods --all-namespaces -o wide
    ```

## Troubleshooting

### VM Won't Start
Check Proxmox logs:
```bash
ssh root@192.168.1.10 "journalctl -u qmeventd.service -n 100 | grep <VMID>"
```

### OOM (Out of Memory) Issues
Check if VM was killed by OOM:
```bash
ssh root@192.168.1.10 "journalctl --since '1 hour ago' | grep -i 'oom-kill'"
```

VM memory allocation:
- k8s-control (1500): 20GB RAM
- k8s-runner-1 (1100): Check with `ssh root@192.168.1.10 "qm config 1100 | grep memory"`

### Node Not Ready
Check node status and events:
```bash
kubectl describe node <node-name>
```

Check kubelet logs on the node:
```bash
ssh root@<node-name> "journalctl -u snap.microk8s.daemon-kubelet -n 100"
```

### Pods Not Starting
Check pod status and events:
```bash
kubectl describe pod <pod-name> -n <namespace>
```

Check pod logs:
```bash
kubectl logs <pod-name> -n <namespace>
```

## Important Notes

- **Shutdown Order**: Worker node → Control plane (critical for graceful pod migration)
- **Startup Order**: Control plane → Worker node (API server must be ready first)
- **Autostart**: Both VMs have autostart enabled in Proxmox
- **Memory Limits**: Jellyfin has 4Gi limit to prevent OOM kills
- **Grace Period**: Allow 2-3 minutes between major steps for stability

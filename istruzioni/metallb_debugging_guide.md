# Understanding & Fixing MetalLB on Talos Linux
**A Field Report for Future Debugging**

## 1. The Symptom: "It's there, but I can't touch it."

You deployed a service, MetalLB gave it an IP (`10.10.20.56`), but you couldn't access it.
*   **ARP Worked**: Your Mac knew `10.10.20.56` belonged to `talos-cp-02`.
*   **Ping Failed**: "Destination Host Unreachable".

**What this means:**
The "physical" connection (Layer 2) was correct. The packet arrived at the Talos node. However, the node *rejected* it.

---

## 2. The Conflict: Talos, MetalLB & The Firewall

This is a classic conflict between how MetalLB assumes Linux works and how Talos (and modern Kubernetes proxies) actually work.

### The Players
1.  **MetalLB (Layer 2 Mode)**: Works by shouting "I have this IP!" (ARP). It expects the node receiving the traffic to just pass it to the Pod. It *does not* actually assign the IP to the network card (`eth0`).
2.  **Kube-Proxy (nftables mode)**: The default traffic router in newer Talos versions. It is strict. If a packet arrives for an IP that *isn't assigned to the interface*, it treats it as "martian" (invalid) traffic and drops it before checking if it belongs to a Service.

### The Crash
*   **Packet**: "Hey `eth0`, here is data for `10.10.20.56`."
*   **Node (eth0)**: "I don't have IP `10.10.20.56`. Drop it."
*   **Result**: Connectivity fails, even though ARP says the node is the destination.

---

## 3. How to Diagnose This (Your Future Checklist)

If you face this again, use these steps to pinpoint the failure.

### Step 1: Is it announcing? (Layer 2)
Check your local ARP table (on your Mac/PC).
```bash
arp -an | grep 10.10.20.56
```
*   **Empty**: MetalLB isn't running or configured (check pools/L2Advertisements).
*   **Present (e.g., at bc:24:11:...)**: Good! MetalLB is working. Note the MAC address.

### Step 2: Who is the Leader?
Find which node owns that MAC address.
```bash
kubectl get nodes -o wide
# Compare the MAC from Step 1 with your known hardware MACs.
```
*   *Verdict*: Let's say it's `talos-cp-02`.

### Step 3: Is the IP assigned? (The Smoking Gun)
Check the interface on that leader node.
```bash
# Debug pod to check node network
kubectl debug node/talos-cp-02 -it --image=busybox -- ip addr show eth0
```
*   **Scenario A**: You see `inet 10.10.20.56` listed. -> **Not this issue.** Check firewalls.
*   **Scenario B**: You **DO NOT** see the IP. -> **This is the issue.** The node receives traffic for an IP it doesn't "own".

---

## 4. The Solution: IPVS Mode

We fixed this by switching `kube-proxy` to **IPVS** mode.

**Why IPVS?**
IPVS (IP Virtual Server) is a high-performance load balancer built into Linux. Unlike `nftables`/`iptables`, IPVS intercepts traffic *before* the strict "is this my IP?" check happens.
It explicitly tells the kernel: "I know you don't own this IP, but I do. Give me the packet." (This is what `strictARP: true` enables).

### How we applied it (Talos)
We updated the Machine Configuration of all nodes:
```yaml
cluster:
  proxy:
    mode: ipvs
    extraArgs:
      strictARP: true
```

### Verification
Once applied:
*   Nodes reboot/reload.
*   MetalLB updates `strictARP` kernel settings.
*   The kernel stops dropping "foreign" packets.
*   Ping works!

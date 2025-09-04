# OPNsense UPnP Configuration for qBittorrent

## Steps to Configure UPnP

### 1. Apply LoadBalancer Service
First, apply the LoadBalancer service to expose qBittorrent:
```bash
kubectl apply -f qbittorrent-bittorrent-loadbalancer.yaml
```

This will assign IP `192.168.1.4` to qBittorrent's BitTorrent service with UPnP compatibility.

### 2. Enable UPnP in OPNsense

**Navigation:** Services → Universal Plug and Play

**Enable UPnP Service:**
- **Enable UPnP & NAT-PMP:** ✓ Checked
- **Allow UPnP Port Mapping:** ✓ Checked
- **Allow NAT-PMP Port Mapping:** ✓ Checked

**Interface Configuration:**
- **External Interface:** WAN
- **Internal Interfaces:** LAN (or your internal network interface)

**Advanced Settings:**
- **Default Deny:** ✓ Checked (for security)
- **Secure Mode:** ✓ Checked
- **Clean NAT Table:** ✓ Checked

### 3. Configure UPnP Access Control

**User entries for qBittorrent:**
```
# Allow qBittorrent LoadBalancer IP to use UPnP
allow 30661-30661 192.168.1.4/32 30661-30661
```

**Add ACL Entry:**
- **Action:** allow
- **External Port Range:** 30661-30661
- **Internal Address:** 192.168.1.4/32
- **Internal Port Range:** 30661-30661
- **Description:** qBittorrent BitTorrent UPnP

### 4. Configure qBittorrent for UPnP

In qBittorrent settings (via web UI at qbittorrent.pindaroli.org):

**Connection Settings:**
- **Use UPnP/NAT-PMP port forwarding from my router:** ✓ Enabled
- **Port used for incoming connections:** 30661
- **Use different port on each startup:** ✗ Disabled (keep consistent)

### 5. Verify Configuration

Check LoadBalancer service:
```bash
kubectl get svc qbittorrent-bittorrent-lb -n arr
```

Check UPnP status in OPNsense:
- **Navigation:** Services → Universal Plug and Play → Status
- Look for active port mappings for 192.168.1.4:30661

Test from qBittorrent:
- Check connection status in qBittorrent web UI
- Should show "Reachable" or "OK" status

## Notes
- UPnP automatically creates port forwards when qBittorrent requests them
- The `externalTrafficPolicy: Local` ensures source IP preservation for UPnP
- qBittorrent will automatically map port 30661 through your OPNsense router
- No manual port forwarding rules needed - UPnP handles this automatically
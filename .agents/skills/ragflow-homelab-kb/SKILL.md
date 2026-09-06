---
name: ragflow-homelab-kb
type: skill
description: "Retrieve official documentation, configuration procedures, parameter guides, and hardware manuals from RAGFlow datasets: opnsense (OPNsense 26.1), truenas (TrueNAS SCALE 25.10), and k8s-lab (physical hardware)."
when_to_use: "When the user asks for OPNsense firewall/networking configurations, TrueNAS storage/ZFS procedures, physical hardware datasheets/pinouts, or official vendor guidelines."
status: active
tags:
  - ragflow
  - opnsense
  - truenas
  - hardware
  - knowledge-base
---

# RAGFlow Homelab Knowledge Base (`ragflow-homelab-kb`)

## Overview
This skill provides automated, intelligent retrieval across all official technical documentation and hardware manuals indexed in **RAGFlow** (`https://ragflow-internal.pindaroli.org`). It acts as the primary knowledge authority for the homelab's core operating systems (OPNsense, TrueNAS SCALE) and physical infrastructure.

---

## 🗺️ Dataset Routing Matrix

Always map the user's intent to the appropriate RAGFlow dataset (or combination of datasets):

| Domain | Scope & Key Topics | Target Dataset (`dataset_names`) |
| :--- | :--- | :---: |
| 🛡️ **OPNsense Firewall** | Stateful packet filter rules, Outbound & Port Forward NAT, policy-based routing, Multi-WAN, Kea DHCP (subnets, reservations), Unbound DNS (overrides, DNSBL, dot), WireGuard & OpenVPN tunnels, HA/CARP failover, MVC API endpoints, official plugins. | `["opnsense"]` |
| 💾 **TrueNAS SCALE** | ZFS pool topologies (RAIDZ2, mirror, stripe), dataset creation, compression, recordsize, quotas, POSIX & NFSv4 ACL permissions, NFS exports (`maproot`, `all_squash`), SMB shares, snapshot tasks, replication tasks, cloud sync, SCALE apps. | `["truenas"]` |
| 🖥️ **Physical Hardware** | Proxmox VE server motherboards (PVE1, PVE2, PVE3), Extreme Networks switch port matrices & cabling, IPMI/BMC default settings & pinouts, SAS/SATA HBAs, disk backplanes, UPS / NUT power specs & serial pinouts, thermal limits. | `["k8s-lab"]` |
| 🔀 **Cross-Domain Scenarios** | Queries spanning multiple systems (e.g., configuring a TrueNAS NFS export and the corresponding OPNsense inter-VLAN firewall rules). | `["truenas", "opnsense"]` or `["k8s-lab", "truenas"]` |

---

## 🎯 Intelligent Trigger Conditions (When to Use)

Activate this skill and query RAGFlow (`ragflow_retrieval_by_name`) when:

1. **OPNsense Official Procedures & Parameters**:
   - The user asks how to configure firewall rules, routing policies, NAT rules, VPNs, or services in OPNsense 26.1.
   - Clarifications are needed on parameter meanings, flags, or recommended settings from official documentation.
2. **TrueNAS Official Procedures & Storage Best Practices**:
   - The user asks for recommended ZFS dataset properties (e.g., recordsize for specific workloads, sync settings), NFS/SMB permission architectures, or backup/replication task setups on TrueNAS SCALE 25.10.
3. **Physical Hardware Specifications & Datasheets**:
   - Questions regarding motherboard pinouts, PCIe slot bifurcation/lane distribution, switch console baud rates, jumper configurations, power draw, or physical cabling.
4. **Local Repository Fallback**:
   - When local configuration files (`rete.json`, `storage.json`, `ansible/`, `wiki/`) specify *what* is deployed, but lack detailed *how-to* instructions, technical specifications, or official vendor guidelines.

---

## 🚫 Strict Exclusions (Do NOT Query RAGFlow)

- **Live Cluster & Node State**: Real-time pod status, service health, live ZFS pool status (`zpool status`), active firewall rules, or system alerts $\rightarrow$ Query live system tools directly (`opnsense` MCP, `truenas-master-mcp`, `talos` MCP, `kubernetes` MCP).
- **Git Workspace Code & Configs**: Helm values (`arr-values.yaml`), Kubernetes manifests, Ansible playbooks, and GitOps logic $\rightarrow$ Inspect local repository files directly.
- **General Programming / Syntax**: Standard Python, YAML, or shell syntax questions.

---

## ⚡ Execution Workflow

1. **Classify Intent & Select Dataset**:
   Determine whether the query pertains to `opnsense`, `truenas`, `k8s-lab`, or a cross-domain combination.
2. **Query RAGFlow via `ragflow-local` MCP**:
   ```python
   ragflow_retrieval_by_name(
       dataset_names=["opnsense"], # or ["truenas"], ["k8s-lab"], or multiple
       query="<focused user question or technical search terms>"
   )
   ```
3. **Synthesize & Cite**:
   - Synthesize the answer clearly and concisely in the user's language (Italian/English).
   - **MANDATORY**: Explicitly cite the source document name, the RAGFlow dataset name, and the section/chapter referenced (e.g., `*Fonte: manual/firewall.md (Dataset: opnsense)*`).

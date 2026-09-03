---
name: ragflow-hardware-kb
type: skill
description: "Retrieve physical hardware manuals, datasheets, installation guides, component specifications, pinouts, and BIOS/IPMI settings from the RAGFlow k8s-lab dataset."
when_to_use: "When the user asks for physical hardware specifications, vendor datasheets, component pinouts, BIOS/IPMI settings, switch cabling, or homelab hardware documentation."
status: active
tags:
  - ragflow
  - hardware
  - datasheets
  - manuals
  - k8s-lab
---

# RAGFlow Hardware Knowledge Base (`k8s-lab`)

## Overview
This skill provides automated, intelligent retrieval of homelab physical hardware documentation indexed in **RAGFlow** (`https://ragflow-internal.pindaroli.org`) under the dataset **`k8s-lab`**.

## Scope & Target Hardware
The `k8s-lab` dataset contains datasheets, installation manuals, hardware reference guides, and technical specifications for:
- **Proxmox VE Nodes (PVE1, PVE2, PVE3)**: Motherboards, CPU sockets, memory configurations, PCIe lane bifurcation, IPMI/BMC interfaces.
- **TrueNAS Bare-Metal Host**: SAS/SATA HBAs, disk backplanes, NVMe adapters, chassis layout, thermal limits, power supply specifications.
- **Network Hardware**: Extreme Networks switches (port layouts, SFP+/QSFP+ cabling, console pinouts), OPNsense appliance hardware, DAC cables, transceivers.
- **Power & Protection**: NUT / UPS systems, serial/USB monitoring pinouts, wattage ratings, runtime curves.

## Intelligent Trigger Conditions (When to Use)
Activate this skill and query RAGFlow (`ragflow_search` or `ragflow_ask_assistant`) when:
1. **Component Specifications & Datasheets**: User asks about power consumption, dimensions, supported RAM types, PCIe slot bandwidth, jumper settings, or hardware limits.
2. **Installation & Cabling Guides**: Questions about motherboard headers, front panel wiring, serial console pinout, fan headers, or storage controller cabling.
3. **Firmware & BIOS/IPMI Configuration**: Vendor-recommended BIOS settings, BMC default IPs, jumper recovery procedures.
4. **Local Repository Fallback**: If local repository files (`rete.json`, `ansible/`, `wiki/`) do not contain the physical component specification, query RAGFlow before declaring missing information.

## Exclusions (Do NOT Use)
- **Live Cluster Operations**: Real-time pod status, service health, live ZFS pool states, Talos cluster events, or OPNsense active firewall states -> Query live system tools directly (`kubectl`, `truenas-master-mcp`, `opnsense`, `talos`).
- **Git Workspace Code & Configs**: Helm values (`arr-values.yaml`), Kubernetes manifests, Ansible playbooks, and GitOps logic -> Inspect local repository files.
- **General Programming / Syntax**: Standard Python, YAML, or bash syntax questions.

## Execution Workflow
1. **Identify Hardware Model**: Extract the exact component, server, switch, or controller model from the user query.
2. **Query RAGFlow**:
   - Use `ragflow_search(query=..., dataset_name="k8s-lab")` to retrieve relevant chunks, tables, and page excerpts.
   - If dataset IDs are needed, use `ragflow_list_datasets()` to verify `k8s-lab` availability.
3. **Synthesize & Cite**:
   - Answer the question clearly in the user's language (Italian/English).
   - **MANDATORY**: Explicitly cite the source document name, the `k8s-lab` dataset, and section/page if available.

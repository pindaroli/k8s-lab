---
created: '2026-08-27T04:17:59.528657+00:00'
sources:
- plugin: local_file
  title: servicenow-k8s-discovery-guide
  url: /Users/olindo/prj/k8s-lab/raw/servicenow-k8s-discovery-guide.html
summary: Guide on integrating ServiceNow with Kubernetes for cluster discovery and
  resource management.
tags:
- service-management
- kubernetes
- gitops
- automation
title: ServiceNow Kubernetes Discovery / 服务现在Kubernetes发现
updated: '2026-08-27T04:17:59.528665+00:00'
---

## English

### Introduction to ServiceNow and Kubernetes Integration

ServiceNow provides robust tools for managing IT operations, including integration with Kubernetes, a popular container orchestration platform. This guide explores how ServiceNow discovers Kubernetes clusters and manages resources using GitOps methodologies.

### Key Concepts

#### 1. GitOps Provisioning
GitOps leverages Git repositories as the single source of truth for infrastructure configurations. In ServiceNow, this involves creating manifests that define desired cluster states and committing them to a repository. See [[gitops-provisioning-autobrr|GitOps Provisioning for Autobrr]] and [[gitops-methodology-autobrr-implementation|GitOps Methodology Implementation]].

#### 2. Cluster Resource Inventory
ServiceNow discovers Kubernetes clusters by interacting with resource inventories. This process involves identifying PersistentVolumes (PVs) and PersistentVolumeClaims (PVCs) managed through Container Storage Interfaces (CSI). The CSI driver handles PV allocation and lifecycle, while ServiceNow collects inventory data via REST APIs or CLI tools like Kubectl.

#### 3. Kubernetes Service Discovery
Service discovery in Kubernetes involves automatically detecting services without manual lookup. This guide covers how to implement DNS-based discovery for internal communication within a cluster and establish external accessibility through Ingress controllers and endpoints.

### Implementation Steps

- **Cluster Connection**: Use either direct Kubectl access or an in-cluster agent部署 to connect clusters within ServiceNow.
- **Configuration Management**: Store Kubernetes configurations, including CSI plugin settings, in Git repositories. Ensure these configurations are versioned and auditable.
- **Resource Discovery**: Implement inventory collection using REST APIs or CLI tools, ensuring compatibility with ServiceNow's CI/CD pipelines.

### Conclusion

ServiceNow facilitates Kubernetes cluster discovery by managing resource inventories and applying GitOps practices. Understanding these mechanisms is crucial for optimizing IT infrastructure management in hybrid environments.

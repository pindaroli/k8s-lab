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
GitOps leverages Git repositories as the single source of truth for infrastructure configurations. In ServiceNow, this involves creating manifests that define desired cluster states and committing them to a repository.

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

## 中文

### 服务现在与Kubernetes集成简介

ServiceNow 提供了强大的工具来管理IT运营，其中包括与Kubernetes的集成。指南探索了ServiceNow如何发现Kubernetes集群并使用GitOps方法进行资源管理。

#### 1. GitOps配置
GitOps通过Git仓库作为基础设施配置的唯一真实来源。在ServiceNow中，这涉及创建定义期望集群状态的手册，并将其提交到存储库中。

#### 2. 集群资源清单
ServiceNow通过与资源清单交互发现Kubernetes集群。过程包括识别PersistentVolumes（PV）和 PersistentVolumeClaims (PVC)，这些由容器存储接口（CSI）管理。

#### 3. Kubernetes服务发现
Kubernetes中的服务发现涉及自动检测服务而不需手动查找。本指南涵盖如何通过DNS实现内部通信服务发现，并设置Ingress控制器和端点以建立外部访问。

### 实施步骤

- 集群连接：使用直接的Kubectl访问或将代理部署到集群中来连接ServiceNow中的集群。
- 配置管理：将 Kubernetes 配置（包括 CSI 插件配置）存储在 Git 仓库中，确保这些配置是版本化的并可审核。
- 资源发现：实现使用REST API或CLI工具的清单收集，与ServiceNow的CI/CD管道兼容。

### 结论

通过管理资源清单和应用GitOps实践，ServiceNow促进Kubernetes集群发现。理解这些机制对于在混合环境中优化IT基础架构管理至关重要。

## 日本語

### ServiceNow と Kubernetes 統合の概要

ServiceNowは、IT運用を管理するための強力なツールです。このガイドでは、ServiceNowがKubernetesクラスターを発見し、GitOpsメソッドでリソースを管理する方法について解説します。

#### 1. GitOpsプロビジョニング
GitOpsはGitリポジトリをインフラストラクチャの定義として使用し、単一の真実源とします。ServiceNowでは、クラスター状態を定義した宣言を作成し、リポジトリにコミットします。

#### 2. クラスター リソース アンティテイ
ServiceNowはKubernetesクラスターを発見するために、PV（PERSISTENTVOLUME）と PVC（PERSISTENTVOLUMECLAIM）のリソースアンティテイを使用します。これがContainderStorageInterface (CSI)により管理されます。

#### 3. Kubernetes サービス 発見
サービス発現はKubernetesの重要な部分です。このガイドでは、クラスター内での内部通信を可能にするDNSベースの発現と、外部アクセスを設定するためのIngressコントローラーとエンドポイントについて説明します。

### 実施手順

- クラスター接続：Kubectl直接使用またはクロスクラスターにAgent配置を使用。
- 設定管理：Gitリポジトリ内にKubernetes設定を保存し、バージョン化。
- リソース発見：REST APIやCLIツールを活用したinventory collectionを実施。

### 結論

ServiceNowはGitOps praticesを使用してクラスター発見。これらのメカニズムの理解はハイブリッド環境でのITインフラ管理最適化に不可欠です。
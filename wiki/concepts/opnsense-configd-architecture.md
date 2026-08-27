---
created: '2026-08-27T04:15:00.794193+00:00'
sources:
- plugin: local_file
  title: opnsens-action-cron-guide
  url: ''
summary: Understanding the core architecture of configd in OPNsense and its role in
  integrating CLI and WebGUI.
tags:
- opnsense
- automation
- system administration
title: OPNsense Configd Architecture / OPNsense的Configd架构
updated: '2026-08-27T04:15:00.794227+00:00'
---

## English

Configd is the backbone of command-line integration and automation scheduling in OPNsense. It consists of three main components:

1. **Executable Scripts**: These are the core logic files (Shell, Python, etc.) that perform specific actions.
2. **Action Configuration Files (`.conf`)**: These map CLI commands to WebGUI actions, defining permissions, log messages, and descriptions.
3. **Configd Daemon**: The background service that reads configurations and executes actions securely through `configctl`.

The architecture ensures seamless integration between command-line operations and the graphical interface, allowing scripts to be scheduled natively within OPNsense.

[[OPNsense System Automation]]

## 中文

configd 是 OPNsense 命令行集成和自动化调度的核心架构。它主要由以下三部分组成：

1. **可执行脚本**：这些是核心逻辑文件（如 Shell、Python 等），用于完成特定的操作。
2. **动作配置文件 (`.conf`)**：这些文件将 CLI 命令映射到 WebGUI 动作，定义权限、日志消息和描述信息。
3. **configd 守护进程**：读取配置并安全执行命令的后台服务。

该架构实现了命令行操作与图形界面之间的无缝集成，使脚本能够原生地在 OPNsense 中进行调度。

[[OPNsense 系统自动化]]

## 日本語

Configd は、OPNsense のコマンドライン統合と自動化スケジューリングの核となるアーキテクチャです。この構成は以下の 3 部分からなります：

1. **Executable Scripts**: 特定のアクションを実行するためのロジックを含むファイル（シェル、Python 等）。
2. **Action Configuration Files (`.conf`)**: CLI コマンドを WebGUI アクションにマッピングし、パーミッションやログメッセージ、記述を定義します。
3. **Configd Daemon**: 設定の読み込みと安全なコマンド実行を行うバックグラウンド サービス。

このアーキテクチャは、コマンドライン操作とグラフィカル インターフェース間のシームレスな統合を可能にし、OPNsense 環境内でのネイティブ スケジューリングを実現します。

[[OPNsense システム アウトソーシング]]
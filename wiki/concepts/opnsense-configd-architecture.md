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

[[opnsense-system-automation|OPNsense System Automation]]

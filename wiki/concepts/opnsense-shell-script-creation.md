---
created: '2026-08-27T04:15:00.799718+00:00'
sources:
- plugin: local_file
  title: opnsens-action-cron-guide
  url: ''
summary: Guide to developing and registering custom shell scripts for automation tasks.
tags:
- opnsense
- scripting
- system administration
title: Creating Custom Shell Scripts in OPNsense / OPNsense中的Shell脚本创建
updated: '2026-08-27T04:15:00.799735+00:00'
---

## English

In OPNsense, custom Shell scripts can be created and registered as automation actions. Here's the process:

1. **Create the Script**: Place executable files in `/usr/local/opnsense/scripts/`.
2. **Make it Executable**: Use `chmod +x` to ensure the script runs properly.
3. **Add Log Statements**: Include logging to track execution (`logger -t your-script-tag`).
4. **Automate with Cron**: Schedule scripts natively through OPNsense's WebGUI Cron interface.

Best practices include testing scripts in CLI before deployment and ensuring proper permissions.

[[opnsense-system-automation|OPNsense System Automation]]

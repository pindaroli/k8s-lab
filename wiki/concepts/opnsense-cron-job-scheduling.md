---
created: '2026-08-27T04:15:00.804284+00:00'
sources:
- plugin: local_file
  title: opnsens-action-cron-guide
  url: ''
summary: Configuring and managing automation tasks using OPNsense's native Cron interface.
tags:
- cron
- scheduling
- opnsense
title: Cron Job Scheduling in OPNsense / OPNsense中的Cron任务调度
updated: '2026-08-27T04:15:00.804292+00:00'
---

## English

OPNsense provides a WebGUI for configuring Cron jobs. To create and manage jobs:

1. **Access the Interface**: Navigate to System > Settings > Cron from the menu.
2. **Create New Job**: Click `+` in the bottom-right corner.
3. **Configure Schedule**: Set intervals for minutes, hours, days, etc.
4. **Select Command**: Use the dropdown to choose predefined actions or custom scripts.
5. **Apply Changes**: Save and apply settings for cron.d updates.

Important notes:
- Clear browser cache (`Ctrl + F5`) after adding new actions to ensure they appear in the GUI.
- Test commands in CLI before scheduling them in WebGUI.

[[opnsense-system-automation|OPNsense System Automation]]

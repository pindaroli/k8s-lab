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

[[OPNsense System Automation]]

## 中文

OPNsense 提供了一个基于 Web 的界面来配置和管理 Cron 任务。以下是具体步骤：

1. **访问界面**：从菜单中导航至系统 > 设置 > Cron。
2. **创建新任务**：点击右下角的 `+` 按钮。
3. **设置调度计划**：为分钟、小时、日期等设定间隔。
4. **选择命令**：使用下拉菜单选择预定义的动作或自定义脚本。
5. **应用更改**：保存并应用设置以更新 cron.d 文件。

重要提示：
- 在新增动作后，清除浏览器缓存（`Ctrl + F5`）以确保它们出现在 GUI 中。
- 在 Web 界面安排任务前，请先在 CLI 上测试命令。

[[OPNsense 系统自动化]]

## 日本語

OPNsense は、Cron ジョブの設定と管理用に、ネイティブな WebGUI を提供します。以下に具体的な手順を示します：

1. **インターフェースへのアクセス**: メニューから System > Settings > Cron に移動します。
2. **新規ジョブの作成**: 右下角にある `+` ボタンをクリックします。
3. **スケジューリングの設定**: 分、時、日などを指定して間隔を設定します。
4. **コマンドの選択**: ドロップダウン メニューを使用してプリント定義されたアクションか独自のスクリプトを選択します。
5. **変更の適用**: 設定を保存し、Cron に変更を反映させます。

重要な注意点：
- 新しい動作を追加した後は、ブラウザー キャッシュをクリア (`Ctrl + F5`) して GUI 上で新規項目が表示されるようにします。
- WebGUI でのスケジューリング前に、CLI 上でのコマンドテストを実施してください。

[[OPNsense システム アウトソーシング]]
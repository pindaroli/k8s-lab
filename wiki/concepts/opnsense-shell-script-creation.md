---
created: '2026-08-27T04:15:00.799718+00:00'
sources:
- plugin: local_file
  title: opnsens-action-cron-guide
  url: ''
summary: Guide to developing and registering custom shell scripts for automation tasks.
tags:
- shell scripting
- opnsense
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

[[OPNsense System Automation]]

## 中文

在 OPNsense 中，可以创建自定义 Shell 脚本并将其注册为自动化动作。以下是具体步骤：

1. **创建脚本**：将可执行文件放置于 `/usr/local/opnsense/scripts/` 目录中。
2. **设置权限**：通过 `chmod +x` 命令确保脚本正确执行。
3. **添加日志语句**：在脚本中加入日志记录（如 `logger -t your-script-tag`）以便追踪执行情况。
4. **自动化任务调度**：通过 OPNsense 的 WebGUI Cron 接口原生地安排脚本运行。

建议在部署前对脚本进行 CLI 测试，并确保所有权限设置正确。

[[OPNsense 系统自动化]]

## 日本語

OPNsense では、独自のシェル スクリプトを作成し、自動化アクションとしてレジ斯特レーション可能です。以下に操作手順を示します：

1. **スクリプト作成**：可執行ファイルを `/usr/local/opnsense/scripts/` ディレクトリ内に配置します。
2. **実行可能権限の設定**: `chmod +x` を使用してスクリプトが正しく実行されるようにします。
3. **ログ記録の追加**: 実行状況を追跡するために、スクリプト内でログ記録を含めます（例: `logger -t your-script-tag`）。
4. **タスクスケジューリング**: OPNsense の WebGUI Cron インターフェースを通じてスクリプトをネイティブに仕様します。

スクリプトのデプロイメント前に CLI でのテストや適切なパーミッション設定を行うことをお勧めします。

[[OPNsense システム アウトソーシング]]
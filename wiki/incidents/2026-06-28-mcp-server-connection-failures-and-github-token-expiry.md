---
title: "MCP Server Connection Failures and GitHub Token Expiry"
type: incident
status: archived
certified_for_ai: false
date: 2026-06-28
severity: P3
resolved: true
resolved_at: 2026-06-28T09:35:00Z
tags:
  - "#incident"
  - "#mcp"
---

# Incident: MCP Server Connection Failures and GitHub Token Expiry
**Date**: 2026-06-28
**Status**: RESOLVED (GitHub token updated and migrated to bare-metal; IDE socket proxies disabled in standalone app)
**Severity**: Medium (Impeded GitHub and IDE MCP operations in the desktop standalone agent)

## 🔍 Diagnosis
During diagnostics of the Google Antigravity local MCP setup:
1. **GitHub MCP Server (401 Bad credentials)**: The containerized `github-mcp-server` failed with bad credentials because the configured Personal Access Token (`ghp_MDUVBh...`) had expired.
2. **Notebooks & Visualization MCP Servers (EOF / Connection closed)**: The client proxy `mcp_proxy_bundle.js` was unable to establish a socket connection (`ECONNREFUSED` / `ENOENT`), because it was looking for IPC sockets (`datacloud-mcp-notebooks-antigravityide.sock`) managed by **Antigravity IDE**. Since the standalone **Antigravity Desktop App** (v2.2.1) was running instead of the IDE, the backend socket hosts were absent.
3. **Dangling Processes**: A Docker container for `ghcr.io/github/github-mcp-server` remained running in the background, keeping the old credentials bound.

## 🛠️ Actions Taken & Resolution

### 1. GitHub MCP Server Migration to Bare-Metal & Token Update
* **Bare-Metal Setup**: Migrated the `github-mcp-server` config in `~/.gemini/config/mcp_config.json` away from Docker to run bare-metal using `npx -y @modelcontextprotocol/server-github`.
* **Token Update**: Configured the valid, tested Personal Access Token (`ghp_SkDQVK...`) in the `GITHUB_PERSONAL_ACCESS_TOKEN` environment variable.
* **Process Clean-up**: Terminated and deleted the lingering Docker container (`docker rm -f 359d5692f831`).

### 2. Disabling Absent IDE Sockets in Standalone Mode
* To prevent background EOF/connection-refused loops on tools that require the IDE context, the proxy configs for `notebooks` and `visualization` were disabled in `mcp_config.json` by prefixing their keys as `_disabled_notebooks` and `_disabled_visualization`.

## 🧪 Verification Results
* **GitHub Integration**: Tested `github-mcp-server` using the `search_repositories` tool; it successfully queried GitHub's API and returned matching repositories.
* **Token Validation**: Verified token authenticity using `curl -H "Authorization: token ..."` which returned correct user metadata for `pindaroli`.
* **Ollama & GMP Assist**: Verified that `ollama` and `gmp-code-assist` MCP servers are fully active and responding.

## 🔗 References
* [[Talos_Cluster]]
* [mcp_config.json](file:///Users/olindo/.gemini/config/mcp_config.json)
* [[Network_Registry]]

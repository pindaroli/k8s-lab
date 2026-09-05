"""Wrapper for talos-mcp-server that:
1. Materializes TALOSCONFIG_DATA into /tmp/talos/config if provided in environment
2. Patches the SupportTool.args_schema bug in talos-mcp-server <= 0.3.10
3. Starts the talos_mcp CLI
"""

import os
import sys

# 1. Check if TALOSCONFIG_DATA is provided in environment
if "TALOSCONFIG_DATA" in os.environ and not os.environ.get("TALOSCONFIG"):
    config_dir = "/tmp/talos"
    os.makedirs(config_dir, exist_ok=True)
    config_file = os.path.join(config_dir, "config")
    with open(config_file, "w", encoding="utf-8") as f:
        f.write(os.environ["TALOSCONFIG_DATA"])
    os.environ["TALOSCONFIG"] = config_file

# Default audit log to /tmp if not explicitly set
if not os.environ.get("TALOS_MCP_AUDIT_LOG_PATH"):
    os.environ["TALOS_MCP_AUDIT_LOG_PATH"] = "/tmp/talos_mcp_audit.log"

# 2. Monkeypatch SupportTool before importing talos_mcp.server
from pydantic import BaseModel, Field
import talos_mcp.tools.support as _support_module


class _SupportSchema(BaseModel):
    """Schema for support bundle arguments (patched)."""

    nodes: str = Field(
        description="Comma-separated list of node IPs or hostnames to target",
    )
    verbose: bool = Field(
        default=False,
        description="Enable verbose logging for the support command",
    )


_support_module.SupportTool.args_schema = _SupportSchema  # type: ignore[attr-defined]

# 3. Start the standard CLI
from talos_mcp.cli import cli  # noqa: E402

if __name__ == "__main__":
    cli()

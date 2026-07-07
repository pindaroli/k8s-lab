"""Wrapper for talos-mcp-server that patches the SupportTool.args_schema bug.

Bug: In talos-mcp-server <= 0.3.10, SupportTool defines `args_schema` as a
regular method (returning a dict) instead of a ClassVar[type[BaseModel]].
This causes `'function' object has no attribute 'model_json_schema'` when
the MCP server tries to register the tool.

This wrapper applies an in-memory monkeypatch before starting the server,
without modifying any cached files on disk.

Usage in mcp_config.json:
  {
    "command": "/opt/homebrew/bin/uv",
    "args": [
      "run",
      "--prerelease=allow",
      "--with", "talos-mcp-server==0.3.10",
      "--with", "mcp>=1.0.0,<2.0.0",
      "/Users/olindo/prj/k8s-lab/scripts/talos_mcp_wrapper.py"
    ],
    "env": {
      "TALOSCONFIG": "/Users/olindo/prj/k8s-lab/talos-config/talosconfig",
      "TALOS_MCP_AUDIT_LOG_PATH": "/Users/olindo/prj/k8s-lab/talos_mcp_audit.log"
    }
  }
"""

# --- Monkeypatch (must run before talos_mcp.server is fully loaded) ---

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

# --- Start the standard CLI ---

from talos_mcp.cli import cli  # noqa: E402

if __name__ == "__main__":
    cli()

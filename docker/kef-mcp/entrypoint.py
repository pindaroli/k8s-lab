import os
import sys

# Default transport for ToolHive Operator is stdio
transport = os.environ.get("MCP_TRANSPORT", "stdio").lower()

if transport == "stdio":
    from server import mcp
    mcp.run(transport="stdio")
else:
    import uvicorn
    from server import app
    host = os.environ.get("MCP_HOST", "0.0.0.0")
    port = int(os.environ.get("MCP_PORT", "8000"))
    uvicorn.run(app, host=host, port=port)

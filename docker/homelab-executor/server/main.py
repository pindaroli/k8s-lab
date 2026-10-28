#!/usr/bin/env python3
"""
Homelab Executor Server
Exposes homelab automation tools via:
1. FastMCP (SSE transport for AI agent integration)
2. FastAPI REST API (/api/run/{tool_name} and /health)
3. OpenSSH Server (interactive CLI via go.py)
"""

import asyncio
import logging
import os
import re
import signal
import sys
import time
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml
from fastapi import Body, FastAPI, HTTPException
from fastapi.responses import JSONResponse
from mcp.server.fastmcp import FastMCP

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    stream=sys.stdout,
)
logger = logging.getLogger("homelab-executor")

# Configuration & Paths
APP_VERSION = os.getenv("APP_VERSION", "1.0.0")

# Determine base repository directory (/app in container, repo root for local dev)
CONTAINER_APP_DIR = Path("/app")
if CONTAINER_APP_DIR.exists() and (CONTAINER_APP_DIR / "scripts").exists():
    BASE_DIR = CONTAINER_APP_DIR
else:
    # Local fallback
    BASE_DIR = Path(__file__).resolve().parent.parent.parent

MCP_TOOLS_FILE = BASE_DIR / "scripts" / "mcp_tools.yaml"

# Global state
active_jobs: int = 0
active_jobs_lock = asyncio.Lock()
is_draining: bool = False
loaded_tools: Dict[str, Dict[str, Any]] = {}

# FastMCP setup
mcp = FastMCP("homelab-executor")
# Allow all hosts / disable DNS rebinding checks behind reverse proxy (Traefik)
if hasattr(mcp.settings, "transport_security") and mcp.settings.transport_security:
    mcp.settings.transport_security.enable_dns_rebinding_protection = False
    mcp.settings.transport_security.allowed_hosts = ["*"]


async def execute_tool(tool_name: str, params: Dict[str, Any]) -> Dict[str, Any]:
    """Execute an automation tool asynchronously via subprocess."""
    global active_jobs, is_draining

    if is_draining:
        return {
            "tool": tool_name,
            "status": "error",
            "returncode": -1,
            "stdout": "",
            "stderr": "Server is in draining state for shutdown/maintenance. Requests rejected.",
            "duration_seconds": 0.0,
        }

    if tool_name not in loaded_tools:
        return {
            "tool": tool_name,
            "status": "error",
            "returncode": -1,
            "stdout": "",
            "stderr": f"Tool '{tool_name}' is not recognized.",
            "duration_seconds": 0.0,
        }

    tool_def = loaded_tools[tool_name]
    tool_type = tool_def.get("type", "bash")
    rel_path = tool_def.get("path", "")
    script_path = BASE_DIR / rel_path

    if not script_path.exists():
        return {
            "tool": tool_name,
            "status": "error",
            "returncode": -1,
            "stdout": "",
            "stderr": f"Script file not found: {script_path}",
            "duration_seconds": 0.0,
        }

    # Build command
    if tool_type == "python":
        cmd = ["python3", str(script_path)]
    elif tool_type == "bash":
        cmd = ["/bin/bash", str(script_path)]
    elif tool_type == "ansible":
        cmd = ["ansible-playbook", str(script_path)]
    else:
        cmd = [str(script_path)]

    # Process CLI mapping
    cli_mapping = tool_def.get("cli_mapping", {})
    ansible_mapping = tool_def.get("ansible_mapping", {})

    if cli_mapping and "args" in cli_mapping:
        for arg in cli_mapping.get("args", []):
            arg_type = arg.get("type")
            flag = arg.get("flag", "")
            bind = arg.get("bind")

            if arg_type == "positional":
                # Check for template replacement {{ var }}
                pos_val = flag
                for k, v in params.items():
                    pos_val = pos_val.replace(f"{{{{ {k} }}}}", str(v)).replace(f"{{{{{k}}}}}", str(v))
                if pos_val and "{{" not in pos_val:
                    cmd.append(pos_val)
                elif bind and bind in params:
                    cmd.append(str(params[bind]))

            elif arg_type == "option":
                val = params.get(bind) if bind else None
                if val is not None and val != "":
                    cmd.extend([flag, str(val)])

            elif arg_type == "flag":
                val = params.get(bind) if bind else None
                if bool(val) is True:
                    cmd.append(flag)

    elif ansible_mapping:
        limit = ansible_mapping.get("limit")
        if limit:
            for k, v in params.items():
                limit = limit.replace(f"{{{{ {k} }}}}", str(v)).replace(f"{{{{{k}}}}}", str(v))
            if limit and limit != "all" and "{{" not in limit:
                cmd.extend(["-l", str(limit)])

    else:
        # Default parameter behavior
        if params.get("dry_run") is True:
            cmd.append("--dry-run")

    # Environment
    env = os.environ.copy()
    env["PYTHONPATH"] = str(BASE_DIR)
    env["SOPS_AGE_KEY_FILE"] = os.getenv(
        "SOPS_AGE_KEY_FILE", "/home/executor/.config/sops/age/keys.txt"
    )
    env["ANSIBLE_CONFIG"] = str(BASE_DIR / "ansible" / "ansible.cfg")
    env["PYTHONUNBUFFERED"] = "1"

    timeout = tool_def.get("timeout_seconds", 60)
    start_time = time.time()

    async with active_jobs_lock:
        active_jobs += 1

    logger.info("Starting execution of tool '%s': %s (timeout: %ds)", tool_name, " ".join(cmd), timeout)
    try:
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=str(BASE_DIR),
            env=env,
        )

        try:
            stdout_bytes, stderr_bytes = await asyncio.wait_for(
                proc.communicate(), timeout=float(timeout)
            )
            rc = proc.returncode
            duration = round(time.time() - start_time, 2)
            stdout_str = stdout_bytes.decode("utf-8", errors="replace")
            stderr_str = stderr_bytes.decode("utf-8", errors="replace")

            status = "success" if rc == 0 else "error"
            logger.info("Finished tool '%s' with code %d in %ss", tool_name, rc, duration)
            return {
                "tool": tool_name,
                "status": status,
                "returncode": rc,
                "stdout": stdout_str,
                "stderr": stderr_str,
                "duration_seconds": duration,
            }

        except asyncio.TimeoutError:
            duration = round(time.time() - start_time, 2)
            logger.warning("Tool '%s' timed out after %ds, killing process...", tool_name, timeout)
            try:
                proc.kill()
            except ProcessLookupError:
                pass
            stdout_bytes, stderr_bytes = await proc.communicate()
            return {
                "tool": tool_name,
                "status": "timeout",
                "returncode": -1,
                "stdout": stdout_bytes.decode("utf-8", errors="replace"),
                "stderr": f"Execution timed out after {timeout} seconds\n"
                + stderr_bytes.decode("utf-8", errors="replace"),
                "duration_seconds": duration,
            }

    finally:
        async with active_jobs_lock:
            active_jobs -= 1


def register_mcp_tool(tool_def: Dict[str, Any]):
    """Dynamically registers an MCP tool on FastMCP."""
    name = tool_def["name"]
    desc = tool_def.get("description", "")
    params_schema = tool_def.get("parameters", {})
    props = params_schema.get("properties", {})
    required = params_schema.get("required", [])

    sig_params = []
    for p_name, p_spec in props.items():
        t = p_spec.get("type", "string")
        if t == "string":
            py_type = "str"
        elif t == "boolean":
            py_type = "bool"
        elif t == "integer":
            py_type = "int"
        else:
            py_type = "Any"

        default = p_spec.get("default")
        if default is not None:
            if isinstance(default, str):
                sig_params.append(f'{p_name}: {py_type} = "{default}"')
            else:
                sig_params.append(f"{p_name}: {py_type} = {default}")
        elif p_name in required:
            sig_params.append(f"{p_name}: {py_type}")
        else:
            sig_params.append(f"{p_name}: Optional[{py_type}] = None")

    args_str = ", ".join(sig_params)
    func_code = f"""async def {name}({args_str}) -> str:
    params = locals()
    # Filter out None values
    clean_params = {{k: v for k, v in params.items() if v is not None}}
    res = await execute_tool('{name}', clean_params)
    if res.get('status') == 'success' and res.get('returncode') == 0:
        out = res.get('stdout', '') or 'Execution completed successfully with no output.'
        return out
    else:
        err = res.get('stderr', '') or res.get('stdout', '') or 'Unknown execution error'
        return f"ERROR (Exit Code {{res.get('returncode')}}):\\n{{err}}"
"""
    local_scope = {"execute_tool": execute_tool, "Optional": Optional, "Any": Any}
    exec(func_code, globals(), local_scope)
    fn = local_scope[name]
    mcp.add_tool(fn, name=name, description=desc)
    logger.debug("Registered MCP tool: %s", name)


def load_tools_catalog():
    """Loads and registers tools from scripts/mcp_tools.yaml."""
    if not MCP_TOOLS_FILE.exists():
        logger.error("mcp_tools.yaml not found at: %s", MCP_TOOLS_FILE)
        return

    with open(MCP_TOOLS_FILE, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    tools = data.get("tools", [])
    for tool_def in tools:
        name = tool_def.get("name")
        if not name:
            continue
        # Security Guardrail: Never expose update_homelab_executor via remote MCP or REST
        if name == "update_homelab_executor":
            continue

        loaded_tools[name] = tool_def
        register_mcp_tool(tool_def)

    logger.info("Loaded %d tools from %s", len(loaded_tools), MCP_TOOLS_FILE)


# Lifespan management for graceful drain
@asynccontextmanager
async def app_lifespan(app: FastAPI):
    global is_draining
    logger.info("Homelab Executor starting up (Version: %s)...", APP_VERSION)
    load_tools_catalog()
    yield
    logger.info("Initiating graceful shutdown drain. Active jobs: %d", active_jobs)
    is_draining = True
    # Wait for active jobs to complete (up to 60s)
    drain_timeout = 60
    start = time.time()
    while active_jobs > 0 and (time.time() - start) < drain_timeout:
        await asyncio.sleep(0.5)
    logger.info("Drain finished. Exiting server.")


# FastAPI Application
app = FastAPI(
    title="Homelab Executor Service",
    version=APP_VERSION,
    description="Remote execution gateway for homelab maintenance scripts and Ansible playbooks",
    lifespan=app_lifespan,
)


@app.get("/health")
async def health():
    """Health check endpoint for Docker and Traefik."""
    status = "draining" if is_draining else "healthy"
    status_code = 503 if is_draining else 200
    return JSONResponse(
        status_code=status_code,
        content={
            "status": status,
            "version": APP_VERSION,
            "draining": is_draining,
            "active_jobs": active_jobs,
        },
    )


@app.get("/api/tools")
async def list_tools():
    """List all available automation tools."""
    return {
        "count": len(loaded_tools),
        "tools": [
            {
                "name": name,
                "description": t.get("description", ""),
                "type": t.get("type", ""),
                "parameters": t.get("parameters", {}),
            }
            for name, t in loaded_tools.items()
        ],
    }


@app.post("/api/run/{tool_name}")
async def run_tool_api(tool_name: str, payload: Dict[str, Any] = Body(default={})):
    """Run an automation tool via REST API."""
    if tool_name not in loaded_tools:
        raise HTTPException(status_code=404, detail=f"Tool '{tool_name}' not found")
    if is_draining:
        raise HTTPException(
            status_code=503,
            detail="Server is draining for maintenance/restart. Requests rejected.",
        )

    result = await execute_tool(tool_name, payload)
    return result


# Mount FastMCP SSE App at root
app.mount("/", mcp.sse_app())

if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=8000, log_level="info")

#!/usr/bin/env python3
"""
Homepage MCP Bridge (Stdio -> Streamless HTTP JSON-RPC 2.0).

Interfaccia leggera per connettere client MCP Stdio (Antigravity/Claude)
all'endpoint Streamless HTTP POST di Homepage (/api/mcp).
"""

import sys
import json
import urllib.request
import urllib.error
import ssl
import argparse
import os


def main():
    parser = argparse.ArgumentParser(description="Homepage MCP Stdio/HTTP Bridge")
    parser.add_argument("--url", required=True, help="Homepage MCP endpoint URL (e.g. https://.../api/mcp)")
    parser.add_argument(
        "--token",
        default=os.environ.get("HOMEPAGE_MCP_TOKEN", ""),
        help="Bearer authentication token",
    )
    parser.add_argument("--insecure", action="store_true", help="Disable SSL certificate verification")
    args = parser.parse_args()

    if not args.token:
        sys.stderr.write("Error: Token not provided via --token or HOMEPAGE_MCP_TOKEN env var\n")
        sys.exit(1)

    ctx = ssl.create_default_context()
    if args.insecure:
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE

    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            msg = json.loads(line)
        except Exception:
            continue

        req = urllib.request.Request(
            args.url,
            data=line.encode("utf-8"),
            headers={
                "Authorization": f"Bearer {args.token}",
                "Content-Type": "application/json",
                "User-Agent": "Homepage-MCP-Bridge/1.0",
            },
        )

        try:
            with urllib.request.urlopen(req, context=ctx) as resp:
                res_data = resp.read().decode("utf-8")
                if res_data and res_data.strip():
                    sys.stdout.write(res_data.strip() + "\n")
                    sys.stdout.flush()
        except urllib.error.HTTPError as e:
            err_body = e.read().decode("utf-8", errors="ignore")
            if "id" in msg:
                err_resp = {
                    "jsonrpc": "2.0",
                    "id": msg["id"],
                    "error": {"code": -32603, "message": f"HTTP {e.code}: {err_body}"},
                }
                sys.stdout.write(json.dumps(err_resp) + "\n")
                sys.stdout.flush()
        except Exception as e:
            if "id" in msg:
                err_resp = {
                    "jsonrpc": "2.0",
                    "id": msg["id"],
                    "error": {"code": -32603, "message": str(e)},
                }
                sys.stdout.write(json.dumps(err_resp) + "\n")
                sys.stdout.flush()


if __name__ == "__main__":
    main()

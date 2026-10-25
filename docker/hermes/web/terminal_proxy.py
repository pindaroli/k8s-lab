#!/usr/bin/env python3
"""
terminal_proxy.py: FastAPI Prepend Router & Reverse Proxy per ttyd (:7681) su Hermes Agent.
Supporta:
- Proxy HTTP su /terminal, /terminal/token, /terminal/{path:path}
- Proxy WebSocket bidirezionale asincrono su /terminal/ws con subprotocol="tty" e frame binari
- Hook di installazione idempotente (--install-hook) in web_server.py e dashboard_auth/middleware.py
"""

import sys
import os
import base64
import logging
import asyncio
from pathlib import Path
from typing import Optional

import httpx
import websockets
from fastapi import APIRouter, FastAPI, Request, Response, WebSocket, WebSocketDisconnect

logger = logging.getLogger("hermes_cli.terminal_proxy")

router = APIRouter(tags=["terminal"])

TTYD_HTTP_BASE = "http://127.0.0.1:7681"
TTYD_WS_URL = "ws://127.0.0.1:7681/terminal/ws"

def _is_authenticated(request: Request) -> bool:
    """Valida se la richiesta ha una sessione attiva (cookie) o credenziali HTTP Basic Auth valide."""
    # 1. Verifica sessione Hermes da request.state
    if getattr(request.state, "session", None) is not None:
        return True

    # 2. Verifica cookie di sessione tramite modulo dashboard_auth
    try:
        from hermes_cli.dashboard_auth.cookies import read_session_cookies
        if read_session_cookies(request) is not None:
            return True
    except Exception:
        pass

    # 3. Verifica credenziali HTTP Basic Auth
    auth_header = request.headers.get("authorization", "")
    if auth_header.startswith("Basic "):
        try:
            raw = base64.b64decode(auth_header[6:]).decode("utf-8")
            user, pwd = raw.split(":", 1)
            exp_user = os.environ.get("HERMES_DASHBOARD_BASIC_AUTH_USERNAME", "admin")
            exp_pwd = os.environ.get("HERMES_DASHBOARD_BASIC_AUTH_PASSWORD") or os.environ.get("HERMES_DASHBOARD_PASSWORD", "")
            if user == exp_user and pwd == exp_pwd and exp_pwd:
                return True
        except Exception:
            pass

    return False

def _unauth_response() -> Response:
    return Response(
        content=b'{"detail": "Unauthorized"}',
        status_code=401,
        headers={"WWW-Authenticate": 'Basic realm="Hermes Terminal"'},
        media_type="application/json"
    )

@router.get("/terminal-inject.js")
async def get_terminal_inject_script():
    """Serve direttamente lo script JS di iniezione UI come asset statico."""
    candidates = [
        Path("/opt/hermes/hermes_cli/web_dist/terminal-inject.js"),
        Path(__file__).parent / "web_dist" / "terminal-inject.js",
        Path(__file__).parent / "terminal-inject.js"
    ]
    for p in candidates:
        if p.is_file():
            return Response(content=p.read_bytes(), media_type="application/javascript")
    return Response(content=b'/* terminal-inject.js non trovato */', status_code=404, media_type="application/javascript")

@router.api_route("/terminal", methods=["GET", "POST", "HEAD", "OPTIONS"])
@router.api_route("/terminal/{full_path:path}", methods=["GET", "POST", "HEAD", "OPTIONS"])
async def proxy_ttyd_http(request: Request, full_path: str = ""):
    """Inoltra le richieste HTTP a ttyd su loopback (:7681)."""
    if not _is_authenticated(request):
        return _unauth_response()

    url_path = f"/terminal/{full_path}" if full_path else "/terminal"
    target_url = f"{TTYD_HTTP_BASE}{url_path}"
    if request.url.query:
        target_url = f"{target_url}?{request.url.query}"

    # Copia degli header escludendo host e hop-by-hop
    excluded_headers = {"host", "content-length", "connection", "accept-encoding"}
    req_headers = {k: v for k, v in request.headers.items() if k.lower() not in excluded_headers}

    body = await request.body()

    try:
        async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
            resp = await client.request(
                method=request.method,
                url=target_url,
                headers=req_headers,
                content=body if body else None
            )

        resp_headers = {
            k: v for k, v in resp.headers.items()
            if k.lower() not in {"content-length", "content-encoding", "transfer-encoding", "connection"}
        }

        return Response(
            content=resp.content,
            status_code=resp.status_code,
            headers=resp_headers,
            media_type=resp.headers.get("content-type")
        )
    except Exception as exc:
        logger.error(f"Errore proxy HTTP verso ttyd ({target_url}): {exc}")
        return Response(
            content=f'{{"error": "ttyd non raggiungibile", "detail": "{str(exc)}"}}'.encode("utf-8"),
            status_code=502,
            media_type="application/json"
        )

@router.websocket("/terminal/ws")
async def proxy_ttyd_websocket(websocket: WebSocket):
    """Bridge bidirezionale asincrono WebSocket verso ttyd con subprotocol='tty'."""
    # Negozia e accetta il subprotocollo nativo ttyd
    await websocket.accept(subprotocol="tty")

    try:
        async with websockets.connect(
            TTYD_WS_URL,
            subprotocols=["tty"]
        ) as tty_ws:

            async def client_to_ttyd():
                try:
                    while True:
                        msg = await websocket.receive()
                        if "bytes" in msg and msg["bytes"]:
                            await tty_ws.send(msg["bytes"])
                        elif "text" in msg and msg["text"]:
                            await tty_ws.send(msg["text"])
                        elif msg.get("type") == "websocket.disconnect":
                            break
                except WebSocketDisconnect:
                    pass
                except Exception as e:
                    logger.debug(f"Disconnessione client -> ttyd: {e}")

            async def ttyd_to_client():
                try:
                    async for msg in tty_ws:
                        if isinstance(msg, bytes):
                            await websocket.send_bytes(msg)
                        else:
                            await websocket.send_text(msg)
                except Exception as e:
                    logger.debug(f"Disconnessione ttyd -> client: {e}")

            t1 = asyncio.create_task(client_to_ttyd())
            t2 = asyncio.create_task(ttyd_to_client())

            done, pending = await asyncio.wait([t1, t2], return_when=asyncio.FIRST_COMPLETED)
            for task in pending:
                task.cancel()

    except Exception as exc:
        logger.warning(f"Errore connessione WebSocket ttyd: {exc}")
    finally:
        try:
            await websocket.close()
        except Exception:
            pass

def register_terminal_routes(app: FastAPI):
    """Inietta le route del terminale IN TESTA a app.router.routes."""
    existing_paths = {getattr(r, "path", None) for r in app.router.routes}
    if "/terminal" not in existing_paths:
        logger.info("⚡ Iniezione delle route /terminal in testa a app.router.routes...")
        for r in reversed(router.routes):
            app.router.routes.insert(0, r)
        logger.info("✅ Route /terminal e /terminal/ws registrate con successo.")

def install_hook():
    """Modifica idempotente dei file FastAPI dentro il container per registrare router e bypass auth."""
    print("🔧 [terminal_proxy] Avvio installazione hook in Hermes Agent...")

    # 1. Modifica dashboard_auth/middleware.py per consentire passaggio a /terminal e /terminal-inject.js
    mid_file = Path("/opt/hermes/hermes_cli/dashboard_auth/middleware.py")
    if mid_file.is_file():
        content = mid_file.read_text(encoding="utf-8")
        if '"/terminal"' not in content:
            print("  -> Aggancio /terminal a _GATE_PUBLIC_PREFIXES in middleware.py...")
            old_str = '"/fonts/", "/fonts-terminal/")'
            new_str = '"/fonts/", "/fonts-terminal/", "/terminal", "/terminal-inject.js")'
            if old_str in content:
                content = content.replace(old_str, new_str)
                mid_file.write_text(content, encoding="utf-8")
                print("  ✅ middleware.py aggiornato.")
            else:
                print("  ⚠️ Pattern _GATE_PUBLIC_PREFIXES non trovato in middleware.py.")
        else:
            print("  ℹ️ /terminal già presente in middleware.py.")

    # 2. Modifica web_server.py per registrare register_terminal_routes(app)
    server_file = Path("/opt/hermes/hermes_cli/web_server.py")
    if server_file.is_file():
        content = server_file.read_text(encoding="utf-8")
        if "register_terminal_routes" not in content:
            print("  -> Iniezione register_terminal_routes in web_server.py...")
            hook_code = "\n# [Auto-Injected Hook] Hermes Terminal Proxy\ntry:\n    from hermes_cli.terminal_proxy import register_terminal_routes\n    register_terminal_routes(app)\nexcept Exception as _e:\n    pass\n\n"
            if "mount_spa(app)" in content:
                content = content.replace("mount_spa(app)", f"{hook_code}mount_spa(app)")
                server_file.write_text(content, encoding="utf-8")
                print("  ✅ web_server.py aggiornato prima di mount_spa(app).")
            else:
                content += hook_code
                server_file.write_text(content, encoding="utf-8")
                print("  ✅ web_server.py aggiornato in coda.")
        else:
            print("  ℹ️ register_terminal_routes già presente in web_server.py.")

    print("🏁 [terminal_proxy] Installazione hook completata.")

if __name__ == "__main__":
    if "--install-hook" in sys.argv:
        install_hook()
    else:
        print("Uso: python3 terminal_proxy.py --install-hook")

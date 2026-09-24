#!/usr/bin/env python3
import json
import sqlite3
import subprocess
import sys
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path

calling = sys.argv[1] if len(sys.argv) > 1 else ""
log_path = Path("/var/log/patrizia_lock.log")
CONFIGCTL = "/usr/local/sbin/configctl"
RADCLIENT = "/usr/local/bin/radclient"
CONFIG_XML = Path("/conf/config.xml")

def log(msg):
    with log_path.open("a") as fh:
        fh.write(f"{datetime.now(timezone.utc).isoformat()} {msg}\n")

def nas_from_config(root):
    for client in root.iter("client"):
        if client.findtext("name") != "ap11000":
            continue
        secret = (client.findtext("secret") or "").strip()
        ip = (client.findtext("ip") or "10.10.20.103").split("/", 1)[0].strip()
        return secret, ip
    return "", "10.10.20.103"

def telegram_from_config(root):
    node = root.find("patriziaLock")
    if node is None:
        return "", ""
    return (node.findtext("telegramToken") or "").strip(), (node.findtext("telegramChatId") or "").strip()

try:
    tree = ET.parse(CONFIG_XML)
    root = tree.getroot()
    disabled = False
    for el in root.iter("user"):
        if el.findtext("username") == "patrizia" and el.findtext("enabled") != "0":
            el.find("enabled").text = "0"
            disabled = True
    if disabled:
        tree.write("/conf/config.xml", encoding="UTF-8", xml_declaration=True)
        subprocess.run([CONFIGCTL, "template", "reload", "OPNsense/Freeradius"], check=False)
        subprocess.run([CONFIGCTL, "freeradius", "restart"], check=False)
    log(f"disabled={disabled} calling={calling}")

    secret, nas = nas_from_config(root)
    if secret:
        pkt = f'User-Name = "patrizia"\nNAS-IP-Address = {nas}\n'
        if calling:
            pkt += f'Calling-Station-Id = "{calling}"\n'
        try:
            db = sqlite3.connect("/usr/local/etc/raddb/freeradius.db")
            rows = db.execute(
                "select acctsessionid from radacct where username = 'patrizia' and acctstoptime is null"
            ).fetchall()
        except Exception:
            rows = []
        if not rows:
            rows = [(None,)]
        for (session_id,) in rows:
            body = pkt
            if session_id:
                body += f'Acct-Session-Id = "{session_id}"\n'
            subprocess.run(
                [RADCLIENT, "-t", "2", "-r", "1", f"{nas}:3799", "disconnect", secret],
                input=body, text=True, check=False,
            )

    token, chat = telegram_from_config(root)
    if token and chat:
        text = (
            "FreeRADIUS: patrizia ha aperto una seconda sessione Wi-Fi. "
            "L'utente e' stato disabilitato e le sessioni vanno abbattute. "
            "Riattivare da Services, FreeRADIUS, Users. "
            f"Calling-Station-Id: {calling or 'n/d'}."
        )
        body = json.dumps({"chat_id": chat, "text": text}).encode()
        req = urllib.request.Request(
            f"https://api.telegram.org/bot{token}/sendMessage",
            data=body,
            headers={"Content-Type": "application/json"},
        )
        try:
            urllib.request.urlopen(req, timeout=15).read()
            log("telegram=sent")
        except Exception as exc:
            log(f"telegram_error={exc}")
except Exception as exc:
    log(f"error={exc}")

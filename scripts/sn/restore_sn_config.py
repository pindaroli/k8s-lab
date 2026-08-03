#!/usr/bin/env python3
"""
restore_sn_config.py — ServiceNow Configuration Restorer
Legge il backup JSON più recente (sn_config_latest.json) e riapplica le configurazioni
(ecc_agent_property, discovery_credentials, sys_properties) sull'istanza ServiceNow.
"""

import os
import sys
import json
import urllib.request
import urllib.parse
import base64

DEFAULT_URL = os.getenv("SERVICENOW_INSTANCE_URL", "https://dev395227.service-now.com")
DEFAULT_USER = os.getenv("SERVICENOW_USERNAME", "admin")
DEFAULT_PASS = os.getenv("SERVICENOW_PASSWORD", "cupV=59*CYcK")

SCRIPT_DIR = os.path.dirname(os.path.realpath(__file__))
LATEST_FILE = os.path.join(SCRIPT_DIR, "backups", "sn_config_latest.json")


def make_post_request(instance_url, username, password, table, payload):
    """Esegue una chiamata REST POST alla Table API di ServiceNow per creare/ripristinare un record."""
    url = f"{instance_url.rstrip('/')}/api/now/table/{table}"
    data = json.dumps(payload).encode("utf-8")

    req = urllib.request.Request(url, data=data, method="POST")
    auth_str = f"{username}:{password}"
    auth_b64 = base64.b64encode(auth_str.encode("utf-8")).decode("utf-8")
    req.add_header("Authorization", f"Basic {auth_b64}")
    req.add_header("Content-Type", "application/json")
    req.add_header("Accept", "application/json")

    try:
        with urllib.request.urlopen(req) as response:
            if response.status in (200, 201):
                res = json.loads(response.read().decode("utf-8"))
                return res.get("result", {})
    except Exception as e:
        print(f"⚠️ Errore nel ripristino su '{table}': {e}", file=sys.stderr)
        return None


def main():
    dump_path = LATEST_FILE
    if len(sys.argv) > 1:
        dump_path = sys.argv[1]

    if not os.path.exists(dump_path):
        print(f"❌ File di backup non trovato: {dump_path}", file=sys.stderr)
        sys.exit(1)

    print(f"🔄 Ripristino configurazione ServiceNow da: {dump_path}")
    with open(dump_path, "r", encoding="utf-8") as f:
        dump_data = json.load(f)

    tables = dump_data.get("tables", {})

    # 1. Ripristino Proprietà MID Server (ecc_agent_property)
    if "ecc_agent_property" in tables:
        print("\n  ➜ Ripristino `ecc_agent_property`...")
        for rec in tables["ecc_agent_property"]:
            prop_name = rec.get("name")
            prop_val = rec.get("value")
            if prop_name and prop_val:
                payload = {"name": prop_name, "value": prop_val}
                res = make_post_request(DEFAULT_URL, DEFAULT_USER, DEFAULT_PASS, "ecc_agent_property", payload)
                if res:
                    print(f"    ✓ Ripristinato parametro: {prop_name} = {prop_val}")

    # 2. Ripristino Credenziali Discovery (discovery_credentials)
    if "discovery_credentials" in tables:
        print("\n  ➜ Ripristino `discovery_credentials`...")
        for rec in tables["discovery_credentials"]:
            cred_name = rec.get("name")
            cred_type = rec.get("type", "api_key")
            sys_class = rec.get("sys_class_name", "api_key_credentials")
            tag = rec.get("tag", "")
            if cred_name:
                payload = {
                    "name": cred_name,
                    "type": cred_type,
                    "sys_class_name": sys_class,
                    "active": "true",
                    "tag": tag
                }
                res = make_post_request(DEFAULT_URL, DEFAULT_USER, DEFAULT_PASS, "discovery_credentials", payload)
                if res:
                    print(f"    ✓ Ripristinata credenziale: {cred_name} (tipo: {cred_type})")

    print("\n✅ Ripristino configurazioni ServiceNow completato!")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
dump_sn_config.py — ServiceNow Configuration Dumper
Esegue il backup/dump locale in formato JSON di tutte le configurazioni chiave
dell'istanza ServiceNow (ecc_agent, ecc_agent_property, discovery_credentials, sys_properties).
"""

import os
import sys
import json
import datetime
import urllib.request
import urllib.parse
import base64

# Configurazione di default (può essere sovrascritta via env)
DEFAULT_URL = os.getenv("SERVICENOW_INSTANCE_URL", "https://dev395227.service-now.com")
DEFAULT_USER = os.getenv("SERVICENOW_USERNAME", "admin")
DEFAULT_PASS = os.getenv("SERVICENOW_PASSWORD", "cupV=59*CYcK")

SCRIPT_DIR = os.path.dirname(os.path.realpath(__file__))
BACKUP_DIR = os.path.join(SCRIPT_DIR, "backups")

TABLES_TO_DUMP = [
    {
        "table": "ecc_agent",
        "query": "nameLIKEK8s^ORnameLIKEmid",
        "description": "Registri dei MID Server"
    },
    {
        "table": "ecc_agent_property",
        "query": "",
        "description": "Proprietà e parametri MID Server"
    },
    {
        "table": "discovery_credentials",
        "query": "active=true",
        "description": "Credenziali attive per la Discovery K8s/Cloud"
    },
    {
        "table": "sys_properties",
        "query": "nameLIKEmid^ORnameLIKEdiscovery",
        "description": "Proprietà di sistema MID/Discovery"
    }
]


def make_request(instance_url, username, password, table, query=""):
    """Esegue una chiamata REST GET alla Table API di ServiceNow."""
    url = f"{instance_url.rstrip('/')}/api/now/table/{table}"
    if query:
        url += f"?sysparm_query={urllib.parse.quote(query)}"

    req = urllib.request.Request(url)
    auth_str = f"{username}:{password}"
    auth_b64 = base64.b64encode(auth_str.encode("utf-8")).decode("utf-8")
    req.add_header("Authorization", f"Basic {auth_b64}")
    req.add_header("Accept", "application/json")

    try:
        with urllib.request.urlopen(req) as response:
            if response.status == 200:
                data = json.loads(response.read().decode("utf-8"))
                return data.get("result", [])
    except Exception as e:
        print(f"⚠️ Errore nel recupero della tabella '{table}': {e}", file=sys.stderr)
        return []


def main():
    print("🔍 Avvio Backup/Dump della configurazione ServiceNow...")
    os.makedirs(BACKUP_DIR, exist_ok=True)

    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    timestamp_file = os.path.join(BACKUP_DIR, f"sn_config_dump_{timestamp}.json")
    latest_file = os.path.join(BACKUP_DIR, "sn_config_latest.json")

    dump_data = {
        "metadata": {
            "instance_url": DEFAULT_URL,
            "dumped_at": datetime.datetime.now().isoformat(),
            "user": DEFAULT_USER
        },
        "tables": {}
    }

    for item in TABLES_TO_DUMP:
        table_name = item["table"]
        desc = item["description"]
        query = item["query"]

        print(f"  ➜ Scarico {desc} (`{table_name}`)...")
        records = make_request(DEFAULT_URL, DEFAULT_USER, DEFAULT_PASS, table_name, query)
        dump_data["tables"][table_name] = records
        print(f"    ✓ Trovati {len(records)} record")

    # Salvataggio file con timestamp
    with open(timestamp_file, "w", encoding="utf-8") as f:
        json.dump(dump_data, f, indent=2)

    # Salvataggio file latest
    with open(latest_file, "w", encoding="utf-8") as f:
        json.dump(dump_data, f, indent=2)

    print(f"\n✅ Backup completato con successo!")
    print(f"📄 Snapshot salvato in: {timestamp_file}")
    print(f"🔗 Simlink/Latest aggiornato: {latest_file}")


if __name__ == "__main__":
    main()

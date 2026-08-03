#!/usr/bin/env python3
"""
dump_sn_xml.py — ServiceNow Native XML Backup
Scarica in una sola chiamata l'XML nativo completo di tutte le configurazioni e modifiche dall'endpoint ufficiale ServiceNow.
I file vengono organizzati in sotto-cartelle con data/ora formattata sotto `sn/backup/<YYYY-MM-DD_HH-MM-SS>/`
senza prefissi di data/ora nel nome dei file. Viene mantenuta anche la cartella `sn/backup/latest/`.
"""

import os
import sys
import datetime
import urllib.request
import base64

INSTANCE_URL = os.getenv("SERVICENOW_INSTANCE_URL")
USERNAME = os.getenv("SERVICENOW_USERNAME")
PASSWORD = os.getenv("SERVICENOW_INSTANCE_PASSWORD")

if not INSTANCE_URL or not USERNAME or not PASSWORD:
    print(
        "❌ Errore: Variabili d'ambiente ServiceNow mancanti!\n"
        "Assicurati di aver definito SERVICENOW_INSTANCE_URL, SERVICENOW_USERNAME e SERVICENOW_INSTANCE_PASSWORD nello shell.",
        file=sys.stderr,
    )
    sys.exit(1)


SCRIPT_DIR = os.path.dirname(os.path.realpath(__file__))
REPO_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, "..", ".."))
BACKUP_BASE_DIR = os.path.join(REPO_ROOT, "sn", "backup")

ENDPOINTS_TO_BACKUP = [
    {
        "filename": "customer_updates_full.xml",
        "endpoint": "sys_update_xml_list.do?UNLOAD",
        "description": "Registro completo delle modifiche e configurazioni utente (sys_update_xml)"
    },
    {
        "filename": "discovery_credentials_full.xml",
        "endpoint": "discovery_credentials_list.do?UNLOAD",
        "description": "Credenziali attive per la Discovery K8s"
    },
    {
        "filename": "mid_properties_full.xml",
        "endpoint": "ecc_agent_property_list.do?UNLOAD",
        "description": "Proprietà e parametri MID Server"
    }
]


def download_single_xml(instance_url, username, password, endpoint, output_path):
    """Scarica il file XML nativo in un'unica chiamata HTTP GET."""
    url = f"{instance_url.rstrip('/')}/{endpoint}"
    req = urllib.request.Request(url)

    auth_str = f"{username}:{password}"
    auth_b64 = base64.b64encode(auth_str.encode("utf-8")).decode("utf-8")
    req.add_header("Authorization", f"Basic {auth_b64}")
    req.add_header("Accept", "application/xml")

    try:
        with urllib.request.urlopen(req) as response:
            if response.status == 200:
                content = response.read()
                with open(output_path, "wb") as f:
                    f.write(content)
                return len(content)
    except Exception as e:
        print(f"⚠️ Errore durante il download da '{endpoint}': {e}", file=sys.stderr)
        return 0


def main():
    print("📦 Avvio Backup XML Semplificato ServiceNow...")

    # Formattazione data e ora pretty-printed per la cartella
    now = datetime.datetime.now()
    folder_timestamp = now.strftime("%Y-%m-%d_%H-%M-%S")

    run_dir = os.path.join(BACKUP_BASE_DIR, folder_timestamp)
    latest_dir = os.path.join(BACKUP_BASE_DIR, "latest")

    os.makedirs(run_dir, exist_ok=True)
    os.makedirs(latest_dir, exist_ok=True)

    print(f"📂 Cartella destinazione backup: {run_dir}")

    for item in ENDPOINTS_TO_BACKUP:
        filename = item["filename"]
        endpoint = item["endpoint"]
        desc = item["description"]

        path_timestamp = os.path.join(run_dir, filename)
        path_latest = os.path.join(latest_dir, filename)

        print(f"  ➜ Scarico {desc} (`{endpoint}`)...")
        size = download_single_xml(INSTANCE_URL, USERNAME, PASSWORD, endpoint, path_timestamp)

        if size > 0:
            # Copia/scarica anche nella cartella latest
            download_single_xml(INSTANCE_URL, USERNAME, PASSWORD, endpoint, path_latest)
            print(f"    ✓ {filename} ({size} bytes)")

    print(f"\n✅ Backup XML completato con successo!")
    print(f"📁 Cartella Datata: {run_dir}")
    print(f"📁 Cartella Latest: {latest_dir}")


if __name__ == "__main__":
    main()

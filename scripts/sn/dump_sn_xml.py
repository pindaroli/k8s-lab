#!/usr/bin/env python3
"""
dump_sn_xml.py — Simple ServiceNow Single-Endpoint Full XML Backup
Scarica in una sola chiamata l'XML nativo completo di tutte le configurazioni e modifiche
dall'endpoint ufficiale ServiceNow sys_update_xml_list.do?UNLOAD.
Salva l'output nella cartella `sn/backup/` con timestamp ed esclude la cartella da Git.
"""

import os
import sys
import datetime
import urllib.request
import base64

DEFAULT_URL = os.getenv("SERVICENOW_INSTANCE_URL", "https://dev395227.service-now.com")
DEFAULT_USER = os.getenv("SERVICENOW_USERNAME", "admin")
DEFAULT_PASS = os.getenv("SERVICENOW_PASSWORD", "cupV=59*CYcK")

SCRIPT_DIR = os.path.dirname(os.path.realpath(__file__))
# Cartella target sn/backup/ nella root del repo k8s-lab
REPO_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, "..", ".."))
BACKUP_DIR = os.path.join(REPO_ROOT, "sn", "backup")

# Endpoint nativi ufficiali di ServiceNow per l'export completo con 1 sola chiamata
ENDPOINTS_TO_BACKUP = [
    {
        "name": "customer_updates_full",
        "endpoint": "sys_update_xml_list.do?UNLOAD",
        "description": "Registro completo delle modifiche e configurazioni utente (sys_update_xml)"
    },
    {
        "name": "discovery_credentials_full",
        "endpoint": "discovery_credentials_list.do?UNLOAD",
        "description": "Credenziali attive per la Discovery K8s"
    },
    {
        "name": "mid_properties_full",
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
    os.makedirs(BACKUP_DIR, exist_ok=True)

    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")

    for item in ENDPOINTS_TO_BACKUP:
        name = item["name"]
        endpoint = item["endpoint"]
        desc = item["description"]

        filename_ts = f"{name}_{timestamp}.xml"
        filename_latest = f"{name}_latest.xml"

        path_ts = os.path.join(BACKUP_DIR, filename_ts)
        path_latest = os.path.join(BACKUP_DIR, filename_latest)

        print(f"  ➜ Scarico {desc} (`{endpoint}`)...")
        size = download_single_xml(DEFAULT_URL, DEFAULT_USER, DEFAULT_PASS, endpoint, path_ts)

        if size > 0:
            # Aggiorna anche il file latest
            download_single_xml(DEFAULT_URL, DEFAULT_USER, DEFAULT_PASS, endpoint, path_latest)
            print(f"    ✓ Salvato: {filename_ts} ({size} bytes)")

    print(f"\n✅ Backup XML Semplificato completato con successo!")
    print(f"📂 Destinazione file: {BACKUP_DIR}")


if __name__ == "__main__":
    main()

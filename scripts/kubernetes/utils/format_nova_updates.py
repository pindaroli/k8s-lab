#!/usr/bin/env python3
"""
Utility script per la formattazione tabulare dell'output di Fairwinds Nova (JSON).
Invocato da check_nova_updates.sh.
"""

import sys
import json
import argparse


def format_containers():
    raw = sys.stdin.read()
    if not raw.strip():
        print("Nessun dato restituito da Nova per le immagini container.")
        return

    try:
        data = json.loads(raw)
        images = data.get("container_images", [])

        header_img = "IMMAGINE"
        header_curr = "VERSIONE IN PRODUZIONE"
        header_latest = "VERSIONE STABILE DISPONIBILE NEI REGISTRI"

        print(f"{header_img:<55} | {header_curr:<24} | {header_latest:<40}")
        print("-" * 125)

        if not images:
            print("Nessuna immagine container trovata.")
        else:
            for img in images:
                name = img.get("name", "N/A")
                current = img.get("current_version", "N/A")
                latest = img.get("latest_version", "N/A")
                outdated = img.get("outdated", False)

                status_flag = " ⚠️ (Aggiornamento disponibile)" if outdated else ""
                print(f"{name:<55} | {current:<24} | {latest:<40}{status_flag}")
    except Exception as e:
        print(f"Errore nell'elaborazione dei dati delle immagini: {e}")


def format_helm():
    raw = sys.stdin.read()
    if not raw.strip():
        print("Nessun dato restituito da Nova per le release Helm.")
        return

    try:
        releases = json.loads(raw)

        header_chart = "RELEASE / CHART"
        header_curr = "VERSIONE IN PRODUZIONE"
        header_latest = "VERSIONE STABILE DISPONIBILE NEI REGISTRI"

        print(f"{header_chart:<55} | {header_curr:<24} | {header_latest:<40}")
        print("-" * 125)

        if not releases:
            print("Nessuna release Helm trovata.")
        else:
            for r in releases:
                rel = r.get("release", "")
                chart = r.get("chartName", "")
                disp_name = f"{rel} ({chart})" if chart and chart != rel else rel

                installed_info = r.get("Installed", {})
                latest_info = r.get("Latest", {})

                installed = installed_info.get("version", "N/A") if isinstance(installed_info, dict) else "N/A"
                latest = latest_info.get("version", "N/A") if isinstance(latest_info, dict) else "N/A"
                outdated = r.get("outdated", False)

                status_flag = " ⚠️ (Aggiornamento disponibile)" if outdated else ""
                print(f"{disp_name:<55} | {installed:<24} | {latest:<40}{status_flag}")
    except Exception as e:
        print(f"Errore nell'elaborazione dei dati delle release Helm: {e}")


def main():
    parser = argparse.ArgumentParser(description="Formattatore tabella per Nova")
    parser.add_argument("mode", choices=["containers", "helm"], help="Tipo di report da formattare")
    args = parser.parse_args()

    if args.mode == "containers":
        format_containers()
    elif args.mode == "helm":
        format_helm()


if __name__ == "__main__":
    main()

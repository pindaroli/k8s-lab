#!/usr/bin/env python3
"""
Prowlarr Indexer Loader for TrueNAS Failover Stack.
Imports indexers from indexerrs_dump.json (or indexers_dump.json) into Prowlarr via REST API.
"""
import os
import sys
import time
import json
import urllib.request
import urllib.error
import urllib.parse
import xml.etree.ElementTree as ET

PROWLARR_URL = os.getenv("PROWLARR_URL", "http://prowlarr:9696")
CONFIG_XML = os.getenv("CONFIG_XML", "/config/config.xml")
DUMP_FILES = [
    os.getenv("DUMP_FILE", ""),
    "/backup/indexerrs_dump.json",
    "/backup/indexers_dump.json",
    "/mnt/stripe/k8s-arr/servarr-prowlarr/indexerrs_dump.json",
    "/mnt/stripe/k8s-arr/servarr-prowlarr/indexers_dump.json",
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "indexers_dump.json"),
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "indexerrs_dump.json")
]

def get_api_key():
    key = os.getenv("PROWLARR_API_KEY")
    if key:
        return key
    config_paths = [
        CONFIG_XML,
        "/config/config.xml",
        "/mnt/stripe/k8s-arr/servarr-prowlarr/sqlite/config.xml",
        "/mnt/stripe/k8s-arr/servarr-prowlarr/config.xml"
    ]
    for cp in config_paths:
        if os.path.isfile(cp):
            try:
                tree = ET.parse(cp)
                api_elem = tree.find("ApiKey")
                if api_elem is not None and api_elem.text:
                    return api_elem.text.strip()
            except Exception as e:
                print(f"[WARN] Errore lettura {cp}: {e}")
    # Fallback to standard lab production key
    return "fad287a6fe814e1b885f1ba0a8f95179"

def wait_for_prowlarr(url, api_key, timeout=60):
    print(f"[INIT] Attesa che Prowlarr a {url} sia online...")
    start = time.time()
    while time.time() - start < timeout:
        try:
            req = urllib.request.Request(f"{url}/api/v1/system/status", headers={"X-Api-Key": api_key})
            with urllib.request.urlopen(req, timeout=3) as resp:
                if resp.status == 200:
                    print("[INIT] Prowlarr ONLINE e pronto a ricevere richieste!")
                    return True
        except Exception:
            time.sleep(2)
    print("[ERROR] Timeout attesa avvio di Prowlarr.")
    return False

def main():
    api_key = get_api_key()
    if not api_key:
        print("[ERROR] Impossibile rilevare ApiKey di Prowlarr. Abort.")
        sys.exit(1)

    # Identificazione file dump
    dump_path = None
    for path in DUMP_FILES:
        if path and os.path.isfile(path):
            dump_path = path
            break

    if not dump_path:
        print("[WARN] Nessun file dump indexer trovato nei percorsi monitorati. Nessun import eseguito.")
        sys.exit(0)

    print(f"[INIT] Rilevato file dump indexer: {dump_path}")
    with open(dump_path, "r", encoding="utf-8") as f:
        dumped_indexers = json.load(f)

    if not wait_for_prowlarr(PROWLARR_URL, api_key):
        sys.exit(1)

    # Elenco indexer esistenti
    req = urllib.request.Request(f"{PROWLARR_URL}/api/v1/indexer", headers={"X-Api-Key": api_key})
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            existing = json.load(resp)
        existing_names = {idx.get("name") for idx in existing}
    except Exception as e:
        print(f"[WARN] Impossibile recuperare indexer esistenti: {e}")
        existing_names = set()

    # Rilevamento tag validi nel nuovo DB
    valid_tag_ids = set()
    try:
        req_tags = urllib.request.Request(f"{PROWLARR_URL}/api/v1/tag", headers={"X-Api-Key": api_key})
        with urllib.request.urlopen(req_tags, timeout=5) as resp:
            tags = json.load(resp)
            valid_tag_ids = {t.get("id") for t in tags}
    except Exception:
        pass

    added_count = 0
    for idx in dumped_indexers:
        name = idx.get("name")
        if name in existing_names:
            print(f"[SKIP] Indexer '{name}' già presente nel database.")
            continue

        payload = dict(idx)
        payload["id"] = 0  # Cruciale per generare nuovo record
        if "tags" in payload:
            payload["tags"] = [t for t in payload["tags"] if t in valid_tag_ids]

        data = json.dumps(payload).encode("utf-8")
        post_req = urllib.request.Request(
            f"{PROWLARR_URL}/api/v1/indexer",
            data=data,
            headers={"X-Api-Key": api_key, "Content-Type": "application/json"},
            method="POST"
        )
        try:
            with urllib.request.urlopen(post_req, timeout=10) as post_resp:
                if post_resp.status in (200, 201):
                    print(f"[OK] Aggiunto indexer '{name}'.")
                    added_count += 1
        except urllib.error.HTTPError as e:
            err_body = e.read().decode("utf-8", errors="ignore")
            print(f"[FAIL] Errore aggiunta '{name}': HTTP {e.code} - {err_body}")
        except Exception as e:
            print(f"[FAIL] Errore timeout/connessione '{name}': {e}")

    print(f"[DONE] Importazione completata con successo: {added_count} indexer registrati su Prowlarr.")

if __name__ == "__main__":
    main()

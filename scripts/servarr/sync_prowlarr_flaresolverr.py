#!/usr/bin/env python3
"""
sync_prowlarr_flaresolverr.py
Sincronizzazione dichiarativa e idempotente di FlareSolverr e Indexer Tags in Prowlarr.
Adatto sia per esecuzione CLI standalone sia come sidecar/init container in Docker Compose.
Utilizza esclusivamente moduli della libreria standard di Python (zero dipendenze).
"""

import sys
import os
import json
import time
import argparse
import urllib.request
import urllib.error
import xml.etree.ElementTree as ET

def parse_api_key_from_xml(xml_path):
    if not os.path.isfile(xml_path):
        raise FileNotFoundError(f"File XML di configurazione non trovato: {xml_path}")
    tree = ET.parse(xml_path)
    root = tree.getroot()
    api_key_elem = root.find("ApiKey")
    if api_key_elem is None or not api_key_elem.text:
        raise ValueError(f"Tag <ApiKey> mancante o vuoto in {xml_path}")
    return api_key_elem.text.strip()

def api_request(base_url, api_key, path, method="GET", payload=None):
    url = f"{base_url.rstrip('/')}{path}"
    headers = {
        "X-Api-Key": api_key,
        "Accept": "application/json",
        "Content-Type": "application/json"
    }
    data = json.dumps(payload).encode("utf-8") if payload is not None else None
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=35) as resp:
            resp_body = resp.read().decode("utf-8")
            return json.loads(resp_body) if resp_body else {}
    except urllib.error.HTTPError as e:
        err_msg = e.read().decode("utf-8")
        raise RuntimeError(f"HTTP {e.code} su {path}: {err_msg}")
    except urllib.error.URLError as e:
        raise RuntimeError(f"Errore di connessione su {path}: {e.reason}")

def wait_for_prowlarr(base_url, api_key, max_attempts=30, delay=2):
    print(f"⏳ In attesa della disponibilità di Prowlarr su {base_url}...")
    for attempt in range(1, max_attempts + 1):
        try:
            api_request(base_url, api_key, "/api/v1/system/status")
            print(f"✅ Prowlarr è pronto e risponde correttamente (tentativo {attempt})!")
            return True
        except Exception as e:
            if attempt == max_attempts:
                raise RuntimeError(f"Timeout in attesa di Prowlarr dopo {max_attempts*delay}s: {e}")
            time.sleep(delay)

def sync_prowlarr(base_url, api_key, config):
    wait_for_prowlarr(base_url, api_key)

    # 1. Riconciliazione Tag
    tag_name = config.get("tag", "flaresolverr")
    existing_tags = api_request(base_url, api_key, "/api/v1/tag")
    tag_id = None
    for t in existing_tags:
        if t.get("label", "").lower() == tag_name.lower():
            tag_id = t["id"]
            print(f"✅ Tag '{tag_name}' già esistente (ID: {tag_id})")
            break

    if tag_id is None:
        print(f"➕ Creazione Tag '{tag_name}'...")
        new_tag = api_request(base_url, api_key, "/api/v1/tag", method="POST", payload={"label": tag_name})
        tag_id = new_tag["id"]
        print(f"✅ Tag '{tag_name}' creato con successo (ID: {tag_id})")

    # 2. Riconciliazione Indexer Proxy FlareSolverr
    proxy_name = config.get("proxy_name", "FlareSolverr")
    proxy_host = config.get("proxy_host", "http://flaresolverr:8191")
    request_timeout = config.get("request_timeout", 60)

    existing_proxies = api_request(base_url, api_key, "/api/v1/indexerproxy")
    proxy_obj = None
    for p in existing_proxies:
        if p.get("name", "").lower() == proxy_name.lower():
            proxy_obj = p
            break

    proxy_payload = {
        "name": proxy_name,
        "implementationName": "FlareSolverr",
        "implementation": "FlareSolverr",
        "configContract": "FlareSolverrSettings",
        "tags": [tag_id],
        "fields": [
            {"name": "host", "value": proxy_host},
            {"name": "requestTimeout", "value": request_timeout}
        ]
    }

    if proxy_obj is None:
        print(f"➕ Creazione Indexer Proxy '{proxy_name}' ({proxy_host}) associato a Tag ID [{tag_id}]...")
        created_proxy = api_request(base_url, api_key, "/api/v1/indexerproxy", method="POST", payload=proxy_payload)
        print(f"✅ Indexer Proxy '{proxy_name}' creato con successo (ID: {created_proxy.get('id')})")
    else:
        proxy_id = proxy_obj["id"]
        proxy_payload["id"] = proxy_id
        # Verifica se è necessario aggiornare
        current_tags = proxy_obj.get("tags", [])
        current_host = next((f["value"] for f in proxy_obj.get("fields", []) if f.get("name") == "host"), "")
        if tag_id in current_tags and current_host == proxy_host:
            print(f"✅ Indexer Proxy '{proxy_name}' è già allineato ({proxy_host}, tags={current_tags}).")
        else:
            print(f"🔄 Aggiornamento Indexer Proxy '{proxy_name}' (ID: {proxy_id})...")
            api_request(base_url, api_key, f"/api/v1/indexerproxy/{proxy_id}", method="PUT", payload=proxy_payload)
            print(f"✅ Indexer Proxy '{proxy_name}' aggiornato con successo.")

    # 3. Riconciliazione Tag sugli Indexer target
    target_indexers = config.get("target_indexers", ["FileMood"])
    all_indexers = api_request(base_url, api_key, "/api/v1/indexer")

    for idx_name in target_indexers:
        target_obj = None
        for idx in all_indexers:
            if idx.get("name", "").lower() == idx_name.lower():
                target_obj = idx
                break

        if not target_obj:
            print(f"⚠️ Indexer '{idx_name}' non trovato tra gli indexer configurati in Prowlarr!")
            continue

        current_tags = target_obj.get("tags", [])
        if tag_id not in current_tags:
            print(f"🏷️ Associazione Tag '{tag_name}' all'indexer '{idx_name}' (ID: {target_obj['id']})...")
            target_obj["tags"] = list(set(current_tags + [tag_id]))
            api_request(base_url, api_key, f"/api/v1/indexer/{target_obj['id']}", method="PUT", payload=target_obj)
            print(f"✅ Indexer '{idx_name}' aggiornato con successo con Tag [{tag_id}].")
        else:
            print(f"✅ Indexer '{idx_name}' ha già il Tag '{tag_name}' associato.")

        # 4. Test di Verifica Indexer
        print(f"🧪 Esecuzione test di connettività per '{idx_name}' (Bypass Turnstile Cloudflare)...")
        try:
            api_request(base_url, api_key, "/api/v1/indexer/test", method="POST", payload=target_obj)
            print(f"🎉 TEST PASSATO per '{idx_name}'! FlareSolverr ha risolto la challenge.")
        except Exception as e:
            print(f"❌ Test indexer fallito per '{idx_name}': {e}")
            raise

def main():
    parser = argparse.ArgumentParser(description="Prowlarr FlareSolverr Declarative Sync")
    parser.add_argument("--url", default="http://10.10.20.50:9696", help="Prowlarr Base URL")
    parser.add_argument("--api-key", default=os.environ.get("PROWLARR_API_KEY", ""), help="Prowlarr API Key")
    parser.add_argument("--config-xml", default="", help="Path to Prowlarr config.xml to extract API key automatically")
    parser.add_argument("--proxy-host", default="http://flaresolverr:8191", help="FlareSolverr Host for Prowlarr")
    parser.add_argument("--tag", default="flaresolverr", help="Tag name to bind")
    parser.add_argument("--indexer", default="FileMood", help="Indexer to protect with FlareSolverr")
    args = parser.parse_args()

    api_key = args.api_key
    if not api_key and args.config_xml:
        try:
            api_key = parse_api_key_from_xml(args.config_xml)
            print(f"🔑 API Key estratta automaticamente da {args.config_xml}")
        except Exception as e:
            print(f"⚠️ Impossibile leggere API key da {args.config_xml}: {e}")

    if not api_key:
        api_key = "fad287a6fe814e1b885f1ba0a8f95179"

    config = {
        "tag": args.tag,
        "proxy_name": "FlareSolverr",
        "proxy_host": args.proxy_host,
        "request_timeout": 60,
        "target_indexers": [args.indexer]
    }

    try:
        sync_prowlarr(args.url, api_key, config)
        print("\n✨ Riconciliazione Prowlarr ↔ FlareSolverr completata con successo al 100%!")
    except Exception as e:
        print(f"\n💥 ERRORE durante la sincronizzazione: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()

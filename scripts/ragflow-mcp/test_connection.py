"""Diagnostic script to verify connectivity and retrieval against RAGFlow."""
import os
import sys
import json
import ssl
import urllib.request
import urllib.error

BASE_URL = os.environ.get("RAGFLOW_BASE_URL", "https://ragflow-internal.pindaroli.org").rstrip("/")
API_KEY = os.environ.get("RAGFLOW_API_KEY", "")
DATASET_NAME = os.environ.get("DEFAULT_DATASET", "k8s-lab")

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

headers = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json"
}

def check_ragflow():
    if not API_KEY:
        print("Error: RAGFLOW_API_KEY environment variable is not set.")
        sys.exit(1)
    print(f"Connecting to RAGFlow at {BASE_URL}...")
    req = urllib.request.Request(f"{BASE_URL}/api/v1/datasets?page=1&page_size=10", headers=headers)
    try:
        with urllib.request.urlopen(req, context=ctx, timeout=15) as resp:
            data = json.loads(resp.read().decode())
            datasets = data.get("data", [])
            print(f"Connection OK (HTTP {resp.status}) - Found {len(datasets)} dataset(s):")
            ds_id = None
            for ds in datasets:
                print(f" - {ds.get('name')} (id: {ds.get('id')}, docs: {ds.get('document_count')}, chunks: {ds.get('chunk_count')})")
                if ds.get('name') == DATASET_NAME:
                    ds_id = ds.get('id')

            if ds_id:
                print(f"\nListing documents in '{DATASET_NAME}' ({ds_id}):")
                doc_req = urllib.request.Request(f"{BASE_URL}/api/v1/datasets/{ds_id}/documents?page=1&page_size=10", headers=headers)
                with urllib.request.urlopen(doc_req, context=ctx, timeout=15) as doc_resp:
                    doc_data = json.loads(doc_resp.read().decode())
                    docs = doc_data.get("data", {}).get("docs", [])
                    for d in docs:
                        print(f"   * {d.get('name')} (status: {d.get('run')})")

    except urllib.error.HTTPError as he:
        print(f"HTTP Error {he.code}: {he.read().decode(errors='replace')}")
        sys.exit(1)
    except Exception as e:
        print(f"Connection error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    check_ragflow()

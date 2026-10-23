#!/usr/bin/env python3
# ==============================================================================
# FILE: scripts/network/switch_failover_dns.py
# DESCRIZIONE: Switchover atomico e idempotente degli Host Overrides Unbound
#              su OPNsense tra TrueNAS (10.10.20.50) e Mac Studio (10.10.20.100).
# ==============================================================================

import argparse
import base64
import json
import os
import re
import ssl
import subprocess
import sys
import urllib.error
import urllib.request

# Risoluzione dinamica della root del repository (conforme a go-launcher-script-pattern)
SCRIPT_DIR = os.path.dirname(os.path.realpath(__file__))
ROOT_DIR = os.path.abspath(os.path.join(SCRIPT_DIR, "..", ".."))
os.chdir(ROOT_DIR)

OPNSENSE_ENDPOINTS = [
    "https://192.168.100.1",
    "https://192.168.2.254",
    "https://10.10.20.1",
]
DOMAIN = "pindaroli.org"

TARGETS = {
    "truenas": {
        "ip": "10.10.20.50",
        "label": "TrueNAS SCALE Bare-Metal (ECO/FULL Mode)",
    },
    "orbstack": {
        "ip": "10.10.20.100",
        "label": "Mac Studio OrbStack Failover (RACK DARK / OFF Mode)",
    },
}

FAILOVER_HOSTS = [
    ("mcp", "MCP Fleet Traefik Umbrella Gateway (:8100)"),
    ("hermes", "Hermes Agent AI Gateway & Dashboard (:9119)"),
    ("litellm", "LiteLLM Inference Proxy & UI (:4000)"),
    ("dozzle", "Dozzle Docker Log Viewer (:8888)"),
]


def load_opnsense_credentials() -> tuple[str, str]:
    """Carica opnsense_api_key e opnsense_api_secret da env, ansible/vars o SOPS."""
    key = os.environ.get("OPNSENSE_API_KEY", "").strip()
    secret = os.environ.get("OPNSENSE_API_SECRET", "").strip()
    if key and secret:
        return key, secret

    candidates = [
        os.path.join(ROOT_DIR, "secrets-sops", "opnsense-mcp-credentials.enc.yaml"),
        os.path.join(ROOT_DIR, "secrets-sops", "opnsense-secrets.enc.yaml"),
        os.path.join(ROOT_DIR, "ansible", "vars", "opnsense_secrets.yml"),
        os.path.join(ROOT_DIR, "ansible", "vars", "common_secrets.yml"),
    ]
    vault_pass = os.path.expanduser("~/.vault_pass.txt")

    for path in candidates:
        if not os.path.exists(path):
            continue
        try:
            with open(path, "r", encoding="utf-8") as fh:
                raw = fh.read()
            if "sops:" in raw or path.endswith(".enc.yaml"):
                proc = subprocess.run(
                    ["sops", "-d", path],
                    capture_output=True,
                    text=True,
                    check=True,
                )
                raw = proc.stdout
            elif raw.startswith("$ANSIBLE_VAULT"):
                cmd = ["ansible-vault", "view"]
                if os.path.exists(vault_pass):
                    cmd.extend(["--vault-password-file", vault_pass])
                cmd.append(path)
                proc = subprocess.run(cmd, capture_output=True, text=True, check=True)
                raw = proc.stdout

            k_match = re.search(r"opnsense_api_key\s*:\s*['\"]?([^'\"\s#]+)", raw, re.IGNORECASE)
            s_match = re.search(r"opnsense_api_secret\s*:\s*['\"]?([^'\"\s#]+)", raw, re.IGNORECASE)
            if k_match and s_match:
                return k_match.group(1), s_match.group(1)
        except Exception:
            continue

    raise RuntimeError(
        "Impossibile caricare opnsense_api_key e opnsense_api_secret da env, secrets-sops o ansible/vars"
    )


class OPNsenseUnboundClient:
    def __init__(self, api_key: str, api_secret: str):
        self.auth_header = "Basic " + base64.b64encode(
            f"{api_key}:{api_secret}".encode("utf-8")
        ).decode("ascii")
        self.ctx = ssl.create_default_context()
        self.ctx.check_hostname = False
        self.ctx.verify_mode = ssl.CERT_NONE
        self.base_url = self._select_reachable_endpoint()

    def _select_reachable_endpoint(self) -> str:
        for url in OPNSENSE_ENDPOINTS:
            try:
                req = urllib.request.Request(
                    f"{url}/api/unbound/settings/searchHostOverride",
                    data=b'{"current":1,"rowCount":1,"searchPhrase":""}',
                    headers={
                        "Authorization": self.auth_header,
                        "Content-Type": "application/json",
                    },
                    method="POST",
                )
                with urllib.request.urlopen(req, context=self.ctx, timeout=4) as resp:
                    if resp.status == 200:
                        return url
            except Exception:
                continue
        raise RuntimeError(
            f"Nessun endpoint OPNsense raggiungibile tra: {', '.join(OPNSENSE_ENDPOINTS)}"
        )

    def request(self, path: str, payload: dict | None = None) -> dict:
        url = f"{self.base_url}{path}"
        data = json.dumps(payload).encode("utf-8") if payload is not None else b""
        headers = {"Authorization": self.auth_header}
        if payload is not None:
            headers["Content-Type"] = "application/json"
        req = urllib.request.Request(url, data=data, headers=headers, method="POST")
        with urllib.request.urlopen(req, context=self.ctx, timeout=10) as resp:
            body = resp.read().decode("utf-8")
            return json.loads(body) if body else {}

    def list_overrides(self) -> list[dict]:
        res = self.request(
            "/api/unbound/settings/searchHostOverride",
            {"current": 1, "rowCount": 2000, "searchPhrase": ""},
        )
        return res.get("rows", [])


def flush_local_dns_cache() -> None:
    """Svuota la cache DNS di macOS per azzerare il TTL sui client locali."""
    if sys.platform != "darwin":
        return
    subprocess.run(["dscacheutil", "-flushcache"], check=False)
    subprocess.run(["sudo", "-n", "killall", "-HUP", "mDNSResponder"], check=False)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Switchover atomico DNS Unbound OPNsense per Failover TrueNAS <-> OrbStack"
    )
    parser.add_argument(
        "--target",
        required=True,
        choices=["truenas", "orbstack"],
        help="Destinazione dei record DNS: 'truenas' (10.10.20.50) o 'orbstack' (10.10.20.100)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Mostra le modifiche previste senza applicarle su OPNsense",
    )
    args = parser.parse_args()

    target_cfg = TARGETS[args.target]
    target_ip = target_cfg["ip"]

    api_key, api_secret = load_opnsense_credentials()
    client = OPNsenseUnboundClient(api_key, api_secret)

    print(f"🌐 [DNS Switchover] Connesso a OPNsense ({client.base_url})")
    print(f"🎯 Target richiesto: {args.target.upper()} -> {target_ip} ({target_cfg['label']})")

    rows = client.list_overrides()
    changed = False

    for hostname, desc_prefix in FAILOVER_HOSTS:
        full_desc = f"{desc_prefix} [Managed Failover -> {args.target}]"
        matches = [
            r
            for r in rows
            if r.get("hostname", "").lower() == hostname.lower()
            and r.get("domain", "").lower() == DOMAIN.lower()
        ]

        if not matches:
            print(f"➕ Creazione Host Override: {hostname}.{DOMAIN} -> {target_ip}")
            if not args.dry_run:
                res = client.request(
                    "/api/unbound/settings/addHostOverride",
                    {
                        "host": {
                            "enabled": "1",
                            "hostname": hostname,
                            "domain": DOMAIN,
                            "rr": "A",
                            "server": target_ip,
                            "description": full_desc,
                        }
                    },
                )
                if res.get("result") != "saved":
                    raise RuntimeError(f"Errore creazione {hostname}.{DOMAIN}: {res}")
            changed = True
        else:
            primary = matches[0]
            uuid = primary["uuid"]
            current_ip = primary.get("server", "")
            enabled = str(primary.get("enabled", "1"))

            if current_ip == target_ip and enabled == "1":
                print(f"✅ [IDEMPOTENT] {hostname}.{DOMAIN} punta già a {target_ip} (UUID: {uuid})")
            else:
                print(f"🔄 Aggiornamento {hostname}.{DOMAIN}: {current_ip} -> {target_ip} (UUID: {uuid})")
                if not args.dry_run:
                    res = client.request(
                        f"/api/unbound/settings/setHostOverride/{uuid}",
                        {
                            "host": {
                                "enabled": "1",
                                "hostname": hostname,
                                "domain": DOMAIN,
                                "rr": "A",
                                "server": target_ip,
                                "description": full_desc,
                            }
                        },
                    )
                    if res.get("result") != "saved":
                        raise RuntimeError(f"Errore aggiornamento {hostname}.{DOMAIN}: {res}")
                changed = True

            # Pulizia eventuali duplicati spuri creati in precedenza
            for dup in matches[1:]:
                dup_uuid = dup["uuid"]
                print(f"🧹 Rimozione Host Override duplicato per {hostname}.{DOMAIN} (UUID: {dup_uuid})")
                if not args.dry_run:
                    client.request(f"/api/unbound/settings/delHostOverride/{dup_uuid}", {})
                changed = True

    if changed and not args.dry_run:
        print("⚙️  Applicazione riconfigurazione dinamica Unbound (/api/unbound/service/reconfigure)...")
        reconf = client.request("/api/unbound/service/reconfigure", {})
        status = reconf.get("status", "").strip().lower()
        if status != "ok":
            raise RuntimeError(f"Riconfigurazione Unbound fallita: {reconf}")
        flush_local_dns_cache()
        print("✅ Unbound riconfigurato con successo e cache DNS macOS invalidata.")
    elif not changed:
        print("ℹ️  Nessuna modifica DNS necessaria: Unbound è già allineato.")

    return 0


if __name__ == "__main__":
    sys.exit(main())

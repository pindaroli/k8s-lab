#!/usr/bin/env bash
# Controllo aggiornamenti versioni container Docker su TrueNAS tramite API OCI V2

set -euo pipefail

export PATH="/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:$PATH"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PYTHON_SCRIPT="$SCRIPT_DIR/utils/check_docker_registry_updates.py"
TRUENAS_HOST="${TRUENAS_HOST:-10.10.20.50}"
TRUENAS_USER="${TRUENAS_USER:-olindo}"

MODE="running"
JSON_FLAG=""

show_help() {
    cat <<EOF
Uso: $(basename "$0") [OPZIONI]

Controlla gli aggiornamenti disponibili nei registri OCI V2 (Docker Hub, GHCR,
LinuxServer.io, Quay) per i container Docker su TrueNAS SCALE ($TRUENAS_HOST).

Opzioni:
  (nessuna)     Analizza i container attualmente in esecuzione (docker ps)
  --compose     Analizza i servizi dichiarati nei file docker-compose.yaml su TrueNAS
  --all         Combina i container in esecuzione e quelli dichiarati nei compose
  --json        Restituisce l'output in formato JSON anziché tabulare
  -h, --help    Mostra questo messaggio di aiuto ed esce
EOF
}

for arg in "$@"; do
    case "$arg" in
        --compose)
            MODE="compose"
            ;;
        --all)
            MODE="all"
            ;;
        --json)
            JSON_FLAG="--json"
            ;;
        -h|--help)
            show_help
            exit 0
            ;;
        *)
            echo "Errore: Opzione non riconosciuta '$arg'" >&2
            show_help >&2
            exit 1
            ;;
    esac
done

if [ ! -f "$PYTHON_SCRIPT" ]; then
    echo "Errore: Motore Python non trovato in $PYTHON_SCRIPT" >&2
    exit 1
fi

# 1. Verifica raggiungibilità host TrueNAS
if ! ping -c 1 -W 2 "$TRUENAS_HOST" >/dev/null 2>&1; then
    echo "Errore: TrueNAS ($TRUENAS_HOST) non raggiungibile via rete (ping fallito)." >&2
    exit 1
fi

# 2. Estrazione metadati container/compose da TrueNAS via SSH passwordless (100% read-only)
RAW_DATA="$(ssh -o BatchMode=yes -o ConnectTimeout=5 "${TRUENAS_USER}@${TRUENAS_HOST}" "python3 - '$MODE'" << 'EOF'
import sys
import json
import subprocess
import re
import os

mode = sys.argv[1] if len(sys.argv) > 1 else "running"
items = []
seen = set()

def get_repo_digests(image_name):
    try:
        out = subprocess.check_output(
            ["sudo", "-n", "docker", "image", "inspect", image_name, "--format", "{{json .RepoDigests}}"],
            stderr=subprocess.DEVNULL,
            text=True
        ).strip()
        return out
    except Exception:
        return ""

if mode in ("running", "all"):
    try:
        ps_out = subprocess.check_output(
            ["sudo", "-n", "docker", "ps", "--no-trunc", "--format", "{{json .}}"],
            text=True
        )
        for line in ps_out.splitlines():
            if not line.strip():
                continue
            obj = json.loads(line)
            name = obj.get("Names", "")
            img = obj.get("Image", "")
            img_id = obj.get("ID", "")
            digests = get_repo_digests(img)
            items.append({
                "Names": name,
                "Image": img,
                "ImageID": f"{img_id} {digests}"
            })
            seen.add(name)
    except Exception as e:
        sys.stderr.write(f"Errore esecuzione docker ps su TrueNAS: {e}\n")
        sys.exit(1)

if mode in ("compose", "all"):
    compose_files = [
        "/mnt/stripe/truenas-docker/docker-compose.yaml",
        "/mnt/stripe/truenas-docker/mcp/docker-compose.yaml"
    ]
    for cfile in compose_files:
        if not os.path.isfile(cfile):
            continue
        try:
            with open(cfile, "r", encoding="utf-8") as f:
                lines = f.readlines()
            current_service = None
            container_name = None
            image_val = None
            for line in lines:
                if line.strip().startswith("#"):
                    continue
                m_svc = re.match(r"^  ([a-zA-Z0-9_-]+):\s*$", line)
                if m_svc:
                    if current_service and image_val:
                        cname = container_name or current_service
                        if cname not in seen:
                            items.append({
                                "Names": cname,
                                "Image": image_val,
                                "ImageID": get_repo_digests(image_val)
                            })
                            seen.add(cname)
                    current_service = m_svc.group(1)
                    container_name = None
                    image_val = None
                    continue
                m_cname = re.match(r"^\s+container_name:\s*(.+?)\s*$", line)
                if m_cname:
                    container_name = m_cname.group(1).strip("'\"")
                m_img = re.match(r"^\s+image:\s*(.+?)\s*$", line)
                if m_img:
                    image_val = m_img.group(1).strip("'\"")
            if current_service and image_val:
                cname = container_name or current_service
                if cname not in seen:
                    items.append({
                        "Names": cname,
                        "Image": image_val,
                        "ImageID": get_repo_digests(image_val)
                    })
                    seen.add(cname)
        except Exception as e:
            sys.stderr.write(f"Warning lettura {cfile}: {e}\n")

print(json.dumps(items))
EOF
)" || {
    echo "Errore: Connessione SSH passwordless o estrazione dati Docker su TrueNAS ($TRUENAS_USER@$TRUENAS_HOST) fallita." >&2
    exit 1
}

if [ -n "$JSON_FLAG" ]; then
    printf "%s\n" "$RAW_DATA" | python3 "$PYTHON_SCRIPT" --json
else
    printf "%s\n" "$RAW_DATA" | python3 "$PYTHON_SCRIPT"
fi

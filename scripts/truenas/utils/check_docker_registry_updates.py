#!/usr/bin/env python3
"""
Motore OCI Distribution V2 per la verifica degli aggiornamenti delle immagini Docker su TrueNAS SCALE.
Interroga i registri OCI (Docker Hub, GHCR, LinuxServer.io, Quay) senza dipendenze esterne.
"""

import sys
import os
import re
import json
import ssl
import urllib.request
import urllib.error
from typing import Dict, List, Optional, Tuple, Any

# Setup SSL context standard
SSL_CTX = ssl.create_default_context()


def parse_image_ref(image_str: str) -> Dict[str, str]:
    """
    Scompone una stringa immagine (es. 'ghcr.io/org/repo:tag' o 'amir20/dozzle:v11.2.0')
    nei suoi componenti canonici.
    """
    tag = "latest"
    image_no_digest = image_str.split("@")[0]

    # Estrazione eventuale tag
    if ":" in image_no_digest:
        parts = image_no_digest.rsplit(":", 1)
        base = parts[0]
        tag = parts[1]
    else:
        base = image_no_digest

    # Determinazione del Registry Host e Repository Path
    segments = base.split("/")
    if "." in segments[0] or ":" in segments[0]:
        registry = segments[0]
        repo = "/".join(segments[1:])
    else:
        # Default Docker Hub
        registry = "registry-1.docker.io"
        if len(segments) == 1:
            repo = f"library/{segments[0]}"
        else:
            repo = "/".join(segments)

    return {
        "raw": image_str,
        "registry": registry,
        "repo": repo,
        "tag": tag,
        "is_local": base.startswith("local/") or registry in ("localhost", "local")
    }


def get_auth_token(registry: str, repo: str) -> Optional[str]:
    """
    Ottiene un token Bearer anonimo per il repository richiesto.
    """
    try:
        if registry == "registry-1.docker.io":
            auth_url = f"https://auth.docker.io/token?service=registry.docker.io&scope=repository:{repo}:pull"
        elif registry == "ghcr.io":
            auth_url = f"https://ghcr.io/token?service=ghcr.io&scope=repository:{repo}:pull"
        elif registry == "lscr.io":
            # lscr.io reindirizza l'autenticazione a GHCR
            auth_url = f"https://ghcr.io/token?service=ghcr.io&scope=repository:{repo}:pull"
        elif registry == "quay.io":
            auth_url = f"https://quay.io/v2/auth?service=quay.io&scope=repository:{repo}:pull"
        else:
            # Probe Www-Authenticate generico
            probe_url = f"https://{registry}/v2/"
            req = urllib.request.Request(probe_url, headers={"User-Agent": "Docker-Client/24.0.0"})
            try:
                urllib.request.urlopen(req, context=SSL_CTX, timeout=5)
                return None  # Nessuna autenticazione richiesta
            except urllib.error.HTTPError as e:
                auth_header = e.headers.get("Www-Authenticate", "")
                m_realm = re.search(r'realm="([^"]+)"', auth_header)
                m_service = re.search(r'service="([^"]+)"', auth_header)
                if not m_realm:
                    return None
                realm = m_realm.group(1)
                service = m_service.group(1) if m_service else registry
                auth_url = f"{realm}?service={service}&scope=repository:{repo}:pull"

        req = urllib.request.Request(auth_url, headers={"User-Agent": "Docker-Client/24.0.0"})
        with urllib.request.urlopen(req, context=SSL_CTX, timeout=7) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            return data.get("token") or data.get("access_token")
    except Exception:
        return None


def fetch_registry_tags(registry: str, repo: str, token: Optional[str]) -> List[str]:
    """
    Recupera l'elenco dei tag disponibili tramite API OCI Distribution V2.
    """
    # Mappatura host registry per API endpoint
    api_host = registry
    if registry == "lscr.io":
        api_host = "ghcr.io"

    url = f"https://{api_host}/v2/{repo}/tags/list"
    headers = {"User-Agent": "Docker-Client/24.0.0"}
    if token:
        headers["Authorization"] = f"Bearer {token}"

    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, context=SSL_CTX, timeout=10) as resp:
        data = json.loads(resp.read().decode("utf-8"))
        return data.get("tags", [])


def fetch_remote_digest(registry: str, repo: str, tag: str, token: Optional[str]) -> Optional[str]:
    """
    Recupera il Docker-Content-Digest remoto di un dato tag.
    """
    api_host = registry
    if registry == "lscr.io":
        api_host = "ghcr.io"

    url = f"https://{api_host}/v2/{repo}/manifests/{tag}"
    headers = {
        "User-Agent": "Docker-Client/24.0.0",
        "Accept": (
            "application/vnd.docker.distribution.manifest.v2+json, "
            "application/vnd.oci.image.index.v1+json, "
            "application/vnd.docker.distribution.manifest.list.v2+json"
        )
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"

    req = urllib.request.Request(url, headers=headers, method="HEAD")
    try:
        with urllib.request.urlopen(req, context=SSL_CTX, timeout=7) as resp:
            return resp.headers.get("Docker-Content-Digest")
    except Exception:
        return None


def parse_semver(tag: str) -> Optional[Tuple[int, int, int, int]]:
    """
    Estrae una tupla semantica numerica da un tag.
    Supporta formati 'v1.2.3', '1.2.3', '1.2' etc.
    """
    clean = tag.lstrip("v")
    m = re.match(r"^(\d+)(?:\.(\d+))?(?:\.(\d+))?(?:\.(\d+))?$", clean)
    if m:
        parts = [int(p) if p is not None else 0 for p in m.groups()]
        return tuple(parts)  # type: ignore
    return None


def is_prerelease(tag: str) -> bool:
    """Verifica se il tag contiene stringhe di prerelease o build transitorie."""
    pattern = r"(?i)(alpha|beta|rc|dev|nightly|test|pr-|\.b\d+|edge|debug|snapshot|testing)"
    return bool(re.search(pattern, tag))


def find_latest_tag(current_tag: str, all_tags: List[str]) -> Tuple[str, bool]:
    """
    Confronta il tag corrente con tutti i tag disponibili e determina
    se esiste una versione stabile più recente.
    Ritorna: (latest_tag_name, is_outdated)
    """
    if not all_tags:
        return (current_tag, False)

    # 1. Caso LinuxServer build (es. '12.0ubu2604-ls48' o '5.2.3_v2.0.13-ls468')
    ls_match = re.match(r"^(.+)-ls(\d+)$", current_tag)
    if ls_match:
        prefix_pattern = re.escape(ls_match.group(1))
        matching_ls_tags = []
        for t in all_tags:
            m = re.match(rf"^{prefix_pattern}-ls(\d+)$", t)
            if m:
                matching_ls_tags.append((int(m.group(1)), t))
        if matching_ls_tags:
            matching_ls_tags.sort(key=lambda x: x[0], reverse=True)
            highest_ls_build, highest_ls_tag = matching_ls_tags[0]
            current_build = int(ls_match.group(2))
            if highest_ls_build > current_build:
                return (highest_ls_tag, True)
            return (current_tag, False)

    # 2. Caso SemVer ordinario
    curr_v = parse_semver(current_tag)
    has_v_prefix = current_tag.startswith("v")

    valid_candidates = []
    for t in all_tags:
        if is_prerelease(t):
            continue
        # Se il tag corrente ha 'v', preferisci tag con 'v' (o viceversa) se coerenti
        if has_v_prefix and not t.startswith("v"):
            continue
        if not has_v_prefix and t.startswith("v"):
            continue

        parsed = parse_semver(t)
        if parsed:
            valid_candidates.append((parsed, t))

    if valid_candidates:
        valid_candidates.sort(key=lambda x: x[0], reverse=True)
        highest_parsed, highest_tag = valid_candidates[0]
        if curr_v:
            if highest_parsed > curr_v:
                return (highest_tag, True)
            return (current_tag, False)
        else:
            return (highest_tag, False)

    return (current_tag, False)


def check_container(item: Dict[str, Any]) -> Dict[str, Any]:
    """
    Esegue l'audit completo di un singolo container.
    """
    container_name = item.get("Names", "unknown")
    raw_image = item.get("Image", "")
    local_id = item.get("ImageID", "")

    parsed = parse_image_ref(raw_image)
    result = {
        "container": container_name,
        "image": raw_image,
        "current_version": parsed["tag"],
        "latest_version": parsed["tag"],
        "outdated": False,
        "status_note": "",
        "is_local": parsed["is_local"]
    }

    if parsed["is_local"]:
        result["latest_version"] = "[Locale / Build interna]"
        return result

    try:
        token = get_auth_token(parsed["registry"], parsed["repo"])

        # Gestione tag :latest tramite confronto digest
        if parsed["tag"] == "latest":
            remote_digest = fetch_remote_digest(parsed["registry"], parsed["repo"], "latest", token)
            short_local = local_id.replace("sha256:", "")[:12] if local_id else "locale"
            if remote_digest:
                short_remote = remote_digest.replace("sha256:", "")[:12]
                result["current_version"] = f"latest ({short_local})"
                result["latest_version"] = f"latest ({short_remote})"
                if short_local != "locale" and short_remote not in local_id:
                    result["outdated"] = True
                    result["status_note"] = " ⚠️ (Nuovo digest remoto)"
                else:
                    result["status_note"] = " ✓ (Aggiornato)"
            else:
                result["latest_version"] = "latest"
            return result

        # Gestione tag specifici di versione
        tags = fetch_registry_tags(parsed["registry"], parsed["repo"], token)
        latest_tag, outdated = find_latest_tag(parsed["tag"], tags)
        result["latest_version"] = latest_tag
        result["outdated"] = outdated
        if outdated:
            result["status_note"] = " ⚠️ (Aggiornamento disponibile)"
        else:
            result["status_note"] = " ✓ (Aggiornato)"

    except Exception as e:
        result["latest_version"] = f"[Verifica fallita: {str(e)[:30]}]"

    return result


def print_table(results: List[Dict[str, Any]]):
    """
    Formatta e stampa la tabella finale nello stile di Nova.
    """
    header_img = "CONTAINER / IMMAGINE"
    header_curr = "VERSIONE IN PRODUZIONE"
    header_latest = "VERSIONE STABILE NEI REGISTRI"

    print("====================================================================================================")
    print("📦 IMMAGINI CONTAINER (TRUENAS DOCKER)")
    print("====================================================================================================")
    print(f"{header_img:<55} | {header_curr:<24} | {header_latest:<40}")
    print("-" * 125)

    if not results:
        print("Nessun container o immagine trovata.")
        return

    for r in results:
        disp_name = f"{r['container']} ({r['image'].split(':')[0]})"
        if len(disp_name) > 54:
            disp_name = disp_name[:51] + "..."
        curr = str(r["current_version"])[:24]
        latest_str = str(r["latest_version"]) + r["status_note"]
        print(f"{disp_name:<55} | {curr:<24} | {latest_str}")


def main():
    raw_input = sys.stdin.read().strip()
    if not raw_input:
        print("Nessun dato JSON ricevuto da stdin.", file=sys.stderr)
        sys.exit(1)

    try:
        # Supporto a un array JSON completo o linee JSON separate
        if raw_input.startswith("["):
            items = json.loads(raw_input)
        else:
            items = []
            for line in raw_input.splitlines():
                if line.strip():
                    items.append(json.loads(line.strip()))
    except Exception as e:
        print(f"Errore nel parsing dell'input JSON: {e}", file=sys.stderr)
        sys.exit(1)

    results = []
    for item in items:
        res = check_container(item)
        results.append(res)

    if "--json" in sys.argv:
        print(json.dumps(results, indent=2))
    else:
        print_table(results)


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
import os
import re
import sys
import argparse
from pathlib import Path
from datetime import datetime

PROJECT_ROOT = Path(__file__).resolve().parent.parent
WIKI_DIR = PROJECT_ROOT / "wiki"
PLANS_DIR = WIKI_DIR / "plans"
INCIDENTS_DIR = WIKI_DIR / "incidents"

# Regular expressions for parsing
YAML_FRONTMATTER_RE = re.compile(r'^---\s*\n(.*?)\n---\s*\n', re.DOTALL)
H1_RE = re.compile(r'^#\s+(.+)$', re.M)

def parse_incident_info(path: Path, content: str) -> dict:
    """Deduce metadata from incident filename and content."""
    info = {
        "title": path.stem,
        "type": "incident",
        "status": "archived",
        "certified_for_ai": "false",
        "date": "",
        "severity": "P2",
        "resolved": "true",
        "resolved_at": "",
        "tags": []
    }

    # Date from filename (e.g., 2026-05-03-dnsbl-filtering-failure.md)
    date_match = re.match(r'^(\d{4}-\d{2}-\d{2})', path.name)
    if date_match:
        info["date"] = date_match.group(1)
        info["resolved_at"] = f"{date_match.group(1)}T23:59:59Z" # Fallback resolved_at

    # Title from H1
    h1_match = H1_RE.search(content)
    if h1_match:
        info["title"] = h1_match.group(1).strip().replace("Incident: ", "").replace("Incident Report: ", "")

    # Severity search
    severity_match = re.search(r'Severity:\s*(\w+)', content, re.IGNORECASE)
    if severity_match:
        sev = severity_match.group(1).upper()
        if sev in ["P1", "P2", "P3", "P4"]:
            info["severity"] = sev
        elif "HIGH" in sev:
            info["severity"] = "P1"
        elif "MEDIUM" in sev:
            info["severity"] = "P2"
        elif "LOW" in sev:
            info["severity"] = "P3"

    # Resolution status (active vs archived)
    # Check if resolved or ongoing
    status_match = re.search(r'Status:\s*(\w+)', content, re.IGNORECASE)
    if status_match:
        status_val = status_match.group(1).lower()
        if "ongoing" in status_val or "active" in status_val:
            info["status"] = "active"
            info["certified_for_ai"] = "true"
            info["resolved"] = "false"
            info["resolved_at"] = ""

    # Double check content for resolved status
    if "resolved" in content.lower() and "ongoing" not in content.lower():
        info["status"] = "archived"
        info["certified_for_ai"] = "false"
        info["resolved"] = "true"

    # Tag heuristics based on keywords
    tags = ["#incident"]
    lower_content = content.lower()
    if "dns" in lower_content: tags.append("#network")
    if "dhcp" in lower_content: tags.append("#network")
    if "database" in lower_content or "postgres" in lower_content or "cnpg" in lower_content: tags.append("#database")
    if "storage" in lower_content or "zfs" in lower_content or "pool" in lower_content: tags.append("#storage")
    if "pve" in lower_content or "proxmox" in lower_content: tags.append("#proxmox")
    if "talos" in lower_content: tags.append("#talos")
    if "opnsense" in lower_content: tags.append("#opnsense")
    info["tags"] = tags

    return info

def parse_plan_info(path: Path, content: str) -> dict:
    """Deduce metadata from plan filename and content."""
    info = {
        "title": path.stem,
        "type": "plan",
        "status": "draft",
        "certified_for_ai": "false",
        "created_at": "",
        "archived_at": "",
        "superseded_by": "",
        "tags": []
    }

    # Title from H1
    h1_match = H1_RE.search(content)
    if h1_match:
        info["title"] = h1_match.group(1).strip()

    # Date creation search (Data creazione: YYYY-MM-DD or similar)
    date_match = re.search(r'(?:Data creazione|Data|Created|Date):\s*(\d{4}-\d{2}-\d{2})', content, re.IGNORECASE)
    if date_match:
        info["created_at"] = date_match.group(1)
    else:
        info["created_at"] = datetime.now().strftime("%Y-%m-%d")

    # Status search
    status_match = re.search(r'Stato:\s*(.+)$', content, re.M | re.I)
    if status_match:
        status_text = status_match.group(1).lower()
        if any(w in status_text for w in ["concluso", "completato", "operativo", "✅"]):
            info["status"] = "archived"
            info["certified_for_ai"] = "false"
            info["archived_at"] = info["created_at"] # Fallback
        elif any(w in status_text for w in ["corso", "in corso", "esecuzione", "attivo"]):
            info["status"] = "active"
            info["certified_for_ai"] = "true"
        elif any(w in status_text for w in ["attesa", "approvazione", "bozza", "draft"]):
            info["status"] = "draft"
            info["certified_for_ai"] = "true" # Ready to review

    # Tags heuristics
    tags = ["#plan"]
    lower_content = content.lower()
    if "dns" in lower_content: tags.append("#network")
    if "dhcp" in lower_content: tags.append("#network")
    if "music" in lower_content or "beets" in lower_content: tags.append("#music")
    if "storage" in lower_content or "zfs" in lower_content or "vdev" in lower_content: tags.append("#storage")
    if "pve" in lower_content or "proxmox" in lower_content: tags.append("#proxmox")
    if "talos" in lower_content: tags.append("#talos")
    if "opnsense" in lower_content: tags.append("#opnsense")
    if "secrets" in lower_content or "sops" in lower_content: tags.append("#security")
    info["tags"] = tags

    return info

def generate_yaml_frontmatter(info: dict) -> str:
    """Generate YAML frontmatter block."""
    lines = ["---"]
    lines.append(f'title: "{info["title"]}"')
    lines.append(f'type: {info["type"]}')
    lines.append(f'status: {info["status"]}')
    lines.append(f'certified_for_ai: {info["certified_for_ai"]}')

    if info["type"] == "incident":
        lines.append(f'date: {info["date"]}')
        lines.append(f'severity: {info["severity"]}')
        lines.append(f'resolved: {info["resolved"]}')
        if info["resolved_at"]:
            lines.append(f'resolved_at: {info["resolved_at"]}')
        if info.get("post_mortem"):
            lines.append(f'post_mortem: {info["post_mortem"]}')
    elif info["type"] == "plan":
        lines.append(f'created_at: {info["created_at"]}')
        if info["status"] == "archived":
            lines.append(f'archived_at: {info.get("archived_at") or info["created_at"]}')
        if info.get("superseded_by"):
            lines.append(f'superseded_by: {info["superseded_by"]}')

    if info["tags"]:
        lines.append("tags:")
        for tag in info["tags"]:
            lines.append(f'  - "{tag}"')

    lines.append("---")
    return "\n".join(lines) + "\n"

def process_file(path: Path, is_incident: bool, overrides: dict = None) -> tuple[str, str, dict]:
    """Reads a file, extracts current frontmatter (if any), generates new frontmatter."""
    raw = path.read_text(encoding="utf-8", errors="replace")

    # Strip existing frontmatter if present
    m = YAML_FRONTMATTER_RE.match(raw)
    if m:
        content = raw[m.end():]
        existing_fm = m.group(1)
    else:
        content = raw
        existing_fm = ""

    if is_incident:
        info = parse_incident_info(path, content)
    else:
        info = parse_plan_info(path, content)

    # Override info with any existing frontmatter fields if they exist and are relevant
    if existing_fm:
        for line in existing_fm.splitlines():
            kv = line.split(":", 1)
            if len(kv) == 2:
                k = kv[0].strip().lower()
                v = kv[1].strip().strip('"\'')
                if k in info:
                    info[k] = v

    # Enforce canonical status and certified_for_ai mappings
    status_lower = str(info.get("status", "")).lower()

    if is_incident:
        if any(w in status_lower for w in ["concluso", "completato", "risolto", "resolved", "archived", "closed", "chiuso", "✅"]):
            info["status"] = "archived"
            info["certified_for_ai"] = "false"
            info["resolved"] = "true"
            # Try to extract date for resolved_at if not present
            if info.get("date") and not info.get("resolved_at"):
                info["resolved_at"] = f"{info['date']}T23:59:59Z"
        else:
            info["status"] = "active"
            info["certified_for_ai"] = "true"
            info["resolved"] = "false"
            info["resolved_at"] = ""
    else:
        if any(w in status_lower for w in ["concluso", "completato", "operativo", "✅", "archived"]):
            info["status"] = "archived"
            info["certified_for_ai"] = "false"
            if info.get("created_at") and not info.get("archived_at"):
                info["archived_at"] = info["created_at"]
        elif any(w in status_lower for w in ["corso", "in corso", "esecuzione", "attivo", "active", "ongoing"]):
            info["status"] = "active"
            info["certified_for_ai"] = "true"
        else:
            info["status"] = "draft"
            info["certified_for_ai"] = "true" # Keep draft visible to AI for review/discussion

    # Apply user overrides from the table if available
    rel_path_str = path.relative_to(PROJECT_ROOT).as_posix()
    if overrides and rel_path_str in overrides:
        user_override = overrides[rel_path_str]
        info["status"] = user_override["status"]
        info["certified_for_ai"] = user_override["certified_for_ai"]
        if is_incident:
            if info["status"] == "archived":
                info["resolved"] = "true"
                if not info.get("resolved_at") and info.get("date"):
                    info["resolved_at"] = f"{info['date']}T23:59:59Z"
            else:
                info["resolved"] = "false"
                info["resolved_at"] = ""
        else:
            if info["status"] == "archived":
                if not info.get("archived_at") and info.get("created_at"):
                    info["archived_at"] = info["created_at"]

    new_fm = generate_yaml_frontmatter(info)
    return content, new_fm, info

def main():
    parser = argparse.ArgumentParser(description="Standardize metadata frontmatter for plans and incidents.")
    parser.add_argument("--apply", action="store_true", help="Apply modifications to files directly.")
    parser.add_argument("--proposal-path", type=str, default="", help="Path where to save the markdown proposal report.")
    args = parser.parse_args()

    # Load user overrides if "mia versione.md" exists
    overrides = {}
    user_proposal = PROJECT_ROOT / "mia versione.md"
    if user_proposal.exists():
        print(f"Loading user overrides from {user_proposal}")
        try:
            user_content = user_proposal.read_text(encoding="utf-8")
            for line in user_content.splitlines():
                m = re.match(r'^\|\s*\[`([^`]+)`\]\([^\)]+\)\s*\|\s*\w+\s*\|\s*`([^`]+)`\s*\|\s*`([^`]+)`\s*\|', line)
                if m:
                    rel_path = m.group(1).strip()
                    status = m.group(2).strip()
                    certified = m.group(3).strip()
                    overrides[rel_path] = {
                        "status": status,
                        "certified_for_ai": certified
                    }
            print(f"Loaded {len(overrides)} file overrides from user proposal.")
        except Exception as e:
            print(f"Error parsing user overrides: {e}")

    proposal_lines = [
        "# Proposta di Standardizzazione Metadati Wiki\n",
        f"Generato il: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n",
        "> Questo report mostra i tag frontmatter YAML che verranno inseriti o aggiornati nei file della wiki.\n\n",
        "## Riepilogo dei Cambiamenti Proposti\n\n",
        "| File | Tipo | Stato Dedotto | Certified AI |\n",
        "| :--- | :--- | :--- | :--- |\n"
    ]

    details_lines = ["\n## Dettagli dei Frontmatter Proposti\n\n"]

    files_to_process = []
    if PLANS_DIR.is_dir():
        for f in sorted(PLANS_DIR.glob("*.md")):
            files_to_process.append((f, False))
    if INCIDENTS_DIR.is_dir():
        for f in sorted(INCIDENTS_DIR.glob("*.md")):
            files_to_process.append((f, True))

    modified_count = 0

    for path, is_incident in files_to_process:
        rel_path = path.relative_to(PROJECT_ROOT)
        content, new_fm, info = process_file(path, is_incident, overrides)

        # Add to summary table
        proposal_lines.append(f"| [`{rel_path}`](file://{path.as_posix()}) | {info['type']} | `{info['status']}` | `{info['certified_for_ai']}` |\n")

        # Add to details
        details_lines.append(f"### `{rel_path}`\n")
        details_lines.append("```yaml\n" + new_fm + "```\n\n")

        if args.apply:
            # Construct new content (frontmatter + content)
            new_total_content = new_fm + "\n" + content.lstrip()
            path.write_text(new_total_content, encoding="utf-8")
            modified_count += 1

    proposal_content = "".join(proposal_lines) + "".join(details_lines)

    if args.proposal_path:
        prop_path = Path(args.proposal_path)
        prop_path.parent.mkdir(parents=True, exist_ok=True)
        prop_path.write_text(proposal_content, encoding="utf-8")
        print(f"Report di proposta generato in: {prop_path}")

    if args.apply:
        print(f"Modifiche applicate con successo a {modified_count} file.")
    else:
        print("Esecuzione completata in modalità DRY-RUN. Nessun file modificato.")

if __name__ == "__main__":
    main()

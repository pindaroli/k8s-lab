#!/usr/bin/env python3
"""
Genera un file Markdown LLM-ready dalla wiki (entities, workflows, piani attivi, rete.json, storage.json).
=====================
build_wiki_context.py — Output: wiki/wiki_context.md

Regole:
  - Salta SEMPRE la cartella incidents/
  - Salta i piani con status: Concluso, Completato, Completato & Operativo
  - Risolve i wikilink [[NomeEntità]] in sezioni cross-reference inline
  - Include rete.json e storage.json in formato leggibile (tabelle + JSON annotato)
  - Output: wiki/wiki_context.md (sovrascrive ogni volta)

Uso:
  python3 scripts/build_wiki_context.py
"""

import os
import re
import json
import sys
from pathlib import Path
from datetime import datetime

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parent.parent
WIKI_DIR = PROJECT_ROOT / "wiki"
OUTPUT_FILE = WIKI_DIR / "wiki_context.md"
RETE_JSON = PROJECT_ROOT / "rete.json"
STORAGE_JSON = PROJECT_ROOT / "storage.json"

# Pattern per rilevare piani conclusi nel frontmatter YAML
DONE_STATUS_RE = re.compile(
    r'status\s*:\s*["\']?\s*(concluso|completato|completato\s*&\s*operativo|✅)',
    re.IGNORECASE
)
# Pattern wikilink: [[NomeEntità]] o [[NomeEntità|Alias]]
WIKILINK_RE = re.compile(r'\[\[([^\]|]+)(?:\|[^\]]+)?\]\]')
# Pattern frontmatter YAML
FRONTMATTER_RE = re.compile(r'^---\s*\n(.*?)\n---\s*\n', re.DOTALL)

# Sezioni da includere nell'ordine desiderato
SECTION_ORDER = [
    ("root",       "📋 Documenti Fondamentali"),
    ("entities",   "🏗️ Entità Infrastrutturali"),
    ("workflows",  "🔄 Workflow Operativi"),
    ("istruzioni", "📖 Istruzioni Tecniche"),
    ("plans",      "🗺️ Piani Attivi"),
]

# ---------------------------------------------------------------------------
# Helper: leggi un file e rimuovi il frontmatter YAML
# ---------------------------------------------------------------------------
def read_file_strip_frontmatter(path: Path) -> tuple[str, dict]:
    """Restituisce (content_senza_frontmatter, meta_dict)."""
    raw = path.read_text(encoding="utf-8", errors="replace")
    meta = {}
    m = FRONTMATTER_RE.match(raw)
    if m:
        fm_text = m.group(1)
        content = raw[m.end():]
        # Parsing basilare del YAML frontmatter (senza dipendenza PyYAML)
        for line in fm_text.splitlines():
            kv = line.split(":", 1)
            if len(kv) == 2:
                key = kv[0].strip().lower()
                val = kv[1].strip().strip('"\'')
                meta[key] = val
    else:
        content = raw
    return content.strip(), meta


# ---------------------------------------------------------------------------
# Helper: è un piano da saltare?
# ---------------------------------------------------------------------------
def is_plan_done(path: Path) -> bool:
    """True se il piano ha status Concluso/Completato."""
    try:
        raw = path.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return False
    return bool(DONE_STATUS_RE.search(raw))


# ---------------------------------------------------------------------------
# Raccoglitore dei file wiki per sezione
# ---------------------------------------------------------------------------
def collect_files() -> dict[str, list[Path]]:
    """Raccoglie i file .md suddivisi per sezione, applicando i filtri."""
    sections: dict[str, list[Path]] = {k: [] for k, _ in SECTION_ORDER}

    # Root files (purpose.md, SCHEMA.md, ecc.) — escludi il file generato
    for f in sorted(WIKI_DIR.glob("*.md")):
        if f.name.startswith(".") or f.name == "wiki_context.md":
            continue
        sections["root"].append(f)

    # Sottocartelle
    for key, _ in SECTION_ORDER:
        if key == "root":
            continue
        subdir = WIKI_DIR / key
        if not subdir.is_dir():
            continue
        for f in sorted(subdir.glob("*.md")):
            if f.name.startswith("."):
                continue
            # Salta incidents (non inclusi nell'order ma per sicurezza)
            if key == "incidents":
                continue
            # Salta piani conclusi
            if key == "plans" and is_plan_done(f):
                print(f"  [SKIP concluso] {f.relative_to(PROJECT_ROOT)}")
                continue
            sections[key].append(f)

    return sections


# ---------------------------------------------------------------------------
# Costruisce la mappa nome->path per la risoluzione dei wikilink
# ---------------------------------------------------------------------------
def build_wikilink_map(sections: dict[str, list[Path]]) -> dict[str, Path]:
    """Crea un dizionario stem->Path per tutti i file inclusi."""
    wmap: dict[str, Path] = {}
    for files in sections.values():
        for f in files:
            stem = f.stem.lower()
            wmap[stem] = f
            # Alias con underscore/spazi
            wmap[stem.replace("_", " ")] = f
            wmap[stem.replace("-", " ")] = f
    return wmap


# ---------------------------------------------------------------------------
# Resolve wikilink nel testo sostituendoli con anchor markdown
# ---------------------------------------------------------------------------
def resolve_wikilinks(text: str, wmap: dict[str, Path]) -> str:
    """Sostituisce [[Link]] con → [Link](#link) se presente, altrimenti testo semplice."""
    def replacer(m: re.Match) -> str:
        target = m.group(1).strip()
        anchor = target.lower().replace(" ", "-").replace("_", "-").replace(".", "")
        if target.lower() in wmap or target.lower().replace("_", " ") in wmap:
            return f"[{target}](#{anchor})"
        # Non risolto — lascia il nome come testo per chiarezza LLM
        return f"`{target}`"
    return WIKILINK_RE.sub(replacer, text)


# ---------------------------------------------------------------------------
# Formatta rete.json in modo leggibile
# ---------------------------------------------------------------------------
def format_rete_json(path: Path) -> str:
    out = ["## 🌐 Inventario di Rete (`rete.json`)\n"]
    out.append("> Fonte canonica della rete: tutti gli IP, hostname e alias sono definitivi.\n")
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception as e:
        return f"## 🌐 Inventario di Rete\n\n> ERRORE lettura rete.json: {e}\n"

    # Hosts / devices
    devices = data.get("hosts") or data.get("devices") or []
    if devices:
        out.append("\n### Dispositivi e Host\n")
        out.append("| ID / Hostname | IP | Tipo / Ruolo | Note |\n")
        out.append("|---|---|---|---|\n")
        for d in devices:
            hostname = d.get("hostname") or d.get("id") or d.get("name") or "—"
            ip       = d.get("ip") or d.get("address") or "—"
            role     = d.get("role") or d.get("type") or d.get("description") or "—"
            notes    = d.get("notes") or d.get("note") or ""
            if isinstance(role, list):
                role = ", ".join(str(r) for r in role)
            out.append(f"| `{hostname}` | `{ip}` | {role} | {notes} |\n")

    # VLANs
    vlans = data.get("vlans") or []
    if vlans:
        out.append("\n### VLAN\n")
        out.append("| VLAN ID | Nome | Subnet | Gateway | Scopo |\n")
        out.append("|---|---|---|---|---|\n")
        for v in vlans:
            vid     = v.get("id") or v.get("vlan_id") or "—"
            name    = v.get("name") or "—"
            subnet  = v.get("subnet") or v.get("network") or "—"
            gw      = v.get("gateway") or "—"
            scope   = v.get("scope") or v.get("description") or "—"
            out.append(f"| `{vid}` | {name} | `{subnet}` | `{gw}` | {scope} |\n")

    # DNS / Aliases
    dns_entries = data.get("dns") or data.get("aliases") or []
    if dns_entries:
        out.append("\n### Record DNS / Alias\n")
        out.append("| Hostname | Risolve a | Note |\n")
        out.append("|---|---|---|\n")
        for e in dns_entries:
            if isinstance(e, dict):
                h = e.get("hostname") or e.get("name") or "—"
                r = e.get("resolves_to") or e.get("ip") or e.get("target") or "—"
                n = e.get("note") or e.get("notes") or ""
                out.append(f"| `{h}` | `{r}` | {n} |\n")

    # Dump grezzo rimanente delle chiavi non processate (top-level)
    known_keys = {"hosts", "devices", "vlans", "dns", "aliases"}
    extra_keys = [k for k in data if k not in known_keys]
    if extra_keys:
        out.append("\n### Altri Dati di Rete\n\n```json\n")
        extra = {k: data[k] for k in extra_keys}
        out.append(json.dumps(extra, indent=2, ensure_ascii=False))
        out.append("\n```\n")

    return "".join(out)


# ---------------------------------------------------------------------------
# Formatta storage.json in modo leggibile
# ---------------------------------------------------------------------------
def format_storage_json(path: Path) -> str:
    out = ["## 💾 Inventario Storage (`storage.json`)\n"]
    out.append("> Fonte canonica degli share NFS e dei dataset ZFS su TrueNAS.\n")
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception as e:
        return f"## 💾 Inventario Storage\n\n> ERRORE lettura storage.json: {e}\n"

    shares = data.get("shares") or data.get("nfs_shares") or data.get("exports") or []
    datasets = data.get("datasets") or data.get("pools") or []

    if shares:
        out.append("\n### Share NFS\n")
        out.append("| Path | Autorizzati | Opzioni | Note |\n")
        out.append("|---|---|---|---|\n")
        for s in shares:
            path_s  = s.get("path") or s.get("name") or "—"
            allowed = s.get("allowed") or s.get("networks") or s.get("hosts") or "—"
            opts    = s.get("options") or s.get("opts") or ""
            notes   = s.get("notes") or s.get("note") or s.get("description") or ""
            if isinstance(allowed, list):
                allowed = ", ".join(str(a) for a in allowed)
            if isinstance(opts, list):
                opts = ", ".join(str(o) for o in opts)
            out.append(f"| `{path_s}` | `{allowed}` | {opts} | {notes} |\n")

    if datasets:
        out.append("\n### Dataset ZFS / Pool\n")
        out.append("| Nome | Pool | Mountpoint | Quota | Note |\n")
        out.append("|---|---|---|---|---|\n")
        for d in datasets:
            name  = d.get("name") or "—"
            pool  = d.get("pool") or "—"
            mnt   = d.get("mountpoint") or "—"
            quota = d.get("quota") or "—"
            notes = d.get("notes") or d.get("note") or ""
            out.append(f"| `{name}` | `{pool}` | `{mnt}` | {quota} | {notes} |\n")

    # Dump generico del resto
    known_keys = {"shares", "nfs_shares", "exports", "datasets", "pools"}
    extra_keys = [k for k in data if k not in known_keys]
    if extra_keys:
        out.append("\n### Altri Dati Storage\n\n```json\n")
        extra = {k: data[k] for k in extra_keys}
        out.append(json.dumps(extra, indent=2, ensure_ascii=False))
        out.append("\n```\n")

    return "".join(out)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main():
    print(f"🔍 Analisi wiki in: {WIKI_DIR}")
    sections = collect_files()
    wmap = build_wikilink_map(sections)

    total_included = sum(len(v) for v in sections.values())
    print(f"✅ File inclusi: {total_included}")

    lines: list[str] = []

    # -----------------------------------------------------------------------
    # Header del documento
    # -----------------------------------------------------------------------
    lines.append("# 🤖 GEMINI Homelab — Wiki Context per LLM\n")
    lines.append(f"> **Generato automaticamente** da `scripts/build_wiki_context.py`  \n")
    lines.append(f"> **Data**: {datetime.now().strftime('%Y-%m-%d %H:%M')}  \n")
    lines.append(f"> **Contenuto**: Wiki strutturata + rete.json + storage.json  \n")
    lines.append(f"> **Esclusi**: Incidents, piani Conclusi/Completati  \n")
    lines.append("\n---\n\n")

    lines.append("## 📑 Indice dei Contenuti\n\n")
    for key, label in SECTION_ORDER:
        files = sections[key]
        if not files:
            continue
        lines.append(f"- **{label}**\n")
        for f in files:
            stem = f.stem
            anchor = stem.lower().replace("_", "-").replace(".", "")
            lines.append(f"  - [{stem}](#{anchor})\n")
    lines.append("- **🌐 Inventario di Rete**\n")
    lines.append("- **💾 Inventario Storage**\n")
    lines.append("\n---\n\n")

    # -----------------------------------------------------------------------
    # Contenuto delle sezioni wiki
    # -----------------------------------------------------------------------
    for key, label in SECTION_ORDER:
        files = sections[key]
        if not files:
            continue

        lines.append(f"# {label}\n\n")

        for f in files:
            content, meta = read_file_strip_frontmatter(f)
            stem = f.stem
            anchor = stem.lower().replace("_", "-").replace(".", "")

            # Titolo di sezione con anchor implicito
            lines.append(f"---\n\n")
            lines.append(f"## {stem} {{#{anchor}}}\n\n")

            # Metadata compatto (se presente)
            if meta:
                meta_parts = []
                if "title" in meta:
                    meta_parts.append(f"**Titolo**: {meta['title']}")
                if "last_updated" in meta:
                    meta_parts.append(f"**Aggiornato**: {meta['last_updated']}")
                if "confidence" in meta:
                    meta_parts.append(f"**Confidenza**: {meta['confidence']}")
                if "status" in meta:
                    meta_parts.append(f"**Stato**: {meta['status']}")
                if meta_parts:
                    lines.append("> " + " · ".join(meta_parts) + "\n\n")

            # Risolvi wikilink nel contenuto
            resolved = resolve_wikilinks(content, wmap)
            lines.append(resolved)
            lines.append("\n\n")

    # -----------------------------------------------------------------------
    # rete.json
    # -----------------------------------------------------------------------
    lines.append("---\n\n")
    if RETE_JSON.exists():
        lines.append(format_rete_json(RETE_JSON))
    else:
        lines.append("## 🌐 Inventario di Rete\n\n> `rete.json` non trovato.\n")
    lines.append("\n\n")

    # -----------------------------------------------------------------------
    # storage.json
    # -----------------------------------------------------------------------
    lines.append("---\n\n")
    if STORAGE_JSON.exists():
        lines.append(format_storage_json(STORAGE_JSON))
    else:
        lines.append("## 💾 Inventario Storage\n\n> `storage.json` non trovato.\n")
    lines.append("\n\n")

    # -----------------------------------------------------------------------
    # Footer
    # -----------------------------------------------------------------------
    lines.append("---\n\n")
    lines.append("> *Fine documento — generato da `scripts/build_wiki_context.py`*\n")

    # -----------------------------------------------------------------------
    # Scrittura output (trailing whitespace stripped per pre-commit hooks)
    # -----------------------------------------------------------------------
    raw_output = "".join(lines)
    # Rimuovi trailing whitespace da ogni riga, mantieni newline finale
    clean_lines = [line.rstrip() for line in raw_output.splitlines()]
    output = "\n".join(clean_lines).rstrip("\n") + "\n"
    # Se esiste già, rimuovi temporaneamente il read-only per sovrascrivere
    if OUTPUT_FILE.exists():
        OUTPUT_FILE.chmod(0o644)
    OUTPUT_FILE.write_text(output, encoding="utf-8")
    # Rendi il file read-only per evitare modifiche manuali accidentali
    OUTPUT_FILE.chmod(0o444)
    size_kb = OUTPUT_FILE.stat().st_size / 1024
    print(f"✅ Output scritto: {OUTPUT_FILE.relative_to(PROJECT_ROOT)} ({size_kb:.1f} KB, {len(output.splitlines())} righe)")
    print(f"🔒 File impostato in sola lettura (chmod 444)")


if __name__ == "__main__":
    main()

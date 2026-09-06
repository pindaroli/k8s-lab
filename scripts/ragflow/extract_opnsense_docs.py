#!/usr/bin/env python3
"""
extract_opnsense_docs.py

Estrae, normalizza e ottimizza la documentazione ufficiale di OPNsense
dal repository GitHub upstream (opnsense/docs) per l'ingestione in RAGFlow.

Caratteristiche:
- Shallow clone mirato al branch/commit specificato (default: master / serie 26.1).
- Two-Pass Semantic Indexer:
    Pass 1: Scansione preliminare per indicizzare titoli effettivi, percorsi dei documenti
            e label/ancore Sphinx (.. _label:) su tutto il corpus.
    Pass 2: Risoluzione ricorsiva di tutti gli include (.. include::), conversione
            reStructuredText in GitHub Flavored Markdown e risoluzione dei link semantici:
            - :doc:`path` e :doc:`Title <path>` con percorsi relativi e titoli automatici.
            - :ref:`label` e :ref:`Title <label>` verso file target e ancore HTML (<a id="...">).
            - :menuselection:`A --> B --> C` in breadcrumb leggibili (**A** > **B** > **C**).
            - :command:, :code:, :rfc:, :pep: e hyperlink reST.
- Conversione Admonition Sphinx in GitHub Alerts standard:
    .. Note:: -> > [!NOTE]
    .. Tip:: / .. Hint:: -> > [!TIP]
    .. Warning:: / .. Danger:: -> > [!WARNING]
    .. Caution:: / .. Important:: -> > [!CAUTION] / > [!IMPORTANT]
- Iniezione header semantico RAGFlow per ciascun articolo.
- Copia degli asset grafici (images/) per preservare i diagrammi.
- Generazione del master index categorizzato (SUMMARY.md).
- Pulizia automatica della directory temporanea di clone.
"""

import argparse
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path


def run_command(cmd, cwd=None):
    """Esegue un comando shell sollevando eccezione in caso di errore."""
    print(f"[*] Esecuzione: {' '.join(cmd)}")
    res = subprocess.run(cmd, cwd=cwd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    if res.returncode != 0:
        print(f"[!] Errore comando: {res.stderr}", file=sys.stderr)
        raise RuntimeError(f"Comando fallito con codice {res.returncode}: {res.stderr}")
    return res.stdout


def shallow_clone_repo(repo_url: str, branch: str, target_dir: Path, commit: str = None):
    """Esegue lo shallow clone del repository OPNsense docs."""
    if target_dir.exists():
        print(f"[*] Directory temporanea esistente rilevata: {target_dir}. Rimozione...")
        shutil.rmtree(target_dir)

    target_dir.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        "git", "clone",
        "--depth", "1",
        "--branch", branch,
        repo_url,
        str(target_dir)
    ]
    run_command(cmd)

    if commit:
        print(f"[*] Checkout al commit specifico: {commit}")
        run_command(["git", "checkout", commit], cwd=str(target_dir))

    print(f"[+] Repository clonato con successo in {target_dir}")


def slugify(text: str) -> str:
    """Genera uno slug valido per le ancore Markdown."""
    text = text.lower().strip()
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[\s_-]+", "-", text)
    return text.strip("-")


def extract_document_title(content: str, fallback: str) -> str:
    """
    Estrae il titolo principale di un file RST.
    Riconosce titoli sottolineati (o sovralineati+sottolineati) con =, -, ~, ^.
    """
    lines = content.splitlines()
    for i, line in enumerate(lines):
        line_s = line.strip()
        if not line_s or line_s.startswith(".."):
            continue

        # Pattern: Sottolineatura semplice (es. Title\n====...)
        if i + 1 < len(lines):
            next_line = lines[i + 1].strip()
            if next_line and len(next_line) >= 3 and all(c in "=-~^#*`" for c in next_line):
                # Assicuriamoci che non sia un blocco commento o directive
                if len(next_line) >= min(len(line_s), 3):
                    return line_s

        # Pattern: Sovralineatura + Titolo + Sottolineatura (es. ====...\nTitle\n====...)
        if i + 2 < len(lines):
            prev_adorn = line_s
            cand_title = lines[i + 1].strip()
            next_adorn = lines[i + 2].strip()
            if (
                all(c in "=-~^#*`" for c in prev_adorn)
                and all(c in "=-~^#*`" for c in next_adorn)
                and len(prev_adorn) >= 3
                and cand_title
            ):
                return cand_title

    return fallback


def index_sphinx_project(source_dir: Path) -> tuple:
    """
    Pass 1: Indicizza l'intero progetto Sphinx.
    Ritorna:
      - doc_registry: mappa da percorsi logici (:doc:) ai metadati del file target.
      - label_registry: mappa dalle label Sphinx (.. _label:) a file target e ancore.
      - include_cache: mappa per lookup rapido di file inclusi tramite .. include::.
    """
    doc_registry = {}
    label_registry = {}
    include_cache = {}

    print(f"[*] Inizio Pass 1: Indicizzazione globale simboli in {source_dir}...")

    for root, _, files in os.walk(source_dir):
        for file in files:
            file_path = Path(root) / file
            rel_rst = file_path.relative_to(source_dir)

            # Indicizza cache per .. include::
            include_cache[str(rel_rst)] = file_path
            include_cache[file] = file_path
            include_cache[str(rel_rst).lower()] = file_path
            include_cache[file.lower()] = file_path

            if not file.endswith(".rst"):
                continue

            rel_no_ext = str(rel_rst.with_suffix(""))
            fallback_title = file_path.stem.replace("_", " ").replace("-", " ").title()

            try:
                with open(file_path, "r", encoding="utf-8", errors="replace") as f:
                    content = f.read()
            except Exception as e:
                print(f"[!] Errore lettura per indicizzazione {file_path}: {e}")
                continue

            title = extract_document_title(content, fallback_title)
            parts = rel_rst.parts
            category = parts[0] if len(parts) > 1 else "Core"
            rel_md = rel_rst.with_suffix(".md")

            doc_info = {
                "file_path": file_path,
                "rel_rst": str(rel_rst),
                "rel_md": str(rel_md),
                "title": title,
                "category": category,
            }

            # Registra varianti di chiave per :doc:
            doc_registry[rel_no_ext] = doc_info
            doc_registry[f"/{rel_no_ext}"] = doc_info
            doc_registry[rel_no_ext.lower()] = doc_info
            doc_registry[f"/{rel_no_ext.lower()}"] = doc_info
            doc_registry[file_path.stem] = doc_info
            doc_registry[file_path.stem.lower()] = doc_info

            # Cerca etichette Sphinx: .. _label_name:
            label_matches = re.finditer(r"^\.\.\s+_([a-zA-Z0-9_\-\.]+):\s*$", content, re.MULTILINE)
            for m in label_matches:
                lbl = m.group(1).strip()
                label_registry[lbl] = {
                    "rel_md": str(rel_md),
                    "anchor": slugify(lbl),
                    "doc_title": title,
                }
                label_registry[lbl.lower()] = label_registry[lbl]

    print(f"[+] Indicizzati {len(doc_registry)} riferimenti doc e {len(label_registry)} label di salto.")
    return doc_registry, label_registry, include_cache


def resolve_includes(text: str, current_file: Path, source_dir: Path, include_cache: dict, used_includes: set, depth=0, max_depth=10) -> str:
    """Risolve ricorsivamente le direttive .. include:: <path> inlinando il contenuto."""
    if depth > max_depth:
        print(f"[!] Attenzione: superata la profondità massima di inclusione per {current_file}")
        return text

    include_pattern = re.compile(r"^\.\.\s+include::\s+([^\n\r]+)$", re.MULTILINE)

    def replacer(match):
        raw_target = match.group(1).strip().strip("'\"")
        # Rimuovi eventuali parametri tipo :start-after:
        target_file_str = raw_target.split()[0] if raw_target else ""

        # Risolvi rispetto alla directory corrente del file o tramite include_cache
        target_path = None
        cand1 = (current_file.parent / target_file_str).resolve()
        cand2 = (source_dir / target_file_str.lstrip("/")).resolve()

        if cand1.exists() and cand1.is_file():
            target_path = cand1
        elif cand2.exists() and cand2.is_file():
            target_path = cand2
        else:
            target_path = include_cache.get(target_file_str) or include_cache.get(os.path.basename(target_file_str))

        if target_path and target_path.exists():
            used_includes.add(str(target_path))
            try:
                with open(target_path, "r", encoding="utf-8", errors="replace") as inc_f:
                    inc_content = inc_f.read()
                # Risolvi ricorsivamente
                return resolve_includes(inc_content, target_path, source_dir, include_cache, used_includes, depth + 1, max_depth)
            except Exception as e:
                print(f"[!] Errore apertura include {target_path}: {e}")
                return f"\n> [Errore Include: {target_file_str}]\n"
        else:
            return f"\n<!-- Include non risolto: {target_file_str} -->\n"

    return include_pattern.sub(replacer, text)


def convert_admonitions(text: str) -> str:
    """
    Converte le direttive Admonition di Sphinx in GitHub Alerts.
    Gestisce blocchi con indentazione standard.
    """
    admonition_regex = re.compile(
        r"^\.\.\s+(Note|Tip|Warning|Caution|Important|Attention|Danger|Hint|Seealso)::(?:[ \t]+([^\n]*))?\n"
        r"((?:(?:[ \t]{2,}[^\n]*|[ \t]*)\n?)+)",
        re.MULTILINE | re.IGNORECASE
    )

    def replacer(match):
        adm_type = match.group(1).upper()
        title_extra = (match.group(2) or "").strip()
        body = match.group(3)

        alert_type = "NOTE"
        if adm_type in ["WARNING", "DANGER"]:
            alert_type = "WARNING"
        elif adm_type in ["TIP", "HINT"]:
            alert_type = "TIP"
        elif adm_type in ["CAUTION"]:
            alert_type = "CAUTION"
        elif adm_type in ["IMPORTANT", "ATTENTION"]:
            alert_type = "IMPORTANT"
        elif adm_type in ["SEEALSO"]:
            alert_type = "NOTE"

        # Rimuovi l'indentazione comune del blocco
        lines = body.splitlines()
        clean_lines = []
        for line in lines:
            if line.startswith("    "):
                clean_lines.append(line[4:])
            elif line.startswith("\t"):
                clean_lines.append(line[1:])
            elif line.strip() == "":
                clean_lines.append("")
            else:
                clean_lines.append(line.lstrip())

        out_lines = [f"> [!{alert_type}]"]
        if title_extra:
            out_lines.append(f"> **{title_extra}**")
        for cl in clean_lines:
            out_lines.append(f"> {cl}" if cl else ">")

        return "\n" + "\n".join(out_lines) + "\n\n"

    return admonition_regex.sub(replacer, text)


def convert_directives_and_code(text: str) -> str:
    """Converte blocchi di codice, diagrammi e direttive Sphinx."""
    # 1. code-block e code
    code_block_regex = re.compile(
        r"^\.\.\s+(?:code-block|code)::[ \t]*([a-zA-Z0-9_\-\+]*)\n"
        r"((?:[ \t]+:[a-zA-Z0-9_\-]+:.*?\n)*)"  # opzioni tipo :caption:
        r"((?:(?:[ \t]{2,}[^\n]*|[ \t]*)\n?)+)",
        re.MULTILINE
    )

    def code_replacer(match):
        lang = match.group(1).strip() or "text"
        body = match.group(3)
        lines = body.splitlines()
        clean_lines = []
        for line in lines:
            if line.startswith("    "):
                clean_lines.append(line[4:])
            elif line.startswith("\t"):
                clean_lines.append(line[1:])
            elif line.strip() == "":
                clean_lines.append("")
            else:
                clean_lines.append(line.lstrip())
        return f"\n```{lang}\n" + "\n".join(clean_lines).rstrip() + "\n```\n\n"

    text = code_block_regex.sub(code_replacer, text)

    # 2. Blockdiag, nwdiag, seqdiag, actdiag
    diag_regex = re.compile(
        r"^\.\.\s+(blockdiag|nwdiag|seqdiag|actdiag)::[ \t]*\n"
        r"((?:[ \t]+:[a-zA-Z0-9_\-]+:.*?\n)*)"
        r"((?:(?:[ \t]{2,}[^\n]*|[ \t]*)\n?)+)",
        re.MULTILINE
    )

    def diag_replacer(match):
        diag_type = match.group(1)
        body = match.group(3)
        lines = body.splitlines()
        clean_lines = [l[4:] if l.startswith("    ") else l for l in lines]
        return f"\n```{diag_type}\n" + "\n".join(clean_lines).rstrip() + "\n```\n\n"

    text = diag_regex.sub(diag_replacer, text)

    # 3. Immagini e figure
    image_regex = re.compile(
        r"^\.\.\s+(?:image|figure)::[ \t]+([^\n\r]+)\n"
        r"((?:[ \t]+:[a-zA-Z0-9_\-]+:.*?\n)*)",
        re.MULTILINE
    )

    def image_replacer(match):
        img_path = match.group(1).strip()
        opts = match.group(2) or ""
        alt_match = re.search(r":alt:[ \t]+([^\n]+)", opts)
        alt_text = alt_match.group(1).strip() if alt_match else os.path.basename(img_path)
        return f"\n![{alt_text}]({img_path})\n\n"

    text = image_regex.sub(image_replacer, text)

    # 4. Rimuovi direttive non documentative (toctree, contents, raw, index)
    text = re.sub(r"^\.\.\s+toctree::.*?\n((?:[ \t]+:[a-zA-Z0-9_\-]+:.*?\n)*)((?:[ \t]{2,}[^\n]*\n?)*)", "", text, flags=re.MULTILINE)
    text = re.sub(r"^\.\.\s+contents::.*?\n", "", text, flags=re.MULTILINE)
    text = re.sub(r"^\.\.\s+index::.*?\n", "", text, flags=re.MULTILINE)

    return text


def resolve_semantic_links(text: str, current_rel_md: str, doc_registry: dict, label_registry: dict) -> str:
    """
    Risolve tutti i collegamenti semantici reST/Sphinx (:doc:, :ref:, :menuselection:, hyperlinks).
    Calcola il percorso relativo corretto per garantire link Markdown funzionanti.
    """
    curr_dir = Path(current_rel_md).parent

    def compute_rel_link(target_rel_md: str, anchor: str = "") -> str:
        """Calcola il percorso relativo dal file corrente al target."""
        target_path = Path(target_rel_md)
        rel_str = os.path.relpath(target_path, curr_dir).replace("\\", "/")
        if not rel_str.startswith("."):
            rel_str = f"./{rel_str}"
        if anchor:
            rel_str = f"{rel_str}#{anchor}"
        return rel_str

    # 1. Ruoli :doc:
    # Pattern A: :doc:`Titolo Personalizzato </manual/how-tos/multiwan>` o :doc:`Titolo <multiwan>`
    doc_custom_pattern = re.compile(r":doc:`([^`<]+)<([^>]+)>`")

    def doc_custom_replacer(m):
        custom_title = m.group(1).strip()
        target_ref = m.group(2).strip().strip("/")
        doc_info = (
            doc_registry.get(target_ref)
            or doc_registry.get(f"/{target_ref}")
            or doc_registry.get(target_ref.lower())
            or doc_registry.get(os.path.basename(target_ref))
        )
        if doc_info:
            link_path = compute_rel_link(doc_info["rel_md"])
            return f"[{custom_title}]({link_path})"
        target_clean = target_ref.replace(".rst", ".md")
        return f"[{custom_title}]({target_clean})"

    text = doc_custom_pattern.sub(doc_custom_replacer, text)

    # Pattern B: :doc:`/manual/how-tos/multiwan` o :doc:`multiwan`
    doc_auto_pattern = re.compile(r":doc:`([^`]+)`")

    def doc_auto_replacer(m):
        target_ref = m.group(1).strip().strip("/")
        doc_info = (
            doc_registry.get(target_ref)
            or doc_registry.get(f"/{target_ref}")
            or doc_registry.get(target_ref.lower())
            or doc_registry.get(os.path.basename(target_ref))
        )
        if doc_info:
            link_path = compute_rel_link(doc_info["rel_md"])
            return f"[{doc_info['title']}]({link_path})"
        return f"[{target_ref}]({target_ref}.md)"

    text = doc_auto_pattern.sub(doc_auto_replacer, text)

    # 2. Ruoli :ref:
    # Pattern A: :ref:`Titolo Personalizzato <label_name>`
    ref_custom_pattern = re.compile(r":ref:`([^`<]+)<([^>]+)>`")

    def ref_custom_replacer(m):
        custom_title = m.group(1).strip()
        target_label = m.group(2).strip()
        label_info = label_registry.get(target_label) or label_registry.get(target_label.lower())
        if label_info:
            link_path = compute_rel_link(label_info["rel_md"], label_info["anchor"])
            return f"[{custom_title}]({link_path})"
        return f"[{custom_title}](#{slugify(target_label)})"

    text = ref_custom_pattern.sub(ref_custom_replacer, text)

    # Pattern B: :ref:`label_name`
    ref_auto_pattern = re.compile(r":ref:`([^`]+)`")

    def ref_auto_replacer(m):
        target_label = m.group(1).strip()
        label_info = label_registry.get(target_label) or label_registry.get(target_label.lower())
        if label_info:
            link_path = compute_rel_link(label_info["rel_md"], label_info["anchor"])
            return f"[{label_info['doc_title']}]({link_path})"
        return f"[{target_label}](#{slugify(target_label)})"

    text = ref_auto_pattern.sub(ref_auto_replacer, text)

    # 3. Ruoli :menuselection:
    def menu_replacer(m):
        menu_path = m.group(1).strip()
        parts = [p.strip() for p in re.split(r"-->|->", menu_path) if p.strip()]
        return " > ".join(f"**{p}**" for p in parts)

    text = re.sub(r":menuselection:`([^`]+)`", menu_replacer, text)

    # 4. Ruoli :command: e :code:
    text = re.sub(r":(?:command|code):`([^`]+)`", r"`\1`", text)

    # 5. RFC e PEP
    text = re.sub(r":rfc:`([0-9]+)`", r"[RFC \1](https://datatracker.ietf.org/doc/html/rfc\1)", text)
    text = re.sub(r":pep:`([0-9]+)`", r"[PEP \1](https://peps.python.org/pep-\1/)", text)

    # 5b. Ruoli :download: (es. :download:`Titolo <path/file.ext>`)
    def download_replacer(m):
        raw = m.group(1).strip()
        dm = re.match(r"^([^<]+)<([^>]+)>$", raw)
        if dm:
            title = dm.group(1).strip()
            target = dm.group(2).strip()
            if "OPNsense_Logo.ai" in target:
                target = target.replace("OPNsense_Logo.ai", "opnsense_logo_horizontaal.png")
            return f"[{title}]({target})"
        return f"`{raw}`"

    text = re.sub(r":download:`([^`]+)`", download_replacer, text)

    # 6. Riferimenti espliciti etichetta: .. _label_name: -> <a id="..."></a>
    def anchor_replacer(m):
        lbl = m.group(1).strip()
        return f'<a id="{slugify(lbl)}"></a>\n'

    text = re.sub(r"^\.\.\s+_([a-zA-Z0-9_\-\.]+):\s*$", anchor_replacer, text, flags=re.MULTILINE)

    # 7. Hyperlinks standard reST
    # `Testo <https://url>`__ o `Testo <https://url>`_
    text = re.sub(r"`([^`<]+)<([^>]+)>`_{1,2}", r"[\1](\2)", text)

    # `Sezione`_ -> [Sezione](#sezione)
    def internal_link_replacer(m):
        sec_name = m.group(1).strip()
        return f"[{sec_name}](#{slugify(sec_name)})"

    text = re.sub(r"`([^`]+)`_", internal_link_replacer, text)

    return text


def convert_rst_tables(text: str) -> str:
    """Converte tabelle semplici reST (delimitate da === ===) in tabelle Markdown GFM."""
    lines = text.splitlines()
    new_lines = []
    i = 0

    while i < len(lines):
        line = lines[i]
        stripped = line.strip()

        # Rileva inizio di tabella semplice: es. ===================== ==========================
        if re.match(r"^(=+[ \t]+)+=+$", stripped) and i + 2 < len(lines):
            # Calcola le posizioni delle colonne sulla riga originale con indentazione
            col_spans = []
            matches = list(re.finditer(r"=+", line))
            for idx, part in enumerate(matches):
                # Per l'ultima colonna, cattura fino alla fine della riga
                col_end = None if idx == len(matches) - 1 else part.end()
                col_spans.append((part.start(), col_end))

            i += 1
            table_rows = []
            while i < len(lines) and not re.match(r"^(=+[ \t]+)+=+$", lines[i].strip()):
                row_str = lines[i]
                if not row_str.strip():
                    i += 1
                    continue
                # Estrai celle in base ai col_spans
                cells = []
                for s, e in col_spans:
                    if s < len(row_str):
                        cell_val = row_str[s:e].strip() if e is not None else row_str[s:].strip()
                    else:
                        cell_val = ""
                    cells.append(cell_val)
                table_rows.append(cells)
                i += 1

            # Salta la linea di chiusura della tabella
            if i < len(lines) and re.match(r"^(=+[ \t]+)+=+$", lines[i].strip()):
                i += 1

            if table_rows:
                # Se la prima riga è header, usa separatore GFM
                header = table_rows[0]
                new_lines.append("")
                new_lines.append("| " + " | ".join(c or "-" for c in header) + " |")
                new_lines.append("| " + " | ".join("---" for _ in header) + " |")
                for row in table_rows[1:]:
                    # Assicura che la riga abbia tutte le celle
                    padded = row + [""] * (len(header) - len(row))
                    new_lines.append("| " + " | ".join(c.replace("|", "\\|") for c in padded) + " |")
                new_lines.append("")
                continue

        new_lines.append(line)
        i += 1

    return "\n".join(new_lines)


def convert_headings(text: str, doc_title: str = "") -> str:
    """
    Converte le intestazioni reStructuredText in gerarchia Markdown standard.
    Riconosce sovralineatura/sottolineatura e sottolineatura singola.
    Ignora blocchi di codice ed evita la duplicazione del titolo principale.
    """
    lines = text.splitlines()
    new_lines = []
    i = 0
    in_code_block = False
    first_heading_seen = False
    valid_adorns = set("=-~^\"'")

    while i < len(lines):
        line = lines[i]
        line_s = line.strip()

        # Monitora stato blocco di codice
        if line_s.startswith("```"):
            in_code_block = not in_code_block
            new_lines.append(line)
            i += 1
            continue

        if in_code_block:
            new_lines.append(line)
            i += 1
            continue

        # Verifica Sovralineatura + Titolo + Sottolineatura
        if i + 2 < len(lines):
            next1 = lines[i + 1].strip()
            next2 = lines[i + 2].strip()
            if (
                len(line_s) >= 3
                and all(c in valid_adorns for c in line_s)
                and next1
                and len(next2) >= 3
                and all(c in valid_adorns for c in next2)
                and line_s[0] == next2[0]
            ):
                char = line_s[0]
                level = 1 if char == "=" else 2
                # Se è il primo titolo e coincide con il titolo del documento, evitalo per non duplicare
                if not first_heading_seen and doc_title and next1.lower() == doc_title.lower():
                    first_heading_seen = True
                    i += 3
                    continue
                first_heading_seen = True
                new_lines.append(f"{'#' * level} {next1}")
                i += 3
                continue

        # Verifica Sottolineatura semplice (Titolo\n======)
        if i + 1 < len(lines):
            next_line = lines[i + 1].strip()
            if (
                line_s
                and not line_s.startswith("..")
                and not line_s.startswith(">")
                and not line_s.startswith("|")
                and len(next_line) >= 3
                and all(c in valid_adorns for c in next_line)
                and len(next_line) >= min(len(line_s), 3)
            ):
                char = next_line[0]
                if char == "=":
                    level = 2
                elif char == "-":
                    level = 3
                elif char == "~":
                    level = 4
                elif char == "^":
                    level = 5
                else:
                    level = 6

                # Se è il primo titolo e coincide con doc_title, salta la duplicazione
                if not first_heading_seen and doc_title and line_s.lower() == doc_title.lower():
                    first_heading_seen = True
                    i += 2
                    continue

                first_heading_seen = True
                new_lines.append(f"{'#' * level} {line_s}")
                i += 2
                continue

        new_lines.append(line)
        i += 1

    return "\n".join(new_lines)


def process_rst_file(
    file_path: Path,
    source_dir: Path,
    doc_registry: dict,
    label_registry: dict,
    include_cache: dict,
    used_includes: set,
    release_version: str
) -> tuple:
    """Processa un singolo file .rst trasformandolo in Markdown RAGFlow-ready."""
    with open(file_path, "r", encoding="utf-8", errors="replace") as f:
        raw_content = f.read()

    rel_rst = file_path.relative_to(source_dir)
    rel_md = str(rel_rst.with_suffix(".md"))
    fallback_title = file_path.stem.replace("_", " ").replace("-", " ").title()
    title = extract_document_title(raw_content, fallback_title)

    # 1. Risolvi ricorsivamente gli include
    content_with_includes = resolve_includes(raw_content, file_path, source_dir, include_cache, used_includes)

    # 2. Converti Admonitions in GitHub Alerts
    content_with_alerts = convert_admonitions(content_with_includes)

    # 3. Converti blocchi di codice, diagrammi e rimuovi toctree
    content_with_code = convert_directives_and_code(content_with_alerts)

    # 4. Converti tabelle semplici
    content_with_tables = convert_rst_tables(content_with_code)

    # 5. Risolvi i collegamenti semantici (:doc:, :ref:, :menuselection:)
    content_with_links = resolve_semantic_links(content_with_tables, rel_md, doc_registry, label_registry)

    # 6. Converti le intestazioni reST in Markdown (#, ##, ###)
    clean_markdown = convert_headings(content_with_links, doc_title=title)

    # 7. Pulizia commenti e righe vuote multiple
    clean_markdown = re.sub(r"^\.\.[ \t]+[^\n]*\n", "", clean_markdown, flags=re.MULTILINE)
    clean_markdown = re.sub(r"\n{3,}", "\n\n", clean_markdown).strip()

    # 7. Costruisci Header Semantico RAGFlow
    parts = rel_rst.parts
    category = parts[0] if len(parts) > 1 else "Core"

    header_parts = [
        f"# {title}\n",
        f"> **OPNsense Documentation** | **Release:** {release_version} (Witty Woodpecker) | **Category:** {category.title()}",
        f"> **Source:** `source/{rel_rst}`\n",
        "---\n"
    ]
    final_content = "\n".join(header_parts) + "\n" + clean_markdown + "\n"

    return title, category, rel_md, final_content


def main():
    parser = argparse.ArgumentParser(description="Estrae e normalizza la documentazione OPNsense per RAGFlow.")
    parser.add_argument("--branch", default="master", help="Ramo Git da estrarre (default: master)")
    parser.add_argument("--commit", default=None, help="Commit SHA specifico (opzionale)")
    parser.add_argument("--repo-url", default="https://github.com/opnsense/docs.git", help="URL del repository upstream")
    parser.add_argument("--output-dir", default="downloads/opnsense-26.1", help="Directory di destinazione Markdown")
    parser.add_argument("--temp-dir", default="scratch/opnsense-docs-repo", help="Directory temporanea di clone")
    parser.add_argument("--release-version", default="26.1", help="Versione di OPNsense documentata (default: 26.1)")
    parser.add_argument("--single-file", default=None, help="Elabora solo un file specifico (relativo a source/) per test")
    parser.add_argument("--with-images", action="store_true", help="Copia anche gli asset grafici web-safe (default: False, text-first ottimizzato per RAGFlow)")
    parser.add_argument("--keep-clone", action="store_true", help="Non eliminare la directory temporanea al termine")
    args = parser.parse_args()

    project_root = Path(__file__).resolve().parent.parent.parent
    temp_path = (project_root / args.temp_dir).resolve()
    output_path = (project_root / args.output_dir).resolve()

    print("==================================================")
    print(f"[*] Avvio estrazione documentazione OPNsense")
    print(f"[*] Release target: OPNsense {args.release_version} (Witty Woodpecker)")
    print(f"[*] Ramo Git:       {args.branch} (Commit: {args.commit or 'HEAD'})")
    print(f"[*] Repo upstream:  {args.repo_url}")
    print(f"[*] Output target:  {output_path}")
    print(f"[*] Temp scratch:   {temp_path}")
    print("==================================================")

    # 1. Shallow clone
    shallow_clone_repo(args.repo_url, args.branch, temp_path, args.commit)

    source_dir = temp_path / "source"
    if not source_dir.exists():
        print(f"[!] Errore fatale: cartella source/ non trovata in {temp_path}", file=sys.stderr)
        sys.exit(1)

    # 2. Pass 1: Indicizzazione globale del progetto Sphinx
    doc_registry, label_registry, include_cache = index_sphinx_project(source_dir)
    used_includes = set()

    # 3. Preparazione directory output
    if not args.single_file and output_path.exists():
        print(f"[*] Pulizia cartella di destinazione esistente: {output_path}")
        shutil.rmtree(output_path)
    output_path.mkdir(parents=True, exist_ok=True)

    # 4. Pass 2: Conversione documenti
    processed_count = 0
    categories_stats = {}
    summary_entries = []

    files_to_process = []
    if args.single_file:
        target_f = source_dir / args.single_file
        if not target_f.exists():
            print(f"[!] Errore: file {target_f} non trovato!", file=sys.stderr)
            sys.exit(1)
        files_to_process.append(target_f)
    else:
        for root, _, files in os.walk(source_dir):
            for f in files:
                if f.endswith(".rst"):
                    files_to_process.append(Path(root) / f)

    for file_path in sorted(files_to_process):
        rel_rst = file_path.relative_to(source_dir)
        title, category, rel_md, final_md = process_rst_file(
            file_path, source_dir, doc_registry, label_registry, include_cache, used_includes, args.release_version
        )

        dest_file = output_path / rel_md
        dest_file.parent.mkdir(parents=True, exist_ok=True)

        with open(dest_file, "w", encoding="utf-8") as out_f:
            out_f.write(final_md)

        processed_count += 1
        categories_stats[category] = categories_stats.get(category, 0) + 1
        summary_entries.append({
            "category": category,
            "rel_path": rel_md,
            "title": title,
        })

    print(f"[+] Elaborati {processed_count} documenti da source/")

    # 5. Sincronizzazione asset immagini (solo formati web supportati da RAGFlow)
    ALLOWED_IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".gif", ".svg", ".webp"}

    def copy_allowed_assets(src_dir: Path, dst_dir: Path):
        if not src_dir.exists():
            return 0
        if dst_dir.exists():
            shutil.rmtree(dst_dir)
        dst_dir.mkdir(parents=True, exist_ok=True)
        count = 0
        for item in src_dir.rglob("*"):
            if item.is_file():
                if item.suffix.lower() in ALLOWED_IMAGE_EXTS:
                    rel = item.relative_to(src_dir)
                    target = dst_dir / rel
                    target.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(item, target)
                    count += 1
                else:
                    print(f"[*] Ignorato asset non-web / sorgente di progetto: {item.name}")
        return count

    if args.with_images and not args.single_file:
        src_images = source_dir / "images"
        dst_images = output_path / "images"
        n_img = copy_allowed_assets(src_images, dst_images)
        print(f"[+] Sincronizzata directory immagini ({n_img} file validi) in {dst_images}")

        src_manual_images = source_dir / "manual" / "images"
        dst_manual_images = output_path / "manual" / "images"
        n_man = copy_allowed_assets(src_manual_images, dst_manual_images)
        print(f"[+] Sincronizzata directory manual/images ({n_man} file validi) in {dst_manual_images}")
    elif not args.single_file:
        print("[*] Modalità Text-First (default): copia asset grafici omessa per massimizzare la pulizia semantica di RAGFlow.")

    # 6. Generazione Master Index (SUMMARY.md)
    if not args.single_file:
        summary_path = output_path / "SUMMARY.md"
        with open(summary_path, "w", encoding="utf-8") as sum_f:
            sum_f.write(f"# OPNsense {args.release_version} Documentation Knowledge Base\n\n")
            sum_f.write("Documentazione ufficiale di OPNsense estratta, convertita con risoluzione dei link semantici e ottimizzata per RAGFlow.\n\n")
            sum_f.write(f"- **Versione OPNsense**: {args.release_version} (Witty Woodpecker)\n")
            sum_f.write(f"- **Totale Documenti**: {processed_count}\n\n")
            sum_f.write("## Categorie e Statistiche\n\n")
            for cat, count in sorted(categories_stats.items()):
                sum_f.write(f"- **{cat.title()}**: {count} documenti\n")
            sum_f.write("\n---\n\n## Indice degli Articoli\n\n")

            current_cat = None
            for entry in sorted(summary_entries, key=lambda x: (x["category"], x["title"])):
                if entry["category"] != current_cat:
                    current_cat = entry["category"]
                    sum_f.write(f"\n### {current_cat.title()}\n\n")
                sum_f.write(f"- [{entry['title']}]({entry['rel_path']})\n")

        print(f"[+] Generato indice master: {summary_path}")

    # 7. Pulizia scratchpad
    if not args.keep_clone:
        print(f"[*] Pulizia directory temporanea di clone: {temp_path}")
        shutil.rmtree(temp_path, ignore_errors=True)

    print("==================================================")
    print(f"[✅] Estrazione OPNsense {args.release_version} completata con successo in: {output_path}")
    print(f"Totale documenti generati: {processed_count}")
    print("==================================================")


if __name__ == "__main__":
    main()

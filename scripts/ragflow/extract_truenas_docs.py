#!/usr/bin/env python3
"""
extract_truenas_docs.py

Estrae, normalizza e ottimizza la documentazione ufficiale di TrueNAS SCALE
dal repository GitHub upstream (truenas/documentation) per l'ingestione in RAGFlow.

Caratteristiche:
- Shallow clone mirato al branch specificato (default: 25.10).
- Risoluzione ricorsiva di tutti gli shortcode Hugo {{< include file="..." >}}
  attingendo a static/includes/ per rendere ogni documento autonomo e completo.
- Conversione di shortcode Hugo (hint -> GitHub alerts, expand -> sezioni,
  trueimage -> markdown images, ref -> markdown links).
- Conversione del frontmatter (title, description, tags, keywords) in intestazioni
  Markdown semantiche ad altissima resa per il chunking vettoriale di RAGFlow.
- Generazione di un master index (SUMMARY.md).
- Pulizia automatica della directory di clone temporanea.
"""

import argparse
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path


def run_command(cmd, cwd=None):
    """Esegue un comando di shell sollevando eccezione in caso di errore."""
    print(f"[*] Esecuzione: {' '.join(cmd)}")
    res = subprocess.run(cmd, cwd=cwd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    if res.returncode != 0:
        print(f"[!] Errore comando: {res.stderr}", file=sys.stderr)
        raise RuntimeError(f"Comando fallito con codice {res.returncode}: {res.stderr}")
    return res.stdout


def shallow_clone_repo(repo_url: str, branch: str, target_dir: Path):
    """Esegue lo shallow clone del ramo indicato."""
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
    print(f"[+] Repository clonato con successo (ramo: {branch}) in {target_dir}")


def build_includes_cache(includes_dir: Path) -> dict:
    """Mappa tutti i file markdown in static/includes/ per lookup rapido (case-insensitive)."""
    cache = {}
    if not includes_dir.exists():
        print(f"[!] Warning: directory includes non trovata in {includes_dir}")
        return cache

    for path in includes_dir.rglob("*"):
        if path.is_file() and path.suffix in [".md", ".txt", ".html"]:
            rel_path = path.relative_to(includes_dir)
            variants = [
                f"/static/includes/{rel_path}",
                f"static/includes/{rel_path}",
                f"/includes/{rel_path}",
                f"includes/{rel_path}",
                str(rel_path),
                path.name,
            ]
            for v in variants:
                cache[v] = path
                cache[v.lower()] = path
    print(f"[+] Indicizzati {len(cache)} riferimenti di inclusione da {includes_dir}")
    return cache


def parse_frontmatter(content: str):
    """Estrae metadati (title, description, tags, keywords) da TOML/YAML frontmatter."""
    metadata = {
        "title": "",
        "description": "",
        "tags": [],
        "keywords": []
    }
    body = content

    # YAML frontmatter --- ... ---
    yaml_match = re.match(r"^---\s*\n(.*?)\n---\s*\n", content, re.DOTALL)
    if yaml_match:
        fm_text = yaml_match.group(1)
        body = content[yaml_match.end():]
        for line in fm_text.splitlines():
            line = line.strip()
            if line.startswith("title:"):
                metadata["title"] = line.split(":", 1)[1].strip().strip('"\'')
            elif line.startswith("description:"):
                metadata["description"] = line.split(":", 1)[1].strip().strip('"\'')
            elif line.startswith("tags:") or line.startswith("keywords:"):
                key = "tags" if line.startswith("tags:") else "keywords"
                # Può essere una lista inline [a, b] o gestita su più righe
                rest = line.split(":", 1)[1].strip()
                if rest.startswith("[") and rest.endswith("]"):
                    items = [x.strip().strip('"\'') for x in rest[1:-1].split(",") if x.strip()]
                    metadata[key].extend(items)
        # Rileva tag su righe successive con trattino
        tag_match = re.findall(r"-\s+([a-zA-Z0-9_\- ]+)", fm_text)
        if tag_match and not metadata["tags"]:
            metadata["tags"] = tag_match

    # TOML frontmatter +++ ... +++
    toml_match = re.match(r"^\+\+\+\s*\n(.*?)\n\+\+\+\s*\n", content, re.DOTALL)
    if toml_match:
        fm_text = toml_match.group(1)
        body = content[toml_match.end():]
        for line in fm_text.splitlines():
            line = line.strip()
            if line.startswith("title ="):
                metadata["title"] = line.split("=", 1)[1].strip().strip('"\'')
            elif line.startswith("description ="):
                metadata["description"] = line.split("=", 1)[1].strip().strip('"\'')

    return metadata, body


def resolve_includes(text: str, includes_cache: dict, used_includes: set, depth=0, max_depth=10) -> str:
    """Risolve ricorsivamente {{< include file="..." >}} e {{% include file="..." %}}."""
    if depth > max_depth:
        print("[!] Raggiunta profondità massima di inclusione, possibile loop ricorsivo.")
        return text

    include_pattern = re.compile(r"\{\{[<%]\s*include\s+file=[\"']([^\"']+)[\"']\s*[>%]\}\}")

    def replacer(match):
        inc_file = match.group(1).strip()
        target_path = (
            includes_cache.get(inc_file)
            or includes_cache.get(inc_file.lower())
            or includes_cache.get(os.path.basename(inc_file))
            or includes_cache.get(os.path.basename(inc_file).lower())
        )

        if target_path and target_path.exists():
            used_includes.add(str(target_path))
            try:
                with open(target_path, "r", encoding="utf-8", errors="replace") as f:
                    inc_content = f.read()
                # Risolvi ricorsivamente eventuali include innestati
                return resolve_includes(inc_content, includes_cache, used_includes, depth + 1, max_depth)
            except Exception as e:
                print(f"[!] Errore nella lettura dell'inclusione {target_path}: {e}")
                return f"\n> [Include Error: {inc_file}]\n"
        else:
            print(f"[?] File di inclusione non trovato: {inc_file}")
            return f"\n> [Include Non Trovato: {inc_file}]\n"

    return include_pattern.sub(replacer, text)


def clean_hugo_shortcodes(text: str) -> str:
    """Converte shortcode Hugo in Markdown standard leggibile per RAGFlow."""
    # 1. Commenti Hugo {{/* ... */}}
    text = re.sub(r"\{\{/\*[\s\S]*?\*/\}\}", "", text)

    # 2. Hints -> GitHub callouts
    def hint_replacer(match):
        hint_type = match.group(1).lower().strip()
        body = match.group(2).strip()
        callout_type = "NOTE"
        if hint_type in ["warning", "warn", "danger"]:
            callout_type = "WARNING"
        elif hint_type in ["tip", "hint"]:
            callout_type = "TIP"
        elif hint_type in ["caution"]:
            callout_type = "CAUTION"
        elif hint_type in ["important"]:
            callout_type = "IMPORTANT"

        indented = "\n".join(f"> {line}" for line in body.splitlines())
        return f"\n> [!{callout_type}]\n{indented}\n"

    text = re.sub(r"\{\{[<%]\s*hint\s+type=[\"']?([a-zA-Z0-9_\-]+)[\"']?\s*[>%]\}\}([\s\S]*?)\{\{[<%]\s*/hint\s*[>%]\}\}", hint_replacer, text)

    # 3. Expand -> Sezioni Markdown
    def expand_replacer(match):
        title = match.group(1).strip()
        body = match.group(2).strip()
        return f"\n### {title}\n\n{body}\n"

    text = re.sub(r"\{\{[<%]\s*expand\s+[\"']([^\"']+)[\"'][^>]*[>%]\}\}([\s\S]*?)\{\{[<%]\s*/expand\s*[>%]\}\}", expand_replacer, text)

    # 4. Trueimage -> Immagini Markdown
    def image_replacer(match):
        tag_str = match.group(0)
        src_m = re.search(r'''src=["']([^"']+)["']''', tag_str)
        alt_m = re.search(r'''alt=["']([^"']*)["']''', tag_str)
        cap_m = re.search(r'''caption=["']([^"']*)["']''', tag_str)
        src = src_m.group(1) if src_m else ""
        alt = alt_m.group(1) if alt_m else "Screenshot"
        cap = f"\n*{cap_m.group(1)}*" if cap_m else ""
        return f"\n![{alt}]({src}){cap}\n"

    text = re.sub(r"\{\{[<%]\s*trueimage\s+[^>]+[>%]\}\}", image_replacer, text)

    # 5. Hugo ref / relref links: [Testo]({{< ref "Percorso" >}})
    text = re.sub(r"\{\{[<%]\s*(?:ref|relref)\s+[\"']([^\"']+)[\"']\s*[>%]\}\}", r"\1", text)

    # 6. Pulizia shortcode generici residui tipo {{< ... >}} o {{% ... %}}
    # Preserva blocchi di codice
    text = re.sub(r"\{\{[<%][^>]*[>%]\}\}", "", text)

    # 7. Normalizzazione righe vuote multiple
    text = re.sub(r"\n{3,}", "\n\n", text)

    return text.strip()


def process_markdown_file(file_path: Path, base_content_dir: Path, includes_cache: dict, used_includes: set) -> tuple:
    """Processa un file markdown convertendolo nel formato RAGFlow-ready."""
    with open(file_path, "r", encoding="utf-8", errors="replace") as f:
        raw_content = f.read()

    metadata, body = parse_frontmatter(raw_content)

    # Risolvi ricorsivamente gli include
    body_with_includes = resolve_includes(body, includes_cache, used_includes)

    # Pulisci shortcode Hugo
    clean_body = clean_hugo_shortcodes(body_with_includes)

    # Costruisci intestazione semantica per RAGFlow
    title = metadata["title"] or file_path.stem.replace("_", " ").title()
    header_parts = [f"# {title}\n"]

    if metadata["description"]:
        header_parts.append(f"> {metadata['description']}\n")

    meta_tags = []
    if metadata["tags"]:
        meta_tags.append(f"**Tags:** {', '.join(metadata['tags'])}")
    if metadata["keywords"]:
        meta_tags.append(f"**Keywords:** {', '.join(metadata['keywords'])}")

    if meta_tags:
        header_parts.append(" | ".join(meta_tags) + "\n")

    header_parts.append("---\n")
    final_content = "\n".join(header_parts) + "\n" + clean_body + "\n"

    return title, metadata["description"], final_content


def main():
    parser = argparse.ArgumentParser(description="Estrae e prepara la documentazione TrueNAS SCALE per RAGFlow.")
    parser.add_argument("--branch", default="25.10", help="Ramo Git da estrarre (default: 25.10)")
    parser.add_argument("--repo-url", default="https://github.com/truenas/documentation.git", help="URL del repository")
    parser.add_argument("--output-dir", default="downloads/truenas-25.10", help="Directory di destinazione")
    parser.add_argument("--temp-dir", default="scratch/truenas-docs-repo", help="Directory temporanea di clone")
    parser.add_argument("--keep-clone", action="store_true", help="Non eliminare la directory di clone temporanea")
    args = parser.parse_args()

    project_root = Path(__file__).resolve().parent.parent.parent
    temp_path = (project_root / args.temp_dir).resolve()
    output_path = (project_root / args.output_dir).resolve()

    print("==================================================")
    print(f"[*] Avvio estrazione documentazione TrueNAS SCALE")
    print(f"[*] Ramo Git:      {args.branch}")
    print(f"[*] Repo upstream: {args.repo_url}")
    print(f"[*] Output target: {output_path}")
    print(f"[*] Temp scratch:  {temp_path}")
    print("==================================================")

    # 1. Shallow clone
    shallow_clone_repo(args.repo_url, args.branch, temp_path)

    content_dir = temp_path / "content"
    includes_dir = temp_path / "static" / "includes"

    if not content_dir.exists():
        print(f"[!] Errore fatale: cartella content/ non trovata in {temp_path}", file=sys.stderr)
        sys.exit(1)

    # 2. Indicizzazione include
    includes_cache = build_includes_cache(includes_dir)
    used_includes = set()

    # 3. Preparazione directory output
    if output_path.exists():
        print(f"[*] Pulizia cartella di destinazione esistente: {output_path}")
        shutil.rmtree(output_path)
    output_path.mkdir(parents=True, exist_ok=True)

    # 4. Elaborazione file content/
    processed_count = 0
    categories_stats = {}
    summary_entries = []

    # Cartelle rilevanti in content/
    for root, _, files in os.walk(content_dir):
        for file in files:
            if not file.endswith(".md"):
                continue

            file_path = Path(root) / file
            rel_to_content = file_path.relative_to(content_dir)

            # Escludi file di ricerca o preview di stampa non documentativi se vuoti
            parts = rel_to_content.parts
            category = parts[0] if len(parts) > 1 else "Root"

            if category in ["search", "PrintPreview"]:
                continue

            title, description, final_md = process_markdown_file(
                file_path, content_dir, includes_cache, used_includes
            )

            # Destinazione
            dest_file = output_path / rel_to_content
            dest_file.parent.mkdir(parents=True, exist_ok=True)

            with open(dest_file, "w", encoding="utf-8") as out_f:
                out_f.write(final_md)

            processed_count += 1
            categories_stats[category] = categories_stats.get(category, 0) + 1
            summary_entries.append({
                "category": category,
                "rel_path": str(rel_to_content),
                "title": title,
                "description": description
            })

    print(f"[+] Elaborati {processed_count} articoli da content/")

    # 5. Gestione degli include standalone (non inclusi direttamente da alcun file)
    standalone_includes_dir = output_path / "Includes_Standalone"
    standalone_count = 0
    for inc_key, inc_file_path in includes_cache.items():
        if inc_key.startswith("/static/includes/") and str(inc_file_path) not in used_includes:
            # Se ha contenuto sostanzioso (>250 byte), esportalo
            if inc_file_path.stat().st_size > 250:
                with open(inc_file_path, "r", encoding="utf-8", errors="replace") as f:
                    raw_inc = f.read()
                clean_inc = clean_hugo_shortcodes(raw_inc)
                inc_title = inc_file_path.stem.replace("-", " ").replace("_", " ").title()
                final_inc = f"# TrueNAS Guide: {inc_title}\n\n{clean_inc}\n"

                dest_inc = standalone_includes_dir / inc_file_path.name
                dest_inc.parent.mkdir(parents=True, exist_ok=True)
                with open(dest_inc, "w", encoding="utf-8") as out_inc:
                    out_inc.write(final_inc)
                standalone_count += 1

    if standalone_count > 0:
        categories_stats["Includes_Standalone"] = standalone_count
        print(f"[+] Esportate {standalone_count} guide standalone da static/includes/")

    # 6. Creazione del file indice MASTER SUMMARY.md
    summary_path = output_path / "SUMMARY.md"
    with open(summary_path, "w", encoding="utf-8") as sum_f:
        sum_f.write(f"# TrueNAS SCALE {args.branch} Documentation Knowledge Base\n\n")
        sum_f.write(f"Documentazione ufficiale estratta e ottimizzata per RAGFlow.\n")
        sum_f.write(f"- **Versione TrueNAS**: {args.branch}\n")
        sum_f.write(f"- **Totale Documenti**: {processed_count + standalone_count}\n\n")
        sum_f.write("## Categorie e Statistiche\n\n")
        for cat, count in sorted(categories_stats.items()):
            sum_f.write(f"- **{cat}**: {count} documenti\n")
        sum_f.write("\n---\n\n## Indice degli Articoli\n\n")

        current_cat = None
        for entry in sorted(summary_entries, key=lambda x: (x["category"], x["title"])):
            if entry["category"] != current_cat:
                current_cat = entry["category"]
                sum_f.write(f"\n### {current_cat}\n\n")
            desc_text = f" - {entry['description']}" if entry['description'] else ""
            sum_f.write(f"- [{entry['title']}]({entry['rel_path']}){desc_text}\n")

    print(f"[+] Generato indice master: {summary_path}")

    # 7. Pulizia scratchpad
    if not args.keep_clone:
        print(f"[*] Pulizia directory temporanea di clone: {temp_path}")
        shutil.rmtree(temp_path, ignore_errors=True)

    print("==================================================")
    print(f"[✅] Estrazione completata con successo in: {output_path}")
    print(f"Totale documenti: {processed_count + standalone_count}")
    print("==================================================")


if __name__ == "__main__":
    main()

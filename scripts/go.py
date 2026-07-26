#!/usr/bin/env python3
"""
Launcher interattivo per gli script del progetto Homelab.
Scansiona la directory corrente (o 'scripts/' se lanciato dalla root),
elenca gli script eseguibili e permette all'utente di selezionarne uno tramite numero.
Supporta anche il lancio diretto tramite argomento (es. ./go 5).
"""

import os
import sys
import subprocess

# Aggiungi scripts/ al path per poter importare utils.common
_base = os.path.dirname(os.path.realpath(__file__))
sys.path.insert(0, _base)
from utils.common import Colors

# Determina la cartella degli script basandosi sulla posizione di questo file
SCRIPT_DIR = _base


def get_script_description(filepath):
    """Estrae una breve descrizione dallo script guardando i primi commenti/docstring."""
    desc = "Nessuna descrizione."
    my_basename = os.path.basename(filepath)
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            lines = []
            for _ in range(15):
                line = f.readline()
                if not line:
                    break
                lines.append(line)

            in_docstring = False
            doc_lines = []
            for line in lines:
                l = line.strip()
                if l.startswith('"""') or l.startswith("'''"):
                    if in_docstring:
                        break
                    in_docstring = True
                    if len(l) > 3:
                        doc_lines.append(l[3:])
                    continue
                if in_docstring:
                    doc_lines.append(l)
            if doc_lines:
                return doc_lines[0][:60] + ("..." if len(doc_lines[0]) > 60 else "")

            for line in lines:
                if line.startswith("#") and not line.startswith("#!"):
                    text = line[1:].strip()
                    if text and text != my_basename:
                        return text[:60] + ("..." if len(text) > 60 else "")
    except Exception:
        pass

    return desc


def main():
    # Trova tutti gli script .py e .sh validi (escludendo se stesso e cartelle di utility/test)
    scripts = []
    my_name = os.path.basename(__file__)
    exclude_dirs = {"unit-test", "mac-network-fix", "utils"}

    for root, dirs, files in os.walk(SCRIPT_DIR):
        dirs[:] = [d for d in dirs if not d.startswith('.') and d not in exclude_dirs]

        for f in files:
            if f == "go.py" or f == my_name or f.startswith('.'):
                continue
            if f.endswith('.py') or f.endswith('.sh'):
                full_path = os.path.join(root, f)
                if os.path.isfile(full_path) and os.access(full_path, os.X_OK):
                    rel_path = os.path.relpath(full_path, SCRIPT_DIR)
                    scripts.append({
                        'name': rel_path,
                        'path': full_path,
                        'desc': get_script_description(full_path)
                    })

    # Ordina gli script in base al percorso relativo
    scripts.sort(key=lambda x: x['name'])

    choice_idx = None
    extra_args = []

    # Controllo se è stato passato un numero come argomento da CLI (es. ./go 5)
    if len(sys.argv) > 1 and sys.argv[1].isdigit():
        choice_idx = int(sys.argv[1])
        extra_args = sys.argv[2:]
    else:
        print(f"\n{Colors.HEADER}{Colors.BOLD}🚀 HOMELAB SCRIPT LAUNCHER 🚀{Colors.ENDC}")
        print(f"[{SCRIPT_DIR}]\n")

        # Stampa Menu ad albero raggruppato per sottocartella
        current_dir = None
        for idx, s in enumerate(scripts, start=1):
            parts = s['name'].split(os.sep)
            if len(parts) > 1:
                dir_name = os.sep.join(parts[:-1])
                file_name = parts[-1]
            else:
                dir_name = ""
                file_name = s['name']

            if dir_name != current_dir:
                current_dir = dir_name
                display_dir = current_dir if current_dir else "root"
                print(f"\n{Colors.HEADER}📁 {display_dir}/{Colors.ENDC}")

            indent = "  " if current_dir else ""
            print(f"{indent}{Colors.OKGREEN}[{idx:2d}]{Colors.ENDC} {Colors.OKCYAN}{file_name:<30}{Colors.ENDC} - {s['desc']}")

        print(f"\n{Colors.WARNING}[ 0]{Colors.ENDC} {Colors.BOLD}Esci{Colors.ENDC}")

        if not sys.stdin.isatty():
            print(f"\n{Colors.FAIL}ATTENZIONE: Il terminale attuale non è interattivo.{Colors.ENDC}")
            print("Esegui lo script direttamente in un terminale reale usando: ./go o ./go <numero>")
            sys.exit(1)

        # Chiedi Input interattivo
        try:
            choice = input(f"\n{Colors.HEADER}Seleziona lo script da lanciare [0-{len(scripts)}]: {Colors.ENDC}")
            choice_idx = int(choice.strip())
        except (ValueError, EOFError):
            print("\nInput non valido o terminale non interattivo. Uscita.")
            sys.exit(1)
        except KeyboardInterrupt:
            print("\nUscita.")
            sys.exit(0)

    if choice_idx == 0:
        print("Uscita.")
        sys.exit(0)

    if choice_idx is not None and 1 <= choice_idx <= len(scripts):
        selected = scripts[choice_idx - 1]
        print(f"\n{Colors.BOLD}Eseguo [{choice_idx}]: {selected['name']}...{Colors.ENDC}")
        print("-" * 50)

        # Prepara l'ambiente con PATH robusto
        env = os.environ.copy()
        common_paths = ["/opt/homebrew/bin", "/usr/local/bin", "/usr/bin", "/bin"]
        current_path = env.get("PATH", "")
        for p in common_paths:
            if p not in current_path:
                current_path = f"{p}:{current_path}"
        env["PATH"] = current_path
        env["PYTHONPATH"] = f"{SCRIPT_DIR}:{env.get('PYTHONPATH', '')}".strip(':')

        for var in ["HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY", "http_proxy", "https_proxy", "all_proxy"]:
            if var in env:
                del env[var]

        # Esegui script
        try:
            if selected['path'].endswith('.py'):
                cmd = [sys.executable, selected['path']] + extra_args
            else:
                cmd = [selected['path']] + extra_args
            subprocess.call(cmd, env=env)
        except KeyboardInterrupt:
            print(f"\n{Colors.WARNING}Esecuzione di {selected['name']} interrotta dall'utente.{Colors.ENDC}")
        except Exception as e:
            print(f"\n{Colors.WARNING}Errore nell'esecuzione: {e}{Colors.ENDC}")

        print("-" * 50)
        print(f"{Colors.BOLD}Esecuzione terminata.{Colors.ENDC}")
    else:
        print(f"{Colors.WARNING}Scelta non valida: {choice_idx}. Inserisci un numero tra 1 e {len(scripts)}.{Colors.ENDC}")


if __name__ == "__main__":
    main()

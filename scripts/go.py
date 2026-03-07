#!/usr/bin/env python3
"""
Launcher interattivo per gli script del progetto Homelab.
Scansiona la directory corrente (o 'scripts/' se lanciato dalla root),
elenca gli script eseguibili e permette all'utente di selezionarne uno tramite numero.
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
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            lines = [next(f) for _ in range(15)]
            
            # Cerca docstring Python (""" o ''')
            in_docstring = False
            doc_lines = []
            for line in lines:
                l = line.strip()
                if l.startswith('"""') or l.startswith("'''"):
                    if in_docstring:
                        break
                    in_docstring = True
                    # Se c'é testo nella stessa linea dopo """
                    if len(l) > 3:
                        doc_lines.append(l[3:])
                    continue
                if in_docstring:
                    doc_lines.append(l)
            if doc_lines:
                return doc_lines[0][:60] + ("..." if len(doc_lines[0]) > 60 else "")

            # Cerca commenti Bash/Python (#)
            for line in lines:
                if line.startswith("#") and not line.startswith("#!"):
                    text = line[1:].strip()
                    if text:
                        return text[:60] + ("..." if len(text) > 60 else "")
    except Exception:
        pass
    
    return desc

def main():
    print(f"\n{Colors.HEADER}{Colors.BOLD}🚀 HOMELAB SCRIPT LAUNCHER 🚀{Colors.ENDC}")
    print(f"[{SCRIPT_DIR}]\n")

    # Trova tutti gli script .py e .sh validi (escludendo se stesso)
    scripts = []
    my_name = os.path.basename(__file__)
    
    try:
        files = sorted(os.listdir(SCRIPT_DIR))
    except Exception as e:
        print(f"{Colors.WARNING}Errore nella lettura della directory: {e}{Colors.ENDC}")
        sys.exit(1)

    for f in files:
        if f == "go.py" or f == my_name or f.startswith('.'):
            continue
        if f.endswith('.py') or f.endswith('.sh'):
            full_path = os.path.join(SCRIPT_DIR, f)
            if os.path.isfile(full_path) and os.access(full_path, os.X_OK):
                scripts.append({
                    'name': f,
                    'path': full_path,
                    'desc': get_script_description(full_path)
                })

    if not scripts:
        print(f"{Colors.WARNING}Nessun script eseguibile (.py o .sh) trovato in {SCRIPT_DIR}{Colors.ENDC}")
        sys.exit(0)

    # Stampa Menu
    for idx, s in enumerate(scripts, start=1):
        print(f"{Colors.OKGREEN}[{idx:2d}]{Colors.ENDC} {Colors.OKCYAN}{s['name']:<25}{Colors.ENDC} - {s['desc']}")
    
    print(f"{Colors.WARNING}[ 0]{Colors.ENDC} {Colors.BOLD}Esci{Colors.ENDC}")

    if not sys.stdin.isatty():
        print(f"\n{Colors.FAIL}ATTENZIONE: Il terminale attuale non è interattivo (forse eseguito tramite un editor o pannello di output senza input).{Colors.ENDC}")
        print("Esegui lo script direttamente in un terminale reale (es. iTerm2 o il Terminale Integrato) usando il comando: ./go")
        sys.exit(1)

    # Chiedi Input
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
    
    if 1 <= choice_idx <= len(scripts):
        selected = scripts[choice_idx - 1]
        print(f"\n{Colors.BOLD}Eseguo: {selected['name']}...{Colors.ENDC}")
        print("-" * 50)
        
        # Prepara l'ambiente con PATH robusto (specialmente per Mac Homebrew)
        # E pulisce eventuali proxy che disturbano la rete locale
        env = os.environ.copy()
        common_paths = ["/opt/homebrew/bin", "/usr/local/bin", "/usr/bin", "/bin"]
        current_path = env.get("PATH", "")
        for p in common_paths:
            if p not in current_path:
                current_path = f"{p}:{current_path}"
        env["PATH"] = current_path
        
        for var in ["HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY", "http_proxy", "https_proxy", "all_proxy"]:
            if var in env:
                del env[var]

        # Esegui script
        try:
            # Usiamo subprocess.call passando l'env robusto
            subprocess.call([selected['path']], env=env)
        except KeyboardInterrupt:
            print(f"\n{Colors.WARNING}Esecuzione di {selected['name']} interrotta dall'utente.{Colors.ENDC}")
        except Exception as e:
            print(f"\n{Colors.WARNING}Errore nell'esecuzione: {e}{Colors.ENDC}")
            
        print("-" * 50)
        print(f"{Colors.BOLD}Esecuzione terminata.{Colors.ENDC}")
    else:
        print(f"{Colors.WARNING}Scelta non valida.{Colors.ENDC}")

if __name__ == "__main__":
    main()

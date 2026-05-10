import subprocess
import json
import os
import sys

# Definizione base path globale valida per tutti gli script importati
# Poiché common.py è dentro scripts/utils/, la root è 2 livelli sopra
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.realpath(__file__))))

class Colors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'

# Stato globale per diagnostiche
warnings_count = 0
errors_count = 0

def log_ok(msg):
    print(f"[ {Colors.OKGREEN}OK{Colors.ENDC} ] 🟢 {msg}")

def log_warn(msg):
    global warnings_count
    warnings_count += 1
    print(f"[{Colors.WARNING}WARN{Colors.ENDC}] 🟡 {msg}")

def log_err(msg):
    global errors_count
    errors_count += 1
    print(f"[{Colors.FAIL}FAIL{Colors.ENDC}] 🔴 {msg}")

def log_info(msg):
    print(f"       {Colors.OKCYAN}├─{Colors.ENDC} {msg}")

def log_info_end(msg):
    print(f"       {Colors.OKCYAN}└─{Colors.ENDC} {msg}")

def print_section(title):
    print(f"\n{Colors.BOLD}{Colors.OKBLUE}>>> {title}{Colors.ENDC}")
    print("-" * 65)

def run_cmd(cmd, capture_output=True, debug=False):
    try:
        env = os.environ.copy()
        # PATH Rescue for common tools (important for Mac)
        common_paths = ["/opt/homebrew/bin", "/usr/local/bin", "/usr/bin", "/bin", "/usr/sbin", "/sbin"]
        current_path = env.get("PATH", "")
        for p in common_paths:
            if p not in current_path:
                current_path = f"{p}:{current_path}"
        env["PATH"] = current_path

        # Unset proxy to avoid interference with local cluster IPs
        for var in ["HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY", "http_proxy", "https_proxy", "all_proxy"]:
            if var in env:
                del env[var]

        res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=True, env=env)
        return res.stdout if capture_output else None
    except subprocess.CalledProcessError as e:
        if debug:
            print(f"{Colors.WARNING}DEBUG: Command failed: {' '.join(cmd)}{Colors.ENDC}", file=sys.stderr)
            print(f"{Colors.WARNING}DEBUG: Error: {e.stderr.strip()}{Colors.ENDC}", file=sys.stderr)
        return None
    except FileNotFoundError as e:
        log_err(f"Comando non trovato: {cmd[0]}. Verifica che sia nel PATH.")
        return None
    except Exception as e:
        return None

def run_cmd_json(cmd, debug=False):
    stdout = run_cmd(cmd, debug=debug)
    if not stdout:
        return None

    # Prova a caricare come singolo oggetto
    try:
        return json.loads(stdout)
    except:
        # Se fallisce, potrebbe essere una serie di oggetti JSON (es. output di kubectl)
        try:
            objs = []
            current_obj = ""
            for line in stdout.splitlines():
                if line.strip().startswith('WARNING:'): continue
                if not line.strip(): continue
                current_obj += line
                try:
                    obj = json.loads(current_obj)
                    objs.append(obj)
                    current_obj = ""
                except:
                    continue
            return objs if objs else None
        except:
            return None

def check_ping(host):
    ping_cmd = ["ping", "-c", "1", "-W", "1000", host] if sys.platform == "darwin" else ["ping", "-c", "1", "-W", "1", host]
    try:
        res = subprocess.run(ping_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        return res.returncode == 0
    except:
        return False

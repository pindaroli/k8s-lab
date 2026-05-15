#!/usr/bin/env python3
import os
import sys
import time
import subprocess
import select

SRC_DIR = "/Volumes/arrdata/media/music"
SUCCESS_LOG = "import_success.log"
ANOMALIES_LOG = "import_anomalies.log"
RAW_LOG = "import_raw.log"
TIMEOUT_SECONDS = 300  # 5 minuti senza output = blocco

def load_processed_dirs():
    if not os.path.exists(SUCCESS_LOG):
        return set()
    with open(SUCCESS_LOG, "r") as f:
        return set(line.strip() for line in f if line.strip())

def log_raw(text):
    with open(RAW_LOG, "a") as f:
        f.write(text)

def log_success(dir_name):
    with open(SUCCESS_LOG, "a") as f:
        f.write(f"{dir_name}\n")

def log_anomaly(dir_name, reason):
    with open(ANOMALIES_LOG, "a") as f:
        f.write(f"[{dir_name}] {reason}\n")

def get_diagnostic_info(dir_path):
    """Esegue un controllo verboso 'per finta' per capire perché Beets ha saltato la cartella."""
    config_path = os.path.join(os.path.dirname(__file__), "import_music_batches-config.yaml")
    cmd = ["beet", "-v", "-c", config_path, "import", "-p", dir_path]
    try:
        res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, timeout=30)
        output = res.stdout
        details = []
        for line in output.splitlines():
            line_l = line.lower()
            # Ignoriamo le righe di setup config
            if "configuration:" in line_l or "data directory:" in line_l or "plugin paths:" in line_l:
                continue
            if "similarity:" in line_l or "missing tracks:" in line_l or "distance:" in line_l:
                details.append(line.strip())
            if "tagging" in line_l and "->" in line_l: # Mostra il match tentato
                details.append(line.strip())

        if not details:
            # Se non troviamo keyword, prendiamo le prime 5 righe che NON siano config
            fallback = [l.strip() for l in output.splitlines() if "configuration:" not in l.lower() and "directory:" not in l.lower()][:5]
            return " | ".join(fallback)
        return " | ".join(details[:5])
    except Exception as e:
        return f"Diagnosi fallita: {str(e)}"

def process_directory(dir_path):
    dir_name = os.path.basename(dir_path)
    print(f"\n========================================")
    print(f"Importing: {dir_name}")
    log_raw(f"\n--- IMPORTING: {dir_name} ---\n")

    # Carica la configurazione specifica per il batch
    config_path = os.path.join(os.path.dirname(__file__), "import_music_batches-config.yaml")
    cmd = ["beet", "-c", config_path, "import", "-q", dir_path]
    process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1)

    last_output_time = time.time()
    anomaly_reasons = []

    while True:
        rlist, _, _ = select.select([process.stdout], [], [], 5.0)

        if rlist:
            line = process.stdout.readline()
            if not line:
                break # EOF
            last_output_time = time.time()
            sys.stdout.write(line)
            log_raw(line)

            line_lower = line.lower()
            # Filtri più ampi per catturare i motivi reali
            keywords = ["skip", "no match", "error", "no files imported", "similarity", "confidence", "missing", "duplicate"]
            if any(key in line_lower for key in keywords):
                anomaly_reasons.append(line.strip())
        else:
            if time.time() - last_output_time > TIMEOUT_SECONDS:
                print(f"\n[!!!] TIMEOUT: Nessun output per {TIMEOUT_SECONDS}s. Uccido il processo.")
                log_raw(f"TIMEOUT: Ucciso dopo {TIMEOUT_SECONDS}s\n")
                process.kill()
                log_anomaly(dir_name, "CRASH/TIMEOUT STUCK")
                return False

        if process.poll() is not None:
            for line in process.stdout:
                sys.stdout.write(line)
                log_raw(line)
                line_lower = line.lower()
                if any(key in line_lower for key in keywords):
                    anomaly_reasons.append(line.strip())
            break

    exit_code = process.wait()

    if anomaly_reasons:
        diag = get_diagnostic_info(dir_path)
        log_anomaly(dir_name, f"LOG: {' | '.join(anomaly_reasons)} | DIAG: {diag} | CMD: beet import -i \"{dir_path}\"")
        print(f"--> Anomalia Registrata con diagnosi per {dir_name}")
        log_success(dir_name) # Lo segniamo comunque processato per non riprovarci all'infinito
    elif exit_code != 0:
        log_anomaly(dir_name, f"Exited with code {exit_code}")
        log_success(dir_name)
    else:
        log_success(dir_name)
        print(f"--> Successo: {dir_name}")

    return True

def main():
    if len(sys.argv) < 2:
        print("Uso: python3 import_music_batches.py <batch_size>")
        sys.exit(1)

    if sys.argv[1] == "reset":
        print("[!] ATTENZIONE: Stai per cancellare il database e svuotare il backup.")
        confirm = input("Sei sicuro di voler procedere? (y/N): ")
        if confirm.lower() == 'y':
            db_path = os.path.join(os.path.dirname(__file__), "musiclibrary.db")
            backup_dir = "/Volumes/arrdata/media/music_backup"

            print("Pulisco database...")
            if os.path.exists(db_path): os.remove(db_path)

            print("Svuoto cartella backup...")
            if os.path.exists(backup_dir):
                subprocess.run(f"rm -rf {backup_dir}/*", shell=True)

            print("Resetto log...")
            for log in [SUCCESS_LOG, ANOMALIES_LOG, RAW_LOG, "beets_batch.log"]:
                if os.path.exists(log): os.remove(log)

            print("Reset completato. Sistema pronto per un nuovo import.")
            sys.exit(0)
        else:
            print("Reset annullato.")
            sys.exit(0)

    try:
        batch_size = int(sys.argv[1])
    except ValueError:
        print("Uso: python3 import_music_batches.py <batch_size|reset>")
        sys.exit(1)

    processed_dirs = load_processed_dirs()

    try:
        all_dirs = sorted([os.path.join(SRC_DIR, d) for d in os.listdir(SRC_DIR) if os.path.isdir(os.path.join(SRC_DIR, d))])
    except FileNotFoundError:
        print(f"Cartella sorgente {SRC_DIR} non trovata.")
        sys.exit(1)

    to_process = [d for d in all_dirs if os.path.basename(d) not in processed_dirs]

    if not to_process:
        print("Tutte le cartelle sono state processate!")
        sys.exit(0)

    print(f"Cartelle totali: {len(all_dirs)}")
    print(f"Già processate: {len(processed_dirs)}")
    print(f"Rimanenti: {len(to_process)}")
    print(f"Elaborazione batch di: {min(batch_size, len(to_process))} cartelle...")

    for i, dir_path in enumerate(to_process[:batch_size]):
        print(f"\nProgress: {i+1}/{batch_size}")
        if not process_directory(dir_path):
            print("Elaborazione batch interrotta a causa di un Timeout di sistema.")
            break

    print("\nBatch completato.")

if __name__ == "__main__":
    main()

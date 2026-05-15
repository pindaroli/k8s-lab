#!/usr/bin/env python3
import os
import sys
import time
import subprocess
import select

SRC_DIR = "/Volumes/arrdata/media/music"
SUCCESS_LOG = os.path.join(os.path.dirname(__file__), "import_success.log")
ANOMALIES_LOG = os.path.join(os.path.dirname(__file__), "import_anomalies.log")
RAW_LOG = os.path.join(os.path.dirname(__file__), "import_raw.log")
TIMEOUT_SECONDS = 600  # 10 minuti senza output = blocco
TARGETS_FILE = os.path.join(os.path.dirname(__file__), "import_targets.txt")

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
    print(f"\n========================================")
    print(f"Importing: {dir_path}")
    log_raw(f"\n--- IMPORTING: {dir_path} ---\n")

    # Carica la configurazione specifica per il batch
    config_path = os.path.join(os.path.dirname(__file__), "import_music_batches-config.yaml")
    # Aggiunto -v per far generare a Beets log diagnostici di rete e plugin interni
    cmd = ["beet", "-v", "-c", config_path, "import", "-q", dir_path]
    process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1)

    last_output_time = time.time()
    anomaly_reasons = []
    rolling_buffer = []  # Mantiene le ultime righe verbose per il debug dei timeout

    while True:
        rlist, _, _ = select.select([process.stdout], [], [], 5.0)

        if rlist:
            line = process.stdout.readline()
            if not line:
                break # EOF
            last_output_time = time.time()

            # Logghiamo tutto su file e nel buffer diagnostico
            log_raw(line)
            rolling_buffer.append(line.strip())
            if len(rolling_buffer) > 15:
                rolling_buffer.pop(0)

            # Nascondiamo i log di debug dal terminale per non inondare lo schermo
            if "DEBUG:" not in line:
                sys.stdout.write(line)

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

                # Salviamo le ultime 15 righe verbose nel log delle anomalie
                last_trace = " | ".join(rolling_buffer[-15:])
                log_anomaly(dir_path, f"CRASH/TIMEOUT STUCK. Verbose Trace: {last_trace}")
                return False

        if process.poll() is not None:
            for line in process.stdout:
                log_raw(line)
                rolling_buffer.append(line.strip())
                if "DEBUG:" not in line:
                    sys.stdout.write(line)
                line_lower = line.lower()
                if any(key in line_lower for key in keywords):
                    anomaly_reasons.append(line.strip())
            break

    exit_code = process.wait()

    if anomaly_reasons:
        diag = get_diagnostic_info(dir_path)
        log_anomaly(dir_path, f"LOG: {' | '.join(anomaly_reasons)} | DIAG: {diag} | CMD: beet import -i \"{dir_path}\"")
        print(f"--> Anomalia Registrata con diagnosi per {dir_path}")
        log_success(dir_path) # Lo segniamo comunque processato
    elif exit_code != 0:
        log_anomaly(dir_path, f"Exited with code {exit_code}")
        log_success(dir_path)
    else:
        log_success(dir_path)
        print(f"--> Successo: {dir_path}")

    return True

def check_for_running_beets(kill=False):
    """Verifica che non ci siano processi 'beet' già in esecuzione sul sistema."""
    try:
        # Cerca i PID dei processi chiamati 'beet'
        res = subprocess.run(["pgrep", "beet"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        pids = [pid for pid in res.stdout.strip().split('\n') if pid.isdigit()]

        if pids:
            if kill:
                print(f"[!] Rilevati processi 'beet' in background (PIDs: {', '.join(pids)}). Li termino prima del reset...")
                subprocess.run(["killall", "beet"], stderr=subprocess.PIPE)
                time.sleep(1) # Aspetta che i processi muoiano effettivamente
            else:
                print(f"\n[!] ATTENZIONE CRITICA: Rilevati processi 'beet' attualmente in esecuzione o sospesi (PIDs: {', '.join(pids)}).")
                print("Avviare istanze parallele causerebbe conflitti nel database e blocchi dalle API di MusicBrainz (Rate Limiting).")
                print("L'esecuzione del batch è stata interrotta per sicurezza.")
                print("-> Esegui un 'reset' per terminarli automaticamente o usa 'killall beet'.\n")
                sys.exit(1)
    except FileNotFoundError:
        pass # Ignora se pgrep non è disponibile sul sistema

def main():
    if len(sys.argv) < 2:
        print("Uso: python3 import_music_batches.py <batch_size|reset>")
        sys.exit(1)

    if sys.argv[1] == "control":
        print("\n=== MUSIC BATCH STATUS ===")
        # 1. Processi
        try:
            res = subprocess.run(["pgrep", "beet"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            pids = [pid for pid in res.stdout.strip().split('\n') if pid.isdigit()]
            if pids:
                print(f"[!] ATTENZIONE: Rilevati {len(pids)} processi 'beet' in esecuzione/sospesi (PIDs: {', '.join(pids)}).")
            else:
                print("[+] Nessun processo 'beet' appeso rilevato.")
        except FileNotFoundError:
            pass

        # 2. Statistiche
        try:
            with open(TARGETS_FILE, "r") as f:
                all_dirs = [line.strip() for line in f if line.strip()]

            processed = load_processed_dirs()
            anomalies_set = set()
            if os.path.exists(ANOMALIES_LOG):
                with open(ANOMALIES_LOG, "r") as f:
                    for line in f:
                        if line.startswith("[") and "] LOG:" in line:
                            path = line.split("] LOG:")[0][1:]
                            anomalies_set.add(path)
            anomalies = len(anomalies_set)

            successes = len(processed) - anomalies
            remaining = len(all_dirs) - len(processed)
            perc = (len(processed) / len(all_dirs) * 100) if all_dirs else 0

            print(f"\n[+] Avanzamento:")
            print(f"    - Target Totali:  {len(all_dirs)}")
            print(f"    - Auto-Import:    {successes} (Completati con successo)")
            print(f"    - Anomalie:       {anomalies} (Saltati / In attesa di review)")
            print(f"    - Rimanenti:      {remaining}")
            print(f"    - Progresso:      {perc:.1f}%\n")
        except FileNotFoundError:
            print("\n[!] Nessun target trovato. Esegui prima 'python3 import_music_batches.py reset'.\n")
        sys.exit(0)

    is_reset = sys.argv[1] == "reset"
    check_for_running_beets(kill=is_reset)

    if is_reset:
        print("[!] ATTENZIONE: Stai per cancellare il database e svuotare il backup.")
        confirm = input("Sei sicuro di voler procedere? (y/N): ")
        if confirm.lower() == 'y':
            db_path = os.path.join(os.path.dirname(__file__), "musiclibrary.db")
            backup_dir = "/Volumes/arrdata/media/music_backup"

            print("Pulisco database...")
            if os.path.exists(db_path): os.remove(db_path)

            print("Svuoto cartella backup...")
            if os.path.exists(backup_dir):
                subprocess.run(f"rm -rf '{backup_dir}' && mkdir -p '{backup_dir}'", shell=True)

            print("Resetto log e stato...")
            for log in [SUCCESS_LOG, ANOMALIES_LOG, RAW_LOG, "beets_batch.log", TARGETS_FILE, "state.pickle"]:
                if os.path.exists(log): os.remove(log)

            print("Eseguo pre-analisi del disco per trovare gli album...")
            valid_extensions = {'.mp3', '.flac', '.m4a', '.ogg', '.wav', '.aac', '.wma'}
            dirs_with_music = set()
            for root, dirs, files in os.walk(SRC_DIR):
                if '/.' in root or '@eaDir' in root:
                    continue
                for f in files:
                    if os.path.splitext(f)[1].lower() in valid_extensions:
                        dirs_with_music.add(root)
                        break

            all_dirs = sorted(list(dirs_with_music))
            with open(TARGETS_FILE, "w") as f:
                for d in all_dirs:
                    f.write(f"{d}\n")
            print(f"Pre-analisi completata: trovate {len(all_dirs)} cartelle con audio.")

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
        with open(TARGETS_FILE, "r") as f:
            all_dirs = [line.strip() for line in f if line.strip()]
    except FileNotFoundError:
        print(f"File {TARGETS_FILE} non trovato. Esegui prima: python3 import_music_batches.py reset")
        sys.exit(1)

    to_process = [d for d in all_dirs if d not in processed_dirs]

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

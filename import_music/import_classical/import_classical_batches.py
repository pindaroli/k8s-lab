#!/usr/bin/env python3
"""
import_classical_batches.py
============================
Pipeline di importazione batch per la Musica Classica.
Architettura identica a import_music_batches.py — con resume automatico,
gestione anomalie, timeout watchdog e modalità control/reset/recover.

UTILIZZO:
  python3 import_classical_batches.py control          # Stato avanzamento
  python3 import_classical_batches.py reset            # Ripartenza da zero
  python3 import_classical_batches.py <N>              # Importa N cartelle
  python3 import_classical_batches.py recover <N>      # Re-importa solo errori tecnici

SORGENTE DATI:
  /Volumes/arrdata/classical/staging/             ← prodotta da segregate_classical.py
  (stesso dataset ZFS di /Volumes/arrdata/classical/library/ — abilita hardlink)
"""

import os
import sys
import time
import subprocess
import select
from pathlib import Path

# ─── Paths ────────────────────────────────────────────────────────────────────
SCRIPT_DIR    = Path(__file__).parent
CONFIG_PATH   = SCRIPT_DIR / "beets_classical_config.yaml"
SRC_DIR       = "/Volumes/classical/staging"

SUCCESS_LOG   = SCRIPT_DIR / "classical_success.log"
ANOMALIES_LOG = SCRIPT_DIR / "classical_anomalies.log"
RAW_LOG       = SCRIPT_DIR / "classical_raw.log"
TARGETS_FILE  = SCRIPT_DIR / "classical_targets.txt"
DB_PATH       = SCRIPT_DIR / "classical_musiclibrary.db"
STATE_FILE    = SCRIPT_DIR / "classical_state.pickle"
BEETS_LOG     = SCRIPT_DIR / "beets_classical_batch.log"

# ─── Tuning ───────────────────────────────────────────────────────────────────
TIMEOUT_SECONDS      = 900   # 15 min senza output = processo bloccato (classica è più lenta)
DELAY_BETWEEN_ALBUMS = 10    # Pausa tra un album e l'altro (rispetto API MusicBrainz)


# ─── Logging helpers ──────────────────────────────────────────────────────────

def load_processed_dirs() -> set:
    if not SUCCESS_LOG.exists():
        return set()
    with open(SUCCESS_LOG, "r") as f:
        return set(line.strip() for line in f if line.strip())


def log_raw(text: str):
    with open(RAW_LOG, "a") as f:
        f.write(text)


def log_success(dir_name: str):
    with open(SUCCESS_LOG, "a") as f:
        f.write(f"{dir_name}\n")


def log_anomaly(dir_name: str, reason: str):
    with open(ANOMALIES_LOG, "a") as f:
        f.write(f"[{dir_name}] LOG: {reason}\n")


# ─── Diagnostics ─────────────────────────────────────────────────────────────

def get_diagnostic_info(dir_path: str) -> str:
    """Esegue un preview beet -p per capire perché Beets ha saltato la cartella."""
    cmd = ["beet", "-v", "-c", str(CONFIG_PATH), "import", "-p", dir_path]
    try:
        res = subprocess.run(
            cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            text=True, timeout=30
        )
        details = []
        for line in res.stdout.splitlines():
            ll = line.lower()
            if any(x in ll for x in ["configuration:", "data directory:", "plugin paths:"]):
                continue
            if any(x in ll for x in ["similarity:", "missing tracks:", "distance:", "parentwork"]):
                details.append(line.strip())
            if "tagging" in ll and "->" in ll:
                details.append(line.strip())
        if not details:
            fallback = [l.strip() for l in res.stdout.splitlines()
                        if "configuration:" not in l.lower() and "directory:" not in l.lower()][:5]
            return " | ".join(fallback)
        return " | ".join(details[:5])
    except Exception as e:
        return f"Diagnosi fallita: {e}"


# ─── Core: process a single directory ────────────────────────────────────────

def process_directory(dir_path: str) -> bool:
    """
    Lancia 'beet import -q' su una singola cartella.
    Ritorna True se il processo è terminato normalmente (anche con anomalie),
    False solo se il watchdog ha rilevato un blocco irreversibile.
    """
    print(f"\n{'='*60}")
    print(f"  IMPORTING: {dir_path}")
    print(f"{'='*60}")
    log_raw(f"\n--- IMPORTING: {dir_path} ---\n")

    cmd = ["beet", "-v", "-c", str(CONFIG_PATH), "import", "-q", dir_path]
    process = subprocess.Popen(
        cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
        text=True, bufsize=1
    )

    last_output_time = time.time()
    anomaly_reasons  = []
    rolling_buffer   = []
    keywords = [
        "no match", "error", "similarity", "confidence",
        "missing tracks", "duplicate"
    ]

    while True:
        rlist, _, _ = select.select([process.stdout], [], [], 5.0)

        if rlist:
            line = process.stdout.readline()
            if not line:
                break  # EOF
            last_output_time = time.time()

            log_raw(line)
            rolling_buffer.append(line.strip())
            if len(rolling_buffer) > 20:
                rolling_buffer.pop(0)

            # Mostriamo tutto tranne il rumore di debug interno di beets
            if "DEBUG:" not in line:
                sys.stdout.write(line)

            line_lower = line.lower()

            # Skip falsi positivi dal log di caricamento plugin
            if "loading plugins:" in line_lower:
                continue

            # Intercettiamo segnali di anomalia significativi (escludendo parentwork)
            if any(key in line_lower for key in keywords) and "parentwork:" not in line_lower:
                if ("previously-imported" not in line_lower
                        and "already in the library" not in line_lower):
                    anomaly_reasons.append(line.strip())
            elif "skipping." in line_lower and "previously" not in line_lower:
                anomaly_reasons.append(line.strip())

        else:
            # Watchdog: nessun output per TIMEOUT_SECONDS
            if time.time() - last_output_time > TIMEOUT_SECONDS:
                print(f"\n[!!!] WATCHDOG: Nessun output per {TIMEOUT_SECONDS}s — processo bloccato. Kill.")
                log_raw(f"TIMEOUT: ucciso dopo {TIMEOUT_SECONDS}s\n")
                process.kill()
                trace = " | ".join(rolling_buffer[-20:])
                log_anomaly(dir_path, f"CRASH/TIMEOUT STUCK. Trace: {trace}")
                return False

        # Drain output residuo se il processo è già terminato
        if process.poll() is not None:
            for line in process.stdout:
                log_raw(line)
                rolling_buffer.append(line.strip())
                if "DEBUG:" not in line:
                    sys.stdout.write(line)
                if any(key in line.lower() for key in keywords) and "parentwork:" not in line.lower():
                    anomaly_reasons.append(line.strip())
            break

    exit_code = process.wait()

    if anomaly_reasons:
        diag = get_diagnostic_info(dir_path)
        log_anomaly(
            dir_path,
            f"{' | '.join(anomaly_reasons)} | DIAG: {diag} | "
            f"CMD: beet import -i \"{dir_path}\""
        )
        print(f"  --> Anomalia registrata: {dir_path}")
        log_success(dir_path)  # Segniamo comunque come processato per il resume
    elif exit_code != 0:
        log_anomaly(dir_path, f"Exit code non-zero: {exit_code}")
        log_success(dir_path)
    else:
        log_success(dir_path)
        print(f"  --> Successo: {os.path.basename(dir_path)}")

    return True


# ─── Process guard ────────────────────────────────────────────────────────────

def check_for_running_beets(kill: bool = False):
    """Impedisce esecuzioni parallele accidentali."""
    try:
        res = subprocess.run(
            ["pgrep", "beet"],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
        )
        pids = [p for p in res.stdout.strip().split('\n') if p.isdigit()]
        if pids:
            if kill:
                print(f"[!] Termino processi beet appesi (PIDs: {', '.join(pids)})...")
                subprocess.run(["killall", "beet"], stderr=subprocess.PIPE)
                time.sleep(1)
            else:
                print(f"\n[!] ATTENZIONE: Processi beet già in esecuzione (PIDs: {', '.join(pids)}).")
                print("    Avviare istanze parallele causa conflitti sul DB SQLite e rate limiting.")
                print("    Usa 'reset' per terminarli o 'killall beet' manualmente.\n")
                sys.exit(1)
    except FileNotFoundError:
        pass


# ─── Subcommands ──────────────────────────────────────────────────────────────

def cmd_control():
    """Mostra lo stato di avanzamento dell'import senza modificare nulla."""
    print("\n=== CLASSICAL BATCH STATUS ===")

    # Controlla se il batch d'importazione principale è in corso
    is_running = False
    pids_batch = []
    try:
        current_pid = str(os.getpid())
        res = subprocess.run(["pgrep", "-f", "import_classical_batches.py"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        pids_batch = [p.strip() for p in res.stdout.strip().split('\n') if p.strip().isdigit() and p.strip() != current_pid]
        if pids_batch:
            is_running = True
    except Exception:
        pass

    if is_running:
        print(f"[🟢] Stato Import    : IN CORSO (Batch attivo, PIDs: {', '.join(pids_batch)})")
    else:
        print(f"[🔴] Stato Import    : INATTIVO / FERMO (Nessun batch in corso)")

    # 1. Processi beet in esecuzione
    try:
        res = subprocess.run(["pgrep", "beet"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        pids = [p for p in res.stdout.strip().split('\n') if p.isdigit()]
        if pids:
            print(f"[!] Processi 'beet'  : ATTIVI (PIDs: {', '.join(pids)})")
        else:
            print("[+] Processi 'beet'  : Nessun sottoprocesso 'beet' attivo")
    except FileNotFoundError:
        pass

    # 2. Avanzamento
    if not TARGETS_FILE.exists():
        print("\n[!] Nessun target trovato. Esegui prima: python3 import_classical_batches.py reset\n")
        sys.exit(0)

    with open(TARGETS_FILE) as f:
        all_dirs = [l.strip() for l in f if l.strip()]

    processed = load_processed_dirs()

    anomalies_set = set()
    if ANOMALIES_LOG.exists():
        with open(ANOMALIES_LOG) as f:
            for line in f:
                if line.startswith("[") and "] LOG:" in line:
                    path = line.split("] LOG:")[0][1:]
                    anomalies_set.add(path)

    anomalies  = len(anomalies_set)
    successes  = len(processed) - anomalies
    remaining  = len(all_dirs) - len(processed)
    perc       = (len(processed) / len(all_dirs) * 100) if all_dirs else 0

    print(f"\n[+] Avanzamento:")
    print(f"    - Target Totali  : {len(all_dirs)}")
    print(f"    - Auto-Import    : {successes} (Completati con successo)")
    print(f"    - Anomalie       : {anomalies} (Saltati / In attesa di review Picard)")
    print(f"    - Rimanenti      : {remaining}")
    print(f"    - Progresso      : {perc:.1f}%\n")
    sys.exit(0)


def cmd_reset():
    """Cancella DB, log, stato e ri-scansiona classical_staging per creare la lista target."""
    check_for_running_beets(kill=True)

    print("[!] RESET: Cancellerà DB beets classica, log e stato incrementale.")
    print(f"    Sorgente audio: {SRC_DIR}")
    confirm = input("Confermare? (y/N): ")
    if confirm.lower() != 'y':
        print("Reset annullato.")
        sys.exit(0)

    # Pulizia
    for f in [DB_PATH, STATE_FILE, SUCCESS_LOG, ANOMALIES_LOG, RAW_LOG, BEETS_LOG, TARGETS_FILE]:
        if f.exists():
            f.unlink()
            print(f"  [DEL] {f.name}")

    # Ri-scansione staging
    if not os.path.isdir(SRC_DIR):
        print(f"\n[ERROR] Staging non trovato: {SRC_DIR}")
        print("        Esegui prima: python3 segregate_classical.py run")
        sys.exit(1)

    print(f"\nScansione sorgente: {SRC_DIR}")
    valid_ext = {'.mp3', '.flac', '.m4a', '.ogg', '.wav', '.aac'}
    dirs_with_music = set()
    for root, dirs, files in os.walk(SRC_DIR):
        if '/.' in root or '@eaDir' in root:
            continue
        for f in files:
            if os.path.splitext(f)[1].lower() in valid_ext:
                dirs_with_music.add(root)
                break

    all_dirs = sorted(dirs_with_music)
    with open(TARGETS_FILE, "w") as f:
        for d in all_dirs:
            f.write(f"{d}\n")

    print(f"Trovate {len(all_dirs)} cartelle con audio in staging.")
    print("Reset completato. Sistema pronto per un nuovo import.\n")
    sys.exit(0)


def cmd_run(batch_size: int, recover_mode: bool = False):
    """Importa le prossime N cartelle dallo staging, riprendendo da dove era rimasto."""
    check_for_running_beets(kill=False)

    processed_dirs = load_processed_dirs()

    if recover_mode:
        # Recover: re-importa solo cartelle con errori tecnici noti (non i match deboli)
        recoverable_keywords = [
            "429:", "JSONDecodeError", "FileNotFoundError",
            "NotFoundError", "file exists", "readonly", "ReadError", "CRASH", "TIMEOUT"
        ]
        recoverable = set()
        if ANOMALIES_LOG.exists():
            with open(ANOMALIES_LOG) as f:
                for line in f:
                    if line.startswith("[") and "] LOG:" in line:
                        path = line.split("] LOG:")[0][1:]
                        if any(kw in line for kw in recoverable_keywords):
                            recoverable.add(path)
        all_dirs = sorted(recoverable)
        print(f"Modalità RECOVER: trovate {len(all_dirs)} cartelle con errori tecnici recuperabili.")
    else:
        if not TARGETS_FILE.exists():
            print(f"[ERROR] {TARGETS_FILE.name} non trovato. Esegui prima: python3 import_classical_batches.py reset")
            sys.exit(1)
        with open(TARGETS_FILE) as f:
            all_dirs = [l.strip() for l in f if l.strip()]

    to_process = [d for d in all_dirs if d not in processed_dirs]

    if not to_process:
        print("✓ Tutte le cartelle dello staging sono state processate!")
        sys.exit(0)

    actual_batch = min(batch_size, len(to_process))
    print(f"\nCartelle totali in staging : {len(all_dirs)}")
    print(f"Già processate             : {len(processed_dirs)}")
    print(f"Rimanenti                  : {len(to_process)}")
    print(f"Batch corrente             : {actual_batch}")

    for i, dir_path in enumerate(to_process[:batch_size]):
        print(f"\nProgress: {i+1}/{actual_batch}")
        if not process_directory(dir_path):
            print("Batch interrotto: watchdog timeout sul processo corrente.")
            break

        if i < batch_size - 1:
            print(f"  Pausa di {DELAY_BETWEEN_ALBUMS}s (rispetto rate limit API)...")
            time.sleep(DELAY_BETWEEN_ALBUMS)

    # Pulizia file fantasma AppleDouble su macOS prima della chiusura
    if sys.platform == "darwin":
        lib_dir = "/Volumes/classical/library"
        if os.path.exists(lib_dir):
            print(f"\n[macOS] Pulizia automatica file fantasma in {lib_dir}...")
            try:
                subprocess.run(["dot_clean", lib_dir], check=True, capture_output=True)
            except Exception as e:
                print(f"[macOS] Avviso: Pulizia dot_clean fallita: {e}")

    print("\nBatch completato.")


# ─── Main ─────────────────────────────────────────────────────────────────────

def main():
    if len(sys.argv) < 2:
        print(__doc__)
        print("Uso: python3 import_classical_batches.py <N|control|reset|recover N>")
        sys.exit(1)

    cmd = sys.argv[1]

    if cmd == "control":
        cmd_control()

    elif cmd == "reset":
        cmd_reset()

    elif cmd == "recover":
        try:
            n = int(sys.argv[2])
        except (IndexError, ValueError):
            print("Uso: python3 import_classical_batches.py recover <N>")
            sys.exit(1)
        cmd_run(n, recover_mode=True)

    else:
        try:
            n = int(cmd)
        except ValueError:
            print(f"Comando non riconosciuto: '{cmd}'")
            print("Uso: python3 import_classical_batches.py <N|control|reset|recover N>")
            sys.exit(1)
        cmd_run(n)


if __name__ == "__main__":
    main()

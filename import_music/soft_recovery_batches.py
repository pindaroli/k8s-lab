#!/usr/bin/env python3
"""
soft_recovery_batches.py
========================
Pipeline di importazione robusta per la Fase 2 (Soft Recovery).
Usa lo stesso engine a tolleranza di errore di import_classical_batches.py:
- Lettura sequenziale da paths_to_recover.txt
- Gestione retry automatici ed exponential backoff per errori di rete
- Watchdog timeout per evitare processi appesi
- Log diagnostici separati per i soft import

UTILIZZO:
  python3 soft_recovery_batches.py control          # Stato avanzamento
  python3 soft_recovery_batches.py reset            # Ripartenza da zero (sola pulizia log soft)
  python3 soft_recovery_batches.py <N>              # Importa N cartelle
  python3 soft_recovery_batches.py recover <N>      # Re-importa solo errori tecnici del soft
"""

import os
import sys
import time
import subprocess
import select
from pathlib import Path

# ─── Paths ────────────────────────────────────────────────────────────────────
SCRIPT_DIR    = Path(__file__).parent
CONFIG_PATH   = SCRIPT_DIR / "soft_recovery_config.yaml"
TARGETS_FILE  = SCRIPT_DIR / "paths_to_recover.txt"

SUCCESS_LOG   = SCRIPT_DIR / "soft_recovery_success.log"
ANOMALIES_LOG = SCRIPT_DIR / "soft_recovery_anomalies.log"
RAW_LOG       = SCRIPT_DIR / "soft_recovery_raw.log"
DB_PATH       = SCRIPT_DIR / "musiclibrary.db"
STATE_FILE    = SCRIPT_DIR / "soft_recovery_state.pickle"
BEETS_LOG     = SCRIPT_DIR / "beets_soft_batch.log"

# Resolving local venv beets binary dynamically
BEET_BIN = str(SCRIPT_DIR / "import_classical" / "venv" / "bin" / "beet")
if not os.path.exists(BEET_BIN):
    BEET_BIN = "beet"


# ─── Tuning ───────────────────────────────────────────────────────────────────
TIMEOUT_SECONDS      = 600   # 10 min senza output = processo bloccato
DELAY_BETWEEN_ALBUMS = 7     # Pausa tra un album e l'altro (rispetto API rate-limit)


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
    """Esegue un preview beet -p per capire perché Beets ha incontrato problemi."""
    cmd = [BEET_BIN, "-v", "-c", str(CONFIG_PATH), "import", "-p", dir_path]
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
            if any(x in ll for x in ["similarity:", "missing tracks:", "distance:"]):
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
    Lancia 'beet import -q' su una singola cartella, con retry esponenziale in caso di errori di rete.
    Ritorna True se il processo è terminato normalmente (anche con anomalie o dopo tentativi),
    False solo se il watchdog ha rilevato un blocco irreversibile.
    """
    max_attempts = 4
    backoff = 30  # secondi di attesa iniziale

    for attempt in range(1, max_attempts + 1):
        if attempt > 1:
            print(f"\n[🔄] RETRY {attempt}/{max_attempts} per {dir_path} dopo errore di rete. Attesa {backoff}s...")
            time.sleep(backoff)
            backoff *= 2  # Raddoppia il tempo di attesa

        print(f"\n{'='*60}")
        print(f"  SOFT IMPORTING (Tentativo {attempt}/{max_attempts}): {dir_path}")
        print(f"{'='*60}")
        log_raw(f"\n--- SOFT IMPORTING: {dir_path} (Tentativo {attempt}) ---\n")

        # Configurazione permissiva con tagging custom
        cmd = [
            BEET_BIN, "-v", "-c", str(CONFIG_PATH),
            "import", "-q",
            "--set", "recovery_status=soft",
            "--set", "recovery_phase=2",
            dir_path
        ]

        process = subprocess.Popen(
            cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            text=True, bufsize=1
        )

        last_output_time = time.time()
        anomaly_reasons  = []
        rolling_buffer   = []
        is_network_error = False

        keywords = [
            "no match", "error", "similarity", "confidence",
            "missing tracks", "duplicate"
        ]

        # Parole chiave che indicano un disservizio di rete o API temporaneo
        network_keywords = [
            "429", "too many requests", "502 bad gateway", "503 service", "504 gateway",
            "jsondecodeerror", "connection aborted", "remotedisconnected", "connection reset",
            "http error", "urlerror", "timeout", "temporary failure"
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

                # Rilevamento errore di rete o API rate-limit
                if any(net_kw in line_lower for net_kw in network_keywords):
                    is_network_error = True

                # Intercettiamo segnali di anomalia significativi
                if any(key in line_lower for key in keywords):
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
                    line_lower = line.lower()
                    if any(net_kw in line_lower for net_kw in network_keywords):
                        is_network_error = True
                    if any(key in line_lower for key in keywords):
                        anomaly_reasons.append(line.strip())
                break

        exit_code = process.wait()

        # Se c'è stato un errore di rete e non abbiamo esaurito i tentativi, eseguiamo retry
        if (is_network_error or exit_code in [2, 3]) and attempt < max_attempts:
            print(f"\n[⚠️] Rilevato errore di rete (Exit code: {exit_code}, Network error flag: {is_network_error}). Eseguo retry...")
            continue

        # Gestione definitiva (successo o anomalia permanente)
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

        break

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
                print("    Usa 'killall beet' manualmente.\n")
                sys.exit(1)
    except FileNotFoundError:
        pass


# ─── Subcommands ──────────────────────────────────────────────────────────────

def cmd_control():
    """Mostra lo stato di avanzamento della Fase 2 senza modificare nulla."""
    print("\n=== SOFT RECOVERY BATCH STATUS ===")

    # Controlla se il batch è in corso
    is_running = False
    pids_batch = []
    try:
        current_pid = str(os.getpid())
        res = subprocess.run(["pgrep", "-f", "soft_recovery_batches.py"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
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
        print(f"\n[!] File dei target ({TARGETS_FILE.name}) non trovato. Esegui prima: python3 isolate_anomalies.py\n")
        sys.exit(0)

    with open(TARGETS_FILE) as f:
        all_dirs = [l.strip() for l in f if l.strip()]
        all_dirs_set = set(all_dirs)

    processed = load_processed_dirs()
    processed_valid = processed.intersection(all_dirs_set)

    anomalies_set = set()
    if ANOMALIES_LOG.exists():
        with open(ANOMALIES_LOG) as f:
            for line in f:
                if line.startswith("[") and "] LOG:" in line:
                    path = line.split("] LOG:")[0][1:]
                    if path in all_dirs_set:
                        anomalies_set.add(path)

    anomalies  = len(anomalies_set)
    successes  = len(processed_valid) - anomalies
    remaining  = len(all_dirs) - len(processed_valid)
    perc       = (len(processed_valid) / len(all_dirs) * 100) if all_dirs else 0

    print(f"\n[+] Avanzamento Fase 2 (Soft Recovery):")
    print(f"    - Target Totali  : {len(all_dirs)}")
    print(f"    - Importati (Soft) : {successes}")
    print(f"    - Nuove Anomalie : {anomalies} (Flipped as-is or error)")
    print(f"    - Rimanenti      : {remaining}")
    print(f"    - Progresso      : {perc:.1f}%\n")
    sys.exit(0)


def cmd_reset():
    """Cancella i log e lo stato della Fase 2."""
    check_for_running_beets(kill=True)

    print("[!] RESET FASE 2: Cancellerà i log e lo stato di soft recovery.")
    confirm = input("Confermare? (y/N): ")
    if confirm.lower() != 'y':
        print("Reset annullato.")
        sys.exit(0)

    # Rimuoviamo solo i file legati alla fase 2
    for f in [SUCCESS_LOG, ANOMALIES_LOG, RAW_LOG, STATE_FILE, BEETS_LOG]:
        if f.exists():
            f.unlink()
            print(f"  [DEL] {f.name}")

    print("Reset Fase 2 completato.\n")
    sys.exit(0)


def cmd_run(batch_size: int, recover_mode: bool = False):
    """Importa le prossime N cartelle dagli scarti, riprendendo da dove era rimasto."""
    check_for_running_beets(kill=False)

    processed_dirs = load_processed_dirs()

    if recover_mode:
        # Recover: re-importa solo cartelle con errori tecnici noti
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
        print(f"Modalità RECOVER FASE 2: trovate {len(all_dirs)} cartelle con errori tecnici recuperabili.")
    else:
        if not TARGETS_FILE.exists():
            print(f"[ERROR] {TARGETS_FILE.name} non trovato. Generalo con: python3 isolate_anomalies.py")
            sys.exit(1)
        with open(TARGETS_FILE) as f:
            all_dirs = [l.strip() for l in f if l.strip()]

    to_process = [d for d in all_dirs if d not in processed_dirs]

    if not to_process:
        print("✓ Tutte le cartelle degli scarti sono state processate!")
        sys.exit(0)

    actual_batch = min(batch_size, len(to_process))
    print(f"\nCartelle totali da recuperare: {len(all_dirs)}")
    print(f"Già processate in Fase 2     : {len(processed_dirs)}")
    print(f"Rimanenti                    : {len(to_process)}")
    print(f"Batch corrente               : {actual_batch}")

    for i, dir_path in enumerate(to_process[:batch_size]):
        print(f"\nProgress: {i+1}/{actual_batch}")
        if not process_directory(dir_path):
            print("Batch interrotto: watchdog timeout sul processo corrente.")
            break

        if i < batch_size - 1:
            print(f"  Pausa di {DELAY_BETWEEN_ALBUMS}s (API rate limit)...")
            time.sleep(DELAY_BETWEEN_ALBUMS)

    # Pulizia file fantasma AppleDouble su macOS prima della chiusura
    if sys.platform == "darwin":
        lib_dir = "/Volumes/arrdata/media/music_backup"
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
        print("Uso: python3 soft_recovery_batches.py <N|control|reset|recover N>")
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
            print("Uso: python3 soft_recovery_batches.py recover <N>")
            sys.exit(1)
        cmd_run(n, recover_mode=True)

    else:
        try:
            n = int(cmd)
        except ValueError:
            print(f"Comando non riconosciuto: '{cmd}'")
            print("Uso: python3 soft_recovery_batches.py <N|control|reset|recover N>")
            sys.exit(1)
        cmd_run(n)


if __name__ == "__main__":
    main()

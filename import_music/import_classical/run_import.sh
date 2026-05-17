#!/bin/bash
# ============================================================
# run_import.sh — Launcher Unico Pipeline Musica Classica
# ============================================================
# UTILIZZO:
#   ./run_import.sh segregate-dry    # Identifica le cartelle classiche (solo stampa)
#   ./run_import.sh segregate        # Sposta fisicamente in classical_staging
#   ./run_import.sh reset            # Ripartenza da zero (cancella DB e log)
#   ./run_import.sh batch <N>        # Importa le prossime N cartelle (resume)
#   ./run_import.sh control          # Stato avanzamento import
#   ./run_import.sh recover <N>      # Re-importa solo errori tecnici
#   ./run_import.sh import-dry       # Preview import beets su classical_staging
#   ./run_import.sh status           # Mostra statistiche DB beets classica
#   ./run_import.sh triage           # Lista i file in _Triage_Unmatched
# ============================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CONFIG="$SCRIPT_DIR/beets_classical_config.yaml"
STAGING="/Volumes/classical/staging"
CLASSICAL_LIB="/Volumes/classical/library"
BATCH_SCRIPT="$SCRIPT_DIR/import_classical_batches.py"

# Local virtual environment resolution
PYTHON_BIN="$SCRIPT_DIR/venv/bin/python3"
BEET_BIN="$SCRIPT_DIR/venv/bin/beet"

if [ ! -f "$PYTHON_BIN" ]; then
    PYTHON_BIN="python3"
fi

if [ ! -f "$BEET_BIN" ]; then
    BEET_BIN="beet"
fi

print_header() {
    echo ""
    echo "╔════════════════════════════════════════════════════════════╗"
    echo "║         🎼 Classical Music Pipeline — Launcher             ║"
    echo "╚════════════════════════════════════════════════════════════╝"
    echo ""
}

check_mount() {
    if [ ! -d "/Volumes/arrdata/media" ]; then
        echo "[ERROR] Mount NFS /Volumes/arrdata/media non disponibile."
        echo "        Montare il volume NFS prima di procedere."
        exit 1
    fi
    echo "[OK] Mount NFS rilevato."
}

check_network() {
    echo -n "[CHECK] Verifica connettività verso musicbrainz.org... "
    if curl -s --connect-timeout 5 https://musicbrainz.org > /dev/null; then
        echo "OK"
    else
        echo "FALLITO"
        echo "[ERROR] Impossibile raggiungere musicbrainz.org."
        echo "        Verifica la tua connessione internet o le regole DNSBL su OPNsense."
        exit 1
    fi
}

# ─── Fase 1: Segregazione ────────────────────────────────────────────────────

cmd_segregate_dry() {
    print_header
    echo "[FASE 1] Segregazione Classica — DRY-RUN (nessun file verrà spostato)"
    echo ""
    check_mount
    "$PYTHON_BIN" "$SCRIPT_DIR/segregate_classical.py"
}

cmd_segregate() {
    print_header
    echo "[FASE 1] Segregazione Classica — ESECUZIONE REALE"
    echo ""
    check_mount
    echo "[WARN] Questa operazione sposta fisicamente le cartelle classiche in:"
    echo "       $STAGING"
    echo ""
    read -p "Confermare? (digita 'si' per procedere): " confirm
    if [ "$confirm" = "si" ]; then
        "$PYTHON_BIN" "$SCRIPT_DIR/segregate_classical.py" run
    else
        echo "Annullato."
    fi
}

# ─── Fase 2: Import Batch con resume automatico ───────────────────────────────

cmd_reset() {
    print_header
    echo "[RESET] Cancella DB, log, stato incrementale, svuota la library finale e ri-scansiona staging."
    echo ""
    check_mount
    echo "[CLEANUP] Rimozione di tutti i file e cartelle in: $CLASSICAL_LIB"
    # Svuota in sicurezza la library senza rimuovere la cartella radice stessa
    find "$CLASSICAL_LIB" -mindepth 1 -maxdepth 1 -exec rm -rf {} +
    "$PYTHON_BIN" "$BATCH_SCRIPT" reset
}

cmd_batch() {
    local n="${1:-50}"
    print_header
    echo "[BATCH] Importa le prossime $n cartelle (riprende da dove è rimasto)"
    echo ""
    check_mount
    check_network
    "$PYTHON_BIN" "$BATCH_SCRIPT" "$n"
}

cmd_control() {
    print_header
    "$PYTHON_BIN" "$BATCH_SCRIPT" control
}

cmd_recover() {
    local n="${1:-50}"
    print_header
    echo "[RECOVER] Re-importa le $n cartelle con errori tecnici (timeout/crash)"
    echo ""
    check_mount
    check_network
    "$PYTHON_BIN" "$BATCH_SCRIPT" recover "$n"
}

# ─── Utility ─────────────────────────────────────────────────────────────────

cmd_import_dry() {
    print_header
    echo "[PREVIEW] Import Beets Classica — DRY-RUN (nessuna modifica)"
    echo ""
    check_mount
    check_network
    if [ ! -d "$STAGING" ]; then
        echo "[ERROR] Staging non trovato: $STAGING"
        echo "        Eseguire prima: ./run_import.sh segregate"
        exit 1
    fi
    "$BEET_BIN" -c "$CONFIG" import -p "$STAGING"
}

cmd_status() {
    print_header
    echo "[STATUS] Libreria classica Beets"
    echo ""
    DB="$SCRIPT_DIR/classical_musiclibrary.db"
    if [ ! -f "$DB" ]; then
        echo "[INFO] DB non ancora creato. Eseguire prima un import."
        exit 0
    fi
    echo "  Album importati:"
    "$BEET_BIN" -c "$CONFIG" stats
    echo ""
    echo "  Path Triage (non risolti):"
    "$BEET_BIN" -c "$CONFIG" ls albumstatus:asis 2>/dev/null | wc -l | xargs -I{} echo "  {} tracce in _Triage_Unmatched"
}

cmd_triage() {
    print_header
    echo "[TRIAGE] File non risolti da processare manualmente con Picard"
    echo ""
    "$BEET_BIN" -c "$CONFIG" ls albumstatus:asis 2>/dev/null || echo "Nessun file in triage o DB non ancora creato."
}

cmd_setup_env() {
    print_header
    echo "[SETUP-ENV] Inizializzazione ambiente virtuale isolato per Beets"
    echo ""

    # Rileva se python3.12 è installato, altrimenti ripiega su python3
    local py_cmd="python3.12"
    if ! command -v python3.12 >/dev/null 2>&1; then
        echo "[WARN] python3.12 non rilevato globalmente. Cerco python3..."
        py_cmd="python3"
    fi

    echo "  -> Utilizzo: $($py_cmd --version 2>/dev/null || $py_cmd -V)"
    echo "  -> Creazione venv in: $SCRIPT_DIR/venv"

    # Rimuove il vecchio venv se parziale/corrotto
    rm -rf "$SCRIPT_DIR/venv"

    if ! "$py_cmd" -m venv "$SCRIPT_DIR/venv"; then
        echo "[ERROR] Impossibile creare il venv con $py_cmd."
        exit 1
    fi

    echo "  -> Aggiornamento pip..."
    "$SCRIPT_DIR/venv/bin/pip" install --upgrade pip >/dev/null

    echo "  -> Installazione dipendenze Beets..."
    if "$SCRIPT_DIR/venv/bin/pip" install beets mutagen pyacoustid discogs-client requests musicbrainzngs pylast; then
        echo ""
        echo "[OK] Ambiente virtuale locale inizializzato correttamente!"
        echo "     I comandi './run_import.sh' useranno ora questo venv."
    else
        echo "[ERROR] Installazione dipendenze fallita."
        exit 1
    fi
}

# ─── Main ────────────────────────────────────────────────────────────────────
case "${1:-help}" in
    segregate-dry)  cmd_segregate_dry ;;
    segregate)      cmd_segregate ;;
    reset)          cmd_reset ;;
    batch)          cmd_batch "${2:-50}" ;;
    control)        cmd_control ;;
    recover)        cmd_recover "${2:-50}" ;;
    import-dry)     cmd_import_dry ;;
    status)         cmd_status ;;
    triage)         cmd_triage ;;
    setup-env)      cmd_setup_env ;;
    *)
        print_header
        echo "UTILIZZO: ./run_import.sh <comando> [argomenti]"
        echo ""
        echo "  ── FASE 1: SEGREGAZIONE ──────────────────────────────────"
        echo "  segregate-dry          Identifica cartelle classiche (safe, solo stampa)"
        echo "  segregate              Sposta le cartelle in classical_staging (modifica FS)"
        echo ""
        echo "  ── FASE 2: IMPORT BATCH (con resume automatico) ──────────"
        echo "  reset                  Cancella DB/log e ri-scansiona staging"
        echo "  batch <N>              Importa le prossime N cartelle (default: 50)"
        echo "  control                Mostra stato avanzamento"
        echo "  recover <N>            Re-importa N cartelle con errori tecnici"
        echo ""
        echo "  ── UTILITY ───────────────────────────────────────────────"
        echo "  setup-env              Inizializza/Ripristina l'ambiente locale Python 3.12"
        echo "  import-dry             Preview beets — nessuna modifica"
        echo "  status                 Statistiche libreria Beets classica"
        echo "  triage                 Lista file non risolti per Picard"
        echo ""
        ;;
esac

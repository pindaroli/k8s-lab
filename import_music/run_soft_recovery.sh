#!/bin/bash
# ============================================================
# run_soft_recovery.sh — Launcher Unico Pipeline Soft Recovery (Fase 2)
# ============================================================
# UTILIZZO:
#   ./run_soft_recovery.sh reset            # Ripartenza da zero (cancella log soft recovery)
#   ./run_soft_recovery.sh batch <N>        # Importa le prossime N cartelle dagli scarti
#   ./run_soft_recovery.sh control          # Stato avanzamento import soft
#   ./run_soft_recovery.sh recover <N>      # Re-importa solo errori tecnici del soft
#   ./run_soft_recovery.sh status           # Mostra statistiche del DB beets globale
# ============================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CONFIG="$SCRIPT_DIR/soft_recovery_config.yaml"
BATCH_SCRIPT="$SCRIPT_DIR/soft_recovery_batches.py"

# Local virtual environment resolution (shared with classical import)
PYTHON_BIN="$SCRIPT_DIR/import_classical/venv/bin/python3"
BEET_BIN="$SCRIPT_DIR/import_classical/venv/bin/beet"

if [ ! -f "$PYTHON_BIN" ]; then
    PYTHON_BIN="python3"
fi

if [ ! -f "$BEET_BIN" ]; then
    BEET_BIN="beet"
fi

print_header() {
    echo ""
    echo "╔════════════════════════════════════════════════════════════╗"
    echo "║         🔄 Soft Recovery Phase 2 — Launcher                ║"
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

cmd_reset() {
    print_header
    echo "[RESET] Cancella log e stato incrementale di Fase 2."
    echo ""
    check_mount
    "$PYTHON_BIN" "$BATCH_SCRIPT" reset
}

cmd_batch() {
    local n="${1:-50}"
    print_header
    echo "[BATCH] Importa le prossime $n cartelle dagli scarti (recovery_status=soft)"
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
    echo "[RECOVER] Re-importa le $n cartelle con errori tecnici (timeout/crash) di Fase 2"
    echo ""
    check_mount
    check_network
    "$PYTHON_BIN" "$BATCH_SCRIPT" recover "$n"
}

cmd_status() {
    print_header
    echo "[STATUS] Stato Libreria Beets (musiclibrary.db)"
    echo ""
    DB="$SCRIPT_DIR/musiclibrary.db"
    if [ ! -f "$DB" ]; then
        echo "[INFO] DB non ancora creato. Eseguire prima un import."
        exit 0
    fi
    echo "  Album totali in libreria:"
    "$BEET_BIN" -c "$CONFIG" stats
    echo ""
    echo "  Album con recovery_status=soft:"
    "$BEET_BIN" -c "$CONFIG" ls recovery_status:soft 2>/dev/null | wc -l | xargs -I{} echo "  {} tracce importate via Soft Recovery"
}

# ─── Main ────────────────────────────────────────────────────────────────────
case "${1:-help}" in
    reset)          cmd_reset ;;
    batch)          cmd_batch "${2:-50}" ;;
    control)        cmd_control ;;
    recover)        cmd_recover "${2:-50}" ;;
    status)         cmd_status ;;
    *)
        print_header
        echo "UTILIZZO: ./run_soft_recovery.sh <comando> [argomenti]"
        echo ""
        echo "  reset                  Cancella log e stato incrementale di Fase 2"
        echo "  batch <N>              Importa le prossime N cartelle dagli scarti (default: 50)"
        echo "  control                Mostra stato avanzamento Fase 2"
        echo "  recover <N>            Re-importa N cartelle con errori tecnici di Fase 2"
        echo "  status                 Mostra statistiche del DB beets principale"
        echo ""
        ;;
esac

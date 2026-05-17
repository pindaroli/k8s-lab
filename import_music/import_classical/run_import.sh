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

# ─── Fase 1: Segregazione ────────────────────────────────────────────────────

cmd_segregate_dry() {
    print_header
    echo "[FASE 1] Segregazione Classica — DRY-RUN (nessun file verrà spostato)"
    echo ""
    check_mount
    python3 "$SCRIPT_DIR/segregate_classical.py"
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
        python3 "$SCRIPT_DIR/segregate_classical.py" run
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
    python3 "$BATCH_SCRIPT" reset
}

cmd_batch() {
    local n="${1:-50}"
    print_header
    echo "[BATCH] Importa le prossime $n cartelle (riprende da dove è rimasto)"
    echo ""
    check_mount
    python3 "$BATCH_SCRIPT" "$n"
}

cmd_control() {
    print_header
    python3 "$BATCH_SCRIPT" control
}

cmd_recover() {
    local n="${1:-50}"
    print_header
    echo "[RECOVER] Re-importa le $n cartelle con errori tecnici (timeout/crash)"
    echo ""
    check_mount
    python3 "$BATCH_SCRIPT" recover "$n"
}

# ─── Utility ─────────────────────────────────────────────────────────────────

cmd_import_dry() {
    print_header
    echo "[PREVIEW] Import Beets Classica — DRY-RUN (nessuna modifica)"
    echo ""
    check_mount
    if [ ! -d "$STAGING" ]; then
        echo "[ERROR] Staging non trovato: $STAGING"
        echo "        Eseguire prima: ./run_import.sh segregate"
        exit 1
    fi
    beet -c "$CONFIG" import -p "$STAGING"
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
    beet -c "$CONFIG" stats
    echo ""
    echo "  Path Triage (non risolti):"
    beet -c "$CONFIG" ls albumstatus:asis 2>/dev/null | wc -l | xargs -I{} echo "  {} tracce in _Triage_Unmatched"
}

cmd_triage() {
    print_header
    echo "[TRIAGE] File non risolti da processare manualmente con Picard"
    echo ""
    beet -c "$CONFIG" ls albumstatus:asis 2>/dev/null || echo "Nessun file in triage o DB non ancora creato."
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
        echo "  import-dry             Preview beets — nessuna modifica"
        echo "  status                 Statistiche libreria Beets classica"
        echo "  triage                 Lista file non risolti per Picard"
        echo ""
        ;;
esac

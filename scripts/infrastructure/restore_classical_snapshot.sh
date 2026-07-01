#!/bin/bash
# Script per ripristinare library e staging dallo snapshot manual-2026-05-21_05-22
# Adatto all'esecuzione su TrueNAS SCALE
#
# UTILIZZO:
#   Di default, lo script gira in modalità DRY-RUN (simulazione sicura).
#   Per applicare realmente le modifiche distruttive, passare il flag --run o --confirm:
#     bash ./restore_classical_snapshot.sh --run

# Configurazione percorsi
BASE_PATH="/mnt/oliraid/arrdata/classical"
SNAPSHOT_PATH="${BASE_PATH}/.zfs/snapshot/manual-2026-05-21_05-22"

LIBRARY_DIR="${BASE_PATH}/library"
STAGING_DIR="${BASE_PATH}/staging"

SNAP_LIBRARY_DIR="${SNAPSHOT_PATH}/library"
SNAP_STAGING_DIR="${SNAPSHOT_PATH}/staging"

# 0. PARSING ARGOMENTI (DRY-RUN DI DEFAULT PER MASSIMA SICUREZZA)
DRY_RUN=true
for arg in "$@"; do
    case $arg in
        --run|--confirm)
            DRY_RUN=false
            shift
            ;;
        --dry-run|-d)
            DRY_RUN=true
            shift
            ;;
        *)
            echo "Opzione sconosciuta: $arg"
            echo "Uso: $0 [--run|--confirm] [--dry-run|-d]"
            exit 1
            ;;
    esac
done

echo "=========================================================="
if [ "$DRY_RUN" = true ]; then
    echo "  AVVIO SIMULAZIONE RIPRISTINO (DRY-RUN) "
    echo "  (Nessun file verrà realmente cancellato o copiato)"
else
    echo "  ⚠️ AVVIO RIPRISTINO REALE DA SNAPSHOT (DISTRUTTIVO) ⚠️"
fi
echo "  Snapshot di origine: manual-2026-05-21_05-22"
echo "  Logica staging: Sovrascrittura (nessuno svuotamento)"
echo "  Logica library: Svuotamento preventivo e ripristino"
echo "=========================================================="

# 1. CONTROLLI DI SICUREZZA PREVENTIVI
echo "Esecuzione controlli di sicurezza in corso..."

# Verifica esistenza dello snapshot sorgente
if [ ! -d "$SNAPSHOT_PATH" ]; then
    echo "Errore: Lo snapshot $SNAPSHOT_PATH non esiste!" >&2
    exit 1
fi
if [ ! -d "$SNAP_LIBRARY_DIR" ] || [ ! -d "$SNAP_STAGING_DIR" ]; then
    echo "Errore: Le cartelle dello snapshot non sono complete (library o staging mancante)!" >&2
    exit 1
fi

# Verifica esistenza delle cartelle di destinazione
if [ ! -d "$LIBRARY_DIR" ] || [ ! -d "$STAGING_DIR" ]; then
    echo "Errore: Le cartelle di destinazione ($LIBRARY_DIR o $STAGING_DIR) non esistono!" >&2
    exit 1
fi

# Se non è un dry-run, verifichiamo la scrivibilità effettiva
if [ "$DRY_RUN" = false ]; then
    if [ ! -w "$LIBRARY_DIR" ] || [ ! -w "$STAGING_DIR" ]; then
        echo "Errore: Permessi di scrittura insufficienti sulle destinazioni!" >&2
        exit 1
    fi
fi

echo "Controlli di sicurezza superati con successo."
echo "----------------------------------------------------------"

# 2. SVUOTAMENTO DELLE DESTINAZIONI (SOLO PER LIBRARY)
if [ "$DRY_RUN" = true ]; then
    files_lib=$(find "$LIBRARY_DIR" -mindepth 1 -type f 2>/dev/null | wc -l)
    dirs_lib=$(find "$LIBRARY_DIR" -mindepth 1 -type d 2>/dev/null | wc -l)

    echo "[DRY-RUN] Simulazione svuotamento 'library':"
    echo "  -> Verrebbero eliminati $files_lib file e $dirs_lib cartelle in $LIBRARY_DIR"
    echo "[DRY-RUN] Info 'staging':"
    echo "  -> 'staging' NON verrà svuotato (i file pre-esistenti non coincidenti rimarranno intatti)."
else
    echo "Svuotamento directory 'library' in corso..."
    find "$LIBRARY_DIR" -mindepth 1 -delete
    echo "Directory 'library' svuotata con successo."

    echo "Info: 'staging' non viene svuotato (andiamo direttamente in sovrascrittura)."
fi
echo "----------------------------------------------------------"

# 3. COPIA INTEGRALE / SOVRASCRITTURA DALLO SNAPSHOT
if [ "$DRY_RUN" = true ]; then
    snap_files_lib=$(find -P "$SNAP_LIBRARY_DIR" -type f 2>/dev/null | wc -l)
    snap_files_stg=$(find -P "$SNAP_STAGING_DIR" -type f 2>/dev/null | wc -l)

    echo "[DRY-RUN] Simulazione ripristino 'library':"
    echo "  -> Verrebbero copiati $snap_files_lib file reali dallo snapshot in $LIBRARY_DIR"
    echo "[DRY-RUN] Simulazione sovrascrittura 'staging':"
    echo "  -> Verrebbero sovrascritti/copiati $snap_files_stg file dallo snapshot in $STAGING_DIR"
else
    echo "Ripristino 'library' dallo snapshot..."
    cp -a "${SNAP_LIBRARY_DIR}/." "$LIBRARY_DIR/"
    echo "Ripristino 'library' completato."

    echo "Sovrascrittura 'staging' dallo snapshot in corso..."
    cp -a "${SNAP_STAGING_DIR}/." "$STAGING_DIR/"
    echo "Sovrascrittura 'staging' completata."
fi

echo "=========================================================="
if [ "$DRY_RUN" = true ]; then
    echo "  SIMULAZIONE COMPLETATA CON SUCCESSO!"
    echo "  Per eseguire realmente il ripristino, lancia:"
    echo "  bash ./restore_classical_snapshot.sh --run"
else
    echo "  ⚠️ RIPRISTINO DA SNAPSHOT COMPLETATO CON SUCCESSO! ⚠️"
fi
echo "=========================================================="

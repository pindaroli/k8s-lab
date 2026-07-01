#!/bin/bash
# Script per identificare lo snapshot di oliraid/arrdata/classical con il massimo numero di file in staging
# Adatto all'esecuzione su TrueNAS SCALE
# NOTA: I link simbolici (symlink) vengono esplicitamente esclusi dal conteggio.

# Configurazione del dataset e del percorso degli snapshot
DATASET_PATH="/mnt/oliraid/arrdata/classical"
SNAPSHOT_DIR="${DATASET_PATH}/.zfs/snapshot"
TARGET_SUBDIR="staging"

# 1. Verifica che la directory degli snapshot ZFS sia accessibile
if [ ! -d "$SNAPSHOT_DIR" ]; then
    echo "Errore: La directory degli snapshot non è accessibile o non esiste a $SNAPSHOT_DIR" >&2
    exit 1
fi

max_count=-1
max_snapshot=""

echo "=========================================================="
echo "Analisi degli snapshot di ${DATASET_PATH} in corso..."
echo "=========================================================="

# 2. Iterazione su tutti gli snapshot
# Utilizziamo find per gestire in sicurezza eventuali caratteri speciali o spazi nei nomi degli snapshot
while IFS= read -r snap_path; do
    [ -d "$snap_path" ] || continue
    snap_name=$(basename "$snap_path")

    # Percorso target
    target_dir="${snap_path}/${TARGET_SUBDIR}"

    # 3. Conteggio ricorsivo dei file
    if [ -d "$target_dir" ]; then
        # -P: non segue MAI i link simbolici
        # -type f: trova solo file regolari (escludendo fisicamente i symlink, che sono di tipo 'l')
        file_count=$(find -P "$target_dir" -type f 2>/dev/null | wc -l)

        echo "Snapshot: '$snap_name' -> $file_count file reali trovati in $TARGET_SUBDIR (esclusi symlink)"

        # 4. Tracciamento del massimo
        if [ "$file_count" -gt "$max_count" ]; then
            max_count=$file_count
            max_snapshot=$snap_name
        fi
    else
        echo "Snapshot: '$snap_name' -> Cartella target non presente"
    fi
done < <(find "$SNAPSHOT_DIR" -maxdepth 1 -mindepth 1 -type d 2>/dev/null)

# 5. Stampa del risultato finale richiesto
echo "=========================================================="
if [ "$max_count" -ge 0 ]; then
    echo "RISULTATO:"
    echo "Lo snapshot con il massimo numero di file reali (esclusi symlink) in staging è:"
    echo "--> $max_snapshot"
    echo "Con un totale di: $max_count file"
else
    echo "Nessuno snapshot valido o contenente la cartella target è stato trovato."
fi
echo "=========================================================="

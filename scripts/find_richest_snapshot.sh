#!/bin/bash
# Script per identificare lo snapshot di oliraid/arrdata con il maggior numero di file di staging/musica

SNAPSHOT_DIR="/mnt/oliraid/arrdata/.zfs/snapshot"

echo "=========================================================="
echo "Analisi degli snapshot del dataset oliraid/arrdata su TrueNAS"
echo "=========================================================="

# Utilizziamo find per elencare i percorsi degli snapshot per gestire in sicurezza gli spazi finali
find "$SNAPSHOT_DIR" -maxdepth 1 -mindepth 1 -type d | while read -r snap_path; do
    snap_name=$(basename "$snap_path")

    # Definizione delle possibili sotto-cartelle di staging/musica
    path_backup="$snap_path/media/music_backup"
    path_music="$snap_path/media/music"
    path_classical="$snap_path/classical/staging"
    path_direct_staging="$snap_path/music/staging"
    path_direct_stanging="$snap_path/music/stanging"

    count_backup=0
    count_music=0
    count_classical=0
    count_direct=0

    # Conteggio dei file se la directory esiste
    if [ -d "$path_backup" ]; then
        count_backup=$(find "$path_backup" -type f | wc -l)
    fi
    if [ -d "$path_music" ]; then
        count_music=$(find "$path_music" -type f | wc -l)
    fi
    if [ -d "$path_classical" ]; then
        count_classical=$(find "$path_classical" -type f | wc -l)
    fi
    if [ -d "$path_direct_staging" ]; then
        count_direct=$(find "$path_direct_staging" -type f | wc -l)
    elif [ -d "$path_direct_stanging" ]; then
        count_direct=$(find "$path_direct_stanging" -type f | wc -l)
    fi

    # Totale combinato delle cartelle adibite a staging/backup
    total_staging_files=$((count_backup + count_classical + count_direct))

    echo "Snapshot: '$snap_name'"
    echo "  - media/music_backup : $count_backup file"
    echo "  - media/music        : $count_music file"
    echo "  - classical/staging  : $count_classical file"
    echo "  - music/staging      : $count_direct file"
    echo "  - TOTALE DI STAGING  : $total_staging_files file"
    echo "----------------------------------------------------------"
done

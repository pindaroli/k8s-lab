#!/usr/bin/env bash
# Comandi beet mbsync per canonicalizzazione via MusicBrainz
# Generato da detect_case_clashes.py — Fase 4.2

# ATTENZIONE: questi comandi aggiornano il DB di Beets.
# Eseguire SOLO dopo aver completato la Fase 4.1 e con il batch fermo.

BEET_CONFIG=/Users/olindo/prj/k8s-lab/import_music/import_music_batches-config.yaml

beet --config="$BEET_CONFIG" mbsync albumartist:"elio e le storie tese"

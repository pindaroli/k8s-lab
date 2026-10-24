#!/bin/bash
# ==============================================================================
# Script: 02-trickplay-config.sh
# Scopo: Garantisce che le impostazioni Trickplay in system.xml siano sempre
#        ottimizzate (KeyFrameOnly=true, Threads=2) per evitare timeout CPU
#        durante l'estrazione miniature da film 4K HEVC HDR.
# ==============================================================================

CONFIG_FILE="/config/system.xml"

if [ -f "$CONFIG_FILE" ]; then
    if grep -q "<EnableKeyFrameOnlyExtraction>false</EnableKeyFrameOnlyExtraction>" "$CONFIG_FILE"; then
        echo "[custom-cont-init] Abilitazione automatica EnableKeyFrameOnlyExtraction in system.xml..."
        sed -i 's|<EnableKeyFrameOnlyExtraction>false</EnableKeyFrameOnlyExtraction>|<EnableKeyFrameOnlyExtraction>true</EnableKeyFrameOnlyExtraction>|g' "$CONFIG_FILE"
    fi
    if grep -q "<ProcessThreads>1</ProcessThreads>" "$CONFIG_FILE"; then
        echo "[custom-cont-init] Ottimizzazione automatica ProcessThreads (1 -> 2) in system.xml..."
        sed -i 's|<ProcessThreads>1</ProcessThreads>|<ProcessThreads>2</ProcessThreads>|g' "$CONFIG_FILE"
    fi
fi

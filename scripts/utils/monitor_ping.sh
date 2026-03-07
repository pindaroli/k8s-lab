#!/bin/bash
# Monitoraggio continuo del ping verso il Gateway con log solo dei fallimenti.

TARGET="10.10.20.1"

echo "Avvio monitoraggio verso $TARGET."
echo "Verranno mostrati a video SOLO i fallimenti."

while true; do
  # Esegue un ping. Salva output e exit code.
  # Se successo (exit 0) -> non fa nulla (sleep 1).
  # Se errore -> Stampa DATA + ERRORE PING + STATO INTERFACCIA.
  
  OUTPUT=$(ping -c 1 -W 1 "$TARGET" 2>&1)
  if [ $? -ne 0 ]; then
    NOW=$(date "+%H:%M:%S")
    echo "---------------------------------------------------"
    echo "[$NOW] ❌ PING FALLITO"
    echo "Errore: $OUTPUT"
    echo "Stato Media: $(ifconfig en10 | grep media)"
    echo "---------------------------------------------------"
  else
    # Opzionale: decommenta riga sotto per vedere un puntino quando funziona
    # echo -n "."
    sleep 0.5
  fi
done

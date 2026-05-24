#!/usr/bin/env bash
# Script di patch architetturale per qBittorrent.conf
# Validato e sicuro per macOS (BSD) e Linux (GNU)
set -euo pipefail

TARGET_CONF="/Volumes/k8s-arr/servarr-qbittorrent/qBittorrent/qBittorrent.conf"

if [ ! -f "$TARGET_CONF" ]; then
    echo "Errore: File di configurazione non trovato in $TARGET_CONF" >&2
    exit 1
fi

# Creazione di una copia di backup di sicurezza
cp "$TARGET_CONF" "${TARGET_CONF}.bak"

# Rilevamento della tipologia di sed (GNU vs BSD)
if sed --version 2>&1 | grep -q "GNU"; then
    SED_INPLACE=(sed -i)
else
    SED_INPLACE=(sed -i '')
fi

# Funzione per inserire o aggiornare chiavi mantenendo lo schema Qt di qBittorrent
patch_key() {
    local key="$1"
    local value="$2"
    # Escaping dei backslash per la regex di ricerca e sostituzione di sed
    local search_key
    search_key=$(echo "$key" | sed 's|\\|\\\\|g')

    if grep -qF "$key" "$TARGET_CONF"; then
        # Se la chiave esiste, viene aggiornata
        "${SED_INPLACE[@]}" "s|^${search_key}=.*|${key}=${value}|" "$TARGET_CONF"
    else
        # Se la chiave manca, viene inserita subito sotto la sezione [Preferences]
        "${SED_INPLACE[@]}" "/^\[Preferences\]/a\\
${key}=${value}
" "$TARGET_CONF"
    fi
}

# Applicazione delle impostazioni di percorso e dei flag di abilitazione obbligatori
patch_key "Session\TempPath" "/data/incomplete"
patch_key "Session\TempPathEnabled" "true"
patch_key "Downloads\TempPath" "/data/incomplete/"
patch_key "Downloads\TempPathEnabled" "true"

echo "Patch di configurazione applicata con successo su $TARGET_CONF"

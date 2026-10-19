#!/usr/bin/env bash
# ==============================================================================
# PROCEDURE_SCOPE.SH — Gestore del ciclo di vita gerarchico delle procedure
# ==============================================================================
# Questo modulo gestisce lo stato gerarchico di esecuzione (Root vs Child)
# attraverso la variabile d'ambiente esportata HOMELAB_PARENT_PROCEDURE.
# Riferimento architetturale: [[hierarchical-automation-alerting-pattern]]
# ==============================================================================

# Inizializza il contesto della procedura.
# Se HOMELAB_PARENT_PROCEDURE non è impostata, questo script opera come Root (master).
# Se è già impostata, questo script opera come Child (sub-procedura / sotto-fase).
init_procedure_scope() {
    local proc_name="$1"
    CURRENT_PROCEDURE_NAME="$proc_name"
    if [ -z "${HOMELAB_PARENT_PROCEDURE:-}" ]; then
        export HOMELAB_PARENT_PROCEDURE="$proc_name"
        IS_ROOT_PROCEDURE=true
        clean_error_marker
    else
        IS_ROOT_PROCEDURE=false
    fi
}

# Ritorna 0 (true) se la procedura corrente è la Root principale
is_root_procedure() {
    [ "${IS_ROOT_PROCEDURE:-true}" = "true" ]
}

# Ritorna il nome del genitore originario (se presente)
get_parent_procedure() {
    echo "${HOMELAB_PARENT_PROCEDURE:-}"
}

# Ritorna il nome della procedura corrente
get_current_procedure() {
    echo "${CURRENT_PROCEDURE_NAME:-}"
}

# ------------------------------------------------------------------------------
# GESTIONE ATOMICA DEDUPLICAZIONE ERRORI GERARCHICI
# ------------------------------------------------------------------------------
_get_error_marker_path() {
    local parent="${HOMELAB_PARENT_PROCEDURE:-${CURRENT_PROCEDURE_NAME:-global}}"
    echo "/tmp/homelab_error_marker_${parent}"
}

mark_error_reported() {
    local marker
    marker="$(_get_error_marker_path)"
    touch "$marker"
}

has_error_been_reported() {
    local marker
    marker="$(_get_error_marker_path)"
    [ -f "$marker" ]
}

clean_error_marker() {
    local marker
    marker="$(_get_error_marker_path)"
    rm -f "$marker"
}

# Termina lo scope della procedura corrente
complete_procedure_scope() {
    if is_root_procedure; then
        clean_error_marker
        unset HOMELAB_PARENT_PROCEDURE
        unset CURRENT_PROCEDURE_NAME
        unset IS_ROOT_PROCEDURE
    fi
}

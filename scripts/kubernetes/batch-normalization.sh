#!/usr/bin/env bash
# USO: ./batch-normalization.sh "<SOURCE_DIR>" "<DEST_DIR>" [--dry-run] [--verbose]
# =============================================================================
# Batch Process Directories — Audio Normalizer Kubernetes Jobs (Remote Exec)
# =============================================================================

set -euo pipefail

# Definizione Colori per Output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
BOLD='\033[1m'
RESET='\033[0m'

MAX_CONCURRENT=3 # Limite massimo di job paralleli attivi
DRY_RUN=false
SOURCE_DIR=""
DEST_DIR=""
INTERACTIVE=false
EMAIL_RECIPIENT=""
NORMALIZATION_TYPE="audio"

# Nome risorsa di qBittorrent per i controlli tramite kubectl exec
QBIT_POD_REF="deploy/servarr-qbittorrent"
QBIT_CONTAINER="servarr"
QBIT_CONTAINER="servarr" # duplicate but let's keep clean
NAMESPACE="arr"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
YAML_DIR="/tmp/audio-normalizer-jobs"

# Funzione per formattare e anteporre /media/ ai percorsi
format_media_path() {
    local p="$1"
    if [[ "$p" != /media* ]]; then
        p="${p#/}"
        p="/media/$p"
    fi
    p="${p%/}"
    echo "$p"
}

# Parsing degli argomenti per gestire opzioni e parametri posizionali
while [[ $# -gt 0 ]]; do
    case "$1" in
        --recipient|-r)
            EMAIL_RECIPIENT="$2"
            shift 2
            ;;
        --verbose|-v)
            SONGKONG_VERBOSE="true"
            shift
            ;;
        --type|-t)
            NORMALIZATION_TYPE="$2"
            shift 2
            ;;
        --dry-run|-n)
            DRY_RUN=true
            shift
            ;;
        -*)
            echo -e "${RED}Errore: Opzione sconosciuta $1${RESET}" >&2
            echo "Uso: $0 <source_dir> <dest_dir> [--type <audio|video>] [--dry-run]"
            exit 1
            ;;
        *)
            if [ -z "$SOURCE_DIR" ]; then
                SOURCE_DIR="$1"
            elif [ -z "$DEST_DIR" ]; then
                DEST_DIR="$1"
            else
                echo -e "${RED}Errore: Troppi argomenti posizionali.${RESET}" >&2
                echo "Uso: $0 <source_dir> <dest_dir> [--type <audio|video>] [--dry-run]"
                exit 1
            fi
            shift
            ;;
    esac
done

# Rileva se manca almeno uno dei parametri obbligatori per abilitare l'interazione
if [ -z "$SOURCE_DIR" ] || [ -z "$DEST_DIR" ]; then
    INTERACTIVE=true
fi

# Intestazione grafica
echo -e "${BOLD}${CYAN}============================================================${RESET}"
echo -e "${BOLD}${CYAN}   Batch Process Directories (Normalizzatore Audio/Video)${RESET}"
echo -e "${BOLD}${CYAN}============================================================${RESET}\n"

# Chiedi interattivamente il tipo di normalizzazione
if [ "$INTERACTIVE" = true ]; then
    echo -e -n "${BOLD}${YELLOW}Seleziona tipo di normalizzazione (1: audio, 2: video, default: 1):${RESET} "
    read -r RESP_T
    if [ "$RESP_T" = "2" ] || [ "$RESP_T" = "video" ]; then
        NORMALIZATION_TYPE="video"
    else
        NORMALIZATION_TYPE="audio"
    fi
    echo ""
fi

# Chiedi interattivamente e valida SOURCE_DIR
while true; do
    if [ -z "$SOURCE_DIR" ]; then
        echo -e -n "${BOLD}${YELLOW}Inserisci la cartella SORGENTE (es: downloads/lidarr-classical o /media/...):${RESET} "
        read -r SOURCE_DIR
        if [ -z "$SOURCE_DIR" ]; then
            echo -e "${RED}Errore: la cartella sorgente non può essere vuota.${RESET}\n"
            continue
        fi
    fi

    FORMATTED_SOURCE_DIR=$(format_media_path "$SOURCE_DIR")

    # Validazione della cartella SORGENTE (Mandatoria via kubectl exec)
    echo -e "Verifica della cartella sorgente (${CYAN}$FORMATTED_SOURCE_DIR${RESET}) nel pod qBittorrent..."
    if kubectl exec -n "$NAMESPACE" "$QBIT_POD_REF" -c "$QBIT_CONTAINER" -- test -d "$FORMATTED_SOURCE_DIR" &>/dev/null; then
        SOURCE_DIR="$FORMATTED_SOURCE_DIR"
        break
    else
        echo -e "${RED}❌ Errore: La cartella sorgente '$FORMATTED_SOURCE_DIR' non esiste all'interno di qBittorrent!${RESET}\n" >&2
        if [ "$INTERACTIVE" = true ]; then
            SOURCE_DIR=""
        else
            exit 1
        fi
    fi
done

# Chiedi interattivamente DEST_DIR se non passata
if [ -z "$DEST_DIR" ]; then
    while true; do
        echo -e -n "${BOLD}${YELLOW}Inserisci la cartella DESTINAZIONE (es: butta o /media/...):${RESET} "
        read -r DEST_DIR
        if [ -z "$DEST_DIR" ]; then
            echo -e "${RED}Errore: la cartella destinazione non può essere vuota.${RESET}\n"
        else
            break
        fi
    done
fi

DEST_DIR=$(format_media_path "$DEST_DIR")

# Validazione della cartella DESTINAZIONE (Warning non bloccante via kubectl exec)
echo -e "Verifica della cartella destinazione (${CYAN}$DEST_DIR${RESET}) nel pod qBittorrent..."
if ! kubectl exec -n "$NAMESPACE" "$QBIT_POD_REF" -c "$QBIT_CONTAINER" -- test -d "$DEST_DIR" &>/dev/null; then
    echo -e "${YELLOW}⚠️  Attenzione: La cartella destinazione '$DEST_DIR' non esiste all'interno del container qBittorrent.${RESET}"
    echo -e "${YELLOW}   Il job tenterà comunque l'esecuzione (potrebbe essere creata dinamicamente o mappata nel container).${RESET}\n"
fi

# Se siamo in modalità interattiva, chiediamo la modalità DRY-RUN e SONGKONG_VERBOSE
if [ "$INTERACTIVE" = true ]; then
    echo -e -n "${BOLD}${YELLOW}Abilitare la modalità DRY-RUN? (s/n, default: n):${RESET} "
    read -r RESP
    if [[ "$RESP" =~ ^[sSyY]$ ]]; then
        DRY_RUN=true
    else
        DRY_RUN=false
    fi
    echo ""

    echo -e -n "${BOLD}${YELLOW}Abilitare la modalità verbosa per SongKong (SONGKONG_VERBOSE)? (s/n, default: n):${RESET} "
    read -r RESP_V
    if [[ "$RESP_V" =~ ^[sSyY]$ ]]; then
        SONGKONG_VERBOSE=true
    else
        SONGKONG_VERBOSE=false
    fi
    echo ""

    echo -e -n "${BOLD}${YELLOW}Inserisci l'indirizzo email del destinatario (opzionale):${RESET} "
    read -r EMAIL_RECIPIENT
    echo ""
fi

echo -e "${GREEN}✓ Validazione completata.${RESET}"
echo -e "Cartella Sorgente: ${CYAN}$SOURCE_DIR${RESET}"
echo -e "Cartella Destinazione: ${CYAN}$DEST_DIR${RESET}"
echo -e "Tipo Normalizzazione: ${CYAN}$NORMALIZATION_TYPE${RESET}"

if [ "$NORMALIZATION_TYPE" = "video" ]; then
    COMMAND="/app/normalize-video.sh"
else
    COMMAND="/app/normalize.sh"
fi

if [ "$DRY_RUN" = true ]; then
    echo -e "Stato: ${BOLD}${YELLOW}DRY-RUN (Simulazione)${RESET}"
else
    echo -e "Stato: ${BOLD}${GREEN}LIVE (Esecuzione reale)${RESET}"
    echo -e "Concorrenza Massima: ${YELLOW}$MAX_CONCURRENT${RESET} job attivi simultaneamente"
fi

echo -e "\nEstrazione dell'elenco delle cartelle da ${CYAN}$SOURCE_DIR${RESET}..."

# Lettura pulita delle directory tramite Process Substitution in un Array Bash
DIRS=()
while IFS= read -r line; do
    line=$(echo "$line" | tr -d '\r')
    [[ -n "$line" ]] && DIRS+=("$line")
done < <(kubectl exec -n "$NAMESPACE" "$QBIT_POD_REF" -c "$QBIT_CONTAINER" -- find "$SOURCE_DIR" -mindepth 1 -maxdepth 1 -type d 2>/dev/null)

TOTAL_DIRS=${#DIRS[@]}

if [ "$TOTAL_DIRS" -eq 0 ]; then
    # Se non ci sono sottocartelle, controlla se la cartella stessa contiene file (singolo album)
    HAS_FILES=$(kubectl exec -n "$NAMESPACE" "$QBIT_POD_REF" -c "$QBIT_CONTAINER" -- find "$SOURCE_DIR" -maxdepth 1 -type f 2>/dev/null | head -n 1)
    if [ -n "$HAS_FILES" ]; then
        echo -e "${CYAN}ℹ️  La cartella '$SOURCE_DIR' non contiene sottocartelle ma contiene file audio. Verrà elaborata direttamente come singola cartella.${RESET}\n"
        DIRS=("$SOURCE_DIR")
        TOTAL_DIRS=1
    else
        echo -e "${YELLOW}⚠️  Nessun file o sottocartella trovata in '$SOURCE_DIR'.${RESET}"
        exit 0
    fi
fi

echo -e "${GREEN}✓ Trovate ${BOLD}$TOTAL_DIRS${RESET}${GREEN} sottocartelle da elaborare.${RESET}\n"
echo -e "---------------------------------------------------"

SUBMITTED_JOBS=()
REPORTED_JOBS=" "

# Funzione per parsare i log ed emettere il report di un Job
parse_and_report_job_log() {
    local job_name="$1"
    local base_folder="$2"
    local log_output
    log_output=$(kubectl logs -n "$NAMESPACE" "job/$job_name" 2>/dev/null || echo "")

    if echo "$log_output" | grep -q "ELABORAZIONE COMPLETATA"; then
        local cds
        local errs
        cds=$(echo "$log_output" | grep "Cartelle CD elaborate" | awk -F':' '{print $2}' | tr -d ' ' || echo "0")
        errs=$(echo "$log_output" | grep "Errori riscontrati" | awk -F':' '{print $2}' | tr -d ' ' || echo "0")
        echo -e "${GREEN}✅ [COMPLETATO] ${CYAN}$base_folder${RESET} (Job: $job_name) — CD elaborate: ${BOLD}$cds${RESET}, Errori: ${BOLD}$errs${RESET}"
    elif echo "$log_output" | grep -q "OPERAZIONE SKIPPATA"; then
        echo -e "${YELLOW}⚠️  [SKIPPATO] ${CYAN}$base_folder${RESET} (Job: $job_name) — Destinazione già esistente.${RESET}"
    elif echo "$log_output" | grep -q "Errore"; then
        local err_msg
        err_msg=$(echo "$log_output" | grep "Errore:" | head -n 1 || echo "Errore sconosciuto durante l'elaborazione")
        echo -e "${RED}❌ [FALLITO] ${CYAN}$base_folder${RESET} (Job: $job_name) — ${BOLD}$err_msg${RESET}"
    else
        echo -e "${CYAN}ℹ️  [TERMINATO] ${CYAN}$base_folder${RESET} (Job: $job_name)${RESET}"
    fi
}

# Funzione per verificare l'esito dei Job terminati
check_completed_jobs() {
    [ ${#SUBMITTED_JOBS[@]} -eq 0 ] && return

    # Estrae lo stato dei Job in JSON
    local jobs_json
    jobs_json=$(kubectl get jobs -n "$NAMESPACE" -l app.kubernetes.io/name=${NORMALIZATION_TYPE}-normalizer -o json 2>/dev/null || echo "")
    [ -z "$jobs_json" ] && return

    for entry in "${SUBMITTED_JOBS[@]}"; do
        local j_name="${entry%%:*}"
        local b_folder="${entry#*:}"

        # Se già segnalato, salta
        [[ "$REPORTED_JOBS" == *" $j_name "* ]] && continue

        # Controlla se il job è terminato (succeeded > 0 oppure failed > 0)
        local status_check
        status_check=$(echo "$jobs_json" | jq -r --arg j "$j_name" '.items[] | select(.metadata.name == $j) | if (.status.succeeded != null and .status.succeeded > 0) then "succeeded" elif (.status.failed != null and .status.failed > 0) then "failed" else "running" end' 2>/dev/null || echo "running")

        if [ "$status_check" = "succeeded" ] || [ "$status_check" = "failed" ]; then
            parse_and_report_job_log "$j_name" "$b_folder"
            REPORTED_JOBS="${REPORTED_JOBS}${j_name} "
        fi
    done
}

# Scansione ed elaborazione dell'Array
for DIR in "${DIRS[@]}"; do
    BASE_NAME=$(basename "$DIR")
    # Genera un nome sicuro per il resource name di K8s (solo caratteri alfanumerici minuscoli e -)
    SAFE_NAME=$(echo "$BASE_NAME" | tr '[:upper:]' '[:lower:]' | tr -cd 'a-z0-9-' | cut -c 1-40)

    # Generazione id casuale pulita via openssl
    RANDOM_SUFFIX=$(openssl rand -hex 3 | cut -c 1-5)
    JOB_NAME="${NORMALIZATION_TYPE}-normalizer-${SAFE_NAME}-${RANDOM_SUFFIX}"

    mkdir -p "$YAML_DIR"
    YAML_FILE="${YAML_DIR}/${JOB_NAME}.yaml"
    TEMPLATE_FILE="${SCRIPT_DIR}/yaml/job-normalizzation-template.yaml"

    # Generazione e salvataggio del manifesto YAML tramite il template statico
    export JOB_NAME NAMESPACE DIR DEST_DIR SONGKONG_VERBOSE="${SONGKONG_VERBOSE:-false}" EMAIL_RECIPIENT="${EMAIL_RECIPIENT:-}" COMMAND NORMALIZATION_TYPE
    envsubst '$JOB_NAME $NAMESPACE $DIR $DEST_DIR $SONGKONG_VERBOSE $EMAIL_RECIPIENT $COMMAND $NORMALIZATION_TYPE' < "$TEMPLATE_FILE" > "$YAML_FILE"

    if [ "$DRY_RUN" = true ]; then
        echo -e "${YELLOW}[DRY-RUN] Directory individuata: ${RESET}${CYAN}$BASE_NAME${RESET}"
        echo -e "          -> Verrebbe sottomesso il Job: ${BOLD}$JOB_NAME${RESET}"
        echo -e "          -> File YAML salvato in: ${CYAN}$YAML_FILE${RESET}"
        echo -e "          -> Path Sorgente Job: $DIR"
        echo -e "          -> Path Destinazione Job: $DEST_DIR"
        echo "---------------------------------------------------"
        continue
    fi

    # =================================================================
    # CONTROLLO CONCORRENZA & REPORTING: Mette in pausa se il pool è pieno
    # =================================================================
    while true; do
        check_completed_jobs

        # Conta quanti job normalizer hanno la proprietà status.active > 0
        ACTIVE_JOBS=$(kubectl get jobs -n "$NAMESPACE" -l app.kubernetes.io/name=${NORMALIZATION_TYPE}-normalizer -o json | jq '[.items[] | select(.status.active != null and .status.active > 0)] | length' 2>/dev/null || echo "0")
        ACTIVE_JOBS=${ACTIVE_JOBS:-0}

        if [ "$ACTIVE_JOBS" -lt "$MAX_CONCURRENT" ]; then
            break # C'è spazio nel pool, esce dal loop di attesa
        fi

        sleep 5
    done
    # =================================================================

    echo -e "🚀 Sottomissione Job in corso per: ${CYAN}$BASE_NAME${RESET} (Job ID: ${BOLD}$JOB_NAME${RESET})"
    kubectl apply -f "$YAML_FILE"

    SUBMITTED_JOBS+=("${JOB_NAME}:${BASE_NAME}")
    echo -e "${GREEN}✓ Job ${JOB_NAME} sottomesso.${RESET}"
    echo "---------------------------------------------------"
done

if [ "$DRY_RUN" = true ]; then
    echo -e "\n${BOLD}${YELLOW}Simulazione completata (Dry-Run). Nessuna risorsa modificata sul cluster.${RESET}\n"
else
    echo -e "\n${BOLD}${CYAN}Tutti i Job sono stati sottomessi. Attesa del completamento dei Job in corso...${RESET}\n"

    # Attesa finale che tutti i Job sottomessi siano terminati
    while true; do
        check_completed_jobs

        # Se tutti i job sottomessi sono stati segnalati come terminati, usciamo
        UNFINISHED_COUNT=0
        for entry in "${SUBMITTED_JOBS[@]}"; do
            j_name="${entry%%:*}"
            if [[ "$REPORTED_JOBS" != *" $j_name "* ]]; then
                UNFINISHED_COUNT=$((UNFINISHED_COUNT + 1))
            fi
        done

        if [ "$UNFINISHED_COUNT" -eq 0 ]; then
            break
        fi

        sleep 5
    done

    echo -e "\n${BOLD}${GREEN}🎉 Tutti i Job del batch sono terminati con successo!${RESET}\n"
fi

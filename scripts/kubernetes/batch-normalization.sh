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

# Nome risorsa di qBittorrent per i controlli tramite kubectl exec
QBIT_POD_REF="deploy/servarr-qbittorrent"
QBIT_CONTAINER="servarr"
NAMESPACE="arr"

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
        --verbose|-v)
            SONGKONG_VERBOSE="true"
            shift
            ;;
        --dry-run|-n)
            DRY_RUN=true
            shift
            ;;
        -*)
            echo -e "${RED}Errore: Opzione sconosciuta $1${RESET}" >&2
            echo "Uso: $0 <source_dir> <dest_dir> [--dry-run]"
            exit 1
            ;;
        *)
            if [ -z "$SOURCE_DIR" ]; then
                SOURCE_DIR="$1"
            elif [ -z "$DEST_DIR" ]; then
                DEST_DIR="$1"
            else
                echo -e "${RED}Errore: Troppi argomenti posizionali.${RESET}" >&2
                echo "Uso: $0 <source_dir> <dest_dir> [--dry-run]"
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
echo -e "${BOLD}${CYAN}   Batch Process Directories (Audio Normalizer K8s Jobs)${RESET}"
echo -e "${BOLD}${CYAN}============================================================${RESET}\n"

# Chiedi interattivamente SOURCE_DIR se non passata
if [ -z "$SOURCE_DIR" ]; then
    while true; do
        echo -e -n "${BOLD}${YELLOW}Inserisci la cartella SORGENTE (es: downloads/lidarr-classical o /media/...):${RESET} "
        read -r SOURCE_DIR
        if [ -z "$SOURCE_DIR" ]; then
            echo -e "${RED}Errore: la cartella sorgente non può essere vuota.${RESET}\n"
        else
            break
        fi
    done
fi

SOURCE_DIR=$(format_media_path "$SOURCE_DIR")

# Validazione della cartella SORGENTE (Mandatoria via kubectl exec)
echo -e "Verifica della cartella sorgente (${CYAN}$SOURCE_DIR${RESET}) nel pod qBittorrent..."
if ! kubectl exec -n "$NAMESPACE" "$QBIT_POD_REF" -c "$QBIT_CONTAINER" -- test -d "$SOURCE_DIR" &>/dev/null; then
    echo -e "${RED}❌ Errore critico: La cartella sorgente '$SOURCE_DIR' non esiste all'interno di qBittorrent!${RESET}" >&2
    exit 1
fi

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
fi

echo -e "${GREEN}✓ Validazione completata.${RESET}"
echo -e "Cartella Sorgente: ${CYAN}$SOURCE_DIR${RESET}"
echo -e "Cartella Destinazione: ${CYAN}$DEST_DIR${RESET}"
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
    echo -e "${YELLOW}⚠️  Nessuna sottocartella trovata in '$SOURCE_DIR'.${RESET}"
    exit 0
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
    jobs_json=$(kubectl get jobs -n "$NAMESPACE" -l app.kubernetes.io/name=audio-normalizer -o json 2>/dev/null || echo "")
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
    JOB_NAME="audio-normalizer-${SAFE_NAME}-${RANDOM_SUFFIX}"

    if [ "$DRY_RUN" = true ]; then
        echo -e "${YELLOW}[DRY-RUN] Directory individuata: ${RESET}${CYAN}$BASE_NAME${RESET}"
        echo -e "          -> Verrebbe sottomesso il Job: ${BOLD}$JOB_NAME${RESET}"
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
        ACTIVE_JOBS=$(kubectl get jobs -n "$NAMESPACE" -l app.kubernetes.io/name=audio-normalizer -o json | jq '[.items[] | select(.status.active != null and .status.active > 0)] | length' 2>/dev/null || echo "0")
        ACTIVE_JOBS=${ACTIVE_JOBS:-0}

        if [ "$ACTIVE_JOBS" -lt "$MAX_CONCURRENT" ]; then
            break # C'è spazio nel pool, esce dal loop di attesa
        fi

        sleep 5
    done
    # =================================================================

    echo -e "🚀 Sottomissione Job in corso per: ${CYAN}$BASE_NAME${RESET} (Job ID: ${BOLD}$JOB_NAME${RESET})"

    # Generazione e applicazione dinamica del manifesto YAML (CORRETTO mountPath: /media)
    cat <<EOF | kubectl apply -f -
apiVersion: batch/v1
kind: Job
metadata:
  name: ${JOB_NAME}
  namespace: ${NAMESPACE}
spec:
  ttlSecondsAfterFinished: 600
  backoffLimit: 0
  template:
    metadata:
      labels:
        app.kubernetes.io/name: audio-normalizer
    spec:
      restartPolicy: Never
      affinity:
        podAntiAffinity:
          requiredDuringSchedulingIgnoredDuringExecution:
            - labelSelector:
                matchExpressions:
                  - key: app.kubernetes.io/name
                    operator: In
                    values:
                      - qbittorrent
              topologyKey: kubernetes.io/hostname
      containers:
        - name: normalizer
          image: ghcr.io/pindaroli/custom-normalizer:1.0.7
          args:
            - "${DIR}"
            - "${DEST_DIR}"
            - "/media"
          resources:
            requests:
              cpu: "200m"
              memory: "512Mi"
            limits:
              cpu: "2"
              memory: "2Gi"
          env:
            - name: SONGKONG_VERBOSE
              value: "${SONGKONG_VERBOSE:-false}"
            - name: TELEGRAM_BOT_TOKEN
              valueFrom:
                secretKeyRef:
                  name: servarr-api-keys
                  key: telegram-token
            - name: TELEGRAM_CHAT_ID
              valueFrom:
                secretKeyRef:
                  name: servarr-api-keys
                  key: telegram-chat-id
          volumeMounts:
            - name: media-data
              mountPath: /media
      volumes:
        - name: media-data
          persistentVolumeClaim:
            claimName: servarr-jellyfin-media
EOF

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

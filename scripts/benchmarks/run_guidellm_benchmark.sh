#!/usr/bin/env bash
# ==============================================================================
# Script: run_guidellm_benchmark.sh
# Progetto: Homelab k8s-lab
# Descrizione: Launcher interattivo e CLI per benchmark GuideLLM conformi
#              allo standard di naming [[guidellm-report-naming-pattern]].
# ==============================================================================
set -euo pipefail

# Colori per output terminale
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Default di sistema
DEFAULT_OUTPUT_DIR="./reports"
DEFAULT_PROFILE="sweep"
DEFAULT_DATA="prompt_tokens=128,output_tokens=64"
DEFAULT_PROCESSOR="gpt2"

OUTPUT_DIR="${DEFAULT_OUTPUT_DIR}"
PROFILE="${DEFAULT_PROFILE}"
DATA="${DEFAULT_DATA}"
PROCESSOR="${DEFAULT_PROCESSOR}"
MAX_REQUESTS=""
MAX_SECONDS=""
RATE=""
DRY_RUN=false

# Parametri operativi
NODE=""
MODEL=""
MEMORY=""
BACKEND_URL=""

# Funzione help
show_help() {
  cat << 'EOF'
Utilizzo:
  run_guidellm_benchmark.sh [OPZIONI] [NODO] [MODELLO] [MEMORIA] [BACKEND_URL]

Descrizione:
  Esegue benchmark prestazionali tramite GuideLLM conformi al pattern:
  report-<nome macchina>-<nome llm>-<memoria macchina>-<YYYYMMDD-HHMMSS>.<ext>

Parametri Posizionali (opzionali se usate le flag):
  $1   Identificativo del nodo (es. lxc-ollama, pve3, macbook-pro, localhost)
  $2   Nome del modello LLM (es. llama-3.2-3b-instruct, qwen2.5-coder-7b)
  $3   Dotazione memoria RAM/VRAM (es. 38gb, 64gb, 64gb-unified)
  $4   URL endpoint OpenAI HTTP (es. http://10.10.20.33:11434/v1)

Opzioni:
  -n, --node <nome>         Identificativo macchina / host
  -m, --model <modello>     Nome del modello LLM da testare
  --mem, --memory <ram>     Dotazione di memoria (RAM/VRAM)
  -b, --backend <url>       URL backend OpenAI-compatibile
  -d, --output-dir <dir>    Cartella destinazione report (default: ./reports)
  -p, --profile <tipo>      Tipo profilo GuideLLM (sweep|throughput|concurrent|...)
  --data <spec>             Dataset o config sintetica (default: prompt_tokens=128,output_tokens=64)
  --processor <tok>         Tokenizer HuggingFace per token counts (default: gpt2)
  --max-requests <num>      Numero massimo di richieste per benchmark
  --max-seconds <sec>       Durata massima in secondi per benchmark
  --rate <val>              Valore di rate o concorrenza
  --dry-run                 Stampa la configurazione e i percorsi senza eseguire
  -h, --help                Mostra questo messaggio di aiuto

Esempi:
  # Batch non-interattivo rapido:
  ./run_guidellm_benchmark.sh -n lxc-ollama -m bge-m3:latest --max-requests 5

  # Dry-run per verifica naming:
  ./run_guidellm_benchmark.sh -n pve3 -m qwen2.5-coder-7b --dry-run

  # Wizard interattivo (nessun parametro):
  ./run_guidellm_benchmark.sh
EOF
}

# Parsing argomenti CLI (flag e posizionali)
POSITIONAL_ARGS=()
while [[ $# -gt 0 ]]; do
  case "$1" in
    -h|--help)
      show_help
      exit 0
      ;;
    -n|--node)
      NODE="$2"
      shift 2
      ;;
    -m|--model)
      MODEL="$2"
      shift 2
      ;;
    --mem|--memory)
      MEMORY="$2"
      shift 2
      ;;
    -b|--backend|--url)
      BACKEND_URL="$2"
      shift 2
      ;;
    -d|--output-dir)
      OUTPUT_DIR="$2"
      shift 2
      ;;
    -p|--profile)
      PROFILE="$2"
      shift 2
      ;;
    --max-requests)
      MAX_REQUESTS="$2"
      shift 2
      ;;
    --max-seconds)
      MAX_SECONDS="$2"
      shift 2
      ;;
    --rate)
      RATE="$2"
      shift 2
      ;;
    --data)
      DATA="$2"
      shift 2
      ;;
    --processor)
      PROCESSOR="$2"
      shift 2
      ;;
    --dry-run)
      DRY_RUN=true
      shift
      ;;
    -*)
      echo -e "${RED}Errore: Opzione sconosciuta $1${NC}" >&2
      show_help
      exit 1
      ;;
    *)
      POSITIONAL_ARGS+=("$1")
      shift
      ;;
  esac
done

# Assegnazione argomenti posizionali rimasti
if [[ -z "$NODE" && ${#POSITIONAL_ARGS[@]} -ge 1 ]]; then
  NODE="${POSITIONAL_ARGS[0]}"
fi
if [[ -z "$MODEL" && ${#POSITIONAL_ARGS[@]} -ge 2 ]]; then
  MODEL="${POSITIONAL_ARGS[1]}"
fi
if [[ -z "$MEMORY" && ${#POSITIONAL_ARGS[@]} -ge 3 ]]; then
  MEMORY="${POSITIONAL_ARGS[2]}"
fi
if [[ -z "$BACKEND_URL" && ${#POSITIONAL_ARGS[@]} -ge 4 ]]; then
  BACKEND_URL="${POSITIONAL_ARGS[3]}"
fi

# Determina se l'utente richiede modalità interattiva (nessun parametro fornito)
INTERACTIVE=false
if [[ -z "$NODE" && -z "$MODEL" ]]; then
  INTERACTIVE=true
fi

# ==============================================================================
# Discovery Dinamica Servizi Ollama da rete.json (Source of Truth)
# ==============================================================================

RETE_FILE="${RETE_FILE:-rete.json}"
if [[ ! -f "$RETE_FILE" && -f "$(dirname "$0")/../../rete.json" ]]; then
  RETE_FILE="$(dirname "$0")/../../rete.json"
fi

OLLAMA_NODE_IDS=()
OLLAMA_NODE_IPS=()
OLLAMA_NODE_PORTS=()
OLLAMA_NODE_MEMS=()
OLLAMA_NODE_HWS=()

if [[ -f "$RETE_FILE" ]]; then
  while IFS='|' read -r nid nip nport nmem nhw; do
    [[ -z "$nid" ]] && continue
    OLLAMA_NODE_IDS+=("$nid")
    OLLAMA_NODE_IPS+=("$nip")
    OLLAMA_NODE_PORTS+=("$nport")
    OLLAMA_NODE_MEMS+=("$nmem")
    OLLAMA_NODE_HWS+=("$nhw")
  done < <(python3 -c "
import json
try:
    with open('${RETE_FILE}') as f:
        d = json.load(f)
    for n in d.get('nodi', []):
        for s in n.get('services', []):
            if s.get('id') == 'ollama':
                print(f\"{n.get('id')}|{n.get('ip')}|{s.get('port', 11434)}|{s.get('memory', '32gb')}|{s.get('hardware', n.get('label', ''))}\")
except Exception:
    pass
" 2>/dev/null || true)
fi

# ==============================================================================
# Procedura Guidata Interattiva (se parametri non passati)
# ==============================================================================

if [[ "$INTERACTIVE" == true ]]; then
  echo -e "${CYAN}======================================================${NC}"
  echo -e "${CYAN}   GuideLLM Benchmark Launcher — Selezione da rete.json ${NC}"
  echo -e "${CYAN}======================================================${NC}"
  echo "Seleziona il nodo target fornitore del servizio Ollama:"

  for i in "${!OLLAMA_NODE_IDS[@]}"; do
    echo "  $((i+1))) ${OLLAMA_NODE_IDS[$i]}    (${OLLAMA_NODE_IPS[$i]}:${OLLAMA_NODE_PORTS[$i]} - ${OLLAMA_NODE_MEMS[$i]}, ${OLLAMA_NODE_HWS[$i]})"
  done
  LOCAL_IDX=$(( ${#OLLAMA_NODE_IDS[@]} + 1 ))
  CUSTOM_IDX=$(( ${#OLLAMA_NODE_IDS[@]} + 2 ))
  echo "  ${LOCAL_IDX}) localhost     (Macchina locale / macOS)"
  echo "  ${CUSTOM_IDX}) Altro / Custom (Inserimento manuale)"
  echo ""
  read -rp "Scelta [1-${CUSTOM_IDX}] (default: 1): " NODE_CHOICE
  NODE_CHOICE="${NODE_CHOICE:-1}"

  if [[ "$NODE_CHOICE" =~ ^[0-9]+$ ]] && (( NODE_CHOICE >= 1 && NODE_CHOICE <= ${#OLLAMA_NODE_IDS[@]} )); then
    SEL_IDX=$(( NODE_CHOICE - 1 ))
    NODE="${OLLAMA_NODE_IDS[$SEL_IDX]}"
    DEFAULT_NODE_MEM="${OLLAMA_NODE_MEMS[$SEL_IDX]}"
    DEFAULT_NODE_BACKEND="http://${OLLAMA_NODE_IPS[$SEL_IDX]}:${OLLAMA_NODE_PORTS[$SEL_IDX]}/v1"
  elif [[ "$NODE_CHOICE" -eq "$LOCAL_IDX" ]]; then
    NODE="localhost"
    DEFAULT_NODE_BACKEND="http://localhost:11434/v1"
    if [[ "$(uname -s)" == "Darwin" ]]; then
      LOCAL_MEM_BYTES=$(sysctl -n hw.memsize 2>/dev/null || echo "0")
      LOCAL_MEM_GB=$(( LOCAL_MEM_BYTES / 1024 / 1024 / 1024 ))
      DEFAULT_NODE_MEM="${LOCAL_MEM_GB}gb-unified"
    else
      DEFAULT_NODE_MEM="16gb"
    fi
  else
    read -rp "Inserisci identificativo nodo (kebab-case es. pve3, server-ai): " CUSTOM_NODE
    NODE="${CUSTOM_NODE:-custom-node}"
    read -rp "Dotazione memoria host [32gb]: " CUSTOM_MEM
    DEFAULT_NODE_MEM="${CUSTOM_MEM:-32gb}"
    read -rp "URL Backend OpenAI [http://10.10.20.33:11434/v1]: " CUSTOM_BACKEND
    DEFAULT_NODE_BACKEND="${CUSTOM_BACKEND:-http://10.10.20.33:11434/v1}"
  fi
else
  # Mapping automatico da rete.json per nodo passato da CLI
  MATCH_FOUND=false
  for i in "${!OLLAMA_NODE_IDS[@]}"; do
    NORM_TARGET=$(echo "$NODE" | tr '[:upper:]' '[:lower:]' | tr -d ' -_')
    NORM_ID=$(echo "${OLLAMA_NODE_IDS[$i]}" | tr '[:upper:]' '[:lower:]' | tr -d ' -_')
    if [[ "$NORM_TARGET" == "$NORM_ID" ]]; then
      NODE="${OLLAMA_NODE_IDS[$i]}"
      DEFAULT_NODE_MEM="${OLLAMA_NODE_MEMS[$i]}"
      DEFAULT_NODE_BACKEND="http://${OLLAMA_NODE_IPS[$i]}:${OLLAMA_NODE_PORTS[$i]}/v1"
      MATCH_FOUND=true
      break
    fi
  done

  # Fallback speciale per pve3 (host hypervisor di lxc-ollama)
  if [[ "$MATCH_FOUND" == false && "$(echo "$NODE" | tr '[:upper:]' '[:lower:]')" == "pve3" ]]; then
    for i in "${!OLLAMA_NODE_IDS[@]}"; do
      if [[ "${OLLAMA_NODE_IDS[$i]}" == "lxc-ollama" ]]; then
        DEFAULT_NODE_MEM="64gb"
        DEFAULT_NODE_BACKEND="http://${OLLAMA_NODE_IPS[$i]}:${OLLAMA_NODE_PORTS[$i]}/v1"
        MATCH_FOUND=true
        break
      fi
    done
  fi

  # Fallback generico per localhost o nodi non trovati
  if [[ "$MATCH_FOUND" == false ]]; then
    case "$(echo "$NODE" | tr '[:upper:]' '[:lower:]')" in
      localhost|macbook*)
        if [[ "$(uname -s)" == "Darwin" ]]; then
          LOCAL_MEM_BYTES=$(sysctl -n hw.memsize 2>/dev/null || echo "0")
          LOCAL_MEM_GB=$(( LOCAL_MEM_BYTES / 1024 / 1024 / 1024 ))
          DEFAULT_NODE_MEM="${LOCAL_MEM_GB}gb-unified"
        else
          DEFAULT_NODE_MEM="16gb"
        fi
        DEFAULT_NODE_BACKEND="http://localhost:11434/v1"
        ;;
      *)
        DEFAULT_NODE_MEM="32gb"
        DEFAULT_NODE_BACKEND="http://10.10.20.33:11434/v1"
        ;;
    esac
  fi
fi

# Risoluzione Backend URL
if [[ -z "$BACKEND_URL" ]]; then
  if [[ "$INTERACTIVE" == true && -t 0 ]]; then
    read -rp "URL Backend OpenAI [$DEFAULT_NODE_BACKEND]: " INPUT_BACKEND
    BACKEND_URL="${INPUT_BACKEND:-$DEFAULT_NODE_BACKEND}"
  else
    BACKEND_URL="$DEFAULT_NODE_BACKEND"
  fi
fi

# Risoluzione Modello LLM
if [[ -z "$MODEL" ]]; then
  echo ""
  echo -e "${CYAN}======================================================${NC}"
  echo -e "${CYAN}   Rilevamento Modelli sulla Macchina Target: ${NODE}   ${NC}"
  echo -e "${CYAN}======================================================${NC}"

  BASE_OLLAMA_URL="${BACKEND_URL%/v1}"
  BASE_OLLAMA_URL="${BASE_OLLAMA_URL%/}"
  TAGS_API="${BASE_OLLAMA_URL}/api/tags"
  MODELS_API="${BACKEND_URL%/}/models"

  AVAILABLE_MODELS=()

  # 1. Tentativo endpoint Ollama (/api/tags)
  if curl -s -m 3 "${TAGS_API}" >/dev/null 2>&1; then
    TAGS_JSON=$(curl -s -m 3 "${TAGS_API}")
    if command -v jq >/dev/null 2>&1; then
      while IFS= read -r line; do
        if [[ -n "$line" ]]; then
          AVAILABLE_MODELS+=("$line")
        fi
      done < <(echo "$TAGS_JSON" | jq -r '.models[].name' 2>/dev/null || true)
    fi
  fi

  # 2. Se vuoto, tentativo endpoint OpenAI/vLLM (/v1/models)
  if [[ ${#AVAILABLE_MODELS[@]} -eq 0 ]] && curl -s -m 3 "${MODELS_API}" >/dev/null 2>&1; then
    MODELS_JSON=$(curl -s -m 3 "${MODELS_API}")
    if command -v jq >/dev/null 2>&1; then
      while IFS= read -r line; do
        if [[ -n "$line" ]]; then
          AVAILABLE_MODELS+=("$line")
        fi
      done < <(echo "$MODELS_JSON" | jq -r '.data[].id' 2>/dev/null || true)
    fi
  fi

  # 3. Se ancora vuoto e target localhost, tentativo CLI ollama locale
  if [[ ${#AVAILABLE_MODELS[@]} -eq 0 && ("$NODE" == "localhost" || "$NODE" == "macbook*") ]]; then
    if command -v ollama >/dev/null 2>&1; then
      while IFS= read -r line; do
        if [[ -n "$line" ]]; then
          AVAILABLE_MODELS+=("$line")
        fi
      done < <(ollama list 2>/dev/null | tail -n +2 | awk '{print $1}' || true)
    fi
  fi

  # Presentazione alternative all'utente
  if [[ ${#AVAILABLE_MODELS[@]} -gt 0 ]]; then
    echo -e "Modelli disponibili ricavati direttamente dalla macchina target (${GREEN}${NODE}${NC}):"
    for i in "${!AVAILABLE_MODELS[@]}"; do
      echo "  $((i+1))) ${AVAILABLE_MODELS[$i]}"
    done
    echo "  m) Inserisci manualmente un altro modello"
    echo ""
    read -rp "Seleziona modello [1-${#AVAILABLE_MODELS[@]} o 'm'] (default: 1): " MODEL_SEL
    MODEL_SEL="${MODEL_SEL:-1}"
    if [[ "$MODEL_SEL" =~ ^[0-9]+$ ]] && (( MODEL_SEL >= 1 && MODEL_SEL <= ${#AVAILABLE_MODELS[@]} )); then
      MODEL="${AVAILABLE_MODELS[$((MODEL_SEL-1))]}"
    elif [[ "$MODEL_SEL" == "m" || "$MODEL_SEL" == "M" ]]; then
      read -rp "Inserisci nome esatto del modello (es. llama-3.2-3b-instruct): " MODEL
    else
      MODEL="$MODEL_SEL"
    fi
  else
    echo -e "${YELLOW}Nessun modello rilevato automaticamente su ${NODE} (${TAGS_API} o ${MODELS_API}).${NC}"
    read -rp "Inserisci nome esatto del modello (es. llama-3.2-3b-instruct): " MODEL
  fi
fi

# Risoluzione Memoria (automatica in base al nodo, override possibile via --mem)
if [[ -z "$MEMORY" ]]; then
  MEMORY="$DEFAULT_NODE_MEM"
fi

# Validazione minima
if [[ -z "$NODE" || -z "$MODEL" || -z "$MEMORY" ]]; then
  echo -e "${RED}Errore: Nodo, Modello e Memoria sono parametri obbligatori.${NC}" >&2
  exit 1
fi

# ==============================================================================
# Normalizzazione e Costruzione Nomi Conforme a [[guidellm-report-naming-pattern]]
# ==============================================================================

# Normalizza nodo: minuscolo, caratteri alfanumerici e trattini
CLEAN_NODE=$(echo "$NODE" | tr '[:upper:]' '[:lower:]' | tr -cd 'a-z0-9-')

# Normalizza modello: minuscolo, sostituisce ':' e '/' con '-', mantiene lettere, numeri, '.', '_' e '-'
CLEAN_MODEL=$(echo "$MODEL" | tr '[:upper:]' '[:lower:]' | tr ':/' '--' | tr -cd 'a-z0-9._-')

# Normalizza memoria: minuscolo, caratteri alfanumerici e trattini
CLEAN_MEM=$(echo "$MEMORY" | tr '[:upper:]' '[:lower:]' | tr -cd 'a-z0-9-')

# Timestamp YYYYMMDD-HHMMSS
TIMESTAMP=$(date +"%Y%m%d-%H%M%S")

# Costruzione del nome base canonico
BASE_NAME="report-${CLEAN_NODE}-${CLEAN_MODEL}-${CLEAN_MEM}-${TIMESTAMP}"

mkdir -p "${OUTPUT_DIR}"
REPORT_JSON="${OUTPUT_DIR}/${BASE_NAME}.json"
REPORT_CSV="${OUTPUT_DIR}/${BASE_NAME}.csv"
REPORT_HTML="${OUTPUT_DIR}/${BASE_NAME}.html"

# Regex di validazione canonica da [[guidellm-report-naming-pattern]]
VALIDATION_REGEX='^report-([a-z0-9-]+)-([a-z0-9._-]+)-([0-9]+[a-z]+(-[a-z0-9]+)*)-([0-9]{8}-[0-9]{4,6})\.(json|csv|html|txt|log)$'
TEST_FILENAME="${BASE_NAME}.json"

if [[ ! "$TEST_FILENAME" =~ $VALIDATION_REGEX ]]; then
  echo -e "${YELLOW}Attenzione: Il nome file '${TEST_FILENAME}' potrebbe discostarsi parzialmente dalla regex standard.${NC}"
fi

# ==============================================================================
# Individuazione Runner (Binary Locale vs uvx Zero-Install)
# ==============================================================================

RUNNER=""
if command -v guidellm >/dev/null 2>&1; then
  RUNNER="guidellm"
elif command -v uvx >/dev/null 2>&1; then
  RUNNER="uvx guidellm"
else
  echo -e "${RED}Errore: né 'guidellm' né 'uvx' sono disponibili nel PATH.${NC}" >&2
  echo "Installa uv con 'brew install uv' o installa guidellm in un ambiente Python." >&2
  exit 1
fi

# ==============================================================================
# Riepilogo e Esecuzione
# ==============================================================================

echo ""
echo -e "${GREEN}======================================================${NC}"
echo -e "${GREEN}   Riepilogo Parametri Benchmark GuideLLM             ${NC}"
echo -e "${GREEN}======================================================${NC}"
echo "  • Nodo Target:     ${CLEAN_NODE} (raw: ${NODE})"
echo "  • Modello LLM:     ${MODEL} (naming: ${CLEAN_MODEL})"
echo "  • Memoria Host:    ${CLEAN_MEM}"
echo "  • Backend URL:     ${BACKEND_URL}"
echo "  • Profilo:         ${PROFILE}"
echo "  • Runner Utilizzato: ${RUNNER}"
echo "  • Destinazione Output:"
echo "      JSON: ${REPORT_JSON}"
echo "      CSV:  ${REPORT_CSV}"
echo "      HTML: ${REPORT_HTML}"
echo "  • Pattern Base:    ${BASE_NAME}"
echo -e "${GREEN}======================================================${NC}"
echo ""

if ${RUNNER} benchmark --help >/dev/null 2>&1 || [[ "$RUNNER" == "guidellm" ]]; then
  # Sintassi GuideLLM benchmark run (versione installata)
  BENCH_CMD=(${RUNNER} benchmark run --target "${BACKEND_URL}" --model "${MODEL}" --processor "${PROCESSOR}" --data "${DATA}" --rate-type "${PROFILE}" --output-path "${REPORT_JSON}")
  [[ -n "$MAX_REQUESTS" ]] && BENCH_CMD+=(--max-requests "$MAX_REQUESTS")
  [[ -n "$MAX_SECONDS" ]] && BENCH_CMD+=(--max-seconds "$MAX_SECONDS")
  [[ -n "$RATE" ]] && BENCH_CMD+=(--rate "$RATE")

  if [[ "$DRY_RUN" == true ]]; then
    echo -e "${YELLOW}[DRY-RUN] Nessun comando eseguito. Comando pianificato:${NC}"
    echo "  ${BENCH_CMD[*]}"
    echo "  # Export CSV da JSON pianificato a seguire:"
    echo "  ${RUNNER} benchmark from-file \"${REPORT_JSON}\" --output-path \"${REPORT_CSV}\""
    exit 0
  fi

  echo -e "${BLUE}Avvio esecuzione GuideLLM (${BENCH_CMD[*]}) in corso...${NC}"
  "${BENCH_CMD[@]}"

  # Esportazione automatica formato CSV a partire dal report JSON prodotto
  if [[ -f "${REPORT_JSON}" ]]; then
    echo -e "${CYAN}Generazione export CSV dal report JSON...${NC}"
    ${RUNNER} benchmark from-file "${REPORT_JSON}" --output-path "${REPORT_CSV}" 2>/dev/null || true
  fi

elif ${RUNNER} run --help 2>&1 | grep -q -- '--output kind'; then
  # Sintassi GuideLLM v0.7+ con output multipli integrati
  BENCH_CMD=(${RUNNER} run --backend kind=openai_http,target="${BACKEND_URL}" --model "${MODEL}" --profile kind="${PROFILE}" --output kind=json,path="${REPORT_JSON}" --output kind=csv,path="${REPORT_CSV}" --output kind=html,path="${REPORT_HTML}")
  [[ -n "$MAX_REQUESTS" ]] && BENCH_CMD+=(--max-requests "$MAX_REQUESTS")
  [[ -n "$MAX_SECONDS" ]] && BENCH_CMD+=(--max-seconds "$MAX_SECONDS")

  if [[ "$DRY_RUN" == true ]]; then
    echo -e "${YELLOW}[DRY-RUN] Nessun comando eseguito. Comando pianificato:${NC}"
    echo "  ${BENCH_CMD[*]}"
    exit 0
  fi

  echo -e "${BLUE}Avvio esecuzione GuideLLM in corso...${NC}"
  "${BENCH_CMD[@]}"

else
  # Fallback generico legacy
  BENCH_CMD=(${RUNNER} run --backend kind=openai_http,target="${BACKEND_URL}" --model "${MODEL}" --profile kind="${PROFILE}" --output-path "${REPORT_JSON}")
  if [[ "$DRY_RUN" == true ]]; then
    echo -e "${YELLOW}[DRY-RUN] Nessun comando eseguito. Comando pianificato:${NC}"
    echo "  ${BENCH_CMD[*]}"
    exit 0
  fi

  echo -e "${BLUE}Avvio esecuzione GuideLLM in corso...${NC}"
  "${BENCH_CMD[@]}"
fi

echo ""
echo -e "${GREEN}✅ Benchmark completato con successo!${NC}"
echo "Report generati:"
if [[ -f "${REPORT_JSON}" ]]; then
  echo "  • JSON: ${REPORT_JSON}"
fi
if [[ -f "${REPORT_CSV}" ]]; then
  echo "  • CSV:  ${REPORT_CSV}"
fi
if [[ -f "${REPORT_HTML}" ]]; then
  echo "  • HTML: ${REPORT_HTML}"
fi
exit 0

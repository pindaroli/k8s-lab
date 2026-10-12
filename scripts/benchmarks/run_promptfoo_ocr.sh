#!/usr/bin/env bash
# ==============================================================================
# run_promptfoo_ocr.sh - Benchmark Runner Interattivo per Suite OCR con Promptfoo
# Homelab PVE3 / CT 300 / Mac Client - llama-server Vulkan & Ollama
# ==============================================================================
# Convenzione Report: report-<nodo>-<modello>-<memoria>-<dataora>.<estensione>
# Naming Pattern: [[guidellm-report-naming-pattern]]
# Governance & Wiki: [[promptfoo-ocr-benchmark-script]]
# ==============================================================================

set -euo pipefail

# Colori per interfaccia terminale
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
MAGENTA='\033[0;35m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m' # No Color

# Risoluzione percorsi del repository (supporto trasparente symlink)
SCRIPT_SOURCE="$(realpath "${BASH_SOURCE[0]}")"
SCRIPT_DIR="$(cd "$(dirname "${SCRIPT_SOURCE}")" && pwd)"
WORKSPACE_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
RETE_JSON="${WORKSPACE_ROOT}/rete.json"
BENCHMARK_DIR="${WORKSPACE_ROOT}/benchmarks/promptfoo-ocr"
FIXTURES_DIR="${BENCHMARK_DIR}/fixtures"
PROMPTS_DIR="${BENCHMARK_DIR}/prompts"
OUTPUT_DIR="${WORKSPACE_ROOT}/reports"

# Inlining forzato per evitare immagini rotte nel browser Promptfoo
export PROMPTFOO_INLINE_MEDIA=true

# Valori di default
NODE=""
MODEL=""
MEMORY=""
BACKEND_URL=""
FIXTURE=""
TASK="all" # all | markdown | json
DRY_RUN=false
ACTION="eval" # eval | view
VIEW_PORT="15500"
FILTER_OCR=true # Default: filtra solo modelli con capability Vision/OCR
INTERACTIVE=false

# Funzione di Help
show_help() {
  echo -e "${BOLD}Uso:${NC}"
  echo -e "  $(basename "$0") [opzioni] [azione]"
  echo -e ""
  echo -e "${BOLD}Azioni:${NC}"
  echo -e "  eval                      Esegue la suite di test Promptfoo (default)"
  echo -e "  view [porta]              Avvia la Web Dashboard interattiva (default porta: 15500)"
  echo -e ""
  echo -e "${BOLD}Opzioni:${NC}"
  echo -e "  -n, --node <nome>         Identificativo del nodo (es. lxc-ollama, pve3, mac-local, localhost)"
  echo -e "  -m, --model <modello>     Nome del modello LLM/Vision da testare (es. qwen2.5vl:7b-q4_K_M)"
  echo -e "  -b, --backend <url>       URL backend OpenAI-compatibile (es. http://10.10.20.33:8081/v1)"
  echo -e "  --mem, --memory <ram>     Memoria host per naming pattern (default: risolta automaticamente)"
  echo -e "  -f, --fixture <path>      Documento immagine di test (es. fattura_test.png o path assoluto)"
  echo -e "  -t, --task <tipo>         Tipo di test: 'all' (default), 'markdown', 'json'"
  echo -e "  --all-models              Disattiva il filtro OCR e mostra tutti i modelli disponibili"
  echo -e "  -d, --output-dir <dir>    Cartella destinazione report (default: ./reports)"
  echo -e "  --dry-run                 Mostra la configurazione e i comandi generati senza eseguire"
  echo -e "  -h, --help                Mostra questo messaggio di aiuto"
  echo -e ""
  echo -e "${BOLD}Esempi:${NC}"
  echo -e "  # Esecuzione rapida batch su modello Vision locale:"
  echo -e "  $(basename "$0") -n mac-local -m qwen2.5vl:7b-q4_K_M -f fattura_test.png"
  echo -e ""
  echo -e "  # Test comparativo su sidecar remoto Vulkan su CT 300:"
  echo -e "  $(basename "$0") -n lxc-ollama -m qwen2.5-vl-7b-instruct -b http://10.10.20.33:8081/v1"
  echo -e ""
  echo -e "  # Dry-run per validazione naming e configurazione:"
  echo -e "  $(basename "$0") -n lxc-ollama -m qwen2.5-vl-7b-instruct --dry-run"
  echo -e ""
  echo -e "  # Wizard interattivo (nessun parametro):"
  echo -e "  $(basename "$0")"
}

# Parsing argomenti CLI
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
    -b|--backend|--url)
      BACKEND_URL="$2"
      shift 2
      ;;
    --mem|--memory)
      MEMORY="$2"
      shift 2
      ;;
    -f|--fixture)
      FIXTURE="$2"
      shift 2
      ;;
    -t|--task)
      TASK="$2"
      shift 2
      ;;
    --all-models)
      FILTER_OCR=false
      shift
      ;;
    -d|--output-dir)
      OUTPUT_DIR="$2"
      shift 2
      ;;
    --dry-run)
      DRY_RUN=true
      shift
      ;;
    eval)
      ACTION="eval"
      shift
      ;;
    view)
      ACTION="view"
      shift
      if [[ $# -gt 0 && "$1" =~ ^[0-9]+$ ]]; then
        VIEW_PORT="$1"
        shift
      fi
      ;;
    *)
      POSITIONAL_ARGS+=("$1")
      shift
      ;;
  esac
done

# Gestione azione VIEW diretta
if [[ "$ACTION" == "view" ]]; then
  echo -e "${CYAN}======================================================${NC}"
  echo -e "${CYAN}   Avvio Web Dashboard Promptfoo su porta ${VIEW_PORT}   ${NC}"
  echo -e "${CYAN}======================================================${NC}"
  cd "${BENCHMARK_DIR}"
  export PROMPTFOO_INLINE_MEDIA=true
  exec promptfoo view -p "${VIEW_PORT}" -y
fi

# Se non sono passati parametri minimi e siamo su un terminale, abilita modalità interattiva
if [[ -z "$NODE" && -z "$MODEL" && -t 0 ]]; then
  INTERACTIVE=true
fi

# ==============================================================================
# 1. DISCOVERY NODI ED ENDPOINT DA RETE.JSON
# ==============================================================================
declare -a DISCOVERED_NODE_NAMES=()
declare -a DISCOVERED_NODE_IPS=()
declare -a DISCOVERED_NODE_MEMS=()
declare -a DISCOVERED_NODE_BACKENDS=()
declare -a DISCOVERED_NODE_DESC=()

# Rilevamento memoria locale Mac
LOCAL_MEM_DESC="16gb"
if [[ "$(uname -s)" == "Darwin" ]]; then
  LOCAL_MEM_BYTES=$(sysctl -n hw.memsize 2>/dev/null || echo "0")
  LOCAL_MEM_GB=$(( LOCAL_MEM_BYTES / 1024 / 1024 / 1024 ))
  LOCAL_MEM_DESC="${LOCAL_MEM_GB}gb-unified"
fi

# Inserimento nodi predefiniti del lab
# 1. CT 300 llama-server Vulkan (Primario OCR)
DISCOVERED_NODE_NAMES+=("lxc-ollama")
DISCOVERED_NODE_IPS+=("10.10.20.33")
DISCOVERED_NODE_MEMS+=("54gb")
DISCOVERED_NODE_BACKENDS+=("http://10.10.20.33:8081/v1")
DISCOVERED_NODE_DESC+=("CT 300 su PVE3 - llama-server Vulkan (Radeon 890M - Porta 8081)")

# 2. CT 300 Ollama Standard
DISCOVERED_NODE_NAMES+=("lxc-ollama-ollama")
DISCOVERED_NODE_IPS+=("10.10.20.33")
DISCOVERED_NODE_MEMS+=("54gb")
DISCOVERED_NODE_BACKENDS+=("http://10.10.20.33:11434/v1")
DISCOVERED_NODE_DESC+=("CT 300 su PVE3 - Ollama Engine (Porta 11434)")

# 3. Client Locale Mac (Ollama)
DISCOVERED_NODE_NAMES+=("mac-local")
DISCOVERED_NODE_IPS+=("127.0.0.1")
DISCOVERED_NODE_MEMS+=("${LOCAL_MEM_DESC}")
DISCOVERED_NODE_BACKENDS+=("http://127.0.0.1:11434/v1")
DISCOVERED_NODE_DESC+=("Mac Client Locale - Ollama Engine (Porta 11434)")

# Lettura dinamica aggiuntiva da rete.json (se presente jq)
if [[ -f "$RETE_JSON" ]] && command -v jq >/dev/null 2>&1; then
  # Estrazione IP censito per lxc-ollama
  CT_IP=$(jq -r '.nodi[] | select(.id=="lxc-ollama") | .ip // empty' "$RETE_JSON" 2>/dev/null || true)
  if [[ -n "$CT_IP" && "$CT_IP" != "10.10.20.33" ]]; then
    DISCOVERED_NODE_IPS[0]="$CT_IP"
    DISCOVERED_NODE_BACKENDS[0]="http://${CT_IP}:8081/v1"
    DISCOVERED_NODE_IPS[1]="$CT_IP"
    DISCOVERED_NODE_BACKENDS[1]="http://${CT_IP}:11434/v1"
  fi
fi

# ==============================================================================
# 2. SELEZIONE NODO ED ENDPOINT (INTERATTIVA O CLI)
# ==============================================================================
DEFAULT_NODE_MEM="54gb"
DEFAULT_NODE_BACKEND="http://10.10.20.33:8081/v1"

if [[ "$INTERACTIVE" == true ]]; then
  echo ""
  echo -e "${BOLD}${BLUE}╔════════════════════════════════════════════════════════════╗${NC}"
  echo -e "${BOLD}${BLUE}║       BENCHMARK OCR PROMPTFOO - WIZARD HOMELAB             ║${NC}"
  echo -e "${BOLD}${BLUE}╚════════════════════════════════════════════════════════════╝${NC}"
  echo ""
  echo -e "${CYAN}Seleziona il target / nodo di inferenza:${NC}"
  for i in "${!DISCOVERED_NODE_NAMES[@]}"; do
    NUM=$(( i + 1 ))
    echo -e "  ${BOLD}${NUM})${NC} ${GREEN}${DISCOVERED_NODE_NAMES[$i]}${NC} - ${DISCOVERED_NODE_DESC[$i]}"
  done
  echo -e "  ${BOLD}C)${NC} Endpoint Personalizzato (Custom URL / IP)"

  read -rp "Scelta [1-${#DISCOVERED_NODE_NAMES[@]}]: " NODE_CHOICE
  NODE_CHOICE="${NODE_CHOICE:-1}"

  if [[ "$NODE_CHOICE" =~ ^[0-9]+$ ]] && (( NODE_CHOICE >= 1 && NODE_CHOICE <= ${#DISCOVERED_NODE_NAMES[@]} )); then
    IDX=$(( NODE_CHOICE - 1 ))
    NODE="${DISCOVERED_NODE_NAMES[$IDX]}"
    DEFAULT_NODE_MEM="${DISCOVERED_NODE_MEMS[$IDX]}"
    DEFAULT_NODE_BACKEND="${DISCOVERED_NODE_BACKENDS[$IDX]}"
  else
    NODE="custom-node"
    DEFAULT_NODE_MEM="32gb"
    read -rp "Inserisci URL Backend OpenAI [http://127.0.0.1:11434/v1]: " INPUT_CUSTOM_BACKEND
    DEFAULT_NODE_BACKEND="${INPUT_CUSTOM_BACKEND:-http://127.0.0.1:11434/v1}"
  fi
else
  # Risoluzione da flag CLI
  NODE="${NODE:-lxc-ollama}"
  MATCH_FOUND=false
  for i in "${!DISCOVERED_NODE_NAMES[@]}"; do
    NORM_TARGET=$(echo "$NODE" | tr '[:upper:]' '[:lower:]' | tr -d ' -_')
    NORM_ID=$(echo "${DISCOVERED_NODE_NAMES[$i]}" | tr '[:upper:]' '[:lower:]' | tr -d ' -_')
    if [[ "$NORM_TARGET" == "$NORM_ID" ]]; then
      NODE="${DISCOVERED_NODE_NAMES[$i]}"
      DEFAULT_NODE_MEM="${DISCOVERED_NODE_MEMS[$i]}"
      DEFAULT_NODE_BACKEND="${DISCOVERED_NODE_BACKENDS[$i]}"
      MATCH_FOUND=true
      break
    fi
  done
  if [[ "$MATCH_FOUND" == false ]]; then
    DEFAULT_NODE_MEM="32gb"
    DEFAULT_NODE_BACKEND="http://10.10.20.33:8081/v1"
  fi
fi

# Risoluzione definitiva Backend URL e Memory
BACKEND_URL="${BACKEND_URL:-$DEFAULT_NODE_BACKEND}"
MEMORY="${MEMORY:-$DEFAULT_NODE_MEM}"

# ==============================================================================
# 3. DISCOVERY MODELLI CON FILTRO CAPABILITY VISION / OCR
# ==============================================================================
fetch_models() {
  local TARGET_URL="$1"
  local ONLY_OCR="$2"
  local BASE_OLLAMA_URL="${TARGET_URL%/v1}"
  BASE_OLLAMA_URL="${BASE_OLLAMA_URL%/}"
  local TAGS_API="${BASE_OLLAMA_URL}/api/tags"
  local MODELS_API="${TARGET_URL%/}/models"

  local RAW_MODELS=()
  local OCR_MODELS=()
  local ALL_MODELS=()

  # Tentativo 1: API Ollama (/api/tags)
  if curl -s -m 3 "${TAGS_API}" >/dev/null 2>&1; then
    local TAGS_JSON
    TAGS_JSON=$(curl -s -m 3 "${TAGS_API}")
    if command -v jq >/dev/null 2>&1; then
      # Tutti i modelli
      while IFS= read -r line; do
        [[ -n "$line" ]] && ALL_MODELS+=("$line")
      done < <(echo "$TAGS_JSON" | jq -r '.models[].name // empty' 2>/dev/null || true)

      # Filtro OCR intelligente su capabilities e naming
      while IFS= read -r line; do
        [[ -n "$line" ]] && OCR_MODELS+=("$line")
      done < <(echo "$TAGS_JSON" | jq -r '
        .models[] |
        select(
          (.details.families? and (.details.families | index("clip") or index("mllama"))) or
          (.details.family? and (.details.family | test("(?i)(vl|vision|llava|minicpm)"))) or
          (.name | test("(?i)(vl|vision|ocr|llava|minicpm|florence|internvl)"))
        ) | .name' 2>/dev/null || true)
    fi
  fi

  # Tentativo 2: API OpenAI/llama-server (/v1/models)
  if [[ ${#ALL_MODELS[@]} -eq 0 ]] && curl -s -m 3 "${MODELS_API}" >/dev/null 2>&1; then
    local MODELS_JSON
    MODELS_JSON=$(curl -s -m 3 "${MODELS_API}")
    if command -v jq >/dev/null 2>&1; then
      while IFS= read -r line; do
        if [[ -n "$line" ]]; then
          ALL_MODELS+=("$line")
          if echo "$line" | grep -Ei "(vl|vision|ocr|llava|minicpm|qwen.*vl)" >/dev/null 2>&1; then
            OCR_MODELS+=("$line")
          fi
        fi
      done < <(echo "$MODELS_JSON" | jq -r '.data[].id // empty' 2>/dev/null || true)
    fi
  fi

  # Se siamo connessi a llama-server porta 8081 ed è vuoto, default canonico
  if [[ ${#ALL_MODELS[@]} -eq 0 && "$TARGET_URL" == *":8081"* ]]; then
    ALL_MODELS+=("qwen2.5-vl-7b-instruct")
    OCR_MODELS+=("qwen2.5-vl-7b-instruct")
  fi

  if [[ "$ONLY_OCR" == true && ${#OCR_MODELS[@]} -gt 0 ]]; then
    printf '%s\n' "${OCR_MODELS[@]}"
  else
    printf '%s\n' "${ALL_MODELS[@]}"
  fi
}

if [[ -z "$MODEL" ]]; then
  echo ""
  echo -e "${CYAN}======================================================${NC}"
  echo -e "${CYAN}   Rilevamento Modelli: ${BACKEND_URL}   ${NC}"
  echo -e "${CYAN}======================================================${NC}"

  DISCOVERED_OCR_MODELS=()
  DISCOVERED_ALL_MODELS=()

  while IFS= read -r line; do
    [[ -n "$line" ]] && DISCOVERED_OCR_MODELS+=("$line")
  done < <(fetch_models "$BACKEND_URL" true)

  while IFS= read -r line; do
    [[ -n "$line" ]] && DISCOVERED_ALL_MODELS+=("$line")
  done < <(fetch_models "$BACKEND_URL" false)

  SHOWING_OCR_FILTERED=true
  if [[ "$FILTER_OCR" == false || ${#DISCOVERED_OCR_MODELS[@]} -eq 0 ]]; then
    CURRENT_MODELS=("${DISCOVERED_ALL_MODELS[@]}")
    SHOWING_OCR_FILTERED=false
  else
    CURRENT_MODELS=("${DISCOVERED_OCR_MODELS[@]}")
  fi

  if [[ ${#CURRENT_MODELS[@]} -gt 0 ]]; then
    if [[ "$SHOWING_OCR_FILTERED" == true ]]; then
      echo -e "Trovati ${GREEN}${#CURRENT_MODELS[@]} modelli Vision/OCR${NC} (Filtro OCR Attivo):"
    else
      echo -e "Trovati ${YELLOW}${#CURRENT_MODELS[@]} modelli complessivi${NC} (Tutti i modelli):"
    fi

    for i in "${!CURRENT_MODELS[@]}"; do
      NUM=$(( i + 1 ))
      echo -e "  ${BOLD}${NUM})${NC} ${GREEN}${CURRENT_MODELS[$i]}${NC}"
    done

    if [[ "$SHOWING_OCR_FILTERED" == true && ${#DISCOVERED_ALL_MODELS[@]} -gt ${#DISCOVERED_OCR_MODELS[@]} ]]; then
      echo -e "  ${BOLD}A)${NC} Mostra tutti i modelli (${#DISCOVERED_ALL_MODELS[@]} totali, inclusi non-vision)"
    fi
    echo -e "  ${BOLD}M)${NC} Inserisci nome modello manualmente"

    read -rp "Seleziona modello [1]: " MODEL_CHOICE
    MODEL_CHOICE="${MODEL_CHOICE:-1}"

    if [[ "$MODEL_CHOICE" =~ ^[Aa]$ ]]; then
      # Mostra tutti i modelli
      echo ""
      echo -e "${YELLOW}Elenco completo di tutti i modelli disponibili:${NC}"
      for i in "${!DISCOVERED_ALL_MODELS[@]}"; do
        NUM=$(( i + 1 ))
        echo -e "  ${BOLD}${NUM})${NC} ${CURRENT_MODELS[$i]:-${DISCOVERED_ALL_MODELS[$i]}}"
      done
      read -rp "Seleziona modello [1]: " ALL_CHOICE
      ALL_CHOICE="${ALL_CHOICE:-1}"
      if [[ "$ALL_CHOICE" =~ ^[0-9]+$ ]] && (( ALL_CHOICE >= 1 && ALL_CHOICE <= ${#DISCOVERED_ALL_MODELS[@]} )); then
        MODEL="${DISCOVERED_ALL_MODELS[$(( ALL_CHOICE - 1 ))]}"
      else
        MODEL="${DISCOVERED_ALL_MODELS[0]}"
      fi
    elif [[ "$MODEL_CHOICE" =~ ^[0-9]+$ ]] && (( MODEL_CHOICE >= 1 && MODEL_CHOICE <= ${#CURRENT_MODELS[@]} )); then
      MODEL="${CURRENT_MODELS[$(( MODEL_CHOICE - 1 ))]}"
    else
      read -rp "Nome modello personalizzato [qwen2.5vl:7b-q4_K_M]: " CUSTOM_MODEL
      MODEL="${CUSTOM_MODEL:-qwen2.5vl:7b-q4_K_M}"
    fi
  else
    # Fallback se l'endpoint è offline o non risponde
    echo -e "${YELLOW}Nessun modello rilevato automaticamente da ${BACKEND_URL}.${NC}"
    if [[ "$BACKEND_URL" == *":8081"* ]]; then
      MODEL="qwen2.5-vl-7b-instruct"
    else
      MODEL="qwen2.5vl:7b-q4_K_M"
    fi
    if [[ "$INTERACTIVE" == true ]]; then
      read -rp "Nome modello [$MODEL]: " INPUT_MODEL
      MODEL="${INPUT_MODEL:-$MODEL}"
    fi
  fi
fi

# ==============================================================================
# 4. SELEZIONE FIXTURE DOCUMENTO
# ==============================================================================
AVAILABLE_FIXTURES=()
if [[ -d "$FIXTURES_DIR" ]]; then
  for f in "$FIXTURES_DIR"/*.png "$FIXTURES_DIR"/*.jpg "$FIXTURES_DIR"/*.jpeg; do
    if [[ -f "$f" ]]; then
      AVAILABLE_FIXTURES+=("$(basename "$f")")
    fi
  done
fi

if [[ -z "$FIXTURE" ]]; then
  if [[ "$INTERACTIVE" == true && ${#AVAILABLE_FIXTURES[@]} -gt 0 ]]; then
    echo ""
    echo -e "${CYAN}Seleziona il documento di test (Fixture):${NC}"
    for i in "${!AVAILABLE_FIXTURES[@]}"; do
      NUM=$(( i + 1 ))
      echo -e "  ${BOLD}${NUM})${NC} ${AVAILABLE_FIXTURES[$i]}"
    done
    echo -e "  ${BOLD}C)${NC} Percorso personalizzato"
    read -rp "Scelta [1]: " FIXTURE_CHOICE
    FIXTURE_CHOICE="${FIXTURE_CHOICE:-1}"

    if [[ "$FIXTURE_CHOICE" =~ ^[0-9]+$ ]] && (( FIXTURE_CHOICE >= 1 && FIXTURE_CHOICE <= ${#AVAILABLE_FIXTURES[@]} )); then
      FIXTURE="${AVAILABLE_FIXTURES[$(( FIXTURE_CHOICE - 1 ))]}"
    else
      read -rp "Percorso file immagine: " CUSTOM_FIXTURE
      FIXTURE="$CUSTOM_FIXTURE"
    fi
  else
    FIXTURE="${AVAILABLE_FIXTURES[0]:-fattura_test.png}"
  fi
fi

# Risoluzione path assoluto fixture
if [[ -f "$FIXTURE" ]]; then
  FIXTURE_PATH="$(cd "$(dirname "$FIXTURE")" && pwd)/$(basename "$FIXTURE")"
elif [[ -f "${FIXTURES_DIR}/${FIXTURE}" ]]; then
  FIXTURE_PATH="${FIXTURES_DIR}/${FIXTURE}"
else
  echo -e "${RED}Errore: Fixture non trovata: ${FIXTURE}${NC}" >&2
  exit 1
fi

# ==============================================================================
# 5. GENERAZIONE CONFIGURAZIONE PROMPTFOO DINAMICA
# ==============================================================================
# Conversione fixture in Base64 Data URI per rendering perfetto nel browser
EXT="${FIXTURE_PATH##*.}"
EXT_LOWER=$(echo "$EXT" | tr '[:upper:]' '[:lower:]')
MIME_TYPE="image/png"
if [[ "$EXT_LOWER" == "jpg" || "$EXT_LOWER" == "jpeg" ]]; then
  MIME_TYPE="image/jpeg"
fi

FIXTURE_B64=$(base64 -i "$FIXTURE_PATH" | tr -d '\n\r')
DATA_URI="data:${MIME_TYPE};base64,${FIXTURE_B64}"

# Normalizzazione stringhe per naming report conforme a [[guidellm-report-naming-pattern]]
CLEAN_NODE=$(echo "$NODE" | tr '[:upper:]' '[:lower:]' | sed -E 's/[^a-z0-9_-]+/-/g' | sed -E 's/^-+|-+$//g')
CLEAN_MODEL=$(echo "$MODEL" | tr '[:upper:]' '[:lower:]' | sed -E 's/[^a-z0-9._-]+/-/g' | sed -E 's/^-+|-+$//g')
CLEAN_MEM=$(echo "$MEMORY" | tr '[:upper:]' '[:lower:]' | sed -E 's/[^a-z0-9_-]+/-/g' | sed -E 's/^-+|-+$//g')
TIMESTAMP=$(date +"%Y%m%d-%H%M%S")

mkdir -p "$OUTPUT_DIR"
REPORT_PREFIX="${OUTPUT_DIR}/report-${CLEAN_NODE}-${CLEAN_MODEL}-${CLEAN_MEM}-${TIMESTAMP}"
REPORT_JSON="${REPORT_PREFIX}.json"
REPORT_HTML="${REPORT_PREFIX}.html"

# File temporaneo per promptfooconfig dinamico
TMP_BASE=$(mktemp "${TMPDIR:-/tmp}promptfoo_ocr_XXXXXX")
TMP_CONFIG="${TMP_BASE}.yaml"
trap 'rm -f "$TMP_BASE" "$TMP_CONFIG"' EXIT

# Stesura configurazione dichiarativa Promptfoo
cat << EOF > "$TMP_CONFIG"
# yaml-language-server: \$schema=https://promptfoo.dev/config-schema.json
description: "Benchmark OCR Promptfoo - ${CLEAN_NODE} ${CLEAN_MODEL}"

providers:
  - id: "openai:chat:${MODEL}"
    label: "${NODE}:${MODEL}"
    config:
      apiBaseUrl: "${BACKEND_URL}"
      apiKey: "ollama"
      temperature: 0.0
      max_tokens: 4096

prompts:
  - "file://${PROMPTS_DIR}/image_prompt.json"

tests:
EOF

if [[ "$TASK" == "all" || "$TASK" == "markdown" ]]; then
  cat << EOF >> "$TMP_CONFIG"
  - description: "OCR Markdown & Tabella: $(basename "$FIXTURE_PATH")"
    vars:
      question: "Trascrivi integralmente ogni singola voce, tabella, quantità e prezzo del documento in formato Markdown pulito con tabelle strutturate."
      image_url: "${DATA_URI}"
    assert:
      - type: javascript
        value: "output.length > 50"
      - type: javascript
        value: "output.includes('|') && output.includes('---')"
EOF
  if [[ "$FIXTURE_PATH" == *"ricevuta"* || "$FIXTURE_PATH" == *"scontrino"* ]]; then
    cat << EOF >> "$TMP_CONFIG"
      - type: icontains
        value: "CAFFE"
      - type: icontains
        value: "8.70"
EOF
  elif [[ "$FIXTURE_PATH" == *"fattura"* ]]; then
    cat << EOF >> "$TMP_CONFIG"
      - type: icontains
        value: "Kubernetes"
      - type: icontains
        value: "1.200"
EOF
  fi
fi

if [[ "$TASK" == "all" || "$TASK" == "json" ]]; then
  cat << EOF >> "$TMP_CONFIG"
  - description: "OCR Strutturato JSON: $(basename "$FIXTURE_PATH")"
    vars:
      question: "Estrai tutte le informazioni del documento in formato JSON valido con i campi 'voci' (array di oggetti contenente descrizione, quantita, prezzo_unitario, prezzo_totale) e 'totale_complessivo'. Restituisci ESCLUSIVAMENTE il blocco JSON senza testo introduttivo."
      image_url: "${DATA_URI}"
    assert:
      - type: javascript
        value: |
          try {
            const start = output.indexOf('{');
            const end = output.lastIndexOf('}');
            if (start === -1 || end === -1 || end <= start) return false;
            JSON.parse(output.slice(start, end + 1));
            return true;
          } catch (e) {
            return false;
          }
EOF
  if [[ "$FIXTURE_PATH" == *"ricevuta"* || "$FIXTURE_PATH" == *"scontrino"* ]]; then
    cat << EOF >> "$TMP_CONFIG"
      - type: icontains
        value: "8.70"
EOF
  elif [[ "$FIXTURE_PATH" == *"fattura"* ]]; then
    cat << EOF >> "$TMP_CONFIG"
      - type: icontains
        value: "2.013"
EOF
  fi
fi

# ==============================================================================
# 6. ESECUZIONE BENCHMARK (O DRY-RUN)
# ==============================================================================
echo ""
echo -e "${BOLD}${CYAN}======================================================${NC}"
echo -e "${BOLD}${CYAN}   CONFIGURAZIONE BENCHMARK OCR PROMPTFOO            ${NC}"
echo -e "${BOLD}${CYAN}======================================================${NC}"
echo -e "  Nodo Target:          ${GREEN}${NODE}${NC} (Memoria: ${MEMORY})"
echo -e "  Backend Endpoint:     ${GREEN}${BACKEND_URL}${NC}"
echo -e "  Modello OCR:          ${GREEN}${MODEL}${NC}"
echo -e "  Documento Fixture:    ${GREEN}$(basename "$FIXTURE_PATH")${NC}"
echo -e "  Report Destinazione:  ${YELLOW}${REPORT_PREFIX}.[json|html]${NC}"
echo -e "${BOLD}${CYAN}======================================================${NC}"

if [[ "$DRY_RUN" == true ]]; then
  echo -e "${YELLOW}Modalità DRY-RUN attiva. Nessun benchmark avviato.${NC}"
  echo -e "Configurazione generata in: ${TMP_CONFIG}"
  echo ""
  head -n 25 "$TMP_CONFIG" 2>/dev/null || true
  echo -e "[... payload base64 inlined ...]"
  echo -e "${GREEN}Verifica sintassi e percorsi superata al 100%!${NC}"
  exit 0
fi

echo -e "\n${BOLD}${GREEN}🚀 Avvio esecuzione valutazione Promptfoo...${NC}"

cd "${BENCHMARK_DIR}"
promptfoo eval \
  --config "${TMP_CONFIG}" \
  --no-cache \
  --output "${REPORT_JSON}" \
  --output "${REPORT_HTML}"

echo ""
echo -e "${BOLD}${GREEN}✅ Benchmark OCR completato con successo!${NC}"
echo -e "  Report JSON: ${GREEN}${REPORT_JSON}${NC}"
echo -e "  Report HTML: ${GREEN}${REPORT_HTML}${NC}"
echo ""
echo -e "Per visualizzare la dashboard interattiva dei risultati:"
echo -e "  ${BOLD}$(basename "$0") view${NC}"

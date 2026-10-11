#!/usr/bin/env bash
# ==============================================================================
# run_promptfoo.sh - Benchmark Runner per Suite OCR Promptfoo
# Homelab PVE3 / CT 300 - Qwen2.5-VL su llama-server vs Ollama
# ==============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WORKSPACE_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
REPORTS_DIR="${WORKSPACE_ROOT}/reports"
CONFIG_FILE="${SCRIPT_DIR}/promptfooconfig.yaml"

mkdir -p "${REPORTS_DIR}"

TIMESTAMP=$(date +"%Y%m%d-%H%M%S")
REPORT_JSON="${REPORTS_DIR}/report-lxc-ollama-ocr-promptfoo-54gb-${TIMESTAMP}.json"
REPORT_HTML="${REPORTS_DIR}/report-lxc-ollama-ocr-promptfoo-54gb-${TIMESTAMP}.html"

ACTION="${1:-eval}"

case "${ACTION}" in
  eval)
    echo "======================================================================"
    echo "🚀 Avvio Benchmark Promptfoo OCR Homelab"
    echo "   Config:  ${CONFIG_FILE}"
    echo "   Report:  ${REPORT_JSON}"
    echo "======================================================================"
    cd "${SCRIPT_DIR}"
    promptfoo eval \
      --config "${CONFIG_FILE}" \
      --output "${REPORT_JSON}" \
      --output "${REPORT_HTML}"
    echo "✅ Benchmark completato con successo!"
    echo "   Report JSON: ${REPORT_JSON}"
    echo "   Report HTML: ${REPORT_HTML}"
    ;;
  view)
    PORT="${2:-15500}"
    echo "🌐 Avvio Dashboard Web Promptfoo su porta ${PORT}..."
    cd "${SCRIPT_DIR}"
    promptfoo view -p "${PORT}"
    ;;
  *)
    echo "Uso: $0 [eval|view] [porta_per_view]"
    exit 1
    ;;
esac

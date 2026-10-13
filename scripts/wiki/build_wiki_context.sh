#!/usr/bin/env bash
# Generazione e compilazione del file di contesto Markdown per LLM (wiki_context.md)
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"
cd "$ROOT_DIR"

exec python3 "$SCRIPT_DIR/build_wiki_context.py" "$@"

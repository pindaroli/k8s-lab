#!/bin/bash
set -euo pipefail

DOCKER_CMD="docker"
if ! docker info >/dev/null 2>&1; then
    DOCKER_CMD="sudo docker"
fi

# Locate directories whether run from repo root, docker/mcp/, or /mnt/stripe/truenas-docker/mcp/
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if [ -d "$SCRIPT_DIR/ragflow-mcp" ]; then
    RAGFLOW_DIR="$SCRIPT_DIR/ragflow-mcp"
elif [ -d "$SCRIPT_DIR/../ragflow-mcp" ]; then
    RAGFLOW_DIR="$SCRIPT_DIR/../ragflow-mcp"
else
    echo "ERROR: ragflow-mcp directory not found relative to $SCRIPT_DIR" >&2
    exit 1
fi

if [ -d "$SCRIPT_DIR/arrstack-mcp" ]; then
    ARRSTACK_DIR="$SCRIPT_DIR/arrstack-mcp"
elif [ -d "$SCRIPT_DIR/../arrstack-mcp" ]; then
    ARRSTACK_DIR="$SCRIPT_DIR/../arrstack-mcp"
else
    echo "ERROR: arrstack-mcp directory not found relative to $SCRIPT_DIR" >&2
    exit 1
fi

echo "==> Building local/talos-mcp:latest..."
printf 'FROM ghcr.io/pindaroli/talos-mcp:2.5.1 AS bin\nFROM supercorp/supergateway:latest\nCOPY --from=bin /usr/local/bin/talos-mcp /usr/local/bin/talos-mcp\nENTRYPOINT ["supergateway", "--port", "8080", "--outputTransport", "streamableHttp", "--streamableHttpPath", "/mcp", "--healthEndpoint", "/healthz", "--stdio", "/usr/local/bin/talos-mcp"]\n' | $DOCKER_CMD build -t local/talos-mcp:latest -

echo "==> Building local/truenas-master-mcp:latest..."
printf 'FROM ghcr.io/pindaroli/truenas-master-mcp:1.0.0-alpha.1 AS bin\nFROM supercorp/supergateway:latest\nCOPY --from=bin /usr/local/bin/truenas-master-mcp /usr/local/bin/truenas-master-mcp\nENTRYPOINT ["supergateway", "--port", "8080", "--outputTransport", "streamableHttp", "--streamableHttpPath", "/mcp", "--healthEndpoint", "/healthz", "--stdio", "truenas-master-mcp"]\n' | $DOCKER_CMD build -t local/truenas-master-mcp:latest -

echo "==> Building local/github-mcp-server:latest..."
printf 'FROM ghcr.io/github/github-mcp-server:latest AS bin\nFROM supercorp/supergateway:latest\nCOPY --from=bin /server/github-mcp-server /usr/local/bin/github-mcp-server\nENTRYPOINT ["supergateway", "--port", "8080", "--outputTransport", "streamableHttp", "--streamableHttpPath", "/mcp", "--healthEndpoint", "/healthz", "--stdio", "/usr/local/bin/github-mcp-server stdio"]\n' | $DOCKER_CMD build -t local/github-mcp-server:latest -

echo "==> Building local/opnsense-mcp:latest..."
printf 'FROM ghcr.io/pindaroli/opnsense-mcp:0.5.3\nUSER root\nRUN npm install -g supergateway\nUSER node\nENTRYPOINT ["supergateway", "--port", "8080", "--outputTransport", "streamableHttp", "--streamableHttpPath", "/mcp", "--healthEndpoint", "/healthz", "--stdio", "opnsense-mcp-server"]\n' | $DOCKER_CMD build -t local/opnsense-mcp:latest -

echo "==> Building local/ollama-mcp:latest..."
printf 'FROM ghcr.io/pindaroli/ollama-mcp:2.1.0\nUSER root\nRUN npm install -g supergateway\nUSER node\nENTRYPOINT ["supergateway", "--port", "8080", "--outputTransport", "streamableHttp", "--streamableHttpPath", "/mcp", "--healthEndpoint", "/healthz", "--stdio", "ollama-mcp"]\n' | $DOCKER_CMD build -t local/ollama-mcp:latest -

echo "==> Building local/nowaikit-mcp:latest..."
printf 'FROM ghcr.io/pindaroli/nowaikit-mcp:4.15.1\nUSER root\nRUN npm install -g supergateway\nUSER node\nENTRYPOINT ["supergateway", "--port", "8080", "--outputTransport", "streamableHttp", "--streamableHttpPath", "/mcp", "--healthEndpoint", "/healthz", "--stdio", "nowaikit-mcp"]\n' | $DOCKER_CMD build -t local/nowaikit-mcp:latest -

echo "==> Building local/arrstack-mcp:1.1.0..."
$DOCKER_CMD build -t local/arrstack-mcp:1.1.0 "$ARRSTACK_DIR"

echo "==> Building local/ragflow-mcp:latest..."
$DOCKER_CMD build -t local/ragflow-mcp:latest "$RAGFLOW_DIR"

echo "==> All local MCP images built successfully!"

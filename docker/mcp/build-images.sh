#!/bin/bash
set -euo pipefail

echo "==> Building local/talos-mcp:latest..."
printf 'FROM ghcr.io/pindaroli/talos-mcp:2.5.1 AS bin\nFROM supercorp/supergateway:latest\nCOPY --from=bin /usr/local/bin/talos-mcp /usr/local/bin/talos-mcp\nENTRYPOINT ["supergateway", "--port", "8080", "--ssePath", "/mcp", "--messagePath", "/message", "--stdio", "/usr/local/bin/talos-mcp"]\n' | docker build -t local/talos-mcp:latest -

echo "==> Building local/truenas-master-mcp:latest..."
printf 'FROM ghcr.io/pindaroli/truenas-master-mcp:1.0.0-alpha.1 AS bin\nFROM supercorp/supergateway:latest\nCOPY --from=bin /usr/local/bin/truenas-master-mcp /usr/local/bin/truenas-master-mcp\nENTRYPOINT ["supergateway", "--port", "8080", "--ssePath", "/mcp", "--messagePath", "/message", "--stdio", "truenas-master-mcp"]\n' | docker build -t local/truenas-master-mcp:latest -

echo "==> Building local/github-mcp-server:latest..."
printf 'FROM ghcr.io/github/github-mcp-server:latest AS bin\nFROM supercorp/supergateway:latest\nCOPY --from=bin /server/github-mcp-server /usr/local/bin/github-mcp-server\nENTRYPOINT ["supergateway", "--port", "8080", "--ssePath", "/mcp", "--messagePath", "/message", "--stdio", "/usr/local/bin/github-mcp-server stdio"]\n' | docker build -t local/github-mcp-server:latest -

echo "==> Building local/opnsense-mcp:latest..."
printf 'FROM ghcr.io/pindaroli/opnsense-mcp:0.5.3\nUSER root\nRUN npm install -g supergateway\nUSER node\nENTRYPOINT ["supergateway", "--port", "8080", "--ssePath", "/mcp", "--messagePath", "/message", "--stdio", "opnsense-mcp-server"]\n' | docker build -t local/opnsense-mcp:latest -

echo "==> Building local/ollama-mcp:latest..."
printf 'FROM ghcr.io/pindaroli/ollama-mcp:2.1.0\nUSER root\nRUN npm install -g supergateway\nUSER node\nENTRYPOINT ["supergateway", "--port", "8080", "--ssePath", "/mcp", "--messagePath", "/message", "--stdio", "ollama-mcp"]\n' | docker build -t local/ollama-mcp:latest -

echo "==> Building local/nowaikit-mcp:latest..."
printf 'FROM ghcr.io/pindaroli/nowaikit-mcp:4.15.1\nUSER root\nRUN npm install -g supergateway\nUSER node\nENTRYPOINT ["supergateway", "--port", "8080", "--ssePath", "/mcp", "--messagePath", "/message", "--stdio", "nowaikit-mcp"]\n' | docker build -t local/nowaikit-mcp:latest -

echo "==> All local MCP images built successfully!"

FROM node:22-alpine

WORKDIR /app

ARG OLLAMA_MCP_VERSION=2.1.0

# Install ollama-mcp globally (pinned to latest official stable release)
RUN npm install -g ollama-mcp@${OLLAMA_MCP_VERSION}

# Use unprivileged node user
USER node

# ToolHive executes the container and communicates via stdio
ENTRYPOINT ["ollama-mcp"]

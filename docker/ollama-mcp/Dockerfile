FROM node:22-alpine

WORKDIR /app

# Install ollama-mcp globally
RUN npm install -g ollama-mcp@2.1.0

# Use unprivileged node user
USER node

# ToolHive executes the container and communicates via stdio
ENTRYPOINT ["ollama-mcp"]

FROM node:22-alpine

WORKDIR /app

ARG OPNSENSE_MCP_VERSION=0.5.3

# Install @richard-stovall/opnsense-mcp-server globally (pinned to latest official stable release)
RUN npm install -g @richard-stovall/opnsense-mcp-server@${OPNSENSE_MCP_VERSION}

# Use unprivileged node user
USER node

# ToolHive executes the container and communicates via stdio
ENTRYPOINT ["opnsense-mcp-server"]

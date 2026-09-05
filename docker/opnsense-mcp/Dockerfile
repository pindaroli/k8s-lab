FROM node:22-alpine

WORKDIR /app

# Install @richard-stovall/opnsense-mcp-server globally
RUN npm install -g @richard-stovall/opnsense-mcp-server@0.5.3

# Use unprivileged node user
USER node

# ToolHive executes the container and communicates via stdio
ENTRYPOINT ["opnsense-mcp-server"]

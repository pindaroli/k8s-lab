FROM node:22-alpine

WORKDIR /app

# Build-time argument for strict version pinning (never use @latest)
ARG APP_VERSION=1.0.0

# Install the MCP server globally from official npm registry
RUN npm install -g <package-name>@${APP_VERSION}

# Drop privileges to standard non-root user (UID 1000)
USER node

# ToolHive executes the container and communicates via stdio
ENTRYPOINT ["<binary-name>"]

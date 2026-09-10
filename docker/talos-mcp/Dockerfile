FROM alpine:3.21

ARG APP_VERSION=2.5.1
ARG TARGETARCH=amd64

WORKDIR /app

# Install ca-certificates, curl, tar, extract binary and configure non-root user
RUN apk add --no-cache ca-certificates curl tar && \
    curl -fsSL "https://github.com/Nosmoht/talos-mcp-server/releases/download/v${APP_VERSION}/talos-mcp-server_${APP_VERSION}_linux_${TARGETARCH}.tar.gz" | tar -xz -C /usr/local/bin talos-mcp && \
    chmod +x /usr/local/bin/talos-mcp && \
    apk del curl tar && \
    rm -rf /var/cache/apk/* && \
    adduser -D -u 1000 -h /app talos

USER 1000

# ToolHive executes the container and communicates via stdio
ENTRYPOINT ["/usr/local/bin/talos-mcp"]

FROM alpine:3.21.3 AS fetcher
ARG TALOS_MCP_VERSION=2.5.1
RUN apk add --no-cache curl tar && \
    curl -fsSL "https://github.com/Nosmoht/talos-mcp-server/releases/download/v${TALOS_MCP_VERSION}/talos-mcp-server_${TALOS_MCP_VERSION}_linux_amd64.tar.gz" \
    | tar -xz -C /usr/local/bin talos-mcp && \
    chmod +x /usr/local/bin/talos-mcp

FROM node:22.14.0-alpine3.21
ARG SUPERGATEWAY_VERSION=4.1.0

RUN npm install -g "supergateway@${SUPERGATEWAY_VERSION}" && \
    npm cache clean --force

COPY --from=fetcher /usr/local/bin/talos-mcp /usr/local/bin/talos-mcp

USER node
WORKDIR /home/node

EXPOSE 8080

ENTRYPOINT [ \
  "supergateway", \
  "--port", "8080", \
  "--outputTransport", "streamableHttp", \
  "--streamableHttpPath", "/mcp", \
  "--healthEndpoint", "/healthz", \
  "--stateful", \
  "--cors", \
  "--stdio", "/usr/local/bin/talos-mcp" \
]

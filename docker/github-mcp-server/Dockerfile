ARG GITHUB_MCP_VERSION=v0.7.0
FROM ghcr.io/github/github-mcp-server:${GITHUB_MCP_VERSION} AS bin

FROM node:22.14.0-alpine3.21
ARG SUPERGATEWAY_VERSION=4.1.0

RUN npm install -g "supergateway@${SUPERGATEWAY_VERSION}" && \
    npm cache clean --force

COPY --from=bin /server/github-mcp-server /usr/local/bin/github-mcp-server

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
  "--stdio", "/usr/local/bin/github-mcp-server stdio" \
]

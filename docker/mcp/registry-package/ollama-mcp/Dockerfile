FROM node:22.14.0-alpine3.21

ARG SUPERGATEWAY_VERSION=4.1.0
ARG OLLAMA_MCP_VERSION=2.1.0

RUN npm install -g \
    "supergateway@${SUPERGATEWAY_VERSION}" \
    "ollama-mcp@${OLLAMA_MCP_VERSION}" && \
    npm cache clean --force

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
  "--stdio", "ollama-mcp" \
]

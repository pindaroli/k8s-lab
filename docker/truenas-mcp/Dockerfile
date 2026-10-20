FROM ghcr.io/pindaroli/truenas-master-mcp:1.0.0-alpha.1 AS bin

FROM node:22.14.0-alpine3.21
ARG SUPERGATEWAY_VERSION=4.1.0

RUN npm install -g "supergateway@${SUPERGATEWAY_VERSION}" && \
    npm cache clean --force

COPY --from=bin /usr/local/bin/truenas-master-mcp /usr/local/bin/truenas-master-mcp

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
  "--stdio", "/usr/local/bin/truenas-master-mcp" \
]

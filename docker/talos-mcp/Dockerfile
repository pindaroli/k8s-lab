FROM python:3.12-slim

ARG TALOS_VERSION=v1.13.5
ARG TARGETARCH=amd64

WORKDIR /app

# Install curl and ca-certificates
RUN apt-get update && \
    apt-get install -y --no-install-recommends curl ca-certificates && \
    curl -fsSL -o /usr/local/bin/talosctl "https://github.com/siderolabs/talos/releases/download/${TALOS_VERSION}/talosctl-linux-${TARGETARCH}" && \
    chmod +x /usr/local/bin/talosctl && \
    apt-get purge -y curl && \
    apt-get autoremove -y && \
    rm -rf /var/lib/apt/lists/*

# Install talos-mcp-server and dependencies
RUN pip install --no-cache-dir "talos-mcp-server==0.3.10" "mcp>=1.0.0,<2.0.0" pydantic

# Create non-root user and directories
RUN useradd -u 1000 -m -s /bin/bash talos && \
    mkdir -p /tmp/talos && \
    chown -R talos:talos /app /tmp/talos

# Copy wrapper script
COPY talos_mcp_wrapper.py /app/talos_mcp_wrapper.py
RUN chown talos:talos /app/talos_mcp_wrapper.py

USER talos

# ToolHive executes the container and communicates via stdio
ENTRYPOINT ["python", "/app/talos_mcp_wrapper.py"]

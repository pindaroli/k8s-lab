FROM python:3.12-slim

ARG ARRSTACK_REF=8da27d8466ab1fb067121fe2731fc8fdd1c13d7b

WORKDIR /app

# Prevent Python from writing .pyc files and buffer stdout/stderr
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Install git to clone repository
RUN apt-get update && apt-get install -y --no-install-recommends git && \
    rm -rf /var/lib/apt/lists/*

# Clone specific ref from fork and install package
RUN git clone https://github.com/pindaroli/arrstack-mcp.git /app && \
    git checkout ${ARRSTACK_REF} && \
    pip install --no-cache-dir . && \
    apt-get purge -y git && apt-get autoremove -y && rm -rf /var/lib/apt/lists/*

# Create unprivileged non-root user (UID 1000)
RUN useradd -u 1000 -m -s /bin/bash appuser && \
    chown -R appuser:appuser /app

USER appuser

# Default to FastMCP Streamable HTTP on port 8080 listening on all interfaces
ENTRYPOINT ["python", "-m", "arrstack_mcp"]
CMD ["--transport", "streamable-http", "--port", "8080", "--host", "0.0.0.0"]

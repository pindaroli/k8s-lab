FROM python:3.12-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Build-time argument for strict version pinning (never use floating versions)
ARG APP_VERSION=1.0.0

# Install the MCP server and pinned dependencies from PyPI
RUN pip install --no-cache-dir \
    "<package-name>==${APP_VERSION}" \
    "mcp==1.3.0" \
    "pydantic==2.10.6"

# Create non-root unprivileged user (UID 1000)
RUN useradd -u 1000 -m -s /bin/bash appuser && \
    chown -R appuser:appuser /app

USER appuser

# ToolHive executes the container and communicates via stdio
ENTRYPOINT ["python", "-m", "<module_name>"]

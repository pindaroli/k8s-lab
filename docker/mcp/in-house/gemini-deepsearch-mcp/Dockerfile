FROM python:3.12-slim

WORKDIR /app

# Prevent Python from writing .pyc files and buffer stdout/stderr
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Install Python dependencies
COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

# Create unprivileged non-root user (UID 1000)
RUN useradd -u 1000 -m -s /bin/bash appuser && \
    chown -R appuser:appuser /app

# Copy application package sources
COPY --chown=appuser:appuser src/ /app/gemini_deepsearch_mcp/

# Set PYTHONPATH so gemini_deepsearch_mcp package is importable
ENV PYTHONPATH=/app

USER appuser

# ToolHive executes the container and communicates via stdio
ENTRYPOINT ["python", "-m", "gemini_deepsearch_mcp.main"]

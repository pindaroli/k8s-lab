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

# Copy application source code
COPY --chown=appuser:appuser src/ /app/

ENV PYTHONPATH=/app

USER appuser

# Default to FastMCP SSE on port 8080 listening on all interfaces
ENTRYPOINT ["python", "/app/server.py"]
CMD ["--transport", "sse", "--port", "8080", "--host", "0.0.0.0"]
